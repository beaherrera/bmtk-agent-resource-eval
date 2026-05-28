#!/usr/bin/env python3
"""Scan all trial folders and write trials/results.csv.

Called automatically by evaluate_trial.py after each evaluation, but can
also be run standalone:

    python scripts/summarize_trials.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "trials"
OUT_CSV = TRIALS / "results.csv"

# ---------------------------------------------------------------------------
# Check columns: shared → PointNet-specific → BioNet-specific
# Rows for the other simulator's checks are left blank ("") in the CSV.
# ---------------------------------------------------------------------------

# Checks with the same name verbatim in BOTH _evaluate_pointnet and _evaluate_bionet
_SHARED_CHECKS = [
    "build script exists",
    "run script exists",
    "config json exists",
    "build script parses",
    "run script parses",
    "config parses as json",
    "config has 'networks' section",
    "config has 'manifest' section",
    "config has 'components' section",
    "config has 'run' section",
    "config has 'output' section",
    "node_types CSV files exist",
    "edge_types CSV files exist",
    "node HDF5 files exist",
    "edge HDF5 files exist",
    "referenced dynamics_params files exist on disk",
    "E population present in node_types",
    "I population present in node_types",
    "E->E edge type",
    "E->I edge type",
    "I->E edge type",
    "I->I edge type",
    "smoke: build_network.py runs without error",
    "smoke: build produced node/edge HDF5 files",
]

# PointNet (NEST) only
_PN_CHECKS = [
    "target_simulator is NEST",
    "simulation duration is 5000 ms",
    "cell node types use PointNet conventions (point_process/point_neuron + nest:*)",
    "edge types use 'static_synapse' template",
    "run script imports bmtk.simulator.pointnet",
    "smoke: run_pointnet.py runs without error",
]

# BioNet (NEURON) only
_BN_CHECKS = [
    "target_simulator is NEURON",
    "simulation duration is 3000 ms",
    "run.dL present",
    "run.spike_threshold present",
    "conditions.celsius present",
    "conditions.v_init present",
    "components declares morphologies_dir",
    "components declares mechanisms_dir or biophysical_neuron_models_dir",
    "cell node types use BioNet conventions (biophysical+ctdb:/nrn: or point_process+nrn:)",
    "edge types use BioNet synapse templates (exp2syn / exp1syn / etc.)",
    "referenced morphology files exist on disk",
    "run script imports bmtk.simulator.bionet",
    "smoke: NEURON mechanisms compiled",
    "smoke: run_bionet.py runs without error",
]

CHECK_COLUMNS = _SHARED_CHECKS + _PN_CHECKS + _BN_CHECKS


def _short(name: str) -> str:
    """Shorten a check name to a tidy CSV column header."""
    # Substitutions applied in order; each operates on the running result.
    # Long explicit matches must come BEFORE the short generic suffixes that
    # might partially match the same string.
    subs = [
        # Normalise smoke: prefix first so later subs can match it
        ("smoke: ",                                               "smoke:"),
        # Smoke test shorthands
        ("smoke:build_network.py runs without error",            "smoke:build_ok"),
        ("smoke:build produced node/edge HDF5 files",            "smoke:h5_ok"),
        ("smoke:run_pointnet.py runs without error",              "smoke:run_pn"),
        ("smoke:run_bionet.py runs without error",               "smoke:run_bn"),
        ("smoke:NEURON mechanisms compiled",                      "smoke:mech_ok"),
        # config has '…' section  →  cfg.…
        ("config has '",                                          "cfg."),
        ("' section",                                             ""),
        # Long cell / edge convention names
        (
            "cell node types use PointNet conventions "
            "(point_process/point_neuron + nest:*)",
            "node_types_pn",
        ),
        (
            "cell node types use BioNet conventions "
            "(biophysical+ctdb:/nrn: or point_process+nrn:)",
            "node_types_bn",
        ),
        ("edge types use 'static_synapse' template",              "edge_static_synapse"),
        (
            "edge types use BioNet synapse templates "
            "(exp2syn / exp1syn / etc.)",
            "edge_exp2syn",
        ),
        # dynamics_params / morphology on disk (explicit before generic " files exist")
        ("referenced dynamics_params files exist on disk",        "dynamics_params_exist"),
        ("referenced morphology files exist on disk",             "morphology_files_exist"),
        # run script imports
        ("run script imports bmtk.simulator.pointnet",            "imports_pn"),
        ("run script imports bmtk.simulator.bionet",              "imports_bn"),
        # simulator / duration
        ("target_simulator is NEST",                              "target_NEST"),
        ("target_simulator is NEURON",                            "target_NEURON"),
        ("simulation duration is 5000 ms",                        "tstop_5000"),
        ("simulation duration is 3000 ms",                        "tstop_3000"),
        # BioNet run / conditions config keys
        ("run.dL present",                                        "run.dL"),
        ("run.spike_threshold present",                           "run.spike_thr"),
        ("conditions.celsius present",                            "cond.celsius"),
        ("conditions.v_init present",                             "cond.v_init"),
        ("components declares morphologies_dir",                  "comp.morphologies"),
        (
            "components declares mechanisms_dir "
            "or biophysical_neuron_models_dir",
            "comp.mechanisms",
        ),
        # Generic suffixes (must come after all long explicit matches above)
        (" files exist",  "_exist"),
        (" parses",       "_parses"),
        (" exists",       "_exists"),
        (" population present in node_types", "_pop"),
        (" edge type",    "_edge"),
        # Arrow notation in E/I connectivity (after " edge type" is gone)
        ("->",            "_to_"),
    ]
    result = name
    for old, new in subs:
        result = result.replace(old, new)
    return result.replace(" ", "_")


def load_trial(trial_dir: Path) -> dict | None:
    eval_path = trial_dir / "evaluation.json"
    meta_path = trial_dir / "TRIAL_METADATA.yaml"

    if not eval_path.is_file():
        return None

    try:
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Parse simple key: value YAML (no external dependency needed)
    meta: dict[str, str] = {}
    if meta_path.is_file():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()

    checks_by_name = {c["name"]: c for c in ev.get("checks", [])}

    # simulator: prefer the evaluation result, fall back to TRIAL_METADATA
    simulator = ev.get("simulator") or meta.get("simulator", "")

    row: dict = {
        "trial_id":  meta.get("trial_id",  trial_dir.name),
        "condition": meta.get("condition", ""),
        "simulator": simulator,
        "model":     meta.get("model",     ""),
        "prompt":    meta.get("prompt",    ""),
        "score":     ev.get("score",       ""),
        "max_score": ev.get("max_score",   ""),
        "pct":       f"{ev.get('fraction', 0) * 100:.1f}",
    }

    # One column per check: 1 = pass, 0 = fail, "" = not scored for this simulator
    for name in CHECK_COLUMNS:
        col = _short(name)
        if name in checks_by_name:
            row[col] = 1 if checks_by_name[name]["passed"] else 0
        else:
            row[col] = ""

    return row


def build_table() -> list[dict]:
    rows = []
    for trial_dir in sorted(TRIALS.iterdir()):
        if not trial_dir.is_dir():
            continue
        row = load_trial(trial_dir)
        if row is not None:
            rows.append(row)
    return rows


def write_csv(rows: list[dict]) -> None:
    if not rows:
        print("No evaluated trials found.")
        return
    # All rows share the same keys (shared + PN + BN check columns);
    # simulator-specific columns that don't apply are stored as "".
    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} trial(s) → {OUT_CSV}")


def print_summary(rows: list[dict]) -> None:
    if not rows:
        return
    header = (
        f"{'trial':<8} {'cond':<10} {'sim':<10} {'model':<20} {'score':>7}  {'%':>6}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['trial_id']:<8} {r['condition']:<10} {r['simulator']:<10} "
            f"{r['model']:<20} "
            f"{str(r['score']):>3}/{str(r['max_score']):<3}  {r['pct']:>6}%"
        )


def main() -> None:
    rows = build_table()
    write_csv(rows)
    print()
    print_summary(rows)


if __name__ == "__main__":
    main()
