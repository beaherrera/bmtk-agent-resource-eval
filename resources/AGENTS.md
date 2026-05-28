# AGENTS.md — BMTK PointNet Modeling Guide

Guidance for coding agents helping a user build **BMTK / SONATA point-neuron and biophysically-detailed**
model projects with the PointNet and BioNet simulators (which run on NEST and NEURON, respectively). Targeted at
*using* BMTK, not developing it.

> **Cross-agent file convention.** This project follows the [AGENTS.md](https://agents.md/)
> standard. The same content is mirrored as `CLAUDE.md`, `GEMINI.md`,
> `.clinerules`, `.cursorrules`, and `.github/copilot-instructions.md`, so any
> agent finds the guide regardless of which filename it natively reads.

## Scope

This guide covers **PointNet** (point-neuron networks via NEST) and **BioNet** (biophysically-detailed networks via NEURON) only.
BMTK also supports PopNet and FilterNet, but those are out of scope here.

## PointNet ≠ BioNet — common confusion to avoid

PointNet and BioNet share file formats (SONATA) and the `NetworkBuilder` API,
so it is easy to mix their attributes. Many BMTK examples and tutorials online
default to BioNet (biophysical). 

Prefer PointNet idioms:

| Concern | PointNet (use this) | BioNet (do **not** use here) |
|---|---|---|
| `model_type` on cells | `point_process` | `biophysical` |
| `model_template` on cells | `nest:iaf_psc_alpha`, `nest:glif_psc`, etc. | `ctdb:Biophys1.hoc`, `nrn:IntFire1` |
| Cell extras | (none required) | `morphology`, `model_processing` |
| `model_template` on edges | `static_synapse` | `Exp2Syn`, `Exp1Syn`, `AlphaSynapse` |
| Edge extras | (none required) | `target_sections`, `distance_range` |
| Simulator import | `from bmtk.simulator import pointnet` | `from bmtk.simulator import bionet` |
| `config.target_simulator` | `"NEST"` | `"NEURON"` |

If you find yourself writing `Exp2Syn` or `morphology` and `model_type` is `point_process`, you have drifted into BioNet — stop and switch back to PointNet attributes.

Prefer BioNet idioms:
| Concern | BioNet (use this) | PointNet (do **not** use here) |
|---|---|---|
| `model_type` on cells | `biophysical` | `point_process` |
| `model_template` on cells | `ctdb:Biophys1.hoc`, `nrn:IntFire1` | `nest:iaf_psc_alpha`, `nest:glif_psc`, etc. |
| `morphology` on cells | *.swc or *.asc file if `model_template == ctdb:Biophys1.hoc` | (none required) |
| `model_processing` on cells | `aibs_perisomatic` if `model_template == ctdb:Biophys1.hoc` otherwise (none required) | (none required) |
| `model_template` on edges | `Exp2Syn`, `Exp1Syn`, `AlphaSynapse` | `static_synapse` |
| Edge extras | `target_sections`, `distance_range` | (none required) |
| Simulator import | `from bmtk.simulator import bionet` | `from bmtk.simulator import pointnet` |
| `config.target_simulator` | `"NEURON"` | `"NEST"` |
| `config.run` | `"dL": 20.0` | (none required) |
| `config.run` | `"spike_threshold": -15` | (none required) |
| `config.run` | `"nsteps_block": 5000` | (none required) |
| `config.conditions` | `{"celsius": 34.0, "v_init": -80}` | (none required) |

## Self-contained parameters — no external downloads

Do **not** try to download cell parameter files from the Allen Cell Types
Database or use the Allen SDK. Write small JSON parameter files yourself using
the NEST model's documented parameter names. See
[pointnet_skills/03_simulation_config.md](pointnet_skills/03_simulation_config.md) for a complete
minimal `iaf_psc_alpha` example.

## Environment

- Use the Python interpreter designated by the project `README.md`,
  `ENVIRONMENT.md`, or any trial-specific section appended at the bottom of
  this guide. Run **all** Python commands with that exact interpreter —
  written throughout the skill files as `<python-command>`.
- Verify the interpreter works before starting:
  - PointNet: `<python-command> -c "import bmtk, nest; from bmtk.simulator import pointnet; print('ok')"`
  - BioNet:   `<python-command> -c "import bmtk, neuron; from bmtk.simulator import bionet; print('ok')"`
- If the project does not name an interpreter, **ask the user** which
  environment to use, or clearly state the interpreter you used when
  summarizing your work.
- Do **not** invent host-specific absolute paths in any generated file.
- Do **not** create a new environment or install packages unless the user
  explicitly requested environment setup as part of the task.
- Use relative paths in all configs. No absolute paths.
- Do **not** download Allen Cell Types Database parameter files. For PointNet
  use NEST built-in models (e.g. `nest:iaf_psc_alpha`, `nest:glif_psc`) with
  small JSON files you write yourself. For BioNet use the parameter files
  already present in `components/`.
- A `components/` folder is pre-populated with starter parameter files
  (JSONs, morphologies, mechanisms). Reference them from `dynamics_params` in
  your CSVs, or edit / add files alongside them. Do not delete them.

## Mental model

A BMTK PointNet or BioNet project has three layers:

1. **Network description** — SONATA HDF5 + CSV files describing nodes and edges.
2. **Components** — JSON parameter files for cell models and synapse models.
3. **Simulation config** — JSON describing network files, run parameters, inputs, outputs.

These three layers must stay consistent: the config must point to files that
the build step actually produces, and the JSON parameter files referenced in
`dynamics_params` must exist in `components/`.

## PointNet canonical project layout

```text
<project>/
├── build_network.py            # creates SONATA files in network/
├── run_pointnet.py             # loads config and runs the simulator
├── config.json                 # SONATA simulation config (or simulation_config.json)
├── network/                    # generated by build_network.py
│   ├── <pop>_nodes.h5
│   ├── <pop>_node_types.csv
│   ├── <src>_<trg>_edges.h5
│   └── <src>_<trg>_edge_types.csv
├── components/
│   ├── point_neuron_models/    # cell dynamics_params JSON files
│   └── synaptic_models/        # synapse dynamics_params JSON files
├── inputs/                     # spike-train h5 files (if external input used)
└── output/                     # spike output, logs (created at runtime)
```

## BioNet canonical project layout

```text
<project>/
├── build_network.py            # creates SONATA files in network/
├── run_bionet.py               # loads config and runs the simulator
├── config.json                 # SONATA simulation config (or simulation_config.json)
├── network/                    # generated by build_network.py
│   ├── <pop>_nodes.h5
│   ├── <pop>_node_types.csv
│   ├── <src>_<trg>_edges.h5
│   └── <src>_<trg>_edge_types.csv
├── components/
│   ├── biophysical_neuron_templates/ # cell dynamics_params JSON files
│   ├── morphologies/                 # .swc or .asc morphology files
│   ├── mechanisms/modfiles           # NEURON .mod files (ion channels, synapse models)
│   └── synaptic_models/              # synapse dynamics_params JSON files
│   
├── inputs/                           # spike-train h5 files (if external input used)
└── output/                           # spike output, logs (created at runtime)
```

## Workflow at a glance

```text
        build_network.py  ──writes──▶  network/, components/
        (create_inputs.py)──writes──▶  inputs/  (spike-train h5)
                                          │
                                          ▼
                                      config.json
                                          │
                                          ▼
                          run_pointnet.py or run_bionet.py ──writes──▶  output/
```

## Atomic skills (read only what is relevant to the current task)

Skill files live under `pointnet_skills/` (PointNet) or `bionet_skills/` (BioNet)
in this project. Each file is short and focused — read whichever apply to the
current step, not all of them at once.

### PointNet skills

| Skill | When to read |
|---|---|
| [pointnet_skills/01_build_pointnet_network.md](pointnet_skills/01_build_pointnet_network.md) | Creating nodes and recurrent edges with `NetworkBuilder`. |
| [pointnet_skills/02_external_inputs.md](pointnet_skills/02_external_inputs.md) | Adding virtual cells + spike-train input to drive the network. |
| [pointnet_skills/03_simulation_config.md](pointnet_skills/03_simulation_config.md) | Writing or generating `config.json` and `components/` files. |
| [pointnet_skills/04_run_simulation.md](pointnet_skills/04_run_simulation.md) | Writing `run_pointnet.py` and invoking the simulator. |
| [pointnet_skills/05_validate_and_debug.md](pointnet_skills/05_validate_and_debug.md) | Pre-flight checks, common PointNet pitfalls, smoke tests. |

If `pointnet_skills/` is not present, follow the orientation here and prefer the
[Allen Institute BMTK PointNet tutorial](https://alleninstitute.github.io/bmtk/tutorials/tutorial_05_pointnet_modeling.html)
patterns.

### BioNet skills

| Skill | When to read |
|---|---|
| [bionet_skills/01_build_bionet_network.md](bionet_skills/01_build_bionet_network.md) | Creating biophysical + point-neuron nodes and recurrent edges with `NetworkBuilder`. |
| [bionet_skills/02_external_inputs.md](bionet_skills/02_external_inputs.md) | Adding virtual cells + spike-train input to drive the network. |
| [bionet_skills/03_simulation_config.md](bionet_skills/03_simulation_config.md) | Writing or generating `config.json` and `components/` files (including mechanisms). |
| [bionet_skills/04_run_simulation.md](bionet_skills/04_run_simulation.md) | Writing `run_bionet.py` and invoking the simulator. |
| [bionet_skills/05_validate_and_debug.md](bionet_skills/05_validate_and_debug.md) | Pre-flight checks, common BioNet pitfalls, smoke tests. |

If `bionet_skills/` is not present, follow the orientation here and prefer the
[Allen Institute BMTK BioNet multi-population tutorial](https://alleninstitute.github.io/bmtk/tutorials/tutorial_04_multi_pop.html)
patterns.

## General principles (apply to all skills)

- **Produce runnable files**, not just descriptions. The user wants something
  they can execute.
- **Start small** when uncertain. A working 10-cell network is more useful than
  a speculative 10,000-cell network. Scale up only after the small version runs.
- **Match what you build to what the config references.** Filenames in
  `config.json` must match files actually generated by `build_network.py`.
- **PointNet is simulator-specific.** Use `model_type='point_process'` and
  `model_template='nest:<model>'` for cells, and `model_template='static_synapse'`
  for edges. Do **not** use BioNet-only attributes like `Exp2Syn`,
  `target_sections`, `distance_range`, `morphology`, or `model_processing='aibs_perisomatic'`.
- **Summarize at the end.** Report populations created, connection classes,
  simulation duration, output paths, and the exact commands needed to reproduce.

## Reference

- BMTK docs: https://alleninstitute.github.io/bmtk/
- PointNet tutorial: https://alleninstitute.github.io/bmtk/tutorials/tutorial_05_pointnet_modeling.html
- NetworkBuilder intro: https://alleninstitute.github.io/bmtk/tutorials/NetworkBuilder_Intro.html
- Examples (PointNet): https://github.com/AllenInstitute/bmtk/tree/develop/examples (`point_120cells`, `point_450glifs`, `point_iclamp`)
- SONATA spec: https://github.com/AllenInstitute/sonata/blob/master/docs/SONATA_DEVELOPER_GUIDE.md
