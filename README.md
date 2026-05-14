# BMTK Agent Resource Evaluation

This repository is a minimal working demonstration for testing whether local agent-facing resources improve coding-agent performance on BMTK model-building tasks.

The goal is not to develop BMTK itself. The goal is to help users build valid BMTK/SONATA model projects with coding agents by copying local guidance files into a new model-project directory.

## Core hypothesis

Coding agents will produce more valid BMTK model projects when the project directory contains concise, local, agent-readable resources:

- `MODELS.md` — canonical BMTK/SONATA model-building patterns
- `SKILLS.md` — procedural workflows agents should follow

## Minimal A/B demonstration

For each trial, give the same prompt to the same coding agent/model.

- **Condition A: control** — empty project folder, no BMTK guidance resources
- **Condition B: treatment** — project folder initialized with `MODELS.md` and `SKILLS.md`

Then evaluate the produced project with the same automated evaluator.

## Suggested first agent/model

- Continue.dev in VS Code
- Qwen2.5-Coder via Ollama
- Temperature low, e.g. 0.1–0.2

## First benchmark prompt

See [prompts/ei_glif_5s.md](prompts/ei_glif_5s.md).

The task asks the agent to create a small BMTK PointNet/SONATA project with excitatory and inhibitory GLIF populations and a 5 second simulation.

## Repository layout

```text
bmtk_agent_resource_eval/
├── README.md
├── docs/
│   └── EXPERIMENTAL_PLAN.md
├── prompts/
│   └── ei_glif_5s.md
├── resources/
│   ├── MODELS.md
│   └── SKILLS.md
├── scripts/
│   ├── init_trial.py
│   └── evaluate_trial.py
└── trials/
    └── <trial folders created here>
```

## Quick start

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for the first-run protocol, Continue.dev configuration notes, and GitHub hygiene recommendations.

Create one control and one treatment trial folder:

```bash
cd /home/dhaufler/ai_project_directory/bmtk_agent_resource_eval
python scripts/init_trial.py --trial-id A001 --condition control
python scripts/init_trial.py --trial-id B001 --condition treatment
```

Open the trial folder in VS Code, ask Continue.dev to complete the benchmark prompt, then run:

```bash
python scripts/evaluate_trial.py trials/B001
```

## Interpreting results

The first goal is not statistical significance. The first goal is to prove that the workflow is measurable:

1. The agent attempts the same task under both conditions.
2. The evaluator produces repeatable metrics.
3. Treatment failures point to missing or unclear guidance in `MODELS.md` / `SKILLS.md`.
4. Iterating the resource files improves the measured score.

Once this works on one prompt, expand to multiple prompts, multiple random seeds, and multiple agents.
