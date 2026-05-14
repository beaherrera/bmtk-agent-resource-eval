# Benchmark prompt: PointNet E/I recurrent network, 5 second simulation

Create a complete BMTK model project in the current folder.

## Task

Build a small recurrent network of excitatory and inhibitory **point neurons**
(LIF or GLIF), set up a 5 second simulation, and provide everything needed to
run it.

## Constraints

1. Use BMTK's **PointNet** simulator (which runs on NEST). Do not use BioNet /
   NEURON / biophysical cell models.
2. Cells must be point neurons. Use NEST built-in models such as
   `nest:iaf_psc_alpha` or `nest:glif_psc`. Do **not** download parameter
   files from the Allen Cell Types Database or use the Allen SDK — write
   small JSON parameter files yourself.
3. Include at least two cell classes: excitatory and inhibitory.
4. Include recurrent connectivity between the populations. At minimum include
   E→E, E→I, and I→E; I→I is preferred.
5. `tstop` must be `5000.0` ms.
6. Provide a network build script, a simulation run script, any required
   parameter / config / component files, and use relative paths so the
   project can be moved.
7. Validate the generated files as much as possible (parse JSON, parse Python,
   try to load the simulator).
8. At the end, summarize the files created and the commands needed to build
   and run the simulation.

## Deliverables

Create the files in this project folder. Do not just describe the solution.

## Starter material

A `components/` folder is already present in this project with example NEST
parameter JSONs (`iaf_exc.json`, `iaf_inh.json`, `static_exc.json`,
`static_inh.json`). You may reference them from your node_types and
edge_types CSVs as-is, edit them, or add new ones. Use these instead of
downloading parameter sets from the Allen Cell Types Database.

## Python environment

Use conda env `BXP2` (BMTK 1.0.6 + NEST 3.0). On this host the system NEST
is broken and shadows the conda env's NEST via `PYTHONPATH`. Always run
python like this:

```bash
unset PYTHONPATH
LD_LIBRARY_PATH=/home/dhaufler/anaconda3/envs/BXP2/lib \
  /home/dhaufler/anaconda3/envs/BXP2/bin/python <script.py>
```

Do NOT use `conda run -n BXP2 ...` (it inherits the broken `PYTHONPATH`).
Do NOT use envs `BMTK_2023` or `bmtk` (broken NEST). Do NOT pip/conda install
anything.
