# Skill 03 — Simulation config and `components/` parameter files

The simulation config is a SONATA JSON file that ties together network files,
components, run parameters, inputs, and outputs. There are two ways to create
it: use BMTK's built-in generator (recommended), or write it by hand.

## Option A — Use `build_env_pointnet` (recommended)

BMTK ships a helper that scaffolds the config plus a working `run_pointnet.py`:

```python
from bmtk.utils.sim_setup import build_env_pointnet

build_env_pointnet(
    base_dir='.',
    network_dir='network',
    tstop=5000.0,
    dt=0.1,
    include_examples=True,   # copies example components into components/
)
```

This produces a `config.json` (or split `circuit_config.json` +
`simulation_config.json`), a stub `run_pointnet.py`, and seeds `components/`
with example parameter files you can then customize.

Equivalent CLI form:

```bash
python -m bmtk.utils.sim_setup --network network --tstop 5000.0 --dt 0.1 \
    --include-examples pointnet .
```

After generation, edit the file paths in the config so they reference the
files your `build_network.py` actually produced (the helper uses generic names).

## Option B — Write `config.json` by hand

Minimum viable PointNet config:

```json
{
  "manifest": {
    "$BASE_DIR": ".",
    "$NETWORK_DIR": "$BASE_DIR/network",
    "$COMPONENT_DIR": "$BASE_DIR/components",
    "$OUTPUT_DIR": "$BASE_DIR/output",
    "$INPUT_DIR": "$BASE_DIR/inputs"
  },
  "target_simulator": "NEST",
  "run": {
    "tstop": 5000.0,
    "dt": 0.1
  },
  "conditions": {},
  "components": {
    "point_neuron_models_dir": "$COMPONENT_DIR/point_neuron_models",
    "synaptic_models_dir": "$COMPONENT_DIR/synaptic_models"
  },
  "networks": {
    "nodes": [
      {
        "nodes_file":      "$NETWORK_DIR/cortex_nodes.h5",
        "node_types_file": "$NETWORK_DIR/cortex_node_types.csv"
      },
      {
        "nodes_file":      "$NETWORK_DIR/LGN_nodes.h5",
        "node_types_file": "$NETWORK_DIR/LGN_node_types.csv"
      }
    ],
    "edges": [
      {
        "edges_file":      "$NETWORK_DIR/cortex_cortex_edges.h5",
        "edge_types_file": "$NETWORK_DIR/cortex_cortex_edge_types.csv"
      },
      {
        "edges_file":      "$NETWORK_DIR/LGN_cortex_edges.h5",
        "edge_types_file": "$NETWORK_DIR/LGN_cortex_edge_types.csv"
      }
    ]
  },
  "inputs": {
    "LGN_spikes": {
      "input_type": "spikes",
      "module": "h5",
      "input_file": "$INPUT_DIR/lgn_spikes.h5",
      "node_set": "LGN"
    }
  },
  "output": {
    "log_file":    "$OUTPUT_DIR/log.txt",
    "output_dir":  "$OUTPUT_DIR",
    "spikes_file": "spikes.h5"
  },
  "reports": {}
}
```

If the network has no external input, omit the `inputs` section and use a
current-clamp entry instead (see skill 02).

### Optional: record membrane potential

Add to `reports`:

```json
"membrane_potential": {
  "cells": { "population": "cortex", "node_ids": [0, 1, 2] },
  "variable_name": "V_m",
  "module": "multimeter_report",
  "sections": "soma"
}
```

## `components/` — cell and synapse parameter JSON files

Files referenced via `dynamics_params` must live in the right subdirectory.

### Cell parameters: `components/point_neuron_models/<name>.json`

For `nest:iaf_psc_alpha`, a complete minimal file:

```json
{
  "V_th":    -50.0,
  "E_L":     -70.0,
  "V_reset": -70.0,
  "C_m":     250.0,
  "tau_m":    20.0,
  "t_ref":     2.0
}
```

These keys must match NEST's parameter names for the chosen model. For
`nest:glif_psc`, see the NEST documentation for valid keys — the parameter
set is larger.

### Synapse parameters: `components/synaptic_models/<name>.json`

For `static_synapse`, a minimal file is essentially empty (weights/delays
come from the edge type), but BMTK still expects the file to exist:

```json
{}
```

You can include defaults if desired, e.g. `{"weight": 1.0, "delay": 1.0}`,
but edge-level `syn_weight`/`delay` will override.

## Sanity checks before running

- Every `*_file` path in `networks` exists on disk after `build_network.py`.
- Every `dynamics_params` filename referenced by a node or edge type exists
  in the matching `components/` subdirectory.
- `target_simulator` is `"NEST"`.
- `run.tstop` matches your intended simulation duration (in **ms**).
- `inputs[*].node_set` matches a NetworkBuilder population name.
