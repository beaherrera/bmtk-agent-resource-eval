# Skill 01 — Build a BioNet network with `NetworkBuilder`

Use this when you need to create SONATA node and edge files for a recurrent
biophysical network. For external/feedforward inputs, see skill 02.

## Imports

```python
from bmtk.builder.networks import NetworkBuilder
# Optional helpers (only if you need them):
from bmtk.builder.auxi.node_params import positions_columinar  # spatial layouts
from bmtk.builder.auxi.edge_connectors import distance_connector  # distance-based conn
```

## Nodes — the BioNet attribute set

For each population, call `add_nodes(N=..., ...)`. BioNet-relevant keys:

| Key | Required? | Purpose |
|---|---|---|
| `N` | yes | Number of cells in this group. |
| `model_type` | yes | Always `'biophysical'` for BioNet cells. |
| `model_template` | yes | `'ctdb:Biophys1.hoc'` for Allen CellTypes database biophysical models. |
| `model_processing` | yes if `model_template != 'nrn:IntFire1'` | `'aibs_perisomatic'` or `'aibs_allactive'` for Allen Cell Types models with perisomatic or all-active dendrites. |
| `dynamics_params` | yes | Filename (no path) of a JSON in `components/biophysical_neuron_templates/`. |
| `morphology` | yes if `model_template != 'nrn:IntFire1'` | Filename of a morphology file in `components/morphologies/`. Not required if the `model_template` is `nrn:IntFire1`. |
| `pop_name` | optional | Human-readable label, e.g. `'Exc'`. Useful for filtering edges. |
| `ei` | optional | `'e'` or `'i'`. Useful for filtering edges. |
| `location` | optional | Free-form label, e.g. `'L4'`. |
| `positions` | optional | `(N, 3)` array if spatial connectivity is needed. |
| `rotation_angle_xaxis` | optional | Rotate morphologies by this angle (degrees) around the x-axis. |
| `rotation_angle_yaxis` | optional | Rotate morphologies by this angle (degrees) around the y-axis. |
| `rotation_angle_zaxis` | optional | Rotate morphologies by this angle (degrees) around the z-axis. |

### Minimal E/I example

```python
net = NetworkBuilder("cortex")

net.add_nodes(
    N=80, pop_name='Scnn1a',
    positions=positions_columinar(N=80, center=[0, 50.0, 0], max_radius=30.0, height=100.0),
    rotation_angle_yaxis=xiter_random(N=80, min_x=0.0, max_x=2*np.pi),
    rotation_angle_zaxis=xiter_random(N=80, min_x=0.0, max_x=2*np.pi),
    tuning_angle=np.linspace(start=0.0, stop=360.0, num=80, endpoint=False),
    location='VisL4',
    ei='e',
    model_type='biophysical',
    model_template='ctdb:Biophys1.hoc',
    model_processing='aibs_perisomatic',
    dynamics_params='472363762_fit.json',
    morphology='Scnn1a_473845048_m.swc'
)

net.add_nodes(
    N=20, pop_name='PV',
    positions=positions_columinar(N=20, center=[0, 50.0, 0], max_radius=30.0, height=100.0),
    rotation_angle_yaxis=xiter_random(N=20, min_x=0.0, max_x=2*np.pi),
    rotation_angle_zaxis=xiter_random(N=20, min_x=0.0, max_x=2*np.pi),
    location='VisL4',
    ei='i',
    model_type='biophysical',
    model_template='ctdb:Biophys1.hoc',
    model_processing='aibs_perisomatic',
    dynamics_params='472912177_fit.json',
    morphology='Pvalb_470522102_m.swc'
)

net.add_nodes(
    N=200, pop_name='LIF_exc',
    positions=positions_columinar(N=200, center=[0, 50.0, 0], min_radius=30.0, max_radius=60.0, height=100.0),
    tuning_angle=np.linspace(start=0.0, stop=360.0, num=200, endpoint=False),
    location='VisL4',
    ei='e',
    model_type='point_process',
    model_template='nrn:IntFire1',
    dynamics_params='IntFire1_exc_1.json'
)

net.add_nodes(
    N=100, pop_name='LIF_inh',
    positions=positions_columinar(N=100, center=[0, 50.0, 0], min_radius=30.0, max_radius=60.0, height=100.0),
    location='VisL4',
    ei='i',
    model_type='point_process',
    model_template='nrn:IntFire1',
    dynamics_params='IntFire1_inh_1.json'
)
```

