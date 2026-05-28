# Skill 04 — Run a BioNet simulation

The canonical `run_bionet.py` is short. If you generated the project with
`build_env_bionet` (see skill 03), a working version already exists — you
usually do not need to write this from scratch.

## Minimal `run_bionet.py`

```python
"""Run a BioNet simulation from a SONATA config."""
import sys
from bmtk.simulator import bionet


def main(config_path: str = 'config.json') -> None:
    configure = bionet.Config.from_json(config_path)
    configure.build_env()
    network = bionet.BioNetwork.from_config(configure)
    sim = bionet.BioSimulator.from_config(configure, network)
    sim.run()


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'config.json')
```

## Invoking it

Use the interpreter command from `AGENTS.md`, `README.md`, or `ENVIRONMENT.md`
for the current project (referred to as `<python-command>` throughout):

```bash
<python-command> run_bionet.py config.json
```

Or, with MPI on a multi-core machine:

```bash
mpirun -np 4 <python-command> run_bionet.py config.json
```

## What happens at run time

1. `Config.from_json` reads the JSON and resolves `$BASE_DIR`/`$NETWORK_DIR` etc.
2. `build_env` creates `output/` (and the log file) if needed.
3. `BioNetwork.from_config` loads SONATA nodes/edges, builds NEURON representation of the network, cell models from each node type's `model_template` + `dynamics_params` are converted into their NEURON equivalents and wires synapses.
4. `BioSimulator.from_config` attaches inputs (spike files, current clamps) and configures any reports (multimeters etc.).
5. `sim.run()` sets up and runs NEURON simulation to `run.tstop` and writes spikes (and any other reports) to `output/`.

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

When the environment is unavailable or you want a faster sanity pass, at least validate that the project is internally consistent:

```bash
<python-command> -m json.tool config.json > /dev/null
<python-command> -m py_compile build_network.py run_bionet.py
```

See skill 05 for deeper validation patterns.
