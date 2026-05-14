# Experimental Plan: Agent Resources for BMTK Model Building

## 1. Motivation

BMTK users increasingly rely on coding agents to build model projects. These projects require coordinated creation of SONATA network files, node/edge type tables, simulation configuration files, input/output paths, and simulator-specific parameters. Agents often fail not because they cannot write Python, but because they do not know the canonical BMTK/SONATA workflow.

This project tests whether local agent-facing resources copied into a user's model project improve outcomes.

## 2. Proposed BMTK-facing feature

Add a model-resource directory to the main BMTK repository, for example:

```text
bmtk/
  agent_resources/
    MODELS.md
    SKILLS.md
    templates/
      pointnet_glif/
      bionet_basic/
```

Add a BMTK function/CLI command that initializes a user's model project:

```bash
bmtk init-agent-project my_model_project
```

or:

```python
from bmtk.utils.agent_resources import init_agent_project
init_agent_project("my_model_project")
```

The initializer copies `MODELS.md`, `SKILLS.md`, and optional templates into the user's project directory.

## 3. Scope clarification

These files are for **using BMTK**, not for developing BMTK.

They should help agents:

- construct valid SONATA node and edge files
- create valid BMTK network-build scripts
- create valid simulation config files
- choose appropriate simulator modules (`pointnet`, `bionet`, etc.)
- validate generated outputs before claiming success

They should not primarily describe:

- BMTK internals
- SONATA standard development
- contribution guidelines for BMTK source code

## 4. Minimal working demonstration

### A/B conditions

- **A: Control** — trial project contains only the benchmark prompt.
- **B: Treatment** — trial project contains the same prompt plus `MODELS.md` and `SKILLS.md`.

### Agent

Initial candidate:

- Continue.dev in VS Code
- Qwen2.5-Coder via Ollama
- Temperature: 0.1–0.2

Keep the model, prompt, and environment fixed across A/B trials.

### First prompt

Ask the agent to create a small PointNet/SONATA project with:

- excitatory and inhibitory GLIF populations
- recurrent E/I connectivity
- current-clamp or Poisson-like input
- a 5 second simulation config
- runnable build and run scripts

This is challenging enough that a generic model may fail, but simple enough to evaluate automatically.

## 5. Metrics

Use a layered score. Early metrics should be simple and robust.

### 5.1 Artifact completeness

- `build_network.py` exists
- simulation script exists, e.g. `run_simulation.py`
- config JSON exists
- network output directory exists after build
- expected SONATA files exist

### 5.2 Static validity

- Python files parse without syntax errors
- JSON config parses
- config contains required top-level sections: `manifest`, `network`, `run`, `output`
- run duration equals 5000 ms or equivalent

### 5.3 BMTK/SONATA structure

- node files exist: `nodes.h5`, `node_types.csv`
- edge files exist: `edges.h5`, `edge_types.csv`
- at least two populations or type groups are represented: excitatory and inhibitory
- edge types include E→E, E→I, I→E, and/or I→I connectivity

### 5.4 Execution validity

- build script runs without error
- simulation setup can be loaded by BMTK
- short smoke simulation runs, or at minimum config loads and simulator initializes

### 5.5 Scientific/semantic validity

Manual or semi-automated checks:

- GLIF cells are used in a PointNet-compatible way
- time units are consistent
- connectivity probabilities/weights are plausible
- output spikes/reports are configured
- no hard-coded absolute paths outside the project

## 6. Trial protocol

For each trial:

1. Create a fresh trial directory.
2. Randomly assign condition: control or treatment.
3. Open only that trial directory in VS Code.
4. Paste the same benchmark prompt into Continue.dev.
5. Let the agent complete the task.
6. Do not manually fix the result.
7. Run `scripts/evaluate_trial.py <trial_dir>`.
8. Save score JSON and optionally the conversation transcript.

Recommended initial sample:

- 5 control trials
- 5 treatment trials

This is not enough for publication-level statistics, but enough to detect large effects and refine the resources.

## 7. Avoiding evaluation bias

- Do not tell the agent whether it is in control or treatment.
- Use identical prompts.
- Start a fresh chat/session for every trial.
- Use the same model and temperature.
- Avoid manual corrections before scoring.
- Record failures as failures; use them to improve `MODELS.md` / `SKILLS.md`.

## 8. Scaling to real use

### 8.1 More prompts

After the first prompt works, add prompts covering:

- BioNet single-cell simulation
- PointNet recurrent network with external spike input
- BioNet network with morphology and synapse templates
- converting existing CSV metadata into SONATA node/edge tables
- debugging invalid config files

### 8.2 More agents

Test across:

- Continue.dev + local model
- GitHub Copilot Chat
- Cursor/Windsurf
- a CLI-based coding agent
- chat-only model as a negative control

### 8.3 More robust metrics

Move from heuristic scoring to pytest-based validation and BMTK-specific validators.
Potential future metrics:

- SONATA schema validation
- BMTK config validation
- simulation initialization success
- reproducible spike output for fixed seeds
- wall-clock time to completion
- number of agent turns
- number of manual interventions

## 9. Long-term BMTK integration

Once the minimal demo shows improvement:

1. Move stable `MODELS.md` and `SKILLS.md` into the BMTK repo.
2. Add a BMTK initializer command.
3. Add tests ensuring the copied resources remain synchronized.
4. Add examples generated from the resources.
5. Publish the evaluation harness separately or as a companion repo.

A clean split is recommended:

- BMTK repo: resource files + initializer
- evaluation repo: benchmarks, trial outputs, scoring scripts

This avoids mixing experimental benchmarking artifacts into the BMTK source tree.