## Edges — BioNet attribute set

| Key | Required? | Purpose |
|---|---|---|
| `source`, `target` | yes | Dict filters on node attributes, e.g. `{'ei': 'e'}`. |
| `connection_rule` | yes | Integer, list, matrix, or function (see below). |
| `model_template` | yes | Synapse model: `'exp2syn'` (double-exponential) for biophysical or `nrn:IntFire1` targets. Also valid: `'exp1syn'`, `'AlphaSynapse'`. Do **not** use `'static_synapse'` — that is PointNet-only. |
| `dynamics_params` | yes | JSON filename in `components/synaptic_models/`. Must contain `level_of_detail`, `tau1`, `tau2`, `erev` for `exp2syn`. |
| `syn_weight` | yes | Conductance in µS for biophysical targets. Positive values only — sign of effect is set by `erev` in the synapse JSON (0 mV → excitatory, −70 mV → inhibitory). |
| `delay` | yes | ms. Typically `1.0`–`2.0`. |
| `target_sections` | recommended for biophysical targets | Section filter for synapse placement, e.g. `['soma', 'basal']`. Omit for `nrn:IntFire1` targets. |
| `distance_range` | recommended for biophysical targets | `[min_µm, max_µm]` along the dendrite, e.g. `[30.0, 150.0]`. Omit for `nrn:IntFire1` targets. |
| `weight_function` | optional | Name of a weight function registered with BioNet, e.g. `'gaussianLL'`. |
| `weight_sigma` | optional | σ parameter passed to `weight_function`. |

### Connection rules

A `connection_rule` may be:

- An integer — every (source, target) pair gets that many synapses.
- A function `(source, target, **params) -> int` returning the number of synapses for that pair. Use `connection_params={...}` to pass kwargs.
- With `iterator='all_to_one'`, a function `(sources, target, **params) -> array[len(sources)]`
  that returns a per-source synapse count for one target at a time. This is the idiomatic pattern for feedforward fan-in.

### Recurrent E/I edges example

