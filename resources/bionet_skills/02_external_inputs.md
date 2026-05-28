# Skill 02 — External inputs (virtual cells + spike trains)

Use this when the network needs external drive — for example, a feedforward
"LGN-like" or "thalamic" population that sends spike trains into the recurrent
network. Without external input, cells at rest will stay silent.

For *current-clamp*-style input (no virtual population needed), see the
"Current clamp" section at the bottom.

## Pattern: virtual population + Poisson spikes

### Step 1 — Add a virtual NetworkBuilder

Virtual cells have `model_type='virtual'` and act as spike-train placeholders.

```python
from bmtk.builder.networks import NetworkBuilder

lgn = NetworkBuilder('LGN')
lgn.add_nodes(N=500, pop_name='LGN_exc', model_type='virtual')
```

### Step 2 — Connect virtual → internal cells

BioNet edges use `model_template='exp2syn'` (or `'exp1syn'`). Do **not** use
`'static_synapse'` — that is PointNet-only syntax.

For connections targeting **biophysical cells**, include `target_sections` and
`distance_range` to place synapses on dendrites:

```python
import numpy as np

def select_sources(sources, target, nsources_min=10, nsources_max=25,
                   nsyns_min=3, nsyns_max=8):
    """Each target picks a random subset of LGN sources, each with a random nsyn."""
    n = np.random.randint(nsources_min, nsources_max)
    chosen = np.random.choice(len(sources), n, replace=False)
    syns = np.zeros(len(sources), dtype=int)
    syns[chosen] = np.random.randint(nsyns_min, nsyns_max, size=n)
    return syns

# LGN → biophysical excitatory cells
lgn.add_edges(
    source=lgn.nodes(), target=net.nodes(ei='e', model_type='biophysical'),
    iterator='all_to_one',          # function receives all sources per target
    connection_rule=select_sources,
    syn_weight=5e-05,               # conductance in µS; positive = excitatory
    delay=2.0,
    target_sections=['basal', 'apical'],
    distance_range=[30.0, 150.0],
    model_template='exp2syn',
    dynamics_params='AMPA_ExcToExc.json',
)
```

For connections targeting **`nrn:IntFire1` point-process cells**, omit
`target_sections` and `distance_range`:

```python
# LGN → IntFire1 point-process cells
lgn.add_edges(
    source=lgn.nodes(), target=net.nodes(ei='e', model_type='point_process'),
    iterator='all_to_one',
    connection_rule=select_sources,
    syn_weight=0.002,
    delay=2.0,
    model_template='exp2syn',
    dynamics_params='instantaneousExc.json',
)

lgn.build()
lgn.save(output_dir='network')
```

### Step 3 — Generate the spike-train file

```python
from bmtk.utils.reports.spike_trains import PoissonSpikeGenerator

psg = PoissonSpikeGenerator(population='LGN')
psg.add(
    node_ids=range(500),
    firing_rate=15.0,        # Hz
    times=(0.0, 3.0),        # seconds — must cover the full simulation duration
)
psg.to_sonata('inputs/lgn_spikes.h5')
```

### Step 4 — Reference the spike file in `config.json`

```json
"inputs": {
  "LGN_spikes": {
    "input_type": "spikes",
    "module": "h5",
    "input_file": "$BASE_DIR/inputs/lgn_spikes.h5",
    "node_set": "LGN"
  }
}
```

`node_set` must match the `NetworkBuilder` name (here `'LGN'`), case-sensitive.

## Pattern: current clamp (no virtual cells needed)

Apply a step current to a subset of cells. Add in the `inputs` section of
`config.json`:

```json
"inputs": {
  "iclamp_drive": {
    "input_type": "current_clamp",
    "module": "IClamp",
    "node_set": {
      "population": "cortex",
      "ei": "e"
    },
    "amp": 200.0,
    "delay": 100.0,
    "duration": 2900.0
  }
}
```

`amp` is in pA; `delay` and `duration` are in ms.

## Notes

- Spike file times in `PoissonSpikeGenerator.add(times=...)` are in **seconds**,
  but simulation `tstop` and current-clamp `duration` are in **milliseconds**.
- `PoissonSpikeGenerator(population=...)` must match the `NetworkBuilder` name
  of the virtual cells exactly (case-sensitive).
- `dynamics_params` files must exist in `components/synaptic_models/`. The
  files in `seed_bio_components/synaptic_models/` (`AMPA_ExcToExc.json`,
  `GABA_InhToExc.json`, `instantaneousExc.json`, etc.) are valid starting points.
- For `nrn:IntFire1` targets, omit `target_sections` and `distance_range`.
  Use `instantaneousExc.json` / `instantaneousInh.json` as `dynamics_params`.
