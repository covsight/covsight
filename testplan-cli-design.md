# CovSight Testplan CLI Design

## Overview

This document designs the `covsight testplan` CLI for working with testplan data
described in `testplan-schema.md`. The goal is a complete, ergonomic CLI that
covers the full testplan lifecycle: authoring/validation, format conversion,
inspection, and closure evaluation against a coverage database.

---

## Current state

Three subcommands exist under `covsight testplan`:

| Subcommand | What it does |
|---|---|
| `import` | Embed a testplan (Hjson only) into a `.cdb` file |
| `closure` | Compute testpoint closure against a `.cdb` file |
| `export-junit` | Export closure results as JUnit XML |

**Gaps:**

- Every existing subcommand requires a `.cdb` file — there is no standalone
  testplan tooling.
- `import` only accepts Hjson. The three vendor-format readers (`vpf`,
  `vc_planner`, `questa`) and the canonical YAML reader (`testplan_yaml`) are
  implemented in `covsight-core` but not exposed through the CLI.
- There is no `show`, `validate`, `stats`, or `convert` command.
- The `closure` output only prints a flat table; there is no goal-aware view.

---

## Design: subcommand tree

```
covsight testplan
  ├── show        Display testplan contents (standalone, no DB needed)
  ├── validate    Validate a testplan file against the JSON schema
  ├── stats       Print statistics / metrics about a testplan
  ├── convert     Convert between testplan formats
  ├── import      Embed a testplan into a .cdb file  (extended)
  ├── export      Extract a testplan from a .cdb file
  ├── closure     Compute testpoint closure  (extended)
  └── export-junit  Export closure as JUnit XML
```

Subcommands split into two groups:

- **Standalone** (`show`, `validate`, `stats`, `convert`) — operate on testplan
  files only; no coverage DB required.
- **DB-linked** (`import`, `export`, `closure`, `export-junit`) — require a
  `.cdb` file.

---

## Standalone subcommands

### `covsight testplan show`

Display the contents of a testplan file in a readable form.

```
covsight testplan show [OPTIONS] <testplan>

Arguments:
  testplan              Path to testplan file (.yaml/.yml/.json/.hjson/.testplan)

Options:
  --input-format, -if   Force input format: yaml | json | hjson | vpf |
                        vcplanner | questa  (default: auto-detect from extension)
  --output-format, -of  Output format: text | json | yaml  (default: text)
  --section, -s         Which section(s) to show: all | goals | testpoints |
                        covergroups  (default: all; repeatable)
  --stage               Filter testpoints by stage (e.g. --stage V1 --stage V2)
  --status              Filter goals by status (planned|in_progress|complete|waived)
  --owner               Filter by owner (substring match)
  --tag                 Filter by tag (exact; repeatable)
  --depth, -d           Max goal hierarchy depth to expand (default: unlimited)
  --show-coverage       Include coverage binding paths in testpoint output
  --show-requirements   Include requirement links in testpoint output
  --show-custom         Include custom dicts in output
  --out, -o             Write output to file (default: stdout)
  --subs                Template substitution KEY=VALUE (repeatable)
```

**Text output** renders an indented tree of goals → testpoints → covergroups,
similar to the worked example in `testplan-schema.md`. Each testpoint line
shows: `[stage] name — desc (N tests)`. With `--show-coverage` each binding is
printed on an indented sub-line.

**JSON/YAML output** serialises the fully-resolved `Testplan.to_dict()` after
applying filters. This round-trips cleanly as a CovSight canonical file.

---

### `covsight testplan validate`

Validate a testplan file against the CovSight JSON Schema.

```
covsight testplan validate [OPTIONS] <testplan> [<testplan> ...]

Arguments:
  testplan              One or more testplan files to validate.

Options:
  --input-format, -if   Force input format (as above)
  --subs                Template substitution KEY=VALUE (repeatable)
  --strict              Treat warnings (unknown binding types, etc.) as errors
  --out, -o             Write validation report to file (default: stdout)
  --output-format, -of  text | json  (default: text)
```

Validation steps (in order):

1. **Parse** — attempt to load with `load_testplan()`. Report parse errors.
2. **Schema** — run `validate_testplan()` (JSON Schema Draft 7). Report each
   violation with the JSON path.
3. **Semantic checks** (independent of JSON Schema):
   - Duplicate testpoint names across merged plan (including imports).
   - Circular imports.
   - Coverage binding `type` values outside `CoverageBinding.TYPES`.
   - `weight` ≤ 0.
   - Goals referencing non-existent stage values (warning, not error).
