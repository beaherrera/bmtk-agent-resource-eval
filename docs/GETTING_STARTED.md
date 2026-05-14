# Getting started: first BMTK agent-resource A/B test

This project is intentionally minimal. Start with one prompt, two conditions,
and static + smoke-test scoring before adding more prompts or richer
validation.

## 1. Choose a coding agent

The trial initializer writes the canonical `AGENTS.md` plus agent-specific
alias files, so any of the major agents will see the guidance automatically:

| Agent             | File it reads                          | Captured by                       |
| ----------------- | -------------------------------------- | --------------------------------- |
| GitHub Copilot    | `.github/copilot-instructions.md`      | manual chat-transcript copy       |
| Cline             | `.clinerules` + `AGENTS.md`            | `scripts/capture_cline_task.py`   |
| Claude Code       | `CLAUDE.md`                            | manual                            |
| Gemini CLI        | `GEMINI.md`                            | manual                            |
| Cursor            | `.cursorrules`                         | manual                            |

For the control condition the same alias files exist but contain only the
minimal environment rules — this isolates the treatment effect to the
*content* of the guidance, not the *filename* the agent recognizes.

### GitHub Copilot specifics

- Use **Copilot Chat in agent mode** (so it can create files), not inline
  suggestions.
- Confirm Copilot is reading the instructions: in the chat sidebar look for a
  reference to `.github/copilot-instructions.md` in the request context, or
  open `.github/copilot-instructions.md` in an editor tab before sending the
  prompt to guarantee it's in context.
- Copilot has no public per-task storage to snapshot. To capture the run:
  1. After the agent finishes, copy the chat transcript via the Copilot Chat
     "..." menu → "Export Chat" (or copy-paste the full conversation) into
     `trials/<id>/cline_task/transcript.md` so the evaluator picks it up.
  2. Optionally also save terminal output into
     `trials/<id>/cline_task/terminal.log`.
  3. There is no automatic token/duration metric for Copilot — leave
     `cline_metrics.json` absent and the evaluator will silently skip it.
- Use one VS Code window per trial. Start a fresh Copilot chat for each
  trial.

### Cline specifics

If using Cline with a remote-served model, start an SSH tunnel before running
trials:

```bash
ssh -N -L 11435:localhost:11434 darrell.haufler@10.128.49.71
curl -s http://localhost:11435/api/tags
```

## 2. BMTK conda environment

The evaluator's smoke test uses the `BXP2` env by default (BMTK 1.0.6 +
NEST 3.0). Verify it works:

```bash
unset PYTHONPATH
LD_LIBRARY_PATH=/home/dhaufler/anaconda3/envs/BXP2/lib \
  /home/dhaufler/anaconda3/envs/BXP2/bin/python -c \
  "import bmtk, nest; from bmtk.simulator import pointnet; print('ok')"
```

If you want a different env, set `BMTK_CONDA_ENV` before running the
evaluator. The evaluator clears `PYTHONPATH` and adds the env's `lib/` to
`LD_LIBRARY_PATH` automatically to avoid the broken system NEST install on
this host.

## 3. Create A/B trial folders

From the repository root:

```bash
python scripts/init_trial.py --trial-id A001 --condition control
python scripts/init_trial.py --trial-id B001 --condition treatment
```

Each trial folder will contain:

- `BENCHMARK_PROMPT.md` — the task
- `README.md` — orientation for the agent
- `AGENTS.md` + alias files — minimal (control) or full (treatment)
- `skills/` — treatment only
- `components/` — identical starter NEST parameter JSONs in both conditions
- `agent_output/` — scratch space for the agent

## 4. Run one trial

1. Open only the trial folder in VS Code (`File > Open Folder...`).
2. Start a fresh agent chat.
3. Open the trial's `BENCHMARK_PROMPT.md` and ask the agent to complete it.
4. Let the agent finish without manual fixes.

## 5. Capture + score

For Cline:

```bash
python scripts/capture_cline_task.py --trial-id A001
python scripts/evaluate_trial.py trials/A001
```

For Copilot (manual transcript export, see §1, then):

```bash
python scripts/evaluate_trial.py trials/A001
```

Each evaluator run writes `evaluation.json` into the trial folder.

## 6. Trial hygiene checklist

For every trial:

- BXP2 env reachable (smoke test passes)
- same agent + model + settings as the previous trial
- same benchmark prompt
- fresh VS Code window with trial folder as workspace root
- fresh chat/session
- no manual fixes before scoring
- `evaluation.json` saved
