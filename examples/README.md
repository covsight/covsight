# Examples

SystemVerilog examples run through Verilator with
[dv-flow](https://github.com/dv-flow/dv-flow-mgr), imported, merged and
checked by covsight. Each one is rendered as a page in the docs (Examples
section), from the output of running it when the docs are built.

| Directory | Shows |
| --- | --- |
| `01-code-basics/` | Line, branch and expression coverage; a hole found and closed |
| `dvflow-verilator/` | The smallest Verilator → covsight flow (not part of the suite) |

## Running

Tools come from ivpm (see the top-level README): `ivpm update -a -d examples`
fetches dv-flow and Verilator 5.052, the version the examples' expected
numbers were recorded with.

```bash
export PATH=$PWD/../packages/python/bin:$PWD/../packages/verilator/bin:$PATH
dfm run all          # every example; fails if any check fails
dfm run docs         # also copies output to docs/source/examples/_gen/
cd 01-code-basics && dfm run all     # one example
```

Output lands in `rundir/` (git-ignored).

## Anatomy of an example

- `design.sv`, `tb.sv` — the design and a self-checking SV testbench (no
  C++; built with `--main --timing`).
- `flow.yaml` — its own dv-flow package: build, run each test, import each
  `coverage.dat` (`covsight.Import`), merge (`covsight.Merge`), keep CLI
  output (`covsight.Show`) and check (`covsight.Check`).
- `expect.yaml` — the merged totals `covsight.Check` requires. Check also
  compares covsight with `verilator_coverage --report summary` and the build
  log's warnings with the `warnings` list; any difference fails the run.
- The docs page is `docs/source/examples/<name>.rst`; the
  `covsight-transcript`, `covsight-parity` and `covsight-download`
  directives pull in the generated output.

To add an example: create its directory, import it in `flow.yaml` here and
add it to the `needs` of `all` and `docs`, add its page to
`docs/source/examples/index.rst`, and its name to `SUITE` in
`tests/dvflow/test_examples.py`.
