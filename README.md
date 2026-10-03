# covsight

## Developer setup

Dependencies are fetched by [ivpm](https://github.com/fvutils/ivpm) into
`packages/`, which also holds the Python virtual environment
(`packages/python`). Pick the dep-set for the work you are doing:

| Dep-set | Use it for | Adds |
| --- | --- | --- |
| `dev` (default) | CLI and analysis work | covsight-core, sphinx-systemverilog, EDA tools |
| `examples` | the SystemVerilog examples and the dv-flow tests | dv-flow, Verilator 5.052 (pinned) |
| `docs` | what the Forgejo docs job installs | `examples` with every dependency pinned, plus Sphinx |

```bash
ivpm update -a -d examples          # --force when switching from another dep-set
uv pip install --python packages/python/bin/python -e ".[dev]"
export PATH=$PWD/packages/python/bin:$PWD/packages/verilator/bin:$PATH
pytest
```

The ivpm venv has no `pip`, so covsight itself is installed with `uv`. After
adding a PyPI dependency to `ivpm.yaml`, run `ivpm update` with
`--py-force-install`; a plain update skips the Python install step.
