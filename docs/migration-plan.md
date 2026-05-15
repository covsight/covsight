# Documentation Migration Plan: pyucis → covsight

## Overview

The pyucis project has a comprehensive Sphinx documentation tree at
`../pyucis/doc/source/`. This plan describes how to migrate and adapt that
content for the covsight project, accounting for differences in package name,
command name, architecture, and missing features.

### Key substitutions

| pyucis | covsight |
|--------|----------|
| `ucis` (CLI command) | `covsight` |
| `pyucis` (PyPI / install name) | `covsight` |
| `pip install pyucis` | `pip install covsight` |
| `ucis.*` (Python modules) | `covsight.core.*` |
| `pyucis-mcp-server` | *(not yet implemented)* |
| `ucis view` (TUI) | *(not yet implemented)* |

### Covsight CLI commands (confirmed present)

`convert`, `merge`, `show` (summary, gaps, covergroups, bins, tests, hierarchy,
metrics, compare, hotspots, code-coverage, assertions, toggle), `report`,
`history`, `testplan`

---

## Sphinx infrastructure (create from scratch)

The pyucis `conf.py` references `ucis`-specific paths, extensions, and metadata.
Create a new `docs/source/conf.py` for covsight:

- Project name: `covsight`
- Package path: `src/` (namespace: `covsight`, `covsight.core`)
- Same extensions: `sphinx.ext.autodoc`, `sphinx.ext.napoleon`,
  `sphinx.ext.intersphinx`, `sphinx.ext.autosectionlabel`,
  `sphinxarg.ext`, `sphinx_design`
- Same theme: `sphinx_rtd_theme`
- Update `issues_github_path` to `covsight/covsight`
- Update copyright

Also create: `docs/source/index.rst`, `docs/requirements.txt`.

---

## Category A — Direct adapt (mechanical substitution + light rewrite)

These files have content that maps 1:1 to covsight. The main work is renaming
`ucis` → `covsight` in commands, and `pyucis` → `covsight` in package references.
Argparse autodoc directives must point to `covsight.cli.main:build_parser`.

### Getting Started

| Source file | Destination | Notes |
|---|---|---|
| `getting-started/index.rst` | `docs/source/getting-started/index.rst` | Rename project, update intro sentence |
| `getting-started/installation.rst` | `docs/source/getting-started/installation.rst` | `pip install pyucis` → `pip install covsight`; remove MCP extras section (not yet available); `ucis --help` → `covsight --help` |
| `getting-started/quickstart.rst` | `docs/source/getting-started/quickstart.rst` | All `ucis convert/merge/report/view` commands become `covsight …`; remove `ucis view` step (TUI not present); replace with `covsight show summary` as step 2 alternative |

### Importing Coverage

| Source file | Destination | Notes |
|---|---|---|
| `importing/index.rst` | `docs/source/importing/index.rst` | Light edits; format detection example uses `covsight.core` |
| `importing/verilator.rst` | `docs/source/importing/verilator.rst` | `ucis convert` → `covsight convert`; same flags |
| `importing/cocotb.rst` | `docs/source/importing/cocotb.rst` | Same as above |
| `importing/avl.rst` | `docs/source/importing/avl.rst` | Same as above |

### Working with Coverage

| Source file | Destination | Notes |
|---|---|---|
| `working-with-coverage/index.rst` | `docs/source/working-with-coverage/index.rst` | Remove TUI reference from step list |
| `working-with-coverage/merging.rst` | `docs/source/working-with-coverage/merging.rst` | `ucis merge` → `covsight merge`; content is accurate |
| `working-with-coverage/analyzing.rst` | `docs/source/working-with-coverage/analyzing.rst` | `ucis show` → `covsight show`; all sub-commands match |
| `working-with-coverage/comparing.rst` | `docs/source/working-with-coverage/comparing.rst` | `ucis show compare` → `covsight show compare` |
| `working-with-coverage/test-history.rst` | `docs/source/working-with-coverage/test-history.rst` | Module refs: `ucis.ncdb.*` → `covsight.core.ncdb.*` |
| `working-with-coverage/testplan.rst` | `docs/source/working-with-coverage/testplan.rst` | Module refs: `ucis.ncdb.*` → `covsight.core.ncdb.*`; CLI: `pyucis testplan` → `covsight testplan` |
| `working-with-coverage/reports.rst` | `docs/source/working-with-coverage/reports.rst` | Module refs: `ucis.ncdb.reports` → `covsight.core.ncdb.reports`; CLI: `pyucis testplan export-junit` → `covsight testplan export-junit` |

### Reporting

| Source file | Destination | Notes |
|---|---|---|
| `reporting/index.rst` | `docs/source/reporting/index.rst` | Light edits |
| `reporting/html-report.rst` | `docs/source/reporting/html-report.rst` | `ucis report` → `covsight report`; upload-artifact YAML updated |
| `reporting/exporting.rst` | `docs/source/reporting/exporting.rst` | `ucis show code-coverage` → `covsight show code-coverage` |

