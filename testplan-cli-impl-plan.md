# Testplan CLI — Implementation, Test, and Documentation Plan

> **Status: DRAFT — for review**
>
> Companion documents: `testplan-schema.md` (data model),
> `testplan-cli-design.md` (UX design).

---

## Scope and priorities

**YAML is the canonical authoring format.** All new CLI work targets YAML/JSON
as the primary input/output. Multi-vendor format support (VPF, VC Planner,
Questa) is handled through a **format registry** described below; vendor readers
are already implemented in `covsight-core` but are out of scope for the initial
CLI milestone and marked as deferred.

**What is in scope:**

| Subcommand | New or Extended | Phase |
|---|---|---|
| `testplan show` | New | 1 |
| `testplan validate` | New | 1 |
| `testplan stats` | New | 1 |
| `testplan convert` (YAML ↔ JSON only) | New | 1 |
| `testplan import` — all formats via registry | Extended | 2 |
| `testplan export` | New | 2 |
| `testplan closure --show-goals --filter-status --show-coverage` | Extended | 3 |
| Format registry + vendor readers plumbed into CLI | Deferred | — |

---

## Current state (starting baseline)

### `covsight` CLI (`src/covsight/cli/cmd_testplan.py`)

| Subcommand | Status |
|---|---|
| `testplan import <db> <hjson_path>` | Exists; hjson-only |
| `testplan closure <db>` | Exists; flat-table output only |
| `testplan export-junit <db>` | Exists |

### `covsight-core` (already done — no changes needed to core in Phase 1)

| Module | Relevant public API |
|---|---|
| `testplan.py` | `Testplan`, `Goal`, `Testpoint`, `CoverageBinding`, `iter_testpoints()` |
| `testplan_yaml.py` | `load_testplan(path, substitutions)`, `validate_testplan(dict)` |
| `testplan_imports.py` | `resolve_imports()`, `ParseError` |
| `testplan_closure.py` | `compute_closure()`, `stage_gate_status()`, `TPStatus` |
| `testplan_export.py` | `export_junit_xml()`, `export_github_annotations()`, `export_summary_markdown()` |
| `testplan_vpf.py` | `import_vpf()` — deferred |
| `testplan_vc_planner.py` | `import_vc_planner()` — deferred |
| `testplan_questa.py` | `import_questa()` — deferred |
| `reports.py` | `report_testpoint_closure()`, `format_testpoint_closure()`, etc. |
| `schema/testplan.schema.json` | JSON Schema for validation |

---

## Phase 1 — Standalone subcommands

### 1.1 Format loader helper

**File:** `src/covsight/cli/cmd_testplan.py`

A private helper used by all Phase 1 commands:

```python
def _load_plan(args) -> Testplan:
    """Load a testplan from args.testplan using args.input_format and args.subs."""
```

- Parses `--subs KEY=VAL` into a `dict[str, list[str]]` (multi-value allowed).
- Calls `load_testplan(args.testplan, substitutions=subs)` from
  `covsight.core.ncdb.testplan_yaml`.
- Raises `SystemExit(1)` with a readable message on `ParseError` or
  `FileNotFoundError`.
- `--input-format` is accepted but only `yaml | json | hjson | auto` are wired
  in Phase 1. Other values produce an actionable error pointing to the deferred
  registry (Phase 2).

### 1.2 Shared `argparse` parent parsers

Defined once at module level in `cmd_testplan.py` and passed as `parents=` to
each subparser:

```python
_P_INPUT  # --input-format, -if  /  --subs KEY=VAL (append)
_P_OUTPUT # --output-format, -of (text|json|yaml)  /  --out, -o
```

### 1.3 `covsight testplan show`

**Handler:** `cmd_testplan_show(args)`

**Argument parsing:**

```
show <testplan>
  parents: _P_INPUT, _P_OUTPUT
  --section, -s       {all,goals,testpoints,covergroups}  append; default all
  --stage             append; filter testpoints by stage
  --status            append; filter goals by status
  --owner             filter by owner (substring)
  --tag               append; filter by tag (exact)
  --depth, -d         int; max goal depth to render (default unlimited)
  --show-coverage     flag; include coverage bindings
  --show-requirements flag; include requirement links
  --show-custom       flag; include custom dicts
```

**Output format: `text`**

Renders an indented goal tree. Each indentation level = 2 spaces.

```
[plan] uart  (uart.yaml)
  Goal: functional — Functional verification  [in_progress]
    Goal: reset — Reset behavior  [complete]
      [V1] uart_reset                    2 tests
           uart_smoke, uart_reset_test
    Goal: baud — Baud rate  [planned]
      [V2] uart_baud_rate    ★ high     1 tests
           uart_baud_uart_test
  Covergroups: uart_cg  (2 coverpoints)
```