4. **Summary line**: `OK` (exit 0) or `N error(s), M warning(s)` (exit 1).

Multiple files are validated independently; the exit code is non-zero if any
file has errors.

---

### `covsight testplan stats`

Print aggregate statistics about a testplan.

```
covsight testplan stats [OPTIONS] <testplan>

Arguments:
  testplan              Path to testplan file.

Options:
  --input-format, -if   Force input format
  --subs                Template substitution KEY=VALUE (repeatable)
  --output-format, -of  text | json  (default: text)
  --out, -o             Write output to file (default: stdout)
```

**Text output** sections:

```
Testplan: uart  (uart.yaml)
────────────────────────────────────────────────────────────
Goals
  Total:        12  (5 planned, 4 in_progress, 2 complete, 1 waived)
  Max depth:    3

Testpoints
  Total:        47
  By stage:     V1=12  V2=28  V2S=5  V3=2
  N/A:          3
  Unimplemented: 1  (no tests assigned)
  With coverage bindings: 31 / 47 (66%)
  With requirements:      18 / 47 (38%)

Coverage bindings
  Total bindings: 58
  By type:  covergroup=20  coverpoint=25  assertion=8  toggle=5

Covergroups declared: 9  (coverpoints listed: 23)

Imports resolved: 2  (common/csr_testplan.yaml, common/power_testplan.yaml)
```

JSON output is the structured equivalent as a flat dict.

---

### `covsight testplan convert`

Convert a testplan between formats.

```
covsight testplan convert [OPTIONS] <input>

Arguments:
  input                 Input testplan file.

Options:
  --input-format, -if   Force input format: yaml | json | hjson |
                        vpf | vcplanner | questa
                        (default: auto-detect from extension / content)
  --output-format, -of  Output format: yaml | json  (default: yaml)
  --out, -o             Output path (default: stdout)
  --subs                Template substitution KEY=VALUE (repeatable)
  --no-resolve-imports  Write imports[] array as-is; do not flatten
                        (only meaningful for yaml/json → yaml/json;
                        has no effect when importing vendor formats)
```

**Format auto-detection** uses the extension map:

| Extension | Format |
|---|---|
| `.yaml`, `.yml`, `.testplan` | YAML (canonical) |
| `.json` | JSON (canonical) |
| `.hjson` | Hjson (OpenTitan) |
| `.xml` | Sniff root tag: `<testplan>` → VPF, `<vcplanner>` → VC Planner, `<questa_testplan>` → Questa |
| `.csv` | Sniff header columns: `tpGoal`/`tpTest` → VC Planner; `id`/`coverage_path` → Questa |

Vendor-format inputs (VPF, VC Planner, Questa) are read via their dedicated
readers (`testplan_vpf`, `testplan_vc_planner`, `testplan_questa`) which are
already implemented in `covsight-core`. The result is always a `Testplan`
object which is then serialised to the requested output format using
`Testplan.to_dict()`.

`--no-resolve-imports` is meaningful only when the input is already a CovSight
YAML/JSON file that contains `imports[]` entries. When set, the imports list is
preserved in the output rather than being flattened into a single merged plan.

---

## DB-linked subcommands (extended)

### `covsight testplan import` (extended)

The existing command accepts only `hjson_path`. It should be extended to accept
any supported format.

```
covsight testplan import [OPTIONS] <db> <testplan>

Arguments:
  db            Path to the NCDB .cdb file
  testplan      Path to the testplan file (any supported format)

Options:
  --input-format, -if  Force input format (as above)
  --subs               Template substitution KEY=VAL (repeatable; existing)
```

Internally, the command loads the testplan with the appropriate reader (auto-
detected or forced), then embeds the resulting `Testplan` object into the `.cdb`
file — identical to the current behaviour after the reader step.

---

### `covsight testplan export` (new)

Extract a testplan embedded in a `.cdb` file to a standalone file.

```
covsight testplan export [OPTIONS] <db>

Arguments:
  db            Path to the NCDB .cdb file.

Options:
  --output-format, -of  yaml | json  (default: yaml)
  --out, -o             Output file (default: stdout)
```

Reads the embedded `testplan.json` from the `.cdb` and serialises it to the
requested format. Useful for extracting and inspecting or editing an embedded
testplan, or for feeding it back into `covsight testplan show` / `validate`.

---

### `covsight testplan closure` (extended)

Add goal-aware output and a `--show-goals` flag to the existing closure command.