### CI/CD Integration

| Source file | Destination | Notes |
|---|---|---|
| `cicd/index.rst` | `docs/source/cicd/index.rst` | Light edits |
| `cicd/github-actions.rst` | `docs/source/cicd/github-actions.rst` | `pip install pyucis` → `pip install covsight`; `ucis` → `covsight` throughout |
| `cicd/gitlab-ci.rst` | `docs/source/cicd/gitlab-ci.rst` | Same substitutions |
| `cicd/jenkins.rst` | `docs/source/cicd/jenkins.rst` | Same substitutions |

### Reference — Formats

| Source file | Destination | Notes |
|---|---|---|
| `reference/formats/index.rst` | `docs/source/reference/formats/index.rst` | Light edits |
| `reference/formats/ncdb-format.rst` | `docs/source/reference/formats/ncdb-format.rst` | Technically accurate; only mention of "PyUCIS" in narrative prose needs updating to "covsight" |
| `reference/formats/xml-interchange.rst` | `docs/source/reference/formats/xml-interchange.rst` | Standard description; update any `pyucis`/`ucis` CLI references |
| `reference/formats/yaml-format.rst` | `docs/source/reference/formats/yaml-format.rst` | Same |
| `reference/formats/sqlite-schema.rst` | `docs/source/reference/formats/sqlite-schema.rst` | Same |

### Reference — Report Formats

| Source file | Destination | Notes |
|---|---|---|
| `reference/report-formats/index.rst` | `docs/source/reference/report-formats/index.rst` | Light edits |
| `reference/report-formats/html-report-format.rst` | `docs/source/reference/report-formats/html-report-format.rst` | CLI examples: `pyucis report` → `covsight report` |
| `reference/report-formats/json-report-format.rst` | `docs/source/reference/report-formats/json-report-format.rst` | JSON schema path: `src/ucis/schema/` → `src/covsight/schema/` (or covsight-core); verify schema exists |

---

## Category B — Significant rewrite required

These files contain content that is correct in structure but requires substantive
changes because the Python API module paths have moved to `covsight.core.*` and
some API classes may have been renamed.

### `introduction.rst` → `docs/source/introduction.rst`

Full rewrite. The pyucis introduction describes the UCIS C API, in-memory, SQLite,
XML, YAML, and verilator backends as first-class pyucis features, and includes long
code examples using `ucis.*` classes.

For covsight:
- Lead with what covsight is: a coverage analysis tool built on `covsight-core`
- Briefly describe the data model (same underlying UCIS concepts)
- Replace all code examples using `from ucis.mem import MemFactory` etc. with
  `from covsight.core.mem import MemFactory` (verify actual module paths in covsight-core)
