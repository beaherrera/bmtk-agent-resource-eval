#!/usr/bin/env python3
"""Create a fresh A/B trial folder for BMTK agent-resource evaluation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "trials"
RESOURCES = ROOT / "resources"
PROMPT = ROOT / "prompts" / "ei_glif_5s.md"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", required=True, help="Example: A001 or B001")
    parser.add_argument("--condition", choices=["control", "treatment"], required=True)
    parser.add_argument("--force", action="store_true", help="Overwrite existing trial folder")
    args = parser.parse_args()

    trial_dir = TRIALS / args.trial_id
    if trial_dir.exists():
        if not args.force:
            raise SystemExit(f"Trial already exists: {trial_dir}. Use --force to overwrite.")
        shutil.rmtree(trial_dir)

    trial_dir.mkdir(parents=True)
    (trial_dir / "agent_output").mkdir()

    shutil.copy2(PROMPT, trial_dir / "BENCHMARK_PROMPT.md")

    if args.condition == "treatment":
        shutil.copy2(RESOURCES / "MODELS.md", trial_dir / "MODELS.md")
        shutil.copy2(RESOURCES / "SKILLS.md", trial_dir / "SKILLS.md")

    metadata = f"condition: {args.condition}\ntrial_id: {args.trial_id}\nprompt: ei_glif_5s\n"
    (trial_dir / "TRIAL_METADATA.yaml").write_text(metadata)

    print(f"Created {args.condition} trial: {trial_dir}")
    print("Open this folder in VS Code and give the agent BENCHMARK_PROMPT.md.")


if __name__ == "__main__":
    main()
