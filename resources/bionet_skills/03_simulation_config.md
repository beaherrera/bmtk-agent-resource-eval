# Skill 03 — Simulation config and `components/` parameter files

The simulation config is a SONATA JSON file that ties together network files,
components, run parameters, inputs, and outputs. There are two ways to create
it: use BMTK's built-in generator (recommended), or write it by hand.

## Option A — Use `build_env_bionet` (recommended)

BMTK ships a helper that scaffolds the config plus a working `run_bionet.py`:

```python
from bmtk.utils.sim_setup import build_env_bionet

build_env_bionet(
    base_dir='.',
    config_file='config.json',
    network_dir='network',
    tstop=3000.0, dt=0.1,
    report_vars=['v'],     # Record membrane potential (default soma)
    include_examples=True,    # Copies components files
    compile_mechanisms=True   # Will try to compile NEURON mechanisms
)
```

This produces a `config.json` (or split `circuit_config.json` +
`simulation_config.json`), a stub `run_bionet.py`, and seeds `components/`
with example parameter files you can then customize.

Equivalent CLI form:

```bash
<python-command> -m bmtk.utils.sim_setup --report-vars v --report-nodes 0,80,100,300 \
    --network network --dt 0.1 --tstop 3000.0 --include-examples --compile-mechanisms bionet .
```

After generation, edit the file paths in the config so they reference the
files your `build_network.py` actually produced (the helper uses generic names).

## Option B — Write `config.json` by hand

Minimum viable Bionet config:

```json
{
  "manifest": {
    "$BASE_DIR": ".",
    "$NETWORK_DIR": "$BASE_DIR/network",
    "$COMPONENT_DIR": "$BASE_DIR/components",
    "$OUTPUT_DIR": "$BASE_DIR/output",
    "$INPUT_DIR": "$BASE_DIR/inputs"
  },
  "target_simulator": "NEURON",
  "run": {
    "tstop": 3000.0,
    "dt": 0.1,
    "dL": 20.0,
    "spike_threshold": -15,
    "nsteps_block": 5000
  },
  "conditions": {
    "celsius": 34.0,
    "v_init": -80
  },

  "components": {
    "morphologies_dir": "$COMPONENT_DIR/morphologies",
    "synaptic_models_dir": "$COMPONENT_DIR/synaptic_models",
    "mechanisms_dir":"$COMPONENT_DIR/mechanisms",
    "biophysical_neuron_models_dir": "$COMPONENT_DIR/biophysical_neuron_templates",
    "point_neuron_models_dir": "$COMPONENT_DIR/point_neuron_templates"
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
  "cells": { "population": "cortex", "node_ids": [0,80,100,300] },
  "variable_name": "v",
  "module": "multimeter_report",
  "sections": "soma"
}
```

## `components/` — cell and synapse parameter JSON files

Files referenced via `dynamics_params` must live in the right subdirectory.

### Cell parameters: `components/biophysical_neuron_templates/<name>.json`

For `ctdb:Biophys1.hoc`, a complete minimal file:

