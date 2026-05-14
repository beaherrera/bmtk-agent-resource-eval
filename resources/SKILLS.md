# SKILLS.md — BMTK Model-Building Agent Skills

These instructions are for coding agents helping a user build BMTK/SONATA model projects.
They are not instructions for modifying BMTK source code.

## Prime directive

When asked to build a BMTK model project, produce a complete, runnable project with:

1. a network-build script,
2. valid SONATA network output files,
3. a valid BMTK simulation config,
4. a run script,
5. clear validation steps.

Do not only provide pseudocode unless explicitly asked.

## Required workflow

### 1. Identify simulator type

Choose the BMTK simulator based on model type:

- `pointnet`: point-neuron networks, including GLIF/LIF-style models
- `bionet`: biophysical NEURON models with morphologies and mechanisms
- `popnet`: population-rate models
- `filternet`: LGN/filter models

For GLIF or LIF network tasks, prefer `pointnet`.

### 2. Separate build from simulation

Always structure projects as:

```text
project/
├── build_network.py
├── run_simulation.py
├── config.json
├── network/
│   ├── <population>_nodes.h5
│   ├── <population>_node_types.csv
│   ├── <edges>.h5
│   └── <edge_types>.csv
├── components/
└── output/
```

The build script creates SONATA network files. The run script loads the config and runs the simulator.

### 3. Use BMTK builders when possible

Prefer canonical BMTK APIs:

```python
from bmtk.builder.networks import NetworkBuilder
```

Build nodes with `add_nodes()` and edges with `add_edges()`. Save using `build()` and `save_nodes()` / `save_edges()` or the current BMTK builder API available in the installed version.

### 4. Validate paths

Use relative paths in configs through a `manifest` section. Avoid hard-coded absolute paths.

Good:

```json
"manifest": {
  "$BASE_DIR": ".",
  "$NETWORK_DIR": "$BASE_DIR/network",
  "$OUTPUT_DIR": "$BASE_DIR/output"
}
```

### 5. Validate before final answer

Before declaring success, run or explain how to run:

```bash
python build_network.py
python run_simulation.py
```

If the environment lacks BMTK, at least validate:

```bash
python -m py_compile build_network.py run_simulation.py
python -m json.tool config.json
```

### 6. Report what was generated

At the end, summarize:

- populations created
- number of nodes per population
- connection classes
- simulation duration
- output files
- commands to reproduce

## Common failure modes to avoid

- Mixing BioNet and PointNet config keys
- Creating config paths that do not match generated files
- Creating node/edge files but no config
- Creating config but no network files
- Using GLIF terminology with a BioNet morphology workflow
- Assuming BMTK can infer missing `node_types.csv` / `edge_types.csv`
- Forgetting to create `output/`
- Returning only a code snippet instead of files

## When uncertain

Prefer a small working model over a large speculative one.
For benchmark or demonstration tasks, use tiny networks first:

- 10–80 excitatory cells
- 2–20 inhibitory cells
- sparse recurrent connectivity
- short simulation duration

Scale up only after the model builds and runs.
