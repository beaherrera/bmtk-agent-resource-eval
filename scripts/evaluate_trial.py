#!/usr/bin/env python3
"""Minimal evaluator for the first BMTK agent-resource benchmark.

This intentionally starts simple. It scores a generated trial folder on:
- expected files
- Python syntax
- JSON validity
- config fields
- simple evidence for E/I populations and 5 s simulation

It does not yet fully validate SONATA/BMTK execution. That is a planned next layer.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


def find_first(root: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = list(root.rglob(pattern))
        if matches:
            return matches[0]
    return None


def py_syntax_ok(path: Path) -> tuple[bool, str]:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True, ""
    except Exception as e:
        return False, str(e)


def json_ok(path: Path) -> tuple[bool, dict | None, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return True, data, ""
    except Exception as e:
        return False, None, str(e)


def contains_any_text(root: Path, patterns: list[str]) -> bool:
    text_parts = []
    for suffix in ["*.py", "*.json", "*.csv", "*.md"]:
        for path in root.rglob(suffix):
            try:
                text_parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    text = "\n".join(text_parts).lower()
    return any(p.lower() in text for p in patterns)


def evaluate(root: Path) -> dict:
    score = 0
    max_score = 0
    checks = []

    def check(name: str, passed: bool, points: int = 1, detail: str = ""):
        nonlocal score, max_score
        max_score += points
        if passed:
            score += points
        checks.append({"name": name, "passed": passed, "points": points, "detail": detail})

    build_script = find_first(root, ["build_network.py", "*build*.py"])
    run_script = find_first(root, ["run_simulation.py", "run*.py", "simulate*.py"])
    config = find_first(root, ["config*.json", "simulation_config*.json"])

    check("build script exists", build_script is not None, 2, str(build_script) if build_script else "")
    check("run script exists", run_script is not None, 2, str(run_script) if run_script else "")
    check("config json exists", config is not None, 2, str(config) if config else "")

    if build_script:
        ok, detail = py_syntax_ok(build_script)
        check("build script parses", ok, 2, detail)
    else:
        check("build script parses", False, 2, "missing")

    if run_script:
        ok, detail = py_syntax_ok(run_script)
        check("run script parses", ok, 2, detail)
    else:
        check("run script parses", False, 2, "missing")

    config_data = None
    if config:
        ok, config_data, detail = json_ok(config)
        check("config parses as json", ok, 2, detail)
    else:
        check("config parses as json", False, 2, "missing")

    if isinstance(config_data, dict):
        for key in ["manifest", "network", "run", "output"]:
            check(f"config has {key}", key in config_data, 1)
        tstop = None
        if isinstance(config_data.get("run"), dict):
            tstop = config_data["run"].get("tstop") or config_data["run"].get("duration")
        check("simulation duration is 5000 ms", float(tstop) == 5000.0 if tstop is not None else False, 3, str(tstop))
    else:
        for key in ["manifest", "network", "run", "output"]:
            check(f"config has {key}", False, 1, "no parsed config")
        check("simulation duration is 5000 ms", False, 3, "no parsed config")

    network_dir_exists = any(p.is_dir() and p.name.lower() == "network" for p in root.rglob("*"))
    check("network directory exists", network_dir_exists, 1)

    node_like = list(root.rglob("*nodes*.h5")) + list(root.rglob("*node_types*.csv"))
    edge_like = list(root.rglob("*edges*.h5")) + list(root.rglob("*edge_types*.csv"))
    check("node/edge output names present", bool(node_like) and bool(edge_like), 2,
          f"node_like={len(node_like)}, edge_like={len(edge_like)}")

    check("mentions BMTK NetworkBuilder", contains_any_text(root, ["NetworkBuilder"]), 2)
    check("mentions pointnet", contains_any_text(root, ["pointnet"]), 2)
    check("mentions GLIF/LIF", contains_any_text(root, ["glif", "lif"]), 1)
    check("has excitatory evidence", contains_any_text(root, ["excitatory", "exc", "ei: e", "ei\": \"e"]), 1)
    check("has inhibitory evidence", contains_any_text(root, ["inhibitory", "inh", "ei: i", "ei\": \"i"]), 1)
    check("has recurrent connectivity evidence", contains_any_text(root, ["add_edges", "e->i", "i->e", "recurrent", "connection"]), 2)

    return {
        "trial_dir": str(root),
        "score": score,
        "max_score": max_score,
        "fraction": round(score / max_score, 3) if max_score else 0,
        "checks": checks,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/evaluate_trial.py <trial_dir>")
    root = Path(sys.argv[1]).resolve()
    result = evaluate(root)
    print(json.dumps(result, indent=2))
    (root / "evaluation.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