With `--show-coverage` each testpoint's coverage bindings are listed below it:

```
      [V2] uart_baud_rate    ★ high     1 tests
           uart_baud_uart_test
           ↳ coverpoint  uart_env.uart_cg.baud_rate_cp
```

Filters are applied before rendering; filtered-out nodes are omitted entirely.
A `--depth 1` shows only top-level goals without recursion.

**Output format: `json` / `yaml`**

Calls `plan.to_dict()` (after applying in-memory filters if section filters are
given) and serialises with `json.dumps(indent=2)` or `yaml.dump()`. This is a
valid CovSight canonical file.

### 1.4 `covsight testplan validate`

**Handler:** `cmd_testplan_validate(args)`

**Argument parsing:**

```
validate <testplan> [<testplan> ...]   (nargs='+')
  parents: _P_INPUT, _P_OUTPUT
  --strict   flag; treat warnings as errors
```

**Validation pipeline per file:**

1. **Parse** via `_load_plan()`. Catch `ParseError`, `FileNotFoundError`,
   `yaml.YAMLError`, `json.JSONDecodeError` — each becomes an error item.
2. **JSON Schema** via `validate_testplan(plan.to_dict())`.
   - Requires `jsonschema`; if missing, emit a warning and skip (do not fail).
3. **Semantic checks** (own code in handler):
   - Coverage binding `type` not in `CoverageBinding.TYPES` → warning (error
     with `--strict`).
   - `weight <= 0` → error.
   - Goals with no `id` → warning.
   - Top-level `name` missing → warning.
4. **Output** — one line per finding: `ERROR`, `WARNING`, path, message.
5. **Summary** line: `OK` or `N error(s), M warning(s)`.
6. **Exit code**: 0 if all files clean (no errors; warnings OK unless `--strict`).

**Text output example:**

```
uart.yaml: ERROR   testpoints/1/weight: weight must be >= 1
uart.yaml: WARNING testpoints/0/coverage/0: unknown binding type 'fg'
uart.yaml: 1 error(s), 1 warning(s)
common/csr_testplan.yaml: OK
```

### 1.5 `covsight testplan stats`

**Handler:** `cmd_testplan_stats(args)`

**Argument parsing:**

```
stats <testplan>
  parents: _P_INPUT, _P_OUTPUT
```

**Computed statistics:**

| Group | Items |
|---|---|
| Plan | name, source file, format_version, import count |
| Goals | total, by status (planned/in_progress/complete/waived), max depth |
| Testpoints | total, by stage (dict), N/A count, unimplemented count, with_coverage count, with_requirements count |
| Coverage bindings | total bindings, by type (dict) |
| Covergroups declared | count, total coverpoints listed |

**Text output** — fixed-width aligned blocks (see design doc example).

**JSON output** — flat `dict` with one key per statistic, suitable for `jq`
queries or CI dashboards.

### 1.6 `covsight testplan convert`

**Handler:** `cmd_testplan_convert(args)`

**Argument parsing:**

```
convert <input>
  parents: _P_INPUT, _P_OUTPUT  (output default: yaml)
  --no-resolve-imports   flag; preserve imports[] in output
```

**Phase 1 scope:** YAML ↔ JSON ↔ Hjson only. `--input-format` values `vpf`,
`vcplanner`, `questa` produce an actionable error: _"vendor format support is
not yet wired; use covsight-core directly"_.

**Logic:**

1. Load via `_load_plan(args)`.
2. If `--no-resolve-imports` and the input was already a CovSight file, preserve
   the `imports[]` list from the raw dict (re-read raw, skip merge, build plan
   without flattening). Otherwise the default `load_testplan()` call already
   resolves imports.
3. Serialise `plan.to_dict()` to `--output-format`.
4. Write to `--out` or stdout.

---

## Phase 2 — DB-linked extensions

### 2.1 Format registry (covsight-core)

**File:** `packages/covsight-core/python/covsight/core/ncdb/testplan_loader.py`
(new module in core)

```python
def load_testplan_any(path: str,
                      format: str | None = None,
                      substitutions: dict | None = None) -> Testplan:
    """Load a testplan from any supported format.

    Format is auto-detected from the file extension when *format* is None.
    Pass an explicit format string to override detection.

    Supported format strings: "yaml", "json", "hjson", "vpf", "vcplanner",
    "questa".  Raises ValueError for unrecognised format strings.
    """
```

**Auto-detection logic** (used when `format=None`):

