# MODELS.md — BMTK/SONATA Model-Building Reference for Agents

This file gives coding agents compact guidance for building valid BMTK model projects.
It focuses on user model-building, not BMTK development.

## BMTK/SONATA mental model

A BMTK project has three layers:

1. **Network description** — SONATA node and edge files
2. **Components** — model parameter files, mechanisms, templates, morphologies, inputs
3. **Simulation config** — JSON describing network files, simulator, run time, outputs

The agent must keep these layers consistent.

## SONATA network essentials

A valid network generally includes:

```text
network/
├── <pop>_nodes.h5
├── <pop>_node_types.csv
├── <edge_pop>_edges.h5
└── <edge_pop>_edge_types.csv
```

The HDF5 files contain per-node/per-edge data. The CSV files contain type-level metadata.
The config must point to the actual generated files.

## PointNet GLIF/LIF-style model pattern

Use PointNet for point-neuron networks.

Typical workflow:

1. Create a `NetworkBuilder`.
2. Add excitatory and inhibitory nodes with distinguishing metadata.
3. Add recurrent edges using probability-based rules.
4. Save SONATA files.
5. Create `config.json` using the PointNet simulator.
6. Run with `bmtk.simulator.pointnet`.

### Minimal population metadata

For a benchmark E/I network, each node type should distinguish:

- `pop_name`: e.g. `Exc` or `Inh`
- `ei`: `e` or `i`
- `model_type`: PointNet-compatible model type
- `model_template` or simulator-specific model identifier
- `dynamics_params`: parameter file if required by the installed BMTK version

Exact keys can vary by BMTK version. If uncertain, inspect installed BMTK examples.

## Simulation config essentials

A config should normally contain:

```json
{
  "manifest": {},
  "target_simulator": "NEST",
  "run": {
    "tstop": 5000.0,
    "dt": 0.1
  },
  "network": {},
  "output": {},
  "reports": {},
  "inputs": {}
}
```

For a 5 second simulation, `tstop` should be `5000.0` ms.

## Recommended benchmark model

For the first benchmark, prefer:

- 80 excitatory cells
- 20 inhibitory cells
- E→E, E→I, I→E, I→I recurrent connections
- sparse probabilities, e.g. 0.05–0.2
- simulation duration: 5000 ms
- output spikes saved in `output/`

## Validation checklist

Before final response, check:

- [ ] `build_network.py` exists
- [ ] `run_simulation.py` exists
- [ ] `config.json` exists
- [ ] `network/` exists
- [ ] node HDF5 and node type CSV files exist after build
- [ ] edge HDF5 and edge type CSV files exist after build
- [ ] config JSON parses
- [ ] config references files that exist
- [ ] `run.tstop` is 5000 ms for a 5 second task
- [ ] E and I populations are represented
- [ ] recurrent connectivity is represented

## Agent behavior constraints

- Prefer canonical BMTK examples over invented APIs.
- If using a BMTK API from memory, verify it by importing or inspecting examples when possible.
- Keep initial models small and reproducible.
- Do not silently skip simulation/config creation.
- If BMTK is unavailable, produce the files and explicitly state which commands should be run in a BMTK environment.
