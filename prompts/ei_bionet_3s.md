# Benchmark prompt: BioNet multi-population recurrent network, 3 second simulation

Create a complete BMTK model project in the current folder.

## Task

Build a recurrent network with both biophysical and integrate-and-fire neurons,
driven by a virtual LGN input population, and set up a 3 second simulation.

## Network specification

Four internal populations:

| Population | N   | Cell type                        |
|---|---|---|
| Scnn1a     | 80  | biophysical (excitatory)         |
| PV         | 20  | biophysical (inhibitory)         |
| LIF_exc    | 200 | integrate-and-fire (excitatory)  |
| LIF_inh    | 100 | integrate-and-fire (inhibitory)  |

One external (virtual) input population:

| Population | N   |
|---|---|
| LGN        | 500 |

Parameter files for all cell types and synapse models are already provided
in `components/`. Use them — do **not** download replacements from the internet.

## Connectivity

Include at minimum:

- Recurrent connections among biophysical cells: Scnn1a→Scnn1a, Scnn1a→PV,
  PV→Scnn1a, PV→PV
- Recurrent connections among LIF cells: LIF_exc→LIF_inh, LIF_inh→LIF_exc
- Feedforward drive from LGN to at least one excitatory population

## Simulation

- Duration: **3000 ms**
- Target simulator: **NEURON** (BioNet)
- Record soma membrane potential for a small sample of cells

## Constraints

1. Use BMTK's **BioNet** simulator (NEURON). Do **not** use PointNet/NEST.
2. Do **not** download parameter files. Use only what is already in `components/`.
3. NEURON `.mod` files in `components/mechanisms/modfiles/` must be compiled
   before the simulation runs. **Run this yourself** before any other step:
   ```bash
   cd components/mechanisms && nrnivmodl modfiles && cd ../..
   ```
4. Use relative paths everywhere. No hard-coded absolute paths.
5. Provide `build_network.py`, `run_bionet.py`, and `config.json`.
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