| Extension | Format |
|---|---|
| `.yaml`, `.yml`, `.testplan` | yaml |
| `.json` | json |
| `.hjson` | hjson |
| `.xml` | Sniff root tag: `<testplan>` → vpf, `<vcplanner>` → vcplanner, `<questa_testplan>` → questa |
| `.csv` | Sniff header columns to distinguish vcplanner vs questa |

**Registry:** A module-level `dict[str, Callable[[str], Testplan]]` maps format
strings to loader functions. This makes the registry extensible from Python
without CLI changes; future callers (plugins, scripts) use the same registry as
the CLI.

```python
_LOADERS: dict[str, Callable] = {
    "yaml":      _load_yaml,
    "json":      _load_json,
    "hjson":     _load_hjson,
    "vpf":       _load_vpf,       # delegates to testplan_vpf.import_vpf
    "vcplanner": _load_vcplanner,
    "questa":    _load_questa,
}
```

This module has no CLI dependency and can be used directly from Python.

### 2.2 Extended `testplan import`

Update `cmd_testplan_import` in `cmd_testplan.py`:

- Replace `import_hjson(args.hjson_path)` with
  `load_testplan_any(args.testplan, format=args.input_format, substitutions=subs)`.
- Rename positional arg from `hjson_path` to `testplan`.
- Add `--input-format` (default `auto`).

**Backward compatibility:** The positional argument name in help text changes
from `hjson_path` to `testplan`. The old name is not exposed in the CLI
interface (no `--` flag), so this is not a breaking change for scripts that pass
the argument positionally.

### 2.3 New `testplan export`

**Handler:** `cmd_testplan_export(args)`

```
export <db>
  parents: _P_OUTPUT  (output default: yaml)
```

**Logic:**

1. Open `.cdb` via `_open_ncdb(args.db)`.
2. Call `get_testplan(db)` from `covsight.core.ncdb.testplan`.
3. If `None` → error: "no testplan embedded; use 'testplan import' first".
4. Serialise `plan.to_dict()` to `--output-format`.
5. Write to `--out` or stdout.

---

## Phase 3 — Closure enhancements

### 3.1 `--show-goals` tree rendering

When `--show-goals` is set the text formatter walks the `Testplan.goals` tree
(using `iter_testpoints()` per goal sub-tree to compute per-goal aggregates)
and renders indented goal nodes with aggregate stats, then testpoint rows beneath.

For each `Goal`:
- Compute `closed / total` from the `TestpointResult` list for testpoints under
  that goal (recursive).
- Render: `Goal: <path>  <pct>%  (<closed>/<total> closed)`.
- Render child goals recursively.
- Render testpoints at this goal level.

Testpoints not nested under any goal are shown at the top level as before.

### 3.2 `--filter-status`

After `compute_closure()`, filter `results` to only those whose `status.value`
is in the provided set. Status names are matched case-insensitively. Invalid
values produce an error listing the valid choices.

```
--filter-status CLOSED --filter-status NOT_RUN
```

### 3.3 `--show-coverage`

When set, include per-binding coverage % in the text output below each
testpoint row (requires the DB to expose `getCoveragePercent`). If the DB does
not support it, emit a single `(coverage % unavailable for this DB format)` note
and continue.

---

## Testing plan

Tests live in two places mirroring the code split:

- **Core library tests**: `packages/covsight-core/tests/ncdb/` — existing
  location for `test_testplan*.py`. No new test files needed here for CLI work;
  `testplan_loader.py` tests go in a new `test_testplan_loader.py`.
- **CLI tests**: `tests/` in the `covsight` package. New file
  `tests/test_cli_testplan.py`.

### New core test: `test_testplan_loader.py`

(Phase 2 — tests for `testplan_loader.py`)

| Test | Description |
|---|---|
| `test_auto_detect_yaml` | `.yaml` extension → yaml loader called |
| `test_auto_detect_json` | `.json` → json loader |
| `test_auto_detect_hjson` | `.hjson` → hjson loader |
| `test_explicit_format_overrides_extension` | `format="json"` on a `.yaml` file → json parser |
| `test_unknown_format_raises` | `format="foo"` → `ValueError` |
| `test_xml_vpf_sniff` | `.xml` with `<testplan>` root → vpf loader |
| `test_xml_vcplanner_sniff` | `.xml` with `<vcplanner>` root → vcplanner loader |
| `test_xml_questa_sniff` | `.xml` with `<questa_testplan>` root → questa loader |
| `test_result_is_testplan` | Returned object is `Testplan` instance |

### New CLI test: `tests/test_cli_testplan.py`

