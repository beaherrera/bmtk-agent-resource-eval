# Getting started: first BMTK agent-resource A/B test

This project is intentionally minimal. Start with one prompt, two conditions,
and static + smoke-test scoring before adding more prompts or richer
validation.

## 1. Choose a coding agent

The trial initializer writes the canonical `AGENTS.md` plus agent-specific
alias files, so any of the major agents will see the guidance automatically:

| Agent          | File it reads                     | Session data captured by                    |
| -------------- | --------------------------------- | ------------------------------------------- |
| GitHub Copilot | `.github/copilot-instructions.md` | manual paste into `cline_task/`             |
| Cline          | `.clinerules` + `AGENTS.md`       | `scripts/capture_cline_task.py` (automatic) |
| Claude Code    | `CLAUDE.md`                       | manual paste into `cline_task/`             |
| Gemini CLI     | `GEMINI.md`                       | manual paste into `cline_task/`             |
| Cursor         | `.cursorrules`                     | manual paste into `cline_task/`             |

For the control condition the same alias files exist but contain only the
minimal environment rules — this isolates the treatment effect to the
*content* of the guidance, not the *filename* the agent recognizes.

### GitHub Copilot specifics

- Use **Copilot Chat in agent mode** (so it can create files), not inline
  suggestions.
- Confirm Copilot is reading the instructions: in the chat sidebar, look for a
  reference to `.github/copilot-instructions.md` in the request context, or
  open that file in an editor tab before sending the prompt.
- Use one VS Code window per trial. Start a fresh Copilot chat for each trial.

After the run completes, optionally save the session for later review:

1. Copy the chat transcript (Copilot Chat "..." menu → "Export Chat", or
   copy-paste) into `trials/<id>/cline_task/transcript.md`.
2. Copy terminal output into `trials/<id>/cline_task/terminal.log`.

Both files are pre-created as empty stubs by `init_trial.py`. The evaluator
does **not** parse them — they are for your own qualitative review only.
The evaluator does read `cline_task/cline_metrics.json` if present (Cline
only), merging token/duration metrics into `evaluation.json`.

### Cline specifics

After each Cline run, capture the task data automatically:

```bash
python scripts/capture_cline_task.py --trial-id A001
```

This writes `transcript.md`, `terminal.log`, and `cline_metrics.json` into
`trials/<id>/cline_task/`. The evaluator reads `cline_metrics.json` and merges
token/duration/tool-use stats into the score output (no effect on score).

## 2. BMTK conda environment

One environment covers both PointNet (NEST) and BioNet (NEURON):

```bash
conda create -n bmtk python=3.9
conda activate bmtk
conda install -c conda-forge nest-simulator   # NEST for PointNet
pip install bmtk neuron                        # BMTK + NEURON for BioNet
```

With mamba (faster dependency resolution):

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

Then edit the repo-root `ENVIRONMENT.md` to point at your interpreter —
`init_trial.py` copies this file into every new trial folder automatically.

## 3. Create A/B trial folders

From the repository root, pass `--model` so results are labeled correctly:

```bash
# PointNet trials
python scripts/init_trial.py \
    --trial-id A001 --condition control  --simulator pointnet \
    --model "copilot-gpt-4o"
python scripts/init_trial.py \
    --trial-id B001 --condition treatment --simulator pointnet \
    --model "copilot-gpt-4o"

# BioNet trials
python scripts/init_trial.py \
    --trial-id A002 --condition control  --simulator bionet \
    --model "copilot-gpt-4o"
python scripts/init_trial.py \
    --trial-id B002 --condition treatment --simulator bionet \
    --model "copilot-gpt-4o"
```

`--model` is free text — use whatever identifier is meaningful to you
(e.g. `"claude-sonnet-4-6"`, `"copilot-gpt-4o"`, `"gemini-2.5-pro"`).
It is stored in `TRIAL_METADATA.yaml` and shown in the summary table; the
evaluator does not use it for scoring.

Each trial folder contains:

- `BENCHMARK_PROMPT.md` — the task
- `README.md` — orientation for the agent
- `AGENTS.md` + alias files — minimal (control) or full (treatment)
- `pointnet_skills/` or `bionet_skills/` — treatment only
- `components/` — identical starter parameter JSONs in both conditions
- `ENVIRONMENT.md` — Python interpreter path (edit if needed before the run)
- `agent_output/` — scratch space for the agent
- `cline_task/transcript.md`, `cline_task/terminal.log` — empty stubs

## 4. Edit ENVIRONMENT.md in each trial folder

Open `trials/<id>/ENVIRONMENT.md` and replace the placeholder with the
real path to your Python interpreter:

```markdown
## Python interpreter

```bash
/opt/anaconda3/envs/bmtk_pointnet/bin/python
```
```

The agent reads this file and substitutes it wherever skill files write
`<python-command>`.

## 5. Run one trial

1. Open only the trial folder in VS Code (`File > Open Folder...`).
2. Start a fresh agent chat in agent/agentic mode.
3. Tell the agent: `Read BENCHMARK_PROMPT.md and complete the task described in it.`
4. Let the agent finish without manual fixes.

## 6. Score the trial

```bash
# Option 1 — pass the interpreter path directly
BMTK_PYTHON=/opt/anaconda3/envs/bmtk/bin/python \
    python scripts/evaluate_trial.py trials/B001

# Option 2 — use a conda env name
BMTK_CONDA_ENV=bmtk python scripts/evaluate_trial.py trials/B001

# Option 3 — activate the env first
conda activate bmtk
python scripts/evaluate_trial.py trials/B001
```

The same environment works for both PointNet and BioNet trials; the evaluator
auto-detects the simulator from `TRIAL_METADATA.yaml`.

Each run writes `trials/<id>/evaluation.json` and prints a summary table
across all evaluated trials.

## 7. Compare results

```bash
python scripts/summarize_trials.py
```

Writes `trials/results.csv` — one row per trial, with columns for score,
percentage, and every individual check (1 = pass, 0 = fail, blank = not
applicable for that simulator).

## 8. Trial hygiene checklist

For every trial:

- [ ] Same agent, model, and settings as the paired trial
- [ ] Same benchmark prompt (`--simulator` matches the prompt)
- [ ] `ENVIRONMENT.md` points at the correct interpreter
- [ ] Fresh VS Code window with the trial folder as workspace root
- [ ] Fresh chat/session (no prior context)
- [ ] No manual fixes before running `evaluate_trial.py`
- [ ] `--model` flag passed to `init_trial.py` so results are labeled
