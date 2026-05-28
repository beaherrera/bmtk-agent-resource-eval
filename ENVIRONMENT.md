## Python interpreter

```bash
/path/to/your/python
```

Replace `/path/to/your/python` with the absolute path to the Python interpreter
for your BMTK environment.  Examples:

```bash
# Conda env by path
/opt/anaconda3/envs/new_bmtk/bin/python

# System Python (if the env is already activated in the shell)
python
```

`init_trial.py` copies this file into every new trial folder.  The agent reads
it and substitutes `<python-command>` in all skill-file examples accordingly.

If this file is absent from a trial folder the agent will ask you which
environment to use before running any Python commands.
