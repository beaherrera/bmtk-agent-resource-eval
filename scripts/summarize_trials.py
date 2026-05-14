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

# Check names to expose as individual columns (in order)
CHECK_COLUMNS = [
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
    "target_simulator is NEST",
    "simulation duration is 5000 ms",
    "node_types CSV files exist",
    "edge_types CSV files exist",
    "node HDF5 files exist",
    "edge HDF5 files exist",
    "cell node types use PointNet conventions (point_process/point_neuron + nest:*)",
    "edge types use 'static_synapse' template",
    "referenced dynamics_params files exist on disk",
    "run script imports bmtk.simulator.pointnet",
    "E population present in node_types",
    "I population present in node_types",
    "E->E edge type",
    "E->I edge type",
    "I->E edge type",
    "I->I edge type",
    "smoke: build_network.py runs without error",
    "smoke: build produced node/edge HDF5 files",
    "smoke: run_simulation.py imports + loads config",
]


def _short(name: str) -> str:
    """Shorten a check name to a tidy column header."""
    return (name
            .replace("smoke: ", "smoke:")
            .replace("config has '", "cfg.")
            .replace("' section", "")
            .replace("cell node types use PointNet conventions (point_process/point_neuron + nest:*)", "node_types_pointnet")
            .replace("edge types use 'static_synapse' template", "edge_static_synapse")
            .replace("referenced dynamics_params files exist on disk", "dynamics_params_exist")
            .replace("run script imports bmtk.simulator.pointnet", "imports_pointnet")
            .replace(" population present in node_types", "_pop")
            .replace("simulation duration is 5000 ms", "tstop_5000")
            .replace("target_simulator is NEST", "target_NEST")
            .replace(" files exist", "_exist")
            .replace(" parses", "_parses")
            .replace(" exists", "_exists")
            .replace(" ", "_"))


def load_trial(trial_dir: Path) -> dict | None:
    eval_path = trial_dir / "evaluation.json"
    meta_path = trial_dir / "TRIAL_METADATA.yaml"

    if not eval_path.is_file():
        return None

    try:
        ev = json.loads(eval_path.read_text())
    except Exception:
        return None

    # Parse simple key: value YAML (no external dependency needed)
    meta: dict[str, str] = {}
    if meta_path.is_file():
        for line in meta_path.read_text().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()

    checks_by_name = {c["name"]: c for c in ev.get("checks", [])}

    row: dict = {
        "trial_id": meta.get("trial_id", trial_dir.name),
        "condition": meta.get("condition", ""),
        "model": meta.get("model", ""),
        "prompt": meta.get("prompt", ""),
        "score": ev.get("score", ""),
        "max_score": ev.get("max_score", ""),
        "pct": f"{ev.get('fraction', 0) * 100:.1f}",
    }

    # One column per check: 1 = pass, 0 = fail, "" = not present
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
    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} trial(s) → {OUT_CSV}")


def print_summary(rows: list[dict]) -> None:
    if not rows:
        return
    header = f"{'trial':<8} {'cond':<10} {'model':<20} {'score':>7}  {'%':>6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['trial_id']:<8} {r['condition']:<10} {r['model']:<20} "
              f"{r['score']:>3}/{r['max_score']:<3}  {r['pct']:>6}%")


def main() -> None:
    rows = build_table()
    write_csv(rows)
    print()
    print_summary(rows)


if __name__ == "__main__":
    main()
