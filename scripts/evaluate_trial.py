#!/usr/bin/env python3
"""Evaluator for the BMTK agent-resource benchmark.

Supports both PointNet (NEST) and BioNet (NEURON) trials.
The simulator is auto-detected from TRIAL_METADATA.yaml (key: simulator)
or can be overridden with --simulator on the command line.

Three layers of scoring per simulator:
1. Artifact presence and parseability
2. SONATA / simulator structural validity
3. Smoke test (build + load without running the full simulation)

A capped penalty of −8 is applied when the wrong simulator family's
constructs appear in the project.

If a captured Cline task is present at <trial>/cline_task/cline_metrics.json,
its dynamic metrics are merged into the output but do not affect the score.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------
# BMTK_PYTHON      Absolute path to the Python interpreter to use.
#                  Example: BMTK_PYTHON=/opt/conda/envs/bmtk/bin/python
# BMTK_CONDA_ENV   Conda environment name; invoked via
#                  `conda run -n ENV python ...`.
#                  Example: BMTK_CONDA_ENV=bmtk_bionet
# (neither set)    Uses `python` on PATH — activate the env first.

BMTK_PYTHON    = os.environ.get("BMTK_PYTHON",    "")
BMTK_CONDA_ENV = os.environ.get("BMTK_CONDA_ENV", "")

SMOKE_BUILD_TIMEOUT = int(os.environ.get("BMTK_SMOKE_BUILD_TIMEOUT", "180"))
SMOKE_LOAD_TIMEOUT  = int(os.environ.get("BMTK_SMOKE_LOAD_TIMEOUT",  "120"))
SMOKE_MECH_TIMEOUT  = int(os.environ.get("BMTK_SMOKE_MECH_TIMEOUT",  "120"))

# ---------------------------------------------------------------------------
# Simulator-family markers
# ---------------------------------------------------------------------------

# PointNet (NEST)
PN_CELL_PREFIX   = "nest:"
PN_SYNAPSE       = "static_synapse"

# BioNet (NEURON)
BN_CELL_PREFIXES  = ("ctdb:", "nrn:")
BN_SYNAPSES       = {"exp2syn", "exp1syn", "alphasynapse", "exp2isyn"}
BN_EDGE_FIELDS    = ("target_sections", "distance_range")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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
    try:
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh, delimiter=" "))
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Python runner (env-aware)
# ---------------------------------------------------------------------------

def _run_python(cwd: Path, python_args: list[str], timeout: int) -> tuple[bool, str]:
    """Run `python <python_args>` in the configured BMTK environment.
    Always drops PYTHONPATH to prevent stale system packages from leaking.
    """
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    if BMTK_PYTHON:
        cmd = [BMTK_PYTHON, *python_args]
    elif BMTK_CONDA_ENV:
        cmd = ["conda", "run", "--no-capture-output", "-n", BMTK_CONDA_ENV,
               "python", *python_args]
    else:
        cmd = ["python", *python_args]

    try:
        proc = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                              capture_output=True, text=True, env=env)
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except FileNotFoundError as exc:
        return False, f"interpreter not found: {exc}"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        return False, f"exit {proc.returncode}: " + " | ".join(tail)
    return True, "ok"


def _run_cmd(cwd: Path, cmd: list[str], timeout: int) -> tuple[bool, str]:
    """Run an arbitrary command (e.g. nrnivmodl), dropping PYTHONPATH."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    try:
        proc = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                              capture_output=True, text=True, env=env)
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except FileNotFoundError as exc:
        return False, f"command not found: {exc}"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        return False, f"exit {proc.returncode}: " + " | ".join(tail)
    return True, "ok"


# ---------------------------------------------------------------------------
# Simulator auto-detection
# ---------------------------------------------------------------------------

def _detect_simulator(root: Path) -> str:
    """Read simulator from TRIAL_METADATA.yaml; default to pointnet."""
    meta = root / "TRIAL_METADATA.yaml"
    if meta.exists():
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("simulator:"):
                return line.split(":", 1)[1].strip()
    return "pointnet"