```python
import random
import math

def dist_tuning_connector(source, target, d_weight_min, d_weight_max, d_max, t_weight_min, t_weight_max, nsyn_min,
                          nsyn_max):
    if source['node_id'] == target['node_id']:
        # Avoid self-connections.n_nodes
        return None

    r = np.linalg.norm(np.array(source['positions']) - np.array(target['positions']))
    if r > d_max:
        dw = 0.0
    else:
        t = r / d_max
        dw = d_weight_max * (1.0 - t) + d_weight_min * t

    if dw <= 0:
        # drop the connection if the weight is too low
        return None

    # next create weights by orientation tuning [ aligned, misaligned ] --> [ 1, 0 ], Check that the orientation
    # tuning property exists for both cells; otherwise, ignore the orientation tuning.
    if 'tuning_angle' in source and 'tuning_angle' in target:

        # 0-180 is the same as 180-360, so just modulo by 180
        delta_tuning = math.fmod(abs(source['tuning_angle'] - target['tuning_angle']), 180.0)

        # 90-180 needs to be flipped, then normalize to 0-1
        delta_tuning = delta_tuning if delta_tuning < 90.0 else 180.0 - delta_tuning

        t = delta_tuning / 90.0
        tw = t_weight_max * (1.0 - t) + t_weight_min * t
    else:
        tw = dw

    # drop the connection if the weight is too low
    if tw <= 0:
        return None

    # filter out nodes by treating the weight as a probability of connection
    if random.random() > tw:
        return None

    # Add the number of synapses for every connection.
    # It is probably very useful to take this out into a separate function.
    return random.randint(nsyn_min, nsyn_max)

### Generating E-to-E connections
net.add_edges(
    source={'ei': 'e'}, target={'pop_name': 'Scnn1a'},
    connection_rule=dist_tuning_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 0.34, 'd_max': 300.0, 't_weight_min': 0.5,
                       't_weight_max': 1.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=5e-05,
    weight_function='gaussianLL',
    weight_sigma=50.0,
    distance_range=[30.0, 150.0],
    target_sections=['basal', 'apical'],
    delay=2.0,
    dynamics_params='AMPA_ExcToExc.json',
    model_template='exp2syn'
)

net.add_edges(
    source={'ei': 'e'}, target={'pop_name': 'LIF_exc'},
    connection_rule=dist_tuning_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 0.34, 'd_max': 300.0, 't_weight_min': 0.5,
                       't_weight_max': 1.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.0019,
    weight_function='gaussianLL',
    weight_sigma=50.0,
    delay=2.0,
    dynamics_params='instantaneousExc.json',
    model_template='exp2syn'
)

### Generating I-to-I connections
net.add_edges(
    source={'ei': 'i'}, target={'ei': 'i', 'model_type': 'biophysical'},
    connection_rule=distance_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 1.0, 'd_max': 160.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.0002,
    weight_function='wmax',
    distance_range=[0.0, 1e+20],
    target_sections=['somatic', 'basal'],
    delay=2.0,
    dynamics_params='GABA_InhToInh.json',
    model_template='exp2syn'
)

net.add_edges(
    source={'ei': 'i'}, target={'ei': 'i', 'model_type': 'point_process'},
    connection_rule=distance_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 1.0, 'd_max': 160.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.001,
    weight_function='wmax',
    delay=2.0,
    dynamics_params='instantaneousInh.json',
    model_template='exp2syn'
)

### Generating I-to-E connections
net.add_edges(
    source={'ei': 'i'}, target={'ei': 'e', 'model_type': 'biophysical'},
    connection_rule=distance_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 1.0, 'd_max': 160.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.0001,
    weight_function='wmax',
    distance_range=[0.0, 50.0],
    target_sections=['somatic', 'basal', 'apical'],
    delay=2.0,
    dynamics_params='GABA_InhToExc.json',
    model_template='exp2syn'
)

net.add_edges(
    source={'ei': 'i'}, target={'ei': 'e', 'model_type': 'point_process'},
    connection_rule=distance_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 1.0, 'd_max': 160.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.009,
    weight_function='wmax',
    delay=2.0,
    dynamics_params='instantaneousInh.json',
    model_template='exp2syn'
)

### Generating E-to-I connections
net.add_edges(
    source={'ei': 'e'}, target={'pop_name': 'PV'},
    connection_rule=distance_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 0.26, 'd_max': 300.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.004,
    weight_function='wmax',
    distance_range=[0.0, 1e+20],
    target_sections=['somatic', 'basal'],
    delay=2.0,
    dynamics_params='AMPA_ExcToInh.json',
    model_template='exp2syn'
)

net.add_edges(
    source={'ei': 'e'}, target={'pop_name': 'LIF_inh'},
    connection_rule=distance_connector,
    connection_params={'d_weight_min': 0.0, 'd_weight_max': 0.26, 'd_max': 300.0, 'nsyn_min': 3, 'nsyn_max': 7},
    syn_weight=0.006,
    weight_function='wmax',
    delay=2.0,
    dynamics_params='instantaneousExc.json',
    model_template='exp2syn'
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
  `components/biophysical_neuron_templates/` (for nodes) or `components/synaptic_models/` (for edges). See skill 03 for the parameter file format.
- Every `morphology` filename you reference must exist in `components/morphologies/`.
- If you use `pop_name` or `ei` as edge filters, make sure those exact attributes were set on the nodes.
- `syn_weight` must be **positive** since they represent conductances in nS.