Uses `subprocess.run([sys.executable, "-m", "covsight", "testplan", ...])` or
`click.testing.CliRunner` if the CLI is refactored to Click (it currently uses
argparse, so subprocess is the right approach). A `tmp_path` pytest fixture
provides a scratch directory.

A shared fixture `uart_yaml` writes a minimal but non-trivial testplan YAML to
`tmp_path/uart.yaml`:

```yaml
$schema: "https://schema.covsight.io/testplan/v1"
format_version: 1
name: uart
owner: dv-team
substitutions:
  name: uart
goals:
  - id: functional
    title: Functional verification
    status: in_progress
    goals:
      - id: reset
        title: Reset behavior
        status: complete
        testpoints:
          - name: uart_reset
            stage: V1
            desc: Verify UART recovers cleanly after reset.
            tests: [uart_smoke, uart_reset_test]
            coverage:
              - type: covergroup
                path: uart_env.uart_reset_cg
      - id: baud
        title: Baud rate
        status: planned
        testpoints:
          - name: uart_baud_rate
            stage: V2
            priority: high
            tests: [uart_baud_{name}_test]
            coverage:
              - type: coverpoint
                path: uart_env.uart_cg.baud_rate_cp
covergroups:
  - name: uart_cg
    desc: UART functional coverage
    coverpoints:
      - name: baud_rate_cp
        path: uart_env.uart_cg.baud_rate_cp
      - name: parity_cp
        path: uart_env.uart_cg.parity_cp
```

#### `show` tests

| Test | Command | Assertion |
|---|---|---|
| `test_show_text_default` | `show uart.yaml` | exit 0; stdout contains "uart_reset", "uart_baud_rate", "uart_cg" |
| `test_show_json` | `show uart.yaml -of json` | exit 0; output is valid JSON; `json.loads` succeeds; `["name"] == "uart"` |
| `test_show_yaml` | `show uart.yaml -of yaml` | exit 0; `yaml.safe_load` succeeds; `["name"] == "uart"` |
| `test_show_section_goals` | `show uart.yaml -s goals` | stdout contains "functional", not "uart_cg" |
| `test_show_section_testpoints` | `show uart.yaml -s testpoints` | stdout contains "uart_reset" |
| `test_show_section_covergroups` | `show uart.yaml -s covergroups` | stdout contains "uart_cg", not "uart_reset" |
| `test_show_filter_stage` | `show uart.yaml --stage V1` | stdout contains "uart_reset", not "uart_baud_rate" |
| `test_show_filter_status` | `show uart.yaml --status complete` | stdout contains "reset" goal, not "baud" goal |
| `test_show_depth_1` | `show uart.yaml -d 1` | stdout contains "functional" but not "reset" or "baud" |
| `test_show_coverage` | `show uart.yaml --show-coverage` | stdout contains "uart_env.uart_cg.baud_rate_cp" |
| `test_show_out_file` | `show uart.yaml -o out.json -of json` | file created; valid JSON |
| `test_show_missing_file` | `show no_such.yaml` | exit 1; stderr contains "not found" |

#### `validate` tests

| Test | Command | Assertion |
|---|---|---|
| `test_validate_ok` | `validate uart.yaml` | exit 0; stdout contains "OK" |
| `test_validate_multiple_ok` | `validate uart.yaml uart.yaml` | exit 0; two "OK" lines |
| `test_validate_bad_weight` | testplan with `weight: 0` | exit 1; stderr/stdout contains "weight" |
| `test_validate_unknown_binding_type` | testplan with `type: "fg"` | exit 0 without `--strict`; contains "WARNING" |
| `test_validate_strict_unknown_binding` | same + `--strict` | exit 1 |
| `test_validate_missing_file` | `validate no_such.yaml` | exit 1 |
| `test_validate_json_output` | `validate uart.yaml -of json` | exit 0; valid JSON with `"errors": []` |

#### `stats` tests

| Test | Command | Assertion |
|---|---|---|
| `test_stats_text` | `stats uart.yaml` | exit 0; contains "Testpoints", "Goals", "2" (testpoint count) |
| `test_stats_json` | `stats uart.yaml -of json` | exit 0; valid JSON; `["testpoints"]["total"] == 2` |
| `test_stats_by_stage` | `stats uart.yaml -of json` | `["testpoints"]["by_stage"]["V1"] == 1` |
| `test_stats_with_coverage` | `stats uart.yaml -of json` | `["testpoints"]["with_coverage"] == 2` |
| `test_stats_goals_depth` | `stats uart.yaml -of json` | `["goals"]["max_depth"] == 2` |

#### `convert` tests

