# Skill 02 — External inputs (virtual cells + spike trains)

Use this when the network needs external drive — for example, a feedforward
"LGN-like" or "thalamic" population that sends spike trains into the recurrent
network. Without external input, a network of LIF cells at rest will simply
stay silent (or fire at a low spontaneous rate determined by parameters).

For *current-clamp*-style input (no virtual population needed), see the
"Current clamp" section at the bottom.

## Pattern: virtual population + Poisson spikes

### Step 1 — Add a virtual NetworkBuilder

Virtual cells have `model_type='virtual'` and act as spike-train placeholders.

```python
from bmtk.builder.networks import NetworkBuilder

lgn = NetworkBuilder('LGN')
lgn.add_nodes(N=100, pop_name='ext_exc', model_type='virtual')
```

### Step 2 — Connect virtual → internal cells

```python
import numpy as np

def select_sources(sources, target, nsources_min=10, nsources_max=20,
                   nsyns_min=3, nsyns_max=8):
    """Each target picks a random subset of sources, each with a random nsyn."""
    n = np.random.randint(nsources_min, nsources_max)
    chosen = np.random.choice(len(sources), n, replace=False)
    syns = np.zeros(len(sources), dtype=int)
    syns[chosen] = np.random.randint(nsyns_min, nsyns_max, size=n)
    return syns

lgn.add_edges(
    source=lgn.nodes(), target=net.nodes(ei='e'),   # `net` is the recurrent NetworkBuilder
    iterator='all_to_one',          # important: function gets all sources per target
    connection_rule=select_sources,
    syn_weight=5.0,
    delay=1.5,
    model_template='static_synapse',
    dynamics_params='ExcToExc.json',
)

lgn.build()
lgn.save(output_dir='network')
```

### Step 3 — Generate the spike-train file

```python
from bmtk.utils.reports.spike_trains import PoissonSpikeGenerator

psg = PoissonSpikeGenerator(population='LGN')
psg.add(
    node_ids=range(100),
    firing_rate=10.0,        # Hz, can also be an array/function for nonhomogeneous
    times=(0.0, 5.0),        # seconds — covers the simulation duration
)
psg.to_sonata('inputs/lgn_spikes.h5')
```

### Step 4 — Reference the spike file in `config.json`

The `inputs` section connects the spike file to the virtual node population
(see skill 03 for the full config):

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

`node_set` must match the NetworkBuilder name (here `'LGN'`).

## Pattern: current clamp (no virtual cells needed)

A simpler alternative for testing — apply a step current to a subset of cells.
Add this in the `inputs` section of `config.json` instead of (or alongside)
spike-train input:

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
    "duration": 4900.0
  }
}
```

`amp` is in pA. `delay` and `duration` are in ms.

You may have multiple inputs in the same config (e.g. one current clamp plus
one spike file); BMTK applies all of them.

## Notes

- Spike file times in `PoissonSpikeGenerator.add(times=...)` are in **seconds**,
  but the simulation `tstop` and current-clamp `duration` are in **milliseconds**.
- Match the population name passed to `PoissonSpikeGenerator(population=...)`
  to the NetworkBuilder name of the virtual cells (case-sensitive).
- For deterministic spike trains (e.g. for reproducibility), seed numpy
  before calling `PoissonSpikeGenerator`.
