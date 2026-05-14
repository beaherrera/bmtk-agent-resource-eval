# Skill 04 — Run a PointNet simulation

The canonical `run_pointnet.py` is short. If you generated the project with
`build_env_pointnet` (see skill 03), a working version already exists — you
usually do not need to write this from scratch.

## Minimal `run_pointnet.py`

```python
"""Run a PointNet simulation from a SONATA config."""
import sys
from bmtk.simulator import pointnet


def main(config_path: str = 'config.json') -> None:
    configure = pointnet.Config.from_json(config_path)
    configure.build_env()
    network = pointnet.PointNetwork.from_config(configure)
    sim = pointnet.PointSimulator.from_config(configure, network)
    sim.run()


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'config.json')
```

## Invoking it

```bash
conda run -n BMTK_2023 python run_pointnet.py config.json
```

Or, with MPI on a multi-core machine:

```bash
conda run -n BMTK_2023 mpirun -np 4 python run_pointnet.py config.json
```

## What happens at run time

1. `Config.from_json` reads the JSON and resolves `$BASE_DIR`/`$NETWORK_DIR` etc.
2. `build_env` creates `output/` (and the log file) if needed.
3. `PointNetwork.from_config` loads SONATA nodes/edges, builds NEST cell models
   from each node type's `model_template` + `dynamics_params`, and wires synapses.
4. `PointSimulator.from_config` attaches inputs (spike files, current clamps)
   and configures any reports (multimeters etc.).
5. `sim.run()` advances NEST to `run.tstop` and writes spikes (and any other
   reports) to `output/`.

## Outputs

After a successful run, expect:

```
output/
├── log.txt
├── spikes.h5             # SONATA spike file for all non-virtual populations
└── <report_name>.h5      # one per report defined in config.reports
```

To peek at spikes quickly:

```python
from bmtk.analyzer.spike_trains import plot_raster
plot_raster(config_file='config.json', group_by='pop_name')
```

## If you cannot actually run the simulation

When the environment is unavailable or you want a faster sanity pass, at
least validate that the project is internally consistent:

```bash
conda run -n BMTK_2023 python -m py_compile build_network.py run_pointnet.py
conda run -n BMTK_2023 python -m json.tool config.json > /dev/null
```

See skill 05 for deeper validation patterns.
