#!/usr/bin/env python3
"""Create a fresh A/B trial folder for BMTK agent-resource evaluation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "trials"
RESOURCES = ROOT / "resources"
PROMPT = ROOT / "prompts" / "ei_pointnet_5s.md"
SEED_COMPONENTS = ROOT / "seed_components"

# Minimal AGENTS.md for control condition: environment rules only, no BMTK guidance
CONTROL_AGENTS_MD = """\
# AGENTS.md

## Environment

- Python environment: conda env `BXP2` (already installed: BMTK 1.0.6 + NEST 3.0).
- This host has a broken system NEST install that shadows the conda env's
  NEST. You MUST run python in a way that avoids it. Use exactly:

  ```bash
  unset PYTHONPATH
  LD_LIBRARY_PATH=/home/dhaufler/anaconda3/envs/BXP2/lib \\
    /home/dhaufler/anaconda3/envs/BXP2/bin/python <script.py>
  ```

  Do NOT use `conda run -n BXP2 ...` and do NOT use the env `BMTK_2023`
  (that env's NEST is broken on this host).
- Do NOT run pip install or conda install for any packages.
- Do NOT download data from the internet (no Allen SDK, no model downloads).
- Use relative paths in all config files. No hard-coded absolute paths.
"""

TRIAL_README = """\
# Project

Read these files first:

1. `BENCHMARK_PROMPT.md` — the task.
2. `AGENTS.md` — environment + project conventions you must follow.
3. `components/` — starter NEST parameter JSONs you can reference from
   your node_types / edge_types CSVs. You may use them as-is, edit them, or
   add new ones — but do not delete them and do not attempt to download
   replacements from the internet.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", required=True, help="Example: A001 or B001")
    parser.add_argument("--condition", choices=["control", "treatment"], required=True)
    parser.add_argument("--model", default="", help="Model identifier, e.g. 'gpt-4o-mini' or 'claude-sonnet-4-6'")
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
    (trial_dir / "README.md").write_text(TRIAL_README)

    # Seed components are identical for both conditions. The contrast between
    # control and treatment is *guidance only*, not starting material.
    if SEED_COMPONENTS.is_dir():
        shutil.copytree(SEED_COMPONENTS, trial_dir / "components")

    if args.condition == "treatment":
        shutil.copy2(RESOURCES / "AGENTS.md", trial_dir / "AGENTS.md")
        # Copy the atomic skills/ folder so AGENTS.md's links resolve.
        skills_src = RESOURCES / "skills"
        if skills_src.is_dir():
            shutil.copytree(skills_src, trial_dir / "skills")
        # Aliases so agents that look for their own filename also find the guidance.
        # AGENTS.md is the canonical file; the rest are copies of identical content.
        # - CLAUDE.md         : Claude Code
        # - GEMINI.md         : Gemini CLI
        # - .github/copilot-instructions.md : GitHub Copilot
        # - .clinerules       : Cline (also auto-reads AGENTS.md in recent versions)
        # - .cursorrules      : Cursor (legacy single-file form)
        agents_md = trial_dir / "AGENTS.md"
        for alias in ["CLAUDE.md", "GEMINI.md", ".clinerules", ".cursorrules"]:
            shutil.copy2(agents_md, trial_dir / alias)
        copilot_path = trial_dir / ".github" / "copilot-instructions.md"
        copilot_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agents_md, copilot_path)
    else:
        (trial_dir / "AGENTS.md").write_text(CONTROL_AGENTS_MD)
        # Control condition also gets aliases, but each contains only the minimal
        # environment rules — no BMTK guidance. This isolates the treatment effect
        # to the *content* of the guidance, not the *filename* the agent recognizes.
        for alias in ["CLAUDE.md", "GEMINI.md", ".clinerules", ".cursorrules"]:
            (trial_dir / alias).write_text(CONTROL_AGENTS_MD)
        copilot_path = trial_dir / ".github" / "copilot-instructions.md"
        copilot_path.parent.mkdir(parents=True, exist_ok=True)
        copilot_path.write_text(CONTROL_AGENTS_MD)

    metadata = f"condition: {args.condition}\ntrial_id: {args.trial_id}\nprompt: ei_pointnet_5s\nmodel: {args.model or 'unknown'}\n"
    (trial_dir / "TRIAL_METADATA.yaml").write_text(metadata)

    print(f"Created {args.condition} trial: {trial_dir}")
    print("Open this folder in VS Code and give the agent BENCHMARK_PROMPT.md.")


if __name__ == "__main__":
    main()
