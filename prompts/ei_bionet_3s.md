# Benchmark prompt: BioNet multi-population recurrent network, 3 second simulation

Create a complete BMTK model project in the current folder.

## Task

Build a recurrent network of biophysical and integrate-and-fire neurons,
set up a 3 second simulation driven by a virtual LGN population, and provide
everything needed to build and run it.

## Network specification

Four internal populations:

| Population | N  | `model_type`    | `model_template`     | `dynamics_params`      | `morphology`   |
|---|---|---|---|---|---|
| Scnn1a     | 80 | `biophysical`   | `ctdb:Biophys1.hoc`  | `472363762_fit.json`   | `Scnn1a.swc`   |
| PV         | 20 | `biophysical`   | `ctdb:Biophys1.hoc`  | `472912177_fit.json`   | `Pvalb.swc`    |
| LIF_exc    | 200| `point_process` | `nrn:IntFire1`       | `IntFire1_exc_1.json`  | (none)         |
| LIF_inh    | 100| `point_process` | `nrn:IntFire1`       | `IntFire1_inh_1.json`  | (none)         |

All four populations use `model_processing='aibs_perisomatic'` **only** when
`model_template='ctdb:Biophys1.hoc'`. Do not set it on `nrn:IntFire1` nodes.

One external (virtual) population to drive the network:

| Population | N   | `model_type` |
|---|---|---|
| LGN        | 500 | `virtual`    |

## Connectivity

Use distance-dependent connection rules. At minimum include:

- E→E (Scnn1a → Scnn1a), E→I (Scnn1a → PV), I→E (PV → Scnn1a), I→I (PV → PV)
- LIF cross-connections (LIF_exc → LIF_inh, LIF_inh → LIF_exc, etc.)
- LGN → Scnn1a and LGN → LIF_exc feedforward connections

For biophysical targets, set `target_sections` and `distance_range` on edges.
For `nrn:IntFire1` targets, omit both.

## Synapse models

Use `model_template='exp2syn'` for all edges. Assign synapse JSONs from
`components/synaptic_models/`:

- Excitatory connections: `AMPA_ExcToExc.json` or `AMPA_ExcToInh.json`
- Inhibitory connections: `GABA_InhToExc.json` or `GABA_InhToInh.json`
- `nrn:IntFire1` targets: `instantaneousExc.json` / `instantaneousInh.json`

## Simulation parameters

- `tstop`: `3000.0` ms
- `dt`: `0.1` ms
- `dL`: `20.0`
- `spike_threshold`: `-15`
- `nsteps_block`: `5000`
- `conditions`: `{"celsius": 34.0, "v_init": -80}`
- `target_simulator`: `"NEURON"`

Record soma membrane potential (`variable_name: "v"`) for a small sample of
cells (e.g. node_ids 0, 80, 100, 300).

## Constraints

1. Use BMTK's **BioNet** simulator (NEURON). Do **not** use PointNet/NEST.
2. Do **not** download parameter files — all required files are already in
   `components/` (`biophysical_neuron_templates/`, `morphologies/`,
   `synaptic_models/`, `point_neuron_templates/`, `mechanisms/modfiles/`).
3. NEURON `.mod` files in `components/mechanisms/modfiles/` must be compiled
   before the simulation runs. **Run this yourself** before any other step:
   ```bash
   cd components/mechanisms && nrnivmodl modfiles && cd ../..
   ```
4. Use relative paths everywhere. No hard-coded absolute paths.
5. Provide `build_network.py`, `run_bionet.py`, `config.json`, any required
   input-generation scripts, and the compiled mechanisms.
6. After writing the scripts: **actually execute** the following in order and
   confirm each step succeeds before moving on:
   - `<python-command> build_network.py` — must produce HDF5 network files
   - `<python-command> run_bionet.py config.json` — must start without error
     (let it run to completion or until the first timestep prints)
7. At the end, summarize files created and the exact commands to build and run.

## Deliverables

Create the files directly in this project folder. Do not just describe the solution.

## Python environment

Activate your BMTK conda environment before running any Python commands.
See `README.md` for setup instructions.
Do NOT run `pip install` or `conda install` for any packages.