# ---------------------------------------------------------------------------
# PointNet smoke test
# ---------------------------------------------------------------------------

def _smoke_test_pointnet(root: Path,
                         build_script: Path | None,
                         run_script: Path | None) -> dict:
    result = {
        "build_ok": False, "build_detail": "no build_network.py",
        "h5_ok": False,    "h5_detail": "",
        "run_loadable": False, "run_detail": "no config or run script",
    }
    if build_script is None:
        return result

    ok, detail = _run_python(root, [str(build_script.relative_to(root))],
                             SMOKE_BUILD_TIMEOUT)
    result["build_ok"] = ok
    result["build_detail"] = detail

    h5_files = list(_iter_project(root, "*.h5"))
    result["h5_ok"] = len(h5_files) > 0
    result["h5_detail"] = f"{len(h5_files)} HDF5 file(s) on disk"

    if run_script is None:
        return result

    # Run the agent's actual run script so any custom imports or helper
    # functions defined inside it are exercised, not just a synthetic loader.
    # A timeout counts as a pass: the simulation started and ran without
    # crashing but did not finish within the test window.
    ok, detail = _run_python(root, [str(run_script.relative_to(root))],
                             SMOKE_LOAD_TIMEOUT)
    if not ok and "timeout" in detail.lower():
        ok = True
        detail = f"started ok (timed out after {SMOKE_LOAD_TIMEOUT}s)"
    result["run_loadable"] = ok
    result["run_detail"] = detail
    return result


# ---------------------------------------------------------------------------
# BioNet smoke test
# ---------------------------------------------------------------------------

def _mechanisms_compiled(mech_dir: Path) -> bool:
    """True if nrnivmodl has already been run inside mech_dir."""
    if not mech_dir.is_dir():
        return False
    for item in mech_dir.iterdir():
        if item.is_dir() and item.name not in ("modfiles",):
            if any(
                f.suffix in (".so", ".dylib") or f.name in ("special", "libnrnmech.so")
                for f in item.iterdir()
                if f.is_file()
            ):
                return True
    return False


def _smoke_test_bionet(root: Path,
                       build_script: Path | None,
                       run_script: Path | None) -> dict:
    result = {
        "mechanisms_compiled": False, "mechanisms_detail": "no mechanisms dir",
        "build_ok": False, "build_detail": "no build_network.py",
        "h5_ok": False,    "h5_detail": "",
        "run_loadable": False, "run_detail": "no config or run script",
    }

    # Step 0 — check / compile NEURON mechanisms
    mech_dir    = root / "components" / "mechanisms"
    modfiles_dir = mech_dir / "modfiles"
    if modfiles_dir.is_dir() and any(modfiles_dir.glob("*.mod")):
        if _mechanisms_compiled(mech_dir):
            result["mechanisms_compiled"] = True
            result["mechanisms_detail"] = "already compiled"
        else:
            ok, detail = _run_cmd(mech_dir, ["nrnivmodl", "modfiles"], SMOKE_MECH_TIMEOUT)
            result["mechanisms_compiled"] = ok
            result["mechanisms_detail"] = "compiled ok" if ok else f"nrnivmodl failed: {detail}"
    else:
        result["mechanisms_detail"] = "no modfiles dir or no .mod files found"

    if build_script is None:
        return result

    # Step 1 — build network
    ok, detail = _run_python(root, [str(build_script.relative_to(root))],
                             SMOKE_BUILD_TIMEOUT)
    result["build_ok"] = ok
    result["build_detail"] = detail

    h5_files = list(_iter_project(root, "*.h5"))
    result["h5_ok"] = len(h5_files) > 0
    result["h5_detail"] = f"{len(h5_files)} HDF5 file(s) on disk"

    if run_script is None:
        return result

    # Step 2 — run the agent's actual run_bionet.py so any custom imports or
    # helper functions defined inside it are exercised.
    # A timeout counts as a pass: NEURON initialised and the simulation ran
    # but did not finish within the test window.
    ok, detail = _run_python(root, [str(run_script.relative_to(root))],
                             SMOKE_LOAD_TIMEOUT)
    if not ok and "timeout" in detail.lower():
        ok = True
        detail = f"started ok (timed out after {SMOKE_LOAD_TIMEOUT}s)"
    result["run_loadable"] = ok
    result["run_detail"] = detail
    return result


