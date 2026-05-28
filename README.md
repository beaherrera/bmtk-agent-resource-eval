# BMTK Agent Resource Evaluation

Test whether local agent-facing resources improve coding-agent performance on
BMTK model-building tasks (PointNet and BioNet).

The goal is not to develop BMTK itself. The goal is to help users build valid
BMTK/SONATA model projects with coding agents by providing local guidance
files that the agent reads automatically.

## Core hypothesis

Coding agents produce more valid BMTK projects when the project directory
contains concise, local, agent-readable resources:

- `AGENTS.md` — top-level orientation, environment rules, project conventions
- `pointnet_skills/` / `bionet_skills/` — short atomic how-to notes for
  individual subtasks

Both follow the [AGENTS.md standard](https://agents.md/) and are mirrored into
agent-specific filenames (`CLAUDE.md`, `GEMINI.md`, `.clinerules`,
`.github/copilot-instructions.md`) by the trial initializer.

## Minimal A/B demonstration

For each trial, give the same prompt to the same coding agent.

- **Condition A (control)** — trial folder contains `BENCHMARK_PROMPT.md`,
  a minimal `AGENTS.md` with only environment rules, and starter `components/`.
- **Condition B (treatment)** — same as control, plus the full `AGENTS.md`
  orientation and the simulator-specific `pointnet_skills/` or `bionet_skills/`
  folder.

Both conditions start from identical starter material. The contrast is
*guidance only*.

## Benchmark prompts

| File | Simulator | Description |
|---|---|---|
| [prompts/ei_pointnet_5s.md](prompts/ei_pointnet_5s.md) | PointNet / NEST | Small E/I recurrent network, point neurons, 5 s simulation |
| [prompts/ei_bionet_3s.md](prompts/ei_bionet_3s.md) | BioNet / NEURON | Multi-population network (biophysical + IntFire1), LGN drive, 3 s simulation |

## Repository layout

```text
bmtk_agent_resource_eval/
├── README.md
├── docs/
│   ├── EXPERIMENTAL_PLAN.md
│   └── GETTING_STARTED.md
├── prompts/
│   ├── ei_pointnet_5s.md
│   └── ei_bionet_3s.md
├── resources/
│   ├── AGENTS.md                    # treatment-condition orientation + skills index
│   ├── pointnet_skills/             # PointNet (NEST) atomic how-to files
│   │   ├── 01_build_pointnet_network.md
│   │   ├── 02_external_inputs.md
│   │   ├── 03_simulation_config.md
│   │   ├── 04_run_simulation.md
│   │   └── 05_validate_and_debug.md
│   └── bionet_skills/               # BioNet (NEURON) atomic how-to files
│       ├── 01_build_bionet_network.md
│       ├── 02_external_inputs.md
│       ├── 03_simulation_config.md
│       ├── 04_run_simulation.md
│       └── 05_validate_and_debug.md
├── seed_components/                 # PointNet starter files (copied into every PointNet trial)
│   ├── point_neuron_models/
│   └── synaptic_models/
├── seed_bio_components/             # BioNet starter files (copied into every BioNet trial)
│   ├── biophysical_neuron_templates/
│   ├── morphologies/
│   ├── mechanisms/modfiles/
│   ├── point_neuron_templates/
│   └── synaptic_models/
├── scripts/
│   ├── init_trial.py
│   ├── evaluate_trial.py
│   ├── capture_cline_task.py
│   └── summarize_trials.py
└── trials/
```

## Environment setup

A single conda environment runs both PointNet (NEST) and BioNet (NEURON).

```bash
conda create -n bmtk python=3.9
conda activate bmtk
conda install -c conda-forge nest-simulator   # NEST for PointNet
pip install bmtk neuron                        # BMTK + NEURON for BioNet
```

If you have [mamba](https://mamba.readthedocs.io) available, the first two
steps are faster:

```bash
mamba create -n bmtk python=3.9 -c conda-forge nest-simulator
conda activate bmtk
pip install bmtk neuron
```

Verify both simulators work:

```bash
python -c "import bmtk, nest; from bmtk.simulator import pointnet; print('PointNet ok')"
python -c "import bmtk, neuron; from bmtk.simulator import bionet; print('BioNet ok')"
```

### Compile NEURON mechanisms (BioNet trials only)

Run this once inside each BioNet trial folder before running or evaluating:

```bash
cd <trial_dir>/components/mechanisms
nrnivmodl modfiles
cd ../..
```

### ENVIRONMENT.md — telling the agent which Python to use

The skills use the placeholder `<python-command>` wherever they call Python.
Edit the repo-root `ENVIRONMENT.md` with your interpreter path once; it is
copied automatically into every new trial folder by `init_trial.py`:

```markdown
## Python interpreter

\`\`\`bash
/opt/anaconda3/envs/bmtk/bin/python
\`\`\`
```

The agent reads this file and substitutes `<python-command>` accordingly. If
`ENVIRONMENT.md` is absent the agent will ask you before running any commands.

### Telling the evaluator which Python to use

```bash
# Option 1 — path to a specific interpreter
BMTK_PYTHON=/opt/anaconda3/envs/bmtk/bin/python \
  python scripts/evaluate_trial.py trials/B001

# Option 2 — conda env name (uses `conda run -n ENV python ...`)
BMTK_CONDA_ENV=bmtk python scripts/evaluate_trial.py trials/B001

# Option 3 — activate the env first, then run (uses PATH python)
conda activate bmtk
python scripts/evaluate_trial.py trials/B001
```

## Quick start

```bash
# PointNet trials (pass --model so results are labeled correctly)
python scripts/init_trial.py --trial-id A001 --condition control  --simulator pointnet --model "Claude Sonnet 4.6"
python scripts/init_trial.py --trial-id B001 --condition treatment --simulator pointnet --model "Claude Sonnet 4.6"

# BioNet trials
python scripts/init_trial.py --trial-id A002 --condition control  --simulator bionet --model "Claude Sonnet 4.6"
python scripts/init_trial.py --trial-id B002 --condition treatment --simulator bionet --model "Claude Sonnet 4.6"

# Open a trial folder in VS Code, run the agent against BENCHMARK_PROMPT.md,
# then score it (simulator is auto-detected from TRIAL_METADATA.yaml)
BMTK_CONDA_ENV=bmtk python scripts/evaluate_trial.py trials/B001
BMTK_CONDA_ENV=bmtk python scripts/evaluate_trial.py trials/B002
```

For Cline trials, after the run completes:

```bash
python scripts/capture_cline_task.py --trial-id B001
```

This snapshots Cline's task history into `trials/<id>/cline_task/` and merges
token/duration/tool-use metrics into the evaluation output.

## Evaluator

[scripts/evaluate_trial.py](scripts/evaluate_trial.py) supports both **PointNet**
and **BioNet** trials. The simulator is auto-detected from `TRIAL_METADATA.yaml`
(key: `simulator`) or can be set explicitly with `--simulator {pointnet,bionet,auto}`.

Each trial is scored on three layers:

1. **Artifact presence** — build script, run script, `config.json` all exist
   and parse.
2. **Structural validity** — config has the right sections, cell `model_type`
   and `model_template` match the target simulator, edges use the correct
   synapse template, referenced `dynamics_params` and morphology files exist
   on disk.
3. **Smoke test** — actually runs `build_network.py` and verifies the project
   loads under the target simulator (without stepping the sim). For BioNet,
   also checks that NEURON `.mod` files are compiled.

BioNet-specific checks include `run.dL`, `run.spike_threshold`,
`conditions.celsius/v_init`, `components` paths, and morphology files on disk.

A capped penalty of −8 is applied if the wrong simulator family's constructs
appear in the project.

## Interpreting results

This is a workflow demonstration, not a publication-ready experiment. Use it to:

1. Confirm the agent reaches the same task under both conditions.
2. Read structural failures back into `AGENTS.md` / `skills/` updates.
3. Iterate.
