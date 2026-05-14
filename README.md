# BMTK Agent Resource Evaluation

Test whether local agent-facing resources improve coding-agent performance on
BMTK PointNet model-building tasks.

The goal is not to develop BMTK itself. The goal is to help users build valid
BMTK/SONATA model projects with coding agents by providing local guidance
files that the agent reads automatically.

## Core hypothesis

Coding agents produce more valid BMTK PointNet projects when the project
directory contains concise, local, agent-readable resources:

- `AGENTS.md` — top-level orientation, environment rules, project conventions
- `skills/*.md` — short atomic how-to notes for individual subtasks

Both files follow the [AGENTS.md standard](https://agents.md/) and are
mirrored into agent-specific filenames (`CLAUDE.md`, `GEMINI.md`,
`.clinerules`, `.github/copilot-instructions.md`) by the trial initializer
so any major coding agent picks them up automatically.

## Minimal A/B demonstration

For each trial, give the same prompt to the same coding agent.

- **Condition A (control)** — trial folder contains `BENCHMARK_PROMPT.md`,
  a minimal `AGENTS.md` with only environment rules, starter `components/`
  with NEST parameter JSONs.
- **Condition B (treatment)** — same as control, plus the full `AGENTS.md`
  orientation and the `skills/` folder.

Both conditions start from identical starter material. The contrast is
*guidance only*.

## First benchmark prompt

See [prompts/ei_pointnet_5s.md](prompts/ei_pointnet_5s.md): a small recurrent
PointNet model with excitatory and inhibitory point neurons, NEST built-in
cell models (`nest:iaf_psc_alpha` or `nest:glif_psc`), and a 5 second
simulation.

## Repository layout

```text
bmtk_agent_resource_eval/
├── README.md
├── docs/
│   ├── EXPERIMENTAL_PLAN.md
│   └── GETTING_STARTED.md
├── prompts/
│   └── ei_pointnet_5s.md
├── resources/
│   ├── AGENTS.md             # treatment-condition orientation + skills index
│   └── skills/
│       ├── 01_build_pointnet_network.md
│       ├── 02_external_inputs.md
│       ├── 03_simulation_config.md
│       ├── 04_run_simulation.md
│       └── 05_validate_and_debug.md
├── seed_components/          # identical starter files copied into every trial
│   ├── point_neuron_models/
│   └── synaptic_models/
├── scripts/
│   ├── init_trial.py
│   ├── evaluate_trial.py
│   └── capture_cline_task.py
└── trials/
```

## Quick start

```bash
cd /home/dhaufler/ai_project_directory/bmtk_agent_resource_eval

# Create a control and a treatment trial
python scripts/init_trial.py --trial-id A001 --condition control
python scripts/init_trial.py --trial-id B001 --condition treatment

# Open one trial folder in VS Code, run the agent against BENCHMARK_PROMPT.md,
# then score it
python scripts/evaluate_trial.py trials/A001
```

For Cline trials, after the run completes:

```bash
python scripts/capture_cline_task.py --trial-id A001
```

This snapshots Cline's task history into `trials/<id>/cline_task/` and merges
token/duration/tool-use metrics into the evaluation output.

## Evaluator

[scripts/evaluate_trial.py](scripts/evaluate_trial.py) scores three things:

1. **Artifact presence** — build script, run script, config.json all exist and
   parse.
2. **PointNet structural validity** — config has the right sections, cell
   `model_type` is `point_process` with `nest:*` template, edges use
   `static_synapse`, referenced `dynamics_params` files actually exist on disk,
   run script imports `bmtk.simulator.pointnet`, E/I populations and recurrent
   edge classes are present.
3. **Smoke test** — actually runs `build_network.py` and loads the project
   under PointNet (without stepping the sim) in the BMTK conda env.

A capped penalty of −8 is applied if BioNet markers leak into the project
(BioNet-only edge fields, biophysical cell templates, `Exp2Syn` synapses, or
`bmtk.simulator.bionet` in the run script).

## Conda environment

The evaluator's smoke test uses the `BXP2` conda env by default (BMTK 1.0.6 +
NEST 3.0, including `iaf_psc_alpha` and `glif_psc`). Override with:

```bash
BMTK_CONDA_ENV=my_env python scripts/evaluate_trial.py trials/X
```

The smoke test clears `PYTHONPATH` and prepends the env's `lib/` to
`LD_LIBRARY_PATH` to avoid conflicts with a broken system NEST install on this
host.

## Interpreting results

This is a workflow demonstration, not a publication-ready experiment. Use it
to:

1. Confirm the agent reaches the same task under both conditions.
2. Read structural failures back into `AGENTS.md` / `skills/` updates.
3. Iterate.