```json
{
  "passive": [
    {
      "ra": 32.0772432623, 
      "cm": [
        {
          "section": "soma", 
          "cm": 1.0
        }, 
        {
          "section": "axon", 
          "cm": 1.0
        }, 
        {
          "section": "dend", 
          "cm": 3.7002019468166822
        }, 
        {
          "section": "apic", 
          "cm": 3.7002019468166822
        }
      ], 
      "e_pas": -84.74527740478516
    }
  ], 
  "fitting": [
    {
      "junction_potential": -14.0, 
      "sweeps": [
        46
      ]
    }
  ], 
  "conditions": [
    {
      "celsius": 34.0, 
      "erev": [
        {
          "ena": 53.0, 
          "section": "soma", 
          "ek": -107.0
        }
      ], 
      "v_init": -84.74527740478516
    }
  ], 
  "genome": [
    {
      "section": "soma", 
      "name": "gbar_Im", 
      "value": 0.00011215709095308002, 
      "mechanism": "Im"
    }, 
    {
      "section": "soma", 
      "name": "gbar_Ih", 
      "value": 0.00045041730360183556, 
      "mechanism": "Ih"
    }, 
    {
      "section": "soma", 
      "name": "gbar_NaTs", 
      "value": 1.1281486914123688, 
      "mechanism": "NaTs"
    }, 
    {
      "section": "soma", 
      "name": "gbar_Nap", 
      "value": 0.00095782168667023497, 
      "mechanism": "Nap"
    }, 
    {
      "section": "soma", 
      "name": "gbar_K_P", 
      "value": 0.096648124440568361, 
      "mechanism": "K_P"
    }, 
    {
      "section": "soma", 
      "name": "gbar_K_T", 
      "value": 2.2406204607139379e-05, 
      "mechanism": "K_T"
    }, 
    {
      "section": "soma", 
      "name": "gbar_SK", 
      "value": 0.0068601737830082388, 
      "mechanism": "SK"
    }, 
    {
      "section": "soma", 
      "name": "gbar_Kv3_1", 
      "value": 0.33043773066721083, 
      "mechanism": "Kv3_1"
    }, 
    {
      "section": "soma", 
      "name": "gbar_Ca_HVA", 
      "value": 0.00026836177945335608, 
      "mechanism": "Ca_HVA"
    }, 
    {
      "section": "soma", 
      "name": "gbar_Ca_LVA", 
      "value": 0.0077938181828292709, 
      "mechanism": "Ca_LVA"
    }, 
    {
      "section": "soma", 
      "name": "gamma_CaDynamics", 
      "value": 0.00044743022380752001, 
      "mechanism": "CaDynamics"
    }, 
    {
      "section": "soma", 
      "name": "decay_CaDynamics", 
      "value": 998.99266101400383, 
      "mechanism": "CaDynamics"
    }, 
    {
      "section": "soma", 
      "name": "g_pas", 
      "value": 0.00091710033541291013, 
      "mechanism": ""
    }, 
    {
      "section": "axon", 
      "name": "g_pas", 
      "value": 0.00074804303211946897, 
      "mechanism": ""
    }, 
    {
      "section": "dend", 
      "name": "g_pas", 
      "value": 0.00016449702719528828, 
      "mechanism": ""
    }, 
    {
      "section": "apic", 
      "name": "g_pas", 
      "value": 4.4606771501076728e-05, 
      "mechanism": ""
    }
  ]
}
```

For `nrn:IntFire1`, a complete minimal file:
```json
{
  "tau": 0.024, 
  "type": "NEURON_IntFire1",
  "refrac": 0.003
}
```

### Synapse parameters: `components/synaptic_models/<name>.json`

For `exp2syn`, a minimal file:

```json
{
  "level_of_detail": "exp2syn",
  "tau1": 1.0,
  "tau2": 3.0,
  "erev": 0.0
}
```

For `model_template='exp2syn'` and `dynamics_params='instantaneousExc.json'`:
```json
{
  "level_of_detail": "instantaneous",
  "sign": 1
}
```

For `model_template='exp2syn'` and `dynamics_params='instantaneousInh.json'`:
```json
{
  "level_of_detail": "instantaneous",
  "sign": -1
}
```

## Sanity checks before running

- Every `*_file` path in `networks` exists on disk after `build_network.py`.
- Every `dynamics_params` filename referenced by a node or edge type exists in the matching `components/` subdirectory.
- Every `morphology` filename referenced by a node type exists in `components/morphologies/`.
- `target_simulator` is `"NEURON"`.
- `run.dL`, `run.spike_threshold`, and `run.nsteps_block` are present and matches your intended simulation settings.
- `run.tstop` matches your intended simulation duration (in **ms**).
- `inputs[*].node_set` matches a NetworkBuilder population name.