```
covsight testplan closure [OPTIONS] <db>

Existing options:
  --testplan, -t        External testplan file
  --waivers             External waivers file
  --stage               Evaluate a stage gate
  --out, -o             Output file
  --output-format, -of  text | json

New options:
  --show-goals          Display results in goal-tree form rather than a flat table
  --filter-status       Only show testpoints with the given closure status
                        (CLOSED|PARTIAL|FAILING|NOT_RUN|N/A|UNIMP; repeatable)
  --show-coverage       Include per-binding coverage % in the output
                        (requires the DB to expose getCoveragePercent())
```

When `--show-goals` is set, the text output renders the goal hierarchy with
aggregate closure percentages at each goal node, and the individual testpoint
rows indented beneath their goal. This mirrors how Cadence vManager and Questa
Visualizer present the data.

Example:
```
Goal: uart / functional                             83%  (10/12 closed)
  Goal: uart / functional / reset                 100%  ( 2/ 2 closed)
    [V1] uart_reset                               ✓ CLOSED    uart_smoke, uart_reset_test
  Goal: uart / functional / baud                   80%  ( 8/10 closed)
    [V2] uart_baud_rate                            ✓ CLOSED    uart_baud_uart_test
    [V2] uart_baud_rate_high                       ? NOT_RUN   uart_baud_high_test
```

---

## Implementation approach

### File / module layout

All new CLI handlers go in `src/covsight/cli/cmd_testplan.py` (the existing
module). No new CLI modules are needed; the file already owns the `testplan`
subparser.

The format-routing helper (auto-detect + dispatch to the correct reader) belongs
in `covsight-core` since the readers already live there, and so that the same
logic can be used from Python directly. A lightweight function
`load_testplan_any(path, format=None, substitutions=None)` in
`covsight/core/ncdb/testplan_yaml.py` (or a new
`covsight/core/ncdb/testplan_loader.py`) would dispatch to the right reader
based on extension/content sniffing.

### Shared options

The options `--input-format/-if`, `--output-format/-of`, `--subs`, and `--out/-o`
appear on multiple subcommands. Use `argparse` parent parsers to avoid
duplication:

```python
_input_parser = argparse.ArgumentParser(add_help=False)
_input_parser.add_argument("--input-format", "-if", ...)
_input_parser.add_argument("--subs", ...)

_output_parser = argparse.ArgumentParser(add_help=False)
_output_parser.add_argument("--output-format", "-of", ...)
_output_parser.add_argument("--out", "-o", ...)
```

### Exit codes

| Exit code | Meaning |
|---|---|
| 0 | Success |
| 1 | User/input error (file not found, parse error, validation failure) |
| 2 | Internal error / unexpected exception |

---

## Usage examples

```sh
# Show the goal tree of a testplan
covsight testplan show uart.yaml --show-coverage

# Validate before committing
covsight testplan validate chip/testplan.yaml --strict

# Quick statistics for a project
covsight testplan stats subsystem/testplan.yaml

# Convert an OpenTitan testplan to canonical YAML
covsight testplan convert ot_uart.hjson -o uart.yaml

# Convert a Cadence VPF export
covsight testplan convert uart_vmanager.xml --input-format vpf -o uart.yaml

# Embed a YAML testplan into a coverage database
covsight testplan import merged.cdb uart.yaml

# Extract the embedded testplan back out
covsight testplan export merged.cdb -o extracted.yaml

# Closure with goal hierarchy view and coverage %
covsight testplan closure merged.cdb --show-goals --show-coverage

# Stage gate check for CI
covsight testplan closure merged.cdb --stage V2 --output-format json \
  | jq '.stage_gate.passed'
```

---

## Open questions / future work

1. **`testplan diff`** — compare two testplans (e.g. before/after merge) and
   show added/removed/changed testpoints. Useful for PR review.

2. **`testplan lint`** — a stricter semantic-check pass beyond `validate`:
   flag testpoints with no coverage bindings, goals with no testpoints, etc.
   Could be a `--lint` flag on `validate` rather than a separate subcommand.

3. **`testplan report`** — generate a standalone HTML report for a testplan
   (without needing a coverage DB), suitable for design-review documents.

4. **`--output-format html`** on `show` / `closure` — HTML output mirroring
   the structure of vendor report tools.

5. **`testplan check-bindings`** — given a testplan and a coverage DB, report
   which coverage binding paths in the testplan match actual items in the DB
   and which are dangling (no match). Currently only computable through
   `closure`; a standalone check would be useful earlier in the flow.