- Remove the "SQLite backend" deep-dive section (that's a covsight-core internal)
- Update MCP / TUI sections to mark them as upcoming / not yet available
- Keep the command-line tools section, updated to `covsight` command

### `reference/index.rst` → `docs/source/reference/index.rst`

Rewrite the intro paragraph (currently describes pyucis devs/integrators). Keep
the toctree structure but adjust entries to drop items not applicable to covsight.

### `reference/python-api/index.rst` → `docs/source/reference/python-api/index.rst`

The Python API for covsight lives in `covsight.core.*`. Update all module references.
Verify the actual submodule layout in `packages/covsight-core/python/covsight/core/`.

### `reference/python-api/oo-api.rst` → `docs/source/reference/python-api/oo-api.rst`

Heavy edit:
- All `.. autoclass:: ucis.*` directives must become `.. autoclass:: covsight.core.*`
- Verify each class still exists under the same relative path in covsight-core
- Classes confirmed present (from exploring covsight-core): `mem.MemFactory`, `mem.MemUCIS`,
  `mem.MemCovergroup`, `mem.MemCoverpoint`, etc.; `visitors.*`; `merge.*`; `api.*`
- Update class hierarchy diagram to use `covsight.core` prefix

### `reference/python-api/c-style-api.rst` → `docs/source/reference/python-api/c-style-api.rst`

Currently a thin stub pointing at `ucis.__init__`. Verify whether covsight-core
exposes a C-style flat API; if not, replace with a note pointing users to the
OO API, or drop this page.

### `reference/best-practices.rst` → `docs/source/reference/best-practices.rst`

Mostly general advice (cross-bin naming conventions) — still relevant. Update any
API references (`ucis.*` → `covsight.core.*`).

### `reference/cli.rst` → `docs/source/reference/cli.rst`

Currently uses `.. argparse:: :module: ucis.__main__ :func: get_parser`. Update to:
```rst
.. argparse::
   :module: covsight.cli.main
   :func: build_parser
   :prog: covsight
```

---

## Category C — Defer (features not yet in covsight)

These docs cover features that exist in pyucis but have not yet been ported to
covsight. Create placeholder stub pages that note the feature is coming.

| pyucis doc | Reason to defer |
|---|---|
| `working-with-coverage/exploring-tui.rst` | covsight has no `view` / TUI command |
| `ai-integration/mcp-server.rst` + `mcp_server.rst` | covsight has no MCP server |
| `reference/native-c-library.rst` | pyucis-specific C binding; covsight-core exposes Python only |

---

## Category D — pyucis-specific; do not migrate

These are internal pyucis documents that have no equivalent in covsight.

| File | Reason |
|---|---|
| `reference/sqlite-api.rst` / `reference/sqlite_api.rst` / `reference/sqlite_schema_reference.rst` | pyucis-specific SQLite backend; covsight-core uses NCDB by default |
| `reference/ucis_c_api.rst` / `reference/ucis_oo_api.rst` | Legacy stubs superseded by `reference/python-api/` |
| `reference/native_api.rst` | Same |
| `reference/xml_interchange.rst` / `reference/yaml_coverage.rst` | Superseded by `reference/formats/` |
| `tui.rst` / `show_commands.rst` / `commands.rst` | Superseded by working-with-coverage guides and `reference/cli.rst` |
| `cocotb_avl_coverage_import.rst` / `verilator_coverage_import.rst` | Superseded by `importing/` tree |
| `doc/README.md`, `doc/ApiDesign.md`, `doc/UcisLrmNotes.md`, `doc/Requirements.md` | pyucis development notes; not user-facing |

---

## Recommended destination directory structure

```
docs/
├── requirements.txt          # Sphinx deps (sphinx, sphinx_rtd_theme, sphinxarg.ext, sphinx_design)
└── source/
    ├── conf.py
    ├── index.rst
    ├── introduction.rst
    ├── getting-started/
    │   ├── index.rst
    │   ├── installation.rst
    │   └── quickstart.rst
    ├── importing/
    │   ├── index.rst
    │   ├── verilator.rst
    │   ├── cocotb.rst
    │   └── avl.rst
    ├── working-with-coverage/
    │   ├── index.rst
    │   ├── merging.rst
    │   ├── analyzing.rst
    │   ├── comparing.rst
    │   ├── test-history.rst
    │   ├── testplan.rst
    │   └── reports.rst
    ├── reporting/
    │   ├── index.rst
    │   ├── html-report.rst
    │   └── exporting.rst
    ├── cicd/
    │   ├── index.rst
    │   ├── github-actions.rst
    │   ├── gitlab-ci.rst
    │   └── jenkins.rst
    └── reference/
        ├── index.rst
        ├── cli.rst
        ├── best-practices.rst
        ├── python-api/
        │   ├── index.rst
        │   ├── oo-api.rst
        │   └── c-style-api.rst
        ├── formats/
        │   ├── index.rst
        │   ├── ncdb-format.rst
        │   ├── xml-interchange.rst
        │   ├── yaml-format.rst
        │   └── sqlite-schema.rst
        └── report-formats/
            ├── index.rst
            ├── html-report-format.rst
            └── json-report-format.rst
```

---

## Suggested work order

1. **Sphinx infrastructure** — `conf.py`, `requirements.txt`, top-level `index.rst`
2. **Getting started** — highest user value; installation + quickstart
3. **Category A files in bulk** — mostly mechanical; can be scripted with sed for
   the `ucis` → `covsight` and `pyucis` → `covsight` substitutions, then reviewed manually
4. **Importing** — verilator, cocotb, avl
5. **Working with coverage** — merging, analyzing, comparing (the TUI page is deferred)
6. **Reporting + CI/CD** — html-report, exporting, github-actions, gitlab-ci, jenkins
7. **Reference formats** — ncdb-format (largest file; ~1400 lines), others
8. **Reference Python API** — requires verifying covsight.core module paths
9. **Introduction rewrite**
10. **Deferred stubs** — TUI, MCP server placeholders

---

## Notes and open questions

- **JSON report schema path**: `json-report-format.rst` references
  `src/ucis/schema/covreport.json`. Verify whether this schema has been copied to
  `src/covsight/` or whether it lives in `covsight-core`. Update the `.. jsonschema::`
  directive accordingly, or remove it if the schema moved out of this repo.

- **`autoclass` module paths**: Before writing the Python API docs, run a quick
  `find packages/covsight-core/python -name "*.py"` to confirm the exact module
  layout and verify each class referenced in pyucis's `oo-api.rst` still exists
  under `covsight.core.*`.

- **`sphinxarg.ext` integration**: The `build_parser` function in
  `src/covsight/cli/main.py` (not `get_parser` as in pyucis) is the right target
  for the `.. argparse::` directive. Confirm the function name before writing
  `reference/cli.rst`.

- **Deferred features**: When MCP server and TUI land in covsight, the corresponding
  deferred docs can be adapted from pyucis with the same Category A approach.
