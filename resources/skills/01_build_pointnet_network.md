# Skill 01 — Build a PointNet network with `NetworkBuilder`

Use this when you need to create SONATA node and edge files for a recurrent
point-neuron network. For external/feedforward inputs, see skill 02.

## Imports

```python
from bmtk.builder.networks import NetworkBuilder
# Optional helpers (only if you need them):
from bmtk.builder.auxi.node_params import positions_columinar  # spatial layouts
from bmtk.builder.auxi.edge_connectors import distance_connector  # distance-based conn
```

## Nodes — the PointNet attribute set

For each population, call `add_nodes(N=..., ...)`. PointNet-relevant keys:

| Key | Required? | Purpose |
|---|---|---|
| `N` | yes | Number of cells in this group. |
| `model_type` | yes | Always `'point_process'` for PointNet cells. |
| `model_template` | yes | NEST model: `'nest:iaf_psc_alpha'`, `'nest:glif_psc'`, `'nest:iaf_psc_exp'`, etc. |
| `dynamics_params` | yes | Filename (no path) of a JSON in `components/point_neuron_models/`. |
| `pop_name` | optional | Human-readable label, e.g. `'Exc'`. Useful for filtering edges. |
| `ei` | optional | `'e'` or `'i'`. Useful for filtering edges. |
| `location` | optional | Free-form label, e.g. `'L4'`. |
| `positions` | optional | `(N, 3)` array if spatial connectivity is needed. |

**Do not** set `morphology`, `model_processing='aibs_perisomatic'`, or biophysical-only keys
when using PointNet — those are BioNet attributes.

### Minimal E/I example

```python
net = NetworkBuilder("cortex")

net.add_nodes(
    N=80, pop_name='Exc', ei='e',
    model_type='point_process',
    model_template='nest:iaf_psc_alpha',
    dynamics_params='exc_iaf.json',
)
net.add_nodes(
    N=20, pop_name='Inh', ei='i',
    model_type='point_process',
    model_template='nest:iaf_psc_alpha',
    dynamics_params='inh_iaf.json',
)
```

## Edges — PointNet attribute set

| Key | Required? | Purpose |
|---|---|---|
| `source`, `target` | yes | Dict filters on node attributes, e.g. `{'ei': 'e'}`. |
| `connection_rule` | yes | Integer, list, matrix, or function (see below). |
| `model_template` | yes | Almost always `'static_synapse'` for PointNet. |
| `dynamics_params` | yes | JSON filename in `components/synaptic_models/`. |
| `syn_weight` | yes | Numeric. Sign convention: positive for excitatory, negative for inhibitory. |
| `delay` | yes | ms. Typically `1.0`–`2.0`. |

**Do not** set `target_sections`, `distance_range`, or `model_template='Exp2Syn'` —
those are BioNet attributes (PointNet ignores `target_sections`/`distance_range`,
but `Exp2Syn` will break the run).

### Connection rules

A `connection_rule` may be:

- An integer — every (source, target) pair gets that many synapses.
- A function `(source, target, **params) -> int` returning the number of
  synapses for that pair. Use `connection_params={...}` to pass kwargs.
- With `iterator='all_to_one'`, a function `(sources, target, **params) -> array[len(sources)]`
  that returns a per-source synapse count for one target at a time. This is the
  idiomatic pattern for feedforward fan-in.

### Recurrent E/I edges example

```python
def random_conn(source, target, p=0.1, nsyn=4):
    if source['node_id'] == target['node_id']:   # no autapses
        return 0
    import numpy as np
    return nsyn if np.random.random() < p else 0

# E -> E, E -> I, I -> E, I -> I
for src, trg, w, dyn in [
    ('e', 'e',  3.0, 'ExcToExc.json'),
    ('e', 'i',  3.0, 'ExcToInh.json'),
    ('i', 'e', -6.0, 'InhToExc.json'),
    ('i', 'i', -6.0, 'InhToInh.json'),
]:
    net.add_edges(
        source={'ei': src}, target={'ei': trg},
        connection_rule=random_conn,
        connection_params={'p': 0.1, 'nsyn': 4},
        syn_weight=w,
        delay=1.5,
        model_template='static_synapse',
        dynamics_params=dyn,
    )
```

## Build and save

```python
net.build()
net.save(output_dir='network')          # writes both nodes and edges
# Or separately:
# net.save_nodes(output_dir='network')
# net.save_edges(output_dir='network')
```

After this runs you should see files like:

```
network/cortex_nodes.h5
network/cortex_node_types.csv
network/cortex_cortex_edges.h5
network/cortex_cortex_edge_types.csv
```

## Sanity checks

- Every `dynamics_params` filename you reference must exist in
  `components/point_neuron_models/` (for nodes) or `components/synaptic_models/`
  (for edges). See skill 03 for the parameter file format.
- If you use `pop_name` or `ei` as edge filters, make sure those exact attributes
  were set on the nodes.
- Inhibitory `syn_weight` must be **negative** to be inhibitory (NEST does not
  flip sign automatically based on `ei`).
