# Skill 05 — Validate and debug a BioNet project

Use this skill before declaring a project complete, or when a simulation
fails. It covers a pre-flight checklist, a smoke test, and a catalog of
BioNet-specific pitfalls.

## Pre-flight checklist

Run through these before claiming the project is ready:

- [ ] `build_network.py` exists and parses (`<python-command> -m py_compile build_network.py`).
- [ ] `run_bionet.py` exists and parses.
- [ ] `config.json` exists and parses (`<python-command> -m json.tool config.json`).
- [ ] `config.target_simulator == "NEURON"`.
- [ ] `config.run.tstop` is the intended duration in **ms**.
- [ ] Every file path in `config.networks` resolves to a real file after build.
- [ ] Every `dynamics_params` filename referenced by node types exists in
      `components/biophysical_neuron_templates/` or `components/point_neuron_templates/`.
- [ ] Every `morphology` filename referenced by node types exists in `components/morphologies/`.
- [ ] Every `dynamics_params` filename referenced by edge types exists in
      `components/synaptic_models/`.
- [ ] `output_dir` exists or will be created at runtime.
- [ ] If inputs are present: `inputs[*].input_file` exists, and
      `inputs[*].node_set` matches a NetworkBuilder population name.

## Smoke test

A two-stage smoke test catches most failures fast.

Use the interpreter command from `AGENTS.md`, `README.md`, or `ENVIRONMENT.md`
(`<python-command>` below):

```bash
# Stage 1 — build the network
<python-command> build_network.py
ls network/                                  # confirm nodes/edges files exist

# Stage 2 — initialize the simulator without running long
<python-command> -c "
from bmtk.simulator import bionet
c = bionet.Config.from_json('config.json')
c.build_env()
net = bionet.BioNetwork.from_config(c)
sim = bionet.BioSimulator.from_config(c, net)
print('Init OK. Populations:', list(net.node_populations))
"
```

If stage 2 succeeds, run the full simulation per skill 04. If stage 2 fails,
the traceback usually points directly at the broken reference (missing file,
unknown NEURON parameter, bad attribute).

## Common BioNet failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `KeyError` on `Exp2Syn` / `model_template not found` | Used a BioNet synapse template. | Set `model_template='exp2syn'` on edges. |
| All cells silent, no spikes | No input drive. | Add external spikes (skill 02) or a current clamp. |
| Cells fire at network step 0 forever | Resting parameters above threshold. | Check `E_L < V_th` in cell `dynamics_params`. |
| `FileNotFoundError` on a `*.json` | `dynamics_params` filename doesn't match what's on disk. | Reconcile node/edge type CSV references with `components/`. |
| `FileNotFoundError` on `*_nodes.h5` | Config references the wrong NetworkBuilder name. | Filenames are `<networkbuilder_name>_nodes.h5`. |
| `NEURONError: unknown parameter ...` | Cell `dynamics_params` JSON has keys not accepted by the chosen NEURON model. | Check the NEURON model docs; drop unknown keys. |
| Build script seems to succeed but no edge files | Missing `net.save_edges(...)` or `net.save(...)`. | After `net.build()`, call `net.save(output_dir='network')`. |

## Static checks worth running

```bash
# JSON validity
<python-command> -m json.tool config.json > /dev/null

# Python syntax
<python-command> -m py_compile build_network.py run_bionet.py

# Quick consistency probe: which dynamics_params / morphologies are referenced and exist?
<python-command> - <<'PY'
import json, pathlib, csv
root = pathlib.Path('.')
referenced = set()
for csv_path in root.glob('network/*_node_types.csv'):
    for row in csv.DictReader(csv_path.open(), delimiter=' '):
        if row.get('dynamics_params'):
            referenced.add(('biophysical_neuron_templates', row['dynamics_params']))
for csv_path in root.glob('network/*_edge_types.csv'):
    for row in csv.DictReader(csv_path.open(), delimiter=' '):
        if row.get('dynamics_params'):
            referenced.add(('synaptic_models', row['dynamics_params']))
missing = [(d, f) for d, f in referenced
           if not (root / 'components' / d / f).exists()]
print('Referenced dynamics_params files:', len(referenced))
print('Missing:', missing or 'none')
PY
```

## When to ask the user instead of guessing

- Whether to use full biophysical cells (`ctdb:Biophys1.hoc`) or NEURON
  integrate-and-fire neurons (`nrn:IntFire1`) — they have very different
  parameter requirements (morphology + channel JSON vs a two-parameter JSON).
- Whether custom NEURON `.mod` files have already been compiled. If not,
  `nrnivmodl components/mechanisms/modfiles` must be run before `run_bionet.py`.
- Which morphology files (`.swc`) are available in `components/morphologies/`.
  If none, default to `nrn:IntFire1` for point neurons and say so.
- The desired input drive (LGN-style virtual population + spike trains vs
  current clamp vs both).
- Whether the simulation must actually be executed, or just produced.