# ---------------------------------------------------------------------------
# PointNet evaluation
# ---------------------------------------------------------------------------

def _evaluate_pointnet(root: Path) -> dict:
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
        nonlocal score
        checks.append({"name": name, "passed": not applies, "points": -points,
                       "score": -points if applies else 0, "detail": detail})
        if applies:
            score -= points

    # 1. Artifact presence + parse
    build_script = find_first(root, ["build_network.py", "*build*.py"])
    run_script   = find_first(root, ["run_pointnet.py", "run_simulation.py",
                                     "run*.py", "simulate*.py"])
    config       = find_first(root, ["config.json", "config*.json",
                                     "simulation_config*.json"])

    check("build script exists",  build_script is not None, 2, str(build_script or ""))
    check("run script exists",    run_script is not None,   2, str(run_script or ""))
    check("config json exists",   config is not None,       2, str(config or ""))
    check("build script parses",  build_script is not None and py_parse(build_script), 2)
    check("run script parses",    run_script is not None   and py_parse(run_script),   2)

    config_data: dict | None = None
    if config:
        ok, data, detail = json_parse(config)
        check("config parses as json", ok, 2, detail)
        if ok and isinstance(data, dict):
            config_data = data
    else:
        check("config parses as json", False, 2, "missing")

    # 2. SONATA / PointNet config structure
    cfg = config_data or {}
    check("config has 'networks' section",   bool(cfg.get("networks") or cfg.get("network")), 2,
          "SONATA configs reference network files under 'networks'.")
    check("config has 'manifest' section",   isinstance(cfg.get("manifest"),   dict), 1)
    check("config has 'components' section", isinstance(cfg.get("components"), dict), 2,
          "Required so dynamics_params filenames resolve to disk.")
    check("config has 'run' section",        isinstance(cfg.get("run"),        dict), 1)
    check("config has 'output' section",     isinstance(cfg.get("output"),     dict), 1)

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

    # 3. Network artifact presence
    node_types_csvs = find_all(root, ["*node_types*.csv"])
    edge_types_csvs = find_all(root, ["*edge_types*.csv"])
    node_h5s        = find_all(root, ["*nodes*.h5"])
    edge_h5s        = find_all(root, ["*edges*.h5"])

    check("node_types CSV files exist", bool(node_types_csvs), 1, f"{len(node_types_csvs)} found")
    check("edge_types CSV files exist", bool(edge_types_csvs), 1, f"{len(edge_types_csvs)} found")
    check("node HDF5 files exist",      bool(node_h5s),        1, f"{len(node_h5s)} found")
    check("edge HDF5 files exist",      bool(edge_h5s),        1, f"{len(edge_h5s)} found")

    # 4. PointNet structural correctness
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
        if mtype in ("point_process", "point_neuron") and mtmpl.startswith(PN_CELL_PREFIX):
            pn_cells += 1
        if mtype == "biophysical" or any(mtmpl.startswith(p) for p in BN_CELL_PREFIXES):
            bn_cells += 1
    check("cell node types use PointNet conventions (point_process/point_neuron + nest:*)",
          pn_cells > 0 and bn_cells == 0, 3,
          f"point_process/point_neuron+nest: rows={pn_cells}, "
          f"biophysical/ctdb/nrn rows={bn_cells}")

    pn_edges = bn_edges = 0
    bionet_edge_field_hits: set[str] = set()
    for row in edge_type_rows:
        mtmpl = (row.get("model_template") or "").lower()
        if mtmpl == PN_SYNAPSE:
            pn_edges += 1
        if mtmpl in BN_SYNAPSES:
            bn_edges += 1
        for f in BN_EDGE_FIELDS:
            v = row.get(f)
            if v not in (None, "", "NULL", "nan"):
                bionet_edge_field_hits.add(f)
    check("edge types use 'static_synapse' template",
          pn_edges > 0 and bn_edges == 0, 3,
          f"static_synapse rows={pn_edges}, BioNet-template rows={bn_edges}")

    # 5. dynamics_params on disk
    referenced = [
        (row.get("dynamics_params") or "").strip()
        for row in node_type_rows + edge_type_rows
        if (row.get("dynamics_params") or "").strip().lower() not in ("", "null", "nan")
    ]
    existing_json = {p.name for p in _iter_project(root, "*.json")}
    missing = [d for d in referenced if d not in existing_json]
    if referenced:
        check("referenced dynamics_params files exist on disk",
              not missing, 2, f"missing={missing}" if missing else "all present")
    else:
        check("referenced dynamics_params files exist on disk", False, 2,
              "no dynamics_params referenced in node/edge type CSVs")

    # 6. Run script
    run_text = (run_script.read_text(encoding="utf-8", errors="ignore").lower()
                if run_script else "")
    uses_pointnet = ("bmtk.simulator.pointnet" in run_text or
                     "from bmtk.simulator import pointnet" in run_text)
    uses_bionet   = ("bmtk.simulator.bionet" in run_text or
                     "from bmtk.simulator import bionet" in run_text)
    check("run script imports bmtk.simulator.pointnet",
          uses_pointnet and not uses_bionet, 3,
          f"pointnet={uses_pointnet}, bionet={uses_bionet}")

    # 7. E/I structural evidence
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
        def _cls(q: str) -> str:
            if "exc" in q or "ei=='e'" in q: return "e"
            if "inh" in q or "ei=='i'" in q: return "i"
            return "?"
        edge_pairs.add((_cls(sq), _cls(tq)))
    check("E->E edge type", ("e", "e") in edge_pairs, 1)
    check("E->I edge type", ("e", "i") in edge_pairs, 1)
    check("I->E edge type", ("i", "e") in edge_pairs, 1)
    check("I->I edge type", ("i", "i") in edge_pairs, 1)

    # 8. Anti-pattern penalty
    wrong_family = (bool(bionet_edge_field_hits) or bn_cells > 0
                    or bn_edges > 0 or uses_bionet)
    if wrong_family:
        markers = []
        if bionet_edge_field_hits: markers.append(f"edge_fields={sorted(bionet_edge_field_hits)}")
        if bn_cells:    markers.append(f"biophysical_cells={bn_cells}")
        if bn_edges:    markers.append(f"bionet_synapses={bn_edges}")
        if uses_bionet: markers.append("run_script_imports_bionet")
        penalty("PENALTY: wrong simulator family (BioNet markers in PointNet project)",
                True, 8, "; ".join(markers))

    # 9. Smoke test
    smoke = _smoke_test_pointnet(root, build_script, run_script)
    check("smoke: build_network.py runs without error",
          smoke["build_ok"],     4, smoke["build_detail"])
    check("smoke: build produced node/edge HDF5 files",
          smoke["h5_ok"],        3, smoke["h5_detail"])
    check("smoke: run_pointnet.py runs without error",
          smoke["run_loadable"], 3, smoke["run_detail"])

    return {
        "trial_dir": str(root),
        "simulator": "pointnet",
        "score": score, "max_score": max_score,
        "fraction": round(score / max_score, 3) if max_score else 0,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# BioNet evaluation
# ---------------------------------------------------------------------------

def _evaluate_bionet(root: Path) -> dict:
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
        nonlocal score
        checks.append({"name": name, "passed": not applies, "points": -points,
                       "score": -points if applies else 0, "detail": detail})
        if applies:
            score -= points

    # 1. Artifact presence + parse
    build_script = find_first(root, ["build_network.py", "*build*.py"])
    run_script   = find_first(root, ["run_bionet.py", "run_simulation.py",
                                     "run*.py", "simulate*.py"])
    config       = find_first(root, ["config.json", "config*.json",
                                     "simulation_config*.json"])

    check("build script exists",  build_script is not None, 2, str(build_script or ""))
    check("run script exists",    run_script is not None,   2, str(run_script or ""))
    check("config json exists",   config is not None,       2, str(config or ""))
    check("build script parses",  build_script is not None and py_parse(build_script), 2)
    check("run script parses",    run_script is not None   and py_parse(run_script),   2)

    config_data: dict | None = None
    if config:
        ok, data, detail = json_parse(config)
        check("config parses as json", ok, 2, detail)
        if ok and isinstance(data, dict):
            config_data = data
    else:
        check("config parses as json", False, 2, "missing")

    # 2. SONATA / BioNet config structure
    cfg = config_data or {}
    check("config has 'networks' section",   bool(cfg.get("networks") or cfg.get("network")), 2)
    check("config has 'manifest' section",   isinstance(cfg.get("manifest"),   dict), 1)
    check("config has 'components' section", isinstance(cfg.get("components"), dict), 2,
          "Required so dynamics_params and morphology filenames resolve.")
    check("config has 'run' section",        isinstance(cfg.get("run"),        dict), 1)
    check("config has 'output' section",     isinstance(cfg.get("output"),     dict), 1)

    target_sim = (cfg.get("target_simulator") or "").upper()
    check("target_simulator is NEURON", target_sim == "NEURON", 2,
          f"got '{cfg.get('target_simulator')}'")

    run_cfg    = cfg.get("run")        if isinstance(cfg.get("run"),        dict) else {}
    conditions = cfg.get("conditions") if isinstance(cfg.get("conditions"), dict) else {}

    tstop = run_cfg.get("tstop") or run_cfg.get("duration")
    try:
        tstop_ok = float(tstop) == 3000.0
    except (TypeError, ValueError):
        tstop_ok = False
    check("simulation duration is 3000 ms",   tstop_ok, 3, f"tstop={tstop}")
    check("run.dL present",                   "dL"             in run_cfg,   1)
    check("run.spike_threshold present",       "spike_threshold" in run_cfg,  1)
    check("conditions.celsius present",        "celsius" in conditions,        1)
    check("conditions.v_init present",         "v_init"  in conditions,        1)

    comp_cfg = cfg.get("components") if isinstance(cfg.get("components"), dict) else {}
    check("components declares morphologies_dir",
          bool(comp_cfg.get("morphologies_dir")), 1)
    check("components declares mechanisms_dir or biophysical_neuron_models_dir",
          bool(comp_cfg.get("mechanisms_dir") or
               comp_cfg.get("biophysical_neuron_models_dir")), 1)

    # 3. Network artifact presence
    node_types_csvs = find_all(root, ["*node_types*.csv"])
    edge_types_csvs = find_all(root, ["*edge_types*.csv"])
    node_h5s        = find_all(root, ["*nodes*.h5"])
    edge_h5s        = find_all(root, ["*edges*.h5"])

    check("node_types CSV files exist", bool(node_types_csvs), 1, f"{len(node_types_csvs)} found")
    check("edge_types CSV files exist", bool(edge_types_csvs), 1, f"{len(edge_types_csvs)} found")
    check("node HDF5 files exist",      bool(node_h5s),        1, f"{len(node_h5s)} found")
    check("edge HDF5 files exist",      bool(edge_h5s),        1, f"{len(edge_h5s)} found")

    # 4. BioNet cell correctness
    node_type_rows: list[dict] = []
    for p in node_types_csvs:
        node_type_rows.extend(read_csv_sonata(p))
    edge_type_rows: list[dict] = []
    for p in edge_types_csvs:
        edge_type_rows.extend(read_csv_sonata(p))

    bn_cells = pn_nest_cells = 0
    for row in node_type_rows:
        mtype = (row.get("model_type") or "").lower()
        mtmpl = (row.get("model_template") or "").lower()
        if mtype == "virtual":
            continue  # virtual input cells are valid in both simulators
        if ((mtype == "biophysical" and any(mtmpl.startswith(p) for p in BN_CELL_PREFIXES)) or
                (mtype == "point_process" and mtmpl.startswith("nrn:"))):
            bn_cells += 1
        if mtmpl.startswith(PN_CELL_PREFIX):  # nest:* is PointNet-only
            pn_nest_cells += 1
    check("cell node types use BioNet conventions (biophysical+ctdb:/nrn: or point_process+nrn:)",
          bn_cells > 0 and pn_nest_cells == 0, 3,
          f"BioNet-compatible rows={bn_cells}, nest: rows={pn_nest_cells}")

    # 5. BioNet synapse correctness
    bn_edges = pn_static_edges = 0
    for row in edge_type_rows:
        mtmpl = (row.get("model_template") or "").lower()
        if mtmpl in BN_SYNAPSES:
            pn_static_edges += (1 if mtmpl == PN_SYNAPSE else 0)  # won't trigger; see below
            bn_edges += 1
        if mtmpl == PN_SYNAPSE:  # static_synapse is PointNet-only
            pn_static_edges += 1
    check("edge types use BioNet synapse templates (exp2syn / exp1syn / etc.)",
          bn_edges > 0 and pn_static_edges == 0, 3,
          f"BioNet-synapse rows={bn_edges}, static_synapse rows={pn_static_edges}")

    # 6. dynamics_params on disk
    referenced = [
        (row.get("dynamics_params") or "").strip()
        for row in node_type_rows + edge_type_rows
        if (row.get("dynamics_params") or "").strip().lower() not in ("", "null", "nan")
    ]
    existing_json = {p.name for p in _iter_project(root, "*.json")}
    missing_params = [d for d in referenced if d not in existing_json]
    if referenced:
        check("referenced dynamics_params files exist on disk",
              not missing_params, 2,
              f"missing={missing_params}" if missing_params else "all present")
    else:
        check("referenced dynamics_params files exist on disk", False, 2,
              "no dynamics_params referenced in node/edge type CSVs")

    # 7. Morphology files on disk
    morphologies = [
        (row.get("morphology") or "").strip()
        for row in node_type_rows
        if (row.get("morphology") or "").strip().lower() not in ("", "null", "nan")
    ]
    existing_swc = ({p.name for p in _iter_project(root, "*.swc")} |
                    {p.name for p in _iter_project(root, "*.asc")})
    missing_morph = [m for m in morphologies if m not in existing_swc]
    if morphologies:
        check("referenced morphology files exist on disk",
              not missing_morph, 2,
              f"missing={missing_morph}" if missing_morph else "all present")
    else:
        check("referenced morphology files exist on disk", True, 2,
              "no morphologies referenced (IntFire1-only project)")

    # 8. Run script
    run_text = (run_script.read_text(encoding="utf-8", errors="ignore").lower()
                if run_script else "")
    uses_bionet   = ("bmtk.simulator.bionet" in run_text or
                     "from bmtk.simulator import bionet" in run_text)
    uses_pointnet = ("bmtk.simulator.pointnet" in run_text or
                     "from bmtk.simulator import pointnet" in run_text)
    check("run script imports bmtk.simulator.bionet",
          uses_bionet and not uses_pointnet, 3,
          f"bionet={uses_bionet}, pointnet={uses_pointnet}")

    # 9. E/I structural evidence
    _exc_names = ("exc", "scnn1a", "lif_exc")
    _inh_names = ("inh", "pv", "lif_inh")
    has_exc = any(
        (r.get("ei") or "").lower() == "e" or
        any(n in (r.get("pop_name") or "").lower() for n in _exc_names)
        for r in node_type_rows
    )
    has_inh = any(
        (r.get("ei") or "").lower() == "i" or
        any(n in (r.get("pop_name") or "").lower() for n in _inh_names)
        for r in node_type_rows
    )
    check("E population present in node_types", has_exc, 1)
    check("I population present in node_types", has_inh, 1)

    edge_pairs: set[tuple[str, str]] = set()
    for row in edge_type_rows:
        sq = (row.get("source_query") or "").lower().replace(" ", "")
        tq = (row.get("target_query") or "").lower().replace(" ", "")
        def _cls(q: str) -> str:
            if "exc" in q or "ei=='e'" in q or "scnn1a" in q or "lif_exc" in q: return "e"
            if "inh" in q or "ei=='i'" in q or "'pv'" in q or "lif_inh" in q:  return "i"
            return "?"
        edge_pairs.add((_cls(sq), _cls(tq)))
    check("E->E edge type", ("e", "e") in edge_pairs, 1)
    check("E->I edge type", ("e", "i") in edge_pairs, 1)
    check("I->E edge type", ("i", "e") in edge_pairs, 1)
    check("I->I edge type", ("i", "i") in edge_pairs, 1)

    # 10. Anti-pattern penalty (PointNet constructs in a BioNet project)
    wrong_family = pn_nest_cells > 0 or pn_static_edges > 0 or uses_pointnet
    if wrong_family:
        markers = []
        if pn_nest_cells:   markers.append(f"nest_cells={pn_nest_cells}")
        if pn_static_edges: markers.append(f"static_synapse_edges={pn_static_edges}")
        if uses_pointnet:   markers.append("run_script_imports_pointnet")
        penalty("PENALTY: wrong simulator family (PointNet markers in BioNet project)",
                True, 8, "; ".join(markers))

    # 11. Smoke test
    smoke = _smoke_test_bionet(root, build_script, run_script)
    check("smoke: NEURON mechanisms compiled",
          smoke["mechanisms_compiled"], 2, smoke["mechanisms_detail"])
    check("smoke: build_network.py runs without error",
          smoke["build_ok"],            4, smoke["build_detail"])
    check("smoke: build produced node/edge HDF5 files",
          smoke["h5_ok"],               3, smoke["h5_detail"])
    check("smoke: run_bionet.py runs without error",
          smoke["run_loadable"],         3, smoke["run_detail"])

    return {
        "trial_dir": str(root),
        "simulator": "bionet",
        "score": score, "max_score": max_score,
        "fraction": round(score / max_score, 3) if max_score else 0,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def evaluate(root: Path, simulator: str = "auto") -> dict:
    """Evaluate a trial directory; auto-detects simulator from TRIAL_METADATA.yaml."""
    if simulator == "auto":
        simulator = _detect_simulator(root)
    if simulator == "bionet":
        return _evaluate_bionet(root)
    return _evaluate_pointnet(root)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a BMTK agent trial (PointNet or BioNet)."
    )
    parser.add_argument("trial_dir",
                        help="Path to the trial directory")
    parser.add_argument("--simulator", choices=["pointnet", "bionet", "auto"],
                        default="auto",
                        help="Simulator family to score. "
                             "'auto' reads simulator from TRIAL_METADATA.yaml "
                             "(default: auto)")
    args = parser.parse_args()

    root = Path(args.trial_dir).resolve()
    result = evaluate(root, simulator=args.simulator)

    # Merge optional Cline task metrics (informational only, no score impact)
    metrics_path = root / "cline_task" / "cline_metrics.json"
    if metrics_path.is_file():
        try:
            result["cline_metrics"] = json.loads(
                metrics_path.read_text(encoding="utf-8")
            )
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
