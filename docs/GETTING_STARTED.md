# Getting started: first BMTK agent-resource A/B test

This project is intentionally minimal. Start with one prompt, two conditions, and static scoring before adding more prompts or richer BMTK validation.

## 1. Continue.dev setup

Use a single Continue configuration for all trials. Keep the model, temperature, context providers, and tools fixed.

Example `config.yaml` entry for a local Ollama model:

```yaml
name: BMTK Agent Resource Eval
version: 1.0.0
schema: v1
models:
  - name: Qwen2.5-Coder 32B
    provider: ollama
    model: qwen2.5-coder:32b
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.1
      topP: 0.9
      maxTokens: 4096
    requestOptions:
      timeout: 600000
context:
  - provider: file
  - provider: code
  - provider: diff
  - provider: terminal
rules:
  - Always work only inside the currently opened trial folder.
  - When given BENCHMARK_PROMPT.md, create files rather than only describing the solution.
  - Prefer the conda environment named BMTK_2023 for Python/BMTK commands.
```

If your installed Ollama model tag differs, replace `qwen2.5-coder:32b` with the exact output from `ollama list`.

## 2. Python/BMTK build environment

For the first benchmark, use the installed conda environment `BMTK_2023` consistently across all trials.

Before starting the experiment, verify manually in a terminal:

```bash
conda activate BMTK_2023
python -c "import bmtk; print(bmtk.__version__ if hasattr(bmtk, '__version__') else 'bmtk import ok')"
python -c "from bmtk.builder.networks import NetworkBuilder; print('NetworkBuilder import ok')"
```

Do not change package versions between control and treatment runs.

## 3. Create first A/B trial folders

From the repository root:

```bash
python scripts/init_trial.py --trial-id A001 --condition control
python scripts/init_trial.py --trial-id B001 --condition treatment
```

Then run one trial at a time:

1. Open only the trial folder in VS Code.
2. Start a fresh Continue chat/session.
3. Select the same model and settings.
4. Paste the contents of `BENCHMARK_PROMPT.md`.
5. Let the agent finish without manual fixes.
6. Close the trial workspace before moving to the next trial.

## 4. Score a trial

From the repository root:

```bash
python scripts/evaluate_trial.py trials/A001
python scripts/evaluate_trial.py trials/B001
```

Each run writes `evaluation.json` into the trial folder.

## 5. Minimal first metrics

The current evaluator focuses on:

- expected files: build script, run script, config JSON
- Python and JSON parseability
- required config sections
- `run.tstop == 5000.0`
- network artifact names
- evidence for `NetworkBuilder`, PointNet, GLIF/LIF, E/I populations, and recurrent connectivity

This is enough to compare early failures without overfitting the evaluator.

## 6. GitHub setup

Recommended repository settings:

- Commit source files, prompts, docs, resources, and evaluator scripts.
- Do not commit generated trial outputs by default.
- If sharing results, commit only curated summaries or selected `evaluation.json` files in a separate results folder.
- Create issues for every repeated treatment failure; update `resources/MODELS.md` or `resources/SKILLS.md` only after confirming the failure pattern.

## 7. First experiment size

Start with:

- 3 control trials: `A001`–`A003`
- 3 treatment trials: `B001`–`B003`

If this is stable, expand to 5+ per condition.

## 8. Trial hygiene checklist

For every trial:

- same Continue config
- same Ollama model tag
- same conda environment
- same benchmark prompt
- fresh VS Code window
- fresh Continue chat/session
- no manual fixes before scoring
- record whether the agent attempted to run build/simulation commands
