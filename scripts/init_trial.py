#!/usr/bin/env python3
"""Create a fresh A/B trial folder for BMTK agent-resource evaluation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "trials"
RESOURCES = ROOT / "resources"

PROMPTS = {
    "pointnet": ROOT / "prompts" / "ei_pointnet_5s.md",
    "bionet":   ROOT / "prompts" / "ei_bionet_3s.md",
}
SEED_COMPONENTS = {
    "pointnet": ROOT / "seed_components",
    "bionet":   ROOT / "seed_bio_components",
}
SKILLS_DIR = {
    "pointnet": "pointnet_skills",
    "bionet":   "bionet_skills",
}

# Minimal AGENTS.md for control condition: environment rules only, no BMTK guidance.
CONTROL_AGENTS_MD = """\
# AGENTS.md

## Environment

- Use the Python interpreter designated by the project `README.md` or
  `ENVIRONMENT.md`. Run **all** Python commands with that exact interpreter
  (`<python-command>` in any instructions you follow).
- If no interpreter is specified, ask the user which environment to use.
- Do NOT run pip install or conda install for any packages.
- Do NOT download data from the internet (no Allen SDK, no model downloads).
- Use relative paths in all config files. No hard-coded absolute paths.
"""

TRIAL_README = """\
# Project

Read these files first:

1. `BENCHMARK_PROMPT.md` — the task.
2. `AGENTS.md` — environment + project conventions you must follow.
3. `components/` — starter parameter files (JSONs, morphologies, mechanisms)
   you can reference from your node_types / edge_types CSVs. You may use them
   as-is, edit them, or add new ones — but do not delete them and do not
   attempt to download replacements from the internet.
"""


def _write_aliases(trial_dir: Path, src: Path) -> None:
    """Mirror src to all agent-specific filenames so any agent finds the guidance."""
    for alias in ["CLAUDE.md", "GEMINI.md", ".clinerules", ".cursorrules"]:
        shutil.copy2(src, trial_dir / alias)
    copilot_path = trial_dir / ".github" / "copilot-instructions.md"
    copilot_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, copilot_path)


def main():
    parser = argparse.ArgumentParser(
        description="Initialise a control or treatment trial folder."
    )
    parser.add_argument("--trial-id", required=True,
                        help="Unique trial identifier, e.g. A001 or B001")
    parser.add_argument("--condition", choices=["control", "treatment"],
                        required=True)
    parser.add_argument("--simulator", choices=["pointnet", "bionet"],
                        default="pointnet",
                        help="Which simulator the trial targets (default: pointnet)")
    parser.add_argument("--model", default="",
                        help="Model identifier, e.g. 'claude-sonnet-4-6'")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing trial folder")
    args = parser.parse_args()

    trial_dir = TRIALS / args.trial_id
    if trial_dir.exists():
        if not args.force:
            raise SystemExit(
                f"Trial already exists: {trial_dir}. Use --force to overwrite."
            )
        shutil.rmtree(trial_dir)

    trial_dir.mkdir(parents=True)
    (trial_dir / "agent_output").mkdir()

    # ENVIRONMENT.md — copy the repo-root template so the user just fills in
    # their interpreter path; if the template is missing, create a minimal stub.
    env_template = ROOT / "ENVIRONMENT.md"
    if env_template.is_file():
        shutil.copy2(env_template, trial_dir / "ENVIRONMENT.md")
    else:
        (trial_dir / "ENVIRONMENT.md").write_text(
            "## Python interpreter\n\n"
            "```bash\n/path/to/your/python\n```\n\n"
            "Replace the path above with your BMTK environment's Python interpreter.\n"
        )

    # cline_task/ stub — pre-create empty log files so Copilot / other agent
    # users can fill them in after their session without having to create the
    # folder structure manually.  capture_cline_task.py silently replaces these
    # stubs when run for a Cline session.
    cline_dir = trial_dir / "cline_task"
    cline_dir.mkdir()
    (cline_dir / "transcript.md").write_text(
        "<!-- Populated after the agent session: paste the agent transcript here,\n"
        "     or run `python scripts/capture_cline_task.py --trial-id "
        f"{args.trial_id}` for Cline. -->\n"
    )
    (cline_dir / "terminal.log").write_text(
        "# Terminal log — paste terminal output from the agent session here.\n"
        "# For Cline, this is generated automatically by capture_cline_task.py.\n"
    )

    # Benchmark prompt and README
    prompt_src = PROMPTS[args.simulator]
    if not prompt_src.exists():
        raise SystemExit(f"Prompt file not found: {prompt_src}")
    shutil.copy2(prompt_src, trial_dir / "BENCHMARK_PROMPT.md")
    (trial_dir / "README.md").write_text(TRIAL_README)

    # Seed components — identical for both conditions within a simulator.
    # The A/B contrast is guidance only, not starting material.
    seed_src = SEED_COMPONENTS[args.simulator]
    if seed_src.is_dir():
        shutil.copytree(seed_src, trial_dir / "components")

    skills_dirname = SKILLS_DIR[args.simulator]

    if args.condition == "treatment":
        shutil.copy2(RESOURCES / "AGENTS.md", trial_dir / "AGENTS.md")
        # Copy the skills folder so AGENTS.md links resolve inside the trial dir.
        skills_src = RESOURCES / skills_dirname
        if skills_src.is_dir():
            shutil.copytree(skills_src, trial_dir / skills_dirname)
        # Mirror AGENTS.md to every agent-specific filename.
        _write_aliases(trial_dir, trial_dir / "AGENTS.md")
    else:
        # Control: minimal env guidance only — no BMTK orientation or skills.
        # Aliases also get the minimal content so the treatment effect is
        # isolated to guidance content, not filename recognition.
        (trial_dir / "AGENTS.md").write_text(CONTROL_AGENTS_MD)
        for alias in ["CLAUDE.md", "GEMINI.md", ".clinerules", ".cursorrules"]:
            (trial_dir / alias).write_text(CONTROL_AGENTS_MD)
        copilot_path = trial_dir / ".github" / "copilot-instructions.md"
        copilot_path.parent.mkdir(parents=True, exist_ok=True)
        copilot_path.write_text(CONTROL_AGENTS_MD)

    prompt_name = prompt_src.stem
    metadata = (
        f"condition: {args.condition}\n"
        f"trial_id: {args.trial_id}\n"
        f"simulator: {args.simulator}\n"
        f"prompt: {prompt_name}\n"
        f"model: {args.model or 'unknown'}\n"
    )
    (trial_dir / "TRIAL_METADATA.yaml").write_text(metadata)

    print(f"Created {args.condition}/{args.simulator} trial: {trial_dir}")
    print("Open this folder in your editor and give the agent BENCHMARK_PROMPT.md.")


if __name__ == "__main__":
    main()
