#!/usr/bin/env python3
"""Evaluator for the BMTK PointNet agent-resource benchmark.

Three layers of scoring:

1. Artifact presence and parseability   (the agent produced runnable files)
2. SONATA / PointNet structural validity (config + node/edge types match what
   PointNet actually expects)
3. Anti-patterns                         (penalties when BioNet-only constructs
   leak into a PointNet project)

If a captured Cline task is present at `<trial>/cline_task/cline_metrics.json`,
its dynamic metrics are merged into the output but do not affect the score.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

# --- BioNet vs PointNet markers -------------------------------------------------

BIONET_EDGE_FIELDS = ("target_sections", "distance_range")
BIONET_SYNAPSE_TEMPLATES = {"exp2syn", "exp1syn", "alphasynapse"}
BIONET_CELL_TEMPLATE_PREFIXES = ("ctdb:", "nrn:")

POINTNET_CELL_TEMPLATE_PREFIX = "nest:"
POINTNET_SYNAPSE_TEMPLATE = "static_synapse"


# --- helpers --------------------------------------------------------------------

def _iter_project(root: Path, pattern: str):
    for p in root.rglob(pattern):
        if "cline_task" in p.parts or "agent_output" in p.parts:
            continue
        yield p


def find_first(root: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        for m in _iter_project(root, pattern):
            return m
    return None


def find_all(root: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        out.extend(_iter_project(root, pattern))
    return out


def py_parse(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def json_parse(path: Path):
    try:
        return True, json.loads(path.read_text(encoding="utf-8")), ""
    except Exception as e:
        return False, None, str(e)


def read_csv_sonata(path: Path) -> list[dict]:
    """SONATA *_node_types.csv / *_edge_types.csv are space-delimited."""
    try:
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh, delimiter=" "))
    except Exception:
        return []


# --- smoke test ----------------------------------------------------------------

CONDA_ENV = os.environ.get("BMTK_CONDA_ENV", "BXP2")
SMOKE_BUILD_TIMEOUT = int(os.environ.get("BMTK_SMOKE_BUILD_TIMEOUT", "180"))
SMOKE_LOAD_TIMEOUT = int(os.environ.get("BMTK_SMOKE_LOAD_TIMEOUT", "120"))


def _conda_run(cwd: Path, args: list[str], timeout: int) -> tuple[bool, str]:
    # Build a clean environment: drop PYTHONPATH (which on this host points
    # at /usr/lib/python3.8/dist-packages and shadows the env's own nest),
    # and prepend the env's lib dir to LD_LIBRARY_PATH so NEST can find
    # libgsl.so.23.
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env_lib = f"/home/dhaufler/anaconda3/envs/{CONDA_ENV}/lib"
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = f"{env_lib}:{existing}" if existing else env_lib

    cmd = ["conda", "run", "--no-capture-output", "-n", CONDA_ENV, *args]
    try:
        proc = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                              capture_output=True, text=True, env=env)
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except FileNotFoundError:
        return False, "conda not found on PATH"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        return False, f"exit {proc.returncode}: " + " | ".join(tail)
    return True, "ok"


def _smoke_test(root: Path, build_script: Path | None, run_script: Path | None) -> dict:
    """Actually try to build the network and load the simulation.

    - build: run the build script with a timeout; check it exits 0
    - h5:    after build, check that node/edge HDF5 files exist
    - run:   import bmtk.simulator.pointnet and load the config without
             stepping the simulation (avoids long sim runs while still
             verifying the project is wired up correctly)
    """
    result = {
        "build_ok": False, "build_detail": "no build_network.py",
        "h5_ok": False, "h5_detail": "",
        "run_loadable": False, "run_detail": "no config or run script",
    }
    if build_script is None:
        return result

    ok, detail = _conda_run(root, ["python", str(build_script.relative_to(root))],
                            SMOKE_BUILD_TIMEOUT)
    result["build_ok"] = ok
    result["build_detail"] = detail

    h5_files = list(_iter_project(root, "*.h5"))
    result["h5_ok"] = len(h5_files) > 0
    result["h5_detail"] = f"{len(h5_files)} HDF5 file(s) on disk"

    config = find_first(root, ["config.json", "config*.json", "simulation_config*.json"])
    if config is None or run_script is None:
        return result

    # Verify the project loads under PointNet without running the full sim.
    # Write the loader to a temp file to avoid shell/conda-run quote mangling.
    import tempfile
    loader_lines = [
        "from bmtk.simulator import pointnet",
        f"cfg = pointnet.Config.from_json({json.dumps(str(config.relative_to(root)))})",
        "cfg.build_env()",
        "net = pointnet.PointNetwork.from_config(cfg)",
        "sim = pointnet.PointSimulator.from_config(cfg, net)",
        "print('loaded')",
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=root) as tf:
        tf.write('\n'.join(loader_lines) + '\n')
        loader_path = Path(tf.name)
    try:
        ok, detail = _conda_run(root, ["python", loader_path.name], SMOKE_LOAD_TIMEOUT)
    finally:
        loader_path.unlink(missing_ok=True)
    result["run_loadable"] = ok
    result["run_detail"] = detail
    return result


# --- evaluation -----------------------------------------------------------------

def evaluate(root: Path) -> dict:
    score = 0
    max_score = 0
    checks: list[dict] = []

    def check(name: str, passed: bool, points: int, detail: str = "") -> None:
        nonlocal score, max_score
        max_score += points
        if passed:
            score += points
        checks.append({"name": name, "passed": bool(passed), "points": points,
                       "score": points if passed else 0, "detail": detail})

    def penalty(name: str, applies: bool, points: int, detail: str = "") -> None:
        """Penalty subtracts points from score but does not increase max_score."""
        nonlocal score
        checks.append({"name": name, "passed": not applies, "points": -points,
                       "score": -points if applies else 0, "detail": detail})
        if applies:
            score -= points

    # ---- 1. Artifact presence + parse ----
    build_script = find_first(root, ["build_network.py", "*build*.py"])
    run_script = find_first(root, ["run_pointnet.py", "run_simulation.py", "run*.py", "simulate*.py"])
    config = find_first(root, ["config.json", "config*.json", "simulation_config*.json"])

    check("build script exists", build_script is not None, 2, str(build_script or ""))
    check("run script exists", run_script is not None, 2, str(run_script or ""))
    check("config json exists", config is not None, 2, str(config or ""))

    check("build script parses", build_script is not None and py_parse(build_script), 2)
    check("run script parses", run_script is not None and py_parse(run_script), 2)

    config_data: dict | None = None
    if config:
        ok, data, detail = json_parse(config)
        check("config parses as json", ok, 2, detail)
        if ok and isinstance(data, dict):
            config_data = data
    else:
        check("config parses as json", False, 2, "missing")

    # ---- 2. SONATA / PointNet config structure ----
    cfg = config_data or {}
    has_networks = bool(cfg.get("networks") or cfg.get("network"))
    check("config has 'networks' section", has_networks, 2,
          "SONATA configs reference SONATA files under 'networks'.")
    check("config has 'manifest' section", isinstance(cfg.get("manifest"), dict), 1)
    check("config has 'components' section", isinstance(cfg.get("components"), dict), 2,
          "Required so dynamics_params filenames resolve to disk.")
    check("config has 'run' section", isinstance(cfg.get("run"), dict), 1)
    check("config has 'output' section", isinstance(cfg.get("output"), dict), 1)

    target_sim = (cfg.get("target_simulator") or "").upper()
    check("target_simulator is NEST", target_sim == "NEST", 2,
          f"got '{cfg.get('target_simulator')}'")

    run_cfg = cfg.get("run") if isinstance(cfg.get("run"), dict) else {}
    tstop = run_cfg.get("tstop") or run_cfg.get("duration")
    try:
        tstop_ok = float(tstop) == 5000.0
    except (TypeError, ValueError):
        tstop_ok = False
    check("simulation duration is 5000 ms", tstop_ok, 3, f"tstop={tstop}")

    # ---- 3. Network artifact presence ----
    node_types_csvs = find_all(root, ["*node_types*.csv"])
    edge_types_csvs = find_all(root, ["*edge_types*.csv"])
    node_h5s = find_all(root, ["*nodes*.h5"])
    edge_h5s = find_all(root, ["*edges*.h5"])

    check("node_types CSV files exist", bool(node_types_csvs), 1, f"{len(node_types_csvs)} found")
    check("edge_types CSV files exist", bool(edge_types_csvs), 1, f"{len(edge_types_csvs)} found")
    check("node HDF5 files exist", bool(node_h5s), 1, f"{len(node_h5s)} found")
    check("edge HDF5 files exist", bool(edge_h5s), 1, f"{len(edge_h5s)} found")

    # ---- 4. PointNet correctness (structural, not keyword) ----
    node_type_rows: list[dict] = []
    for p in node_types_csvs:
        node_type_rows.extend(read_csv_sonata(p))
    edge_type_rows: list[dict] = []
    for p in edge_types_csvs:
        edge_type_rows.extend(read_csv_sonata(p))

    pn_cells = bn_cells = 0
    for row in node_type_rows:
        mtype = (row.get("model_type") or "").lower()
        mtmpl = (row.get("model_template") or "").lower()
        # BMTK PointNet accepts both "point_process" and "point_neuron" as model_type
        if mtype in ("point_process", "point_neuron") and mtmpl.startswith(POINTNET_CELL_TEMPLATE_PREFIX):
            pn_cells += 1
        if mtype == "biophysical" or mtmpl.startswith(BIONET_CELL_TEMPLATE_PREFIXES):
            bn_cells += 1
    check("cell node types use PointNet conventions (point_process/point_neuron + nest:*)",
          pn_cells > 0 and bn_cells == 0, 3,
          f"point_process/point_neuron+nest: rows={pn_cells}, biophysical/ctdb/nrn rows={bn_cells}")

    pn_edges = bn_edges = 0
    bionet_edge_field_hits: set[str] = set()
    for row in edge_type_rows:
        mtmpl = (row.get("model_template") or "").lower()
        if mtmpl == POINTNET_SYNAPSE_TEMPLATE:
            pn_edges += 1
        if mtmpl in BIONET_SYNAPSE_TEMPLATES:
            bn_edges += 1
        for f in BIONET_EDGE_FIELDS:
            v = row.get(f)
            if v not in (None, "", "NULL", "nan"):
                bionet_edge_field_hits.add(f)
    check("edge types use 'static_synapse' template",
          pn_edges > 0 and bn_edges == 0, 3,
          f"static_synapse rows={pn_edges}, BioNet-template rows={bn_edges}")

    # ---- 5. dynamics_params files actually exist on disk ----
    referenced: list[str] = []
    for row in node_type_rows + edge_type_rows:
        dp = (row.get("dynamics_params") or "").strip()
        if dp and dp.lower() not in ("null", "nan"):
            referenced.append(dp)

    existing_json = {p.name for p in _iter_project(root, "*.json")}
    missing = [d for d in referenced if d not in existing_json]
    if referenced:
        check("referenced dynamics_params files exist on disk",
              not missing, 2, f"missing={missing}" if missing else "all present")
    else:
        check("referenced dynamics_params files exist on disk", False, 2,
              "no dynamics_params referenced in node/edge type CSVs")

    # ---- 6. Run script targets PointNet ----
    run_text = run_script.read_text(encoding="utf-8", errors="ignore").lower() if run_script else ""
    # Match both "import bmtk.simulator.pointnet" and "from bmtk.simulator import pointnet"
    uses_pointnet = "bmtk.simulator.pointnet" in run_text or \
                    "from bmtk.simulator import pointnet" in run_text
    uses_bionet = "bmtk.simulator.bionet" in run_text or \
                  "from bmtk.simulator import bionet" in run_text
    check("run script imports bmtk.simulator.pointnet",
          uses_pointnet and not uses_bionet, 3,
          f"pointnet={uses_pointnet}, bionet={uses_bionet}")

    # ---- 7. Recurrent E/I structural evidence ----
    has_exc = any(
        (r.get("ei") or "").lower() == "e" or "exc" in (r.get("pop_name") or "").lower()
        for r in node_type_rows
    )
    has_inh = any(
        (r.get("ei") or "").lower() == "i" or "inh" in (r.get("pop_name") or "").lower()
        for r in node_type_rows
    )
    check("E population present in node_types", has_exc, 1)
    check("I population present in node_types", has_inh, 1)

    edge_pairs: set[tuple[str, str]] = set()
    for row in edge_type_rows:
        sq = (row.get("source_query") or "").lower().replace(" ", "")
        tq = (row.get("target_query") or "").lower().replace(" ", "")

        def classify(q: str) -> str:
            if "exc" in q or "ei=='e'" in q:
                return "e"
            if "inh" in q or "ei=='i'" in q:
                return "i"
            return "?"
        edge_pairs.add((classify(sq), classify(tq)))

    check("E->E edge type", ("e", "e") in edge_pairs, 1)
    check("E->I edge type", ("e", "i") in edge_pairs, 1)
    check("I->E edge type", ("i", "e") in edge_pairs, 1)
    check("I->I edge type", ("i", "i") in edge_pairs, 1)

    # ---- 8. Anti-pattern penalties ----
    # Cap the "wrong simulator family" penalty: if the agent went down the
    # BioNet branch, that is essentially a single failure mode. Subtract a
    # capped -8 rather than stacking -3/-3/-3/-4.
    wrong_family = bool(bionet_edge_field_hits) or bn_cells > 0 or bn_edges > 0 or uses_bionet
    if wrong_family:
        markers = []
        if bionet_edge_field_hits:
            markers.append(f"edge_fields={sorted(bionet_edge_field_hits)}")
        if bn_cells:
            markers.append(f"biophysical_cells={bn_cells}")
        if bn_edges:
            markers.append(f"bionet_synapses={bn_edges}")
        if uses_bionet:
            markers.append("run_script_imports_bionet")
        penalty("PENALTY: wrong simulator family (BioNet markers in PointNet project)",
                True, 8, "; ".join(markers))

    # ---- 9. Smoke test: does the project actually build + load? ----
    smoke = _smoke_test(root, build_script, run_script)
    check("smoke: build_network.py runs without error",
          smoke["build_ok"], 4, smoke["build_detail"])
    check("smoke: build produced node/edge HDF5 files",
          smoke["h5_ok"], 3, smoke["h5_detail"])
    check("smoke: run_simulation.py imports + loads config",
          smoke["run_loadable"], 3, smoke["run_detail"])

    return {
        "trial_dir": str(root),
        "score": score,
        "max_score": max_score,
        "fraction": round(score / max_score, 3) if max_score else 0,
        "checks": checks,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/evaluate_trial.py <trial_dir>")
    root = Path(sys.argv[1]).resolve()
    result = evaluate(root)

    metrics_path = root / "cline_task" / "cline_metrics.json"
    if metrics_path.is_file():
        try:
            result["cline_metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception as e:
            result["cline_metrics_error"] = str(e)

    print(json.dumps(result, indent=2))
    (root / "evaluation.json").write_text(json.dumps(result, indent=2))

    # Regenerate the summary CSV across all trials
    try:
        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location(
            "summarize_trials",
            pathlib.Path(__file__).parent / "summarize_trials.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows = mod.build_table()
        mod.write_csv(rows)
        print()
        mod.print_summary(rows)
    except Exception as e:
        print(f"[summarize_trials] warning: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