| Test | Command | Assertion |
|---|---|---|
| `test_convert_yaml_to_json` | `convert uart.yaml -of json` | exit 0; valid JSON output |
| `test_convert_yaml_to_json_file` | `convert uart.yaml -of json -o out.json` | file created; valid JSON |
| `test_convert_json_to_yaml` | `convert uart.json -of yaml` | exit 0; valid YAML |
| `test_convert_roundtrip` | yaml→json→yaml | parsed name matches original |
| `test_convert_vendor_format_deferred` | `convert foo.xml -if vpf` | exit 1; error mentions "not yet wired" |
| `test_convert_with_subs` | `convert templ.yaml --subs name=uart` | expanded test names in output |

#### CLI smoke extension

Extend `tests/test_cli_smoke.py`:

```python
def test_testplan_help():
    r = subprocess.run([..., "testplan", "--help"], ...)
    assert "show" in r.stdout
    assert "validate" in r.stdout
    assert "stats" in r.stdout
    assert "convert" in r.stdout
```

---

## Documentation plan

### User guide

**New file:** `docs/testplan-cli.md`

Sections:

1. **Quick start** — create a minimal `uart.yaml`, run `show`, `validate`,
   `stats`. Three commands, each with annotated output.
2. **Authoring a testplan** — link to `testplan-schema.md`; show a complete
   YAML example; explain `substitutions`, `imports`, `custom`.
3. **Validating testplans** — `validate` usage; how to read error output; CI
   integration snippet (run `covsight testplan validate` in pre-commit or CI).
4. **Inspecting testplans** — `show` with filters; `show -of json | jq` recipes.
5. **Getting statistics** — `stats` output explained; `stats -of json` for
   dashboards.
6. **Format conversion** — `convert` usage for YAML ↔ JSON and for Hjson
   (OpenTitan) → YAML; a note on vendor formats (deferred; link to registry
   section).
7. **Embedding in a coverage database** — `import` and `export`; when to embed
   vs. keep standalone.
8. **Closure evaluation** — `closure`; `--show-goals`; `--stage` gate; CI
   JUnit / GitHub Annotations exports.
9. **Format registry** (stub or appendix) — note that vendor readers exist in
   `covsight-core` and will be wired via the registry in a future release.

### API docs (Sphinx)

No new public API is added to `covsight-core` in Phase 1. Phase 2 adds
`testplan_loader.py`:

- Docstring on `load_testplan_any()` follows the pattern in `testplan_yaml.py`.
- Add to `docs/api/testplan.rst` under a new "Format loader" section.

---

## Implementation order and dependencies

```
Phase 1
  1. Shared argparse parent parsers (_P_INPUT, _P_OUTPUT) in cmd_testplan.py
  2. _load_plan() helper
  3. cmd_testplan_show  → tests
  4. cmd_testplan_validate  → tests
  5. cmd_testplan_stats  → tests
  6. cmd_testplan_convert  → tests
  7. testplan-cli.md user guide (can be written alongside or after the above)

Phase 2
  8. testplan_loader.py in covsight-core  → test_testplan_loader.py
  9. Extend cmd_testplan_import to use load_testplan_any
 10. cmd_testplan_export  → tests

Phase 3
 11. --show-goals renderer for closure  → tests
 12. --filter-status, --show-coverage flags  → tests
 13. Update docs

Deferred (Phase 4 / future)
 14. Wire VPF, VC Planner, Questa readers into format registry CLI
 15. --output-format html on show / closure
 16. testplan diff
 17. testplan lint (semantic checks beyond validate)
 18. testplan check-bindings
```

Items within each phase are independent and can be implemented in parallel.
Phase 2 depends on Phase 1 only in the sense that the shared parent parsers and
`_load_plan()` should exist before writing `import` / `export`; the core
`testplan_loader.py` module has no dependency on Phase 1 CLI work.

---

## File change summary

### `covsight` package

| File | Change |
|---|---|
| `src/covsight/cli/cmd_testplan.py` | Major extension: add `show`, `validate`, `stats`, `convert`, `export`; extend `import`; add `--show-goals`, `--filter-status`, `--show-coverage` to `closure` |
| `tests/test_cli_testplan.py` | New; all Phase 1 and 2 CLI tests |
| `tests/test_cli_smoke.py` | Add `test_testplan_help` |
| `docs/testplan-cli.md` | New user guide |

### `covsight-core` package

| File | Change |
|---|---|
| `python/covsight/core/ncdb/testplan_loader.py` | New; format registry and `load_testplan_any()` |
| `tests/ncdb/test_testplan_loader.py` | New; unit tests for the loader |
| `docs/api/testplan.rst` | Add "Format loader" section |
