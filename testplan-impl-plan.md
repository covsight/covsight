# Testplan Schema — Implementation, Test, and Documentation Plan

> **Status: COMPLETE** — All 13 implementation tasks have been finished.
> See the test coverage summary at the bottom for test file details.

This document is the detailed implementation plan for bringing the Python
back-end, test suite, and Sphinx documentation up to the level described in
`docs/testplan-schema.md`.

Each section identifies the **current state**, the **gap**, the **work
required** (file-by-file), and the **test strategy** for that area.

---

## Overview of gaps

The schema design in `testplan-schema.md` is substantially richer than what is
currently implemented in `python/covsight/core/ncdb/testplan*.py`.

| Area | Designed | Implemented |
|---|---|---|
| Goals hierarchy | ✅ | ❌ |
| Top-level plan metadata (`name`, `owner`, `tags`, …) | ✅ | ❌ |
| `imports[]` with transitive resolution | ✅ | ❌ |
| Top-level `substitutions` dict | ✅ | partial (hjson reader only) |
| `Testpoint.coverage[]` bindings | ✅ | ❌ |
| `Testpoint.owner`, `priority`, `weight` | ✅ | ❌ |
| `custom` dicts on every object | ✅ | ❌ |
| `CovergroupEntry.coverpoints[]` with paths | ✅ | ❌ |
| YAML/JSON canonical reader for new schema | ✅ | ❌ |
| Compatibility reader: Cadence VPF XML | ✅ | ❌ |
| Compatibility reader: Synopsys VC Planner CSV/XML | ✅ | ❌ |
| Compatibility reader: Siemens Questa XML/CSV | ✅ | ❌ |
| JSON Schema / validator | ✅ | ❌ |
| Goal-aware closure computation | ✅ | ❌ |
| Coverage-binding closure (coverage % per testpoint) | ✅ | ❌ |
| Sphinx API docs for new public classes | ✅ | ❌ |
| User guide: authoring testplans | ✅ | ❌ |
| User guide: compatibility import | ✅ | ❌ |

---

## 1. Data model (`testplan.py`)

### Current state

`Testplan` holds a flat `testpoints: List[Testpoint]` and
`covergroups: List[CovergroupEntry]`.  No hierarchy, no imports, no metadata,
no coverage bindings, no `custom` bags.

`Testpoint` has: `name`, `stage`, `desc`, `tests`, `tags`, `na`,
`source_template`, `requirements`.

`CovergroupEntry` has: `name`, `desc`.

### Gap

All the richer schema objects are absent.  The serialisation round-trip
(`to_dict` / `from_dict`) therefore only covers the stripped-down model.

### Work required

#### `python/covsight/core/ncdb/testplan.py`

**New leaf dataclasses**

```python
@dataclass
class CoverageBinding:
    type: str   # covergroup | coverpoint | cross | assertion | expression |
                #   toggle | line | branch | functional
    path: str   # hierarchical path in coverage DB (glob patterns allowed)
    desc: str = ""

@dataclass
class CoverpointEntry:
    name: str
    desc: str = ""
    path: str = ""   # optional DB path
    custom: dict = field(default_factory=dict)
```

**Extended `CovergroupEntry`**

Add `coverpoints: List[CoverpointEntry]` and `custom: dict`.

**Extended `Testpoint`**

Add:
- `coverage: List[CoverageBinding]`
- `owner: str`
- `priority: str`   # "high" | "medium" | "low" | ""
- `weight: int`     # 1 by default
- `custom: dict`

**New `Goal` dataclass**

```python
@dataclass
class Goal:
    id:       str = ""
    title:    str = ""
    desc:     str = ""
    owner:    str = ""
    priority: str = ""
    status:   str = ""   # planned | in_progress | complete | waived
    tags:     List[str] = field(default_factory=list)
    goals:    List["Goal"] = field(default_factory=list)
    testpoints: List[Testpoint] = field(default_factory=list)
    custom:   dict = field(default_factory=dict)
```

**New `ImportEntry` dataclass**

```python
@dataclass
class ImportEntry:
    path:          str
    substitutions: dict = field(default_factory=dict)
```

**Extended `Testplan`**

Add:
- `schema: str`           # "$schema" URI
- `name: str`
- `description: str`
- `owner: str`
- `tags: List[str]`
- `substitutions: dict`
- `imports: List[ImportEntry]`
- `goals: List[Goal]`
- `custom: dict`

**Updated `to_dict` / `from_dict`**

Both methods must serialise and deserialise every new field, including the
recursive `Goal` tree.  `goals` is serialised as a nested list; `testpoints`
at the top level remains as a convenience flattening.

**New helper: `iter_testpoints(plan)`**

Yield all `Testpoint` objects regardless of whether they are at top level or
nested inside a `goals` tree.  This ensures all existing consumers
(`compute_closure`, reports, etc.) continue to work without modification.

### Test strategy (`tests/ncdb/test_testplan.py`)

Extend existing test file with:

- `TestGoal` — construction, nesting, serialisation round-trip.
- `TestCoverageBinding` — all nine types, glob path round-trip.
- `TestPlanMetadata` — name/owner/tags serialise and restore.
- `TestPlanExtended` — full `to_dict` / `from_dict` round-trip on a plan that
  exercises every field including deeply nested goals.
- `TestIterTestpoints` — flattens goals tree and top-level testpoints
  correctly; deduplicates if the same object appears in both.

---

## 2. Canonical YAML/JSON reader (`testplan_yaml.py`)

### Current state

No reader exists for the new CovSight YAML/JSON format.  The only importer is
`testplan_hjson.py`, which only handles the OpenTitan Hjson subset.

### Gap

The schema's primary authoring format is YAML (with JSON as an alternative).
A reader must:

1. Parse `.yaml`, `.yml`, `.json`, and `.hjson` files.
2. Populate every field of the extended model (Goals, CoverageBindings, etc.).
3. Perform `{key}` substitution expansion on `tests` lists (cartesian product,
   same logic as the existing `_expand_template`).
4. Resolve and merge `imports[]` (see §3).

### Work required

**New file: `python/covsight/core/ncdb/testplan_yaml.py`**

```python
def load_testplan(path: str,
                  substitutions: dict | None = None) -> Testplan:
    """Load a CovSight testplan from YAML, JSON, or Hjson.

    Recursively resolves imports, expands substitutions, and returns a
    fully-populated Testplan.  Raises ParseError on schema violations or
    circular imports.
    """
```

Implementation outline:
1. Detect format from extension (`.yaml`/`.yml` → PyYAML, `.json` → stdlib
   json, `.hjson` → hjson package with json fallback).
2. Parse to raw dict.
3. Pass dict through `_build_plan(raw, base_dir, resolved_paths, subs)`.
4. `_build_plan` constructs `Testplan` from every top-level key.
5. Call `_resolve_imports` before populating testpoints/goals so that imported
   testpoints are merged before expansion.
6. Expand `{key}` templates in `tests` lists using cartesian product.

**`ParseError` class** (subclass of `ValueError`) with `path` and `message`
attributes.

**Dependency:** `pyyaml` must be added to `pyproject.toml` dependencies (it is
likely already present; verify and add if missing).

### Test strategy (`tests/ncdb/test_testplan_yaml.py`)

New file.  Use `tmp_path` fixture for in-test file creation.

- `TestLoadYaml` — basic YAML load, all top-level metadata, Goals tree,
  CoverageBindings, custom dicts.
- `TestLoadJson` — same plan as YAML but in JSON; results must be identical.
- `TestSubstitutionExpansion` — `{key}` cartesian expansion via file-level
  `substitutions`.
- `TestCoverageBindingLoad` — all nine coverage types round-trip through parser.
- `TestParseErrors` — missing required field `name` on testpoint, unknown
  coverage type (warn, don't fail), duplicate testpoint name (error).

---

## 3. Import resolver (`testplan_imports.py`)

### Current state

No import resolution exists.  `testplan_hjson.py` reads only the single file
it is given.

### Gap

The schema supports multi-level `imports[]` with:
- Paths relative to the importing file or absolute.
- Per-import `substitutions` that override plan-level substitutions.
- Transitive imports (recursive).
- Deduplication by resolved absolute path (each file merged once).
- Circular import detection (parse error).

### Work required

**New file: `python/covsight/core/ncdb/testplan_imports.py`**

```python
def resolve_imports(plan_dict: dict,
                    base_dir: str,
                    resolved_paths: set[str] | None = None) -> dict:
    """Recursively load and merge imported testplans into *plan_dict*.

    Args:
        plan_dict:      Raw parsed dict for the current file.
        base_dir:       Directory of the current file (for relative paths).
        resolved_paths: Accumulator of already-merged absolute paths
                        (prevents duplicates and detects cycles).

    Returns:
        Mutated *plan_dict* with all imports merged in.

    Raises:
        ParseError: On circular import or unresolvable path.
    """
```

Algorithm:
1. Initialise `resolved_paths` with the current file's path.
2. For each `ImportEntry` in `plan_dict["imports"]`:
   a. Resolve to absolute path.
   b. Raise `ParseError` if the path is already in `resolved_paths` (cycle).
   c. Skip silently if already merged (dedup).
   d. Add path to `resolved_paths`.
   e. Parse the imported file.
   f. Recursively call `resolve_imports` on it.
   g. Merge its `testpoints`, `goals`, and `covergroups` into `plan_dict`,
      applying the import's `substitutions`.
3. Name-collision check: after all imports are merged, verify that every
   testpoint `name` is globally unique; raise `ParseError` on collision.

### Test strategy (`tests/ncdb/test_testplan_imports.py`)

New file.

- `TestBasicImport` — single import merges testpoints.
- `TestSubstitutionOverride` — import's substitutions override plan-level ones
  for testpoints from that import.
- `TestTransitiveImport` — three-level chain; all testpoints appear in merged
  plan.
- `TestDeduplication` — two different imports both import the same third file;
  that file is merged only once.
- `TestCircularImport` — A imports B, B imports A → `ParseError`.
- `TestMissingFile` — import path does not exist → `ParseError`.
- `TestNameCollision` — two imports define a testpoint with the same name →
  `ParseError`.

---

## 4. Compatibility readers

### 4a. OpenTitan Hjson (`testplan_hjson.py`)

#### Current state

Handles `testpoints[]`, `covergroups[]`, `{key}` expansion.  Does **not** handle:
- `import_testplans[]` (OpenTitan's own import key)
- Plan-level `name` / `substitutions` dict
- `requirements` list on testpoints
- `tags` list on testpoints

#### Work required

- Parse `import_testplans` and forward to `resolve_imports`.
- Parse plan-level `name` and `substitutions` dict (already partially present
  for substitutions but not merged with the argument dict correctly).
- Parse `requirements` list per testpoint into `RequirementLink` objects.
- Preserve original `tags`.

#### Test strategy

Extend `tests/ncdb/test_testplan_hjson.py`:

- `TestImportTestplans` — `import_testplans` resolves and merges.
- `TestPlanLevelSubstitutions` — plan-level `substitutions` key merged with
  caller-supplied substitutions (caller wins on collision).
- `TestRequirementsPreserved` — requirements list round-trips through import.

---

### 4b. Cadence vManager VPF XML (`testplan_vpf.py`)

#### Current state

Does not exist.

#### Work required

**New file: `python/covsight/core/ncdb/testplan_vpf.py`**

```python
def import_vpf(xml_path: str) -> Testplan:
    """Parse a Cadence vManager VPF XML file into a Testplan."""
```

Mapping (from `testplan-schema.md` compatibility table):

| VPF element | Target |
|---|---|
| `<tpGoal name=…>` (nested) | `Goal.title` + `Goal.goals[]` |
| `<tpGoal id=…>` | `Goal.id` |
| `<tpGoal owner=…>` | `Goal.owner` |
| `<tpGoal status=…>` | `Goal.status` (value mapping needed) |
| `<tpGroup>` | leaf `Goal` (no sub-goals) |
| `<tpTest name=…>` | `Testpoint.name` |
| `<tpCoverPoint name=…>` | split to `CovergroupEntry` + `CoverageBinding` |
| `<attributes>` | `custom` |

Use `xml.etree.ElementTree` (stdlib, no new dependency).

#### Test strategy (`tests/ncdb/test_testplan_vpf.py`)

- `TestVpfImport` — parse a minimal VPF fixture XML; verify goal hierarchy,
  testpoints, attributes in `custom`.
- `TestVpfStatusMapping` — VPF status strings map to schema status values.
- `TestVpfCoverPoint` — `<tpCoverPoint>` appears in both `covergroups` and
  as a `CoverageBinding` on the nearest testpoint.

---

### 4c. Synopsys VC Planner CSV/XML (`testplan_vc_planner.py`)

#### Current state

Does not exist.

#### Work required

**New file: `python/covsight/core/ncdb/testplan_vc_planner.py`**

```python
def import_vc_planner(path: str) -> Testplan:
    """Parse a Synopsys Verdi VC Planner CSV or XML file."""
```

Dispatch on extension: `.xml` → ElementTree, `.csv` → `csv.DictReader`.

Mapping:

| VC Planner field | Target |
|---|---|
| `type: group` | `Goal` |
| `type: test` | `Testpoint` |
| `type: coverpoint` | `CoverpointEntry` inside matching `CovergroupEntry` |
| `owner`, `status`, `priority`, `weight`, `description` | direct fields |

Hierarchy is expressed via indent level in CSV or parent-child XML structure.

#### Test strategy (`tests/ncdb/test_testplan_vc_planner.py`)

- `TestVcPlannerCsv` — parse a minimal CSV fixture; verify goal hierarchy,
  testpoints, priority/weight/owner.
- `TestVcPlannerXml` — same fixture in XML produces identical `Testplan`.
- `TestVcPlannerNestedGroups` — multi-level group nesting round-trips correctly.

---

### 4d. Siemens Questa Visualizer XML/CSV (`testplan_questa.py`)

#### Current state

Does not exist.

#### Work required

**New file: `python/covsight/core/ncdb/testplan_questa.py`**

```python
def import_questa(path: str) -> Testplan:
    """Parse a Siemens Questa Visualizer XML or CSV testplan."""
```

Mapping:

| Questa field | Target |
|---|---|
| `<goal id=…>` | `Goal.id` |
| `<goal title=…>` | `Goal.title` |
| `<goal description=…>` | `Goal.desc` |
| `<metric type=… coverage=…>` | `CoverageBinding.type` + `.path` |
| `<tag>` | `*.tags[]` |

The `coverage=` attribute on `<metric>` maps directly to `CoverageBinding.path`
— this is Questa's explicit coverage-DB path binding that the schema design
specifically highlights as a key feature.

#### Test strategy (`tests/ncdb/test_testplan_questa.py`)

- `TestQuestaXml` — parse a minimal XML fixture; verify goal tree, coverage
  bindings are populated.
- `TestQuestaMetricTypes` — all coverage types in `<metric type=…>` map to
  the correct `CoverageBinding.type` values.
- `TestQuestaTags` — `<tag>` elements appear on the correct objects.

---

## 5. JSON Schema file (`testplan.schema.json`)

### Current state

No JSON Schema exists for the testplan format.

### Work required

**New file: `python/covsight/core/schema/testplan.schema.json`**

A JSON Schema (draft-07) that validates a CovSight testplan file.  Key points:

- Top-level required properties: `format_version`.
- `testpoints` items: required `name` and `stage`.
- `goals` items: required `id` and `title`; recursive `$ref` for nesting.
- `coverage` items: `type` must be one of the nine enumerated values.
- `custom` properties: `additionalProperties: true` everywhere (opaque).
- `priority` enum: `"high"`, `"medium"`, `"low"`.
- `status` enum: `"planned"`, `"in_progress"`, `"complete"`, `"waived"`.

**New helper: `validate_testplan(plan_dict: dict) -> list[str]`**
in `testplan_yaml.py` (or a new `testplan_validate.py`) using
`jsonschema.validate` (add `jsonschema` to optional dependencies).

### Test strategy (`tests/ncdb/test_testplan_schema.py`)

- `TestSchemaValid` — the worked example from `testplan-schema.md` passes
  validation with zero errors.
- `TestSchemaMissingRequiredFields` — missing `name` on a testpoint is caught.
- `TestSchemaInvalidCoverageType` — unknown coverage type is rejected.
- `TestSchemaCustomPassthrough` — arbitrary content in `custom` is accepted.
- `TestSchemaRecursiveGoal` — deeply nested goals pass validation.

---

## 6. Closure computation — goals and coverage binding

### Current state

`compute_closure` and `stage_gate_status` in `testplan_closure.py` work on the
flat `testpoints` list only.  They are unaware of the Goals hierarchy and have
no concept of coverage binding.

### Work required

#### `python/covsight/core/ncdb/testplan_closure.py`

**`compute_closure` — no change needed for the common path**, because the new
`iter_testpoints(plan)` helper (§1) provides a flat view.  Update the call
site inside `compute_closure` to use `iter_testpoints` instead of
`plan.testpoints` directly.

**New: `CoverageResult` dataclass**

```python
@dataclass
class CoverageResult:
    binding:   CoverageBinding
    hits:      int   # number of times the bound item has been hit
    total:     int   # total bins / lines / etc.
    pct:       float # hits / total * 100, or 0.0 if total == 0
```

**New: `compute_coverage_binding(testpoint, db) -> List[CoverageResult]`**

For each `CoverageBinding` on a testpoint, look up the matching scope(s) in
the coverage DB using the dotted path.  Glob patterns (`*`, `**`) are
resolved by walking the UCIS scope tree.  Returns a list of
`CoverageResult` objects.

**Extended `TestpointResult`**

Add `coverage_results: List[CoverageResult] = field(default_factory=list)`.

**Extended `compute_closure`**

When a coverage DB is provided and `plan` contains testpoints with
`coverage` bindings, populate `TestpointResult.coverage_results` for each
testpoint.

**`stage_gate_status` — goals-aware version**

Add an optional `require_goals_closed: bool = False` parameter.  When True,
a stage gate also fails if any `Goal` whose effective stage-rank is ≤ the
target stage has status `"in_progress"` or `"planned"` and has blocking
testpoints.

#### `python/covsight/core/ncdb/reports.py`

- Extend `ClosureSummary` with `total_coverage_pct: float` — aggregate
  coverage percentage across all testpoints that have bindings.
- Extend `format_testpoint_closure` to display per-testpoint coverage % when
  binding data is present.

### Test strategy

Extend `tests/ncdb/test_testplan_closure.py`:

- `TestGoalAwareClosure` — a plan with nested goals; `iter_testpoints` yields
  the correct flat set, `compute_closure` returns one result per testpoint.
- `TestCoverageBindingResult` — stub DB with mock coverage items; verify
  `CoverageResult.pct` is computed correctly.
- `TestGlobBinding` — a `CoverageBinding.path` containing `*` resolves to
  multiple scopes; `hits`/`total` are aggregated.
- `TestStageGateGoalAware` — stage gate respects goal-status when
  `require_goals_closed=True`.

---

## 7. Export updates

### Work required

#### `python/covsight/core/ncdb/testplan_export.py`

- `export_junit_xml`: add a `<properties>` block per testcase with
  `coverage_pct` when `TestpointResult.coverage_results` is non-empty.
- `export_summary_markdown`: add an optional **Coverage Bindings** section
  that lists per-testpoint coverage % for testpoints that have bindings.
- `export_github_annotations`: emit `::notice::` lines for testpoints whose
  coverage is < 100% but whose closure status is CLOSED.

### Test strategy

Extend `tests/ncdb/test_testplan_export.py`:

- `TestJUnitCoverageProperties` — results with `coverage_results` produce
  `<properties>` block in JUnit XML.
- `TestMarkdownCoverageSection` — markdown output includes coverage section
  when bindings are present.
- `TestGithubNoticeAnnotation` — notice annotations emitted for partially
  covered CLOSED testpoints.

---

## 8. NCDB embedding

### Current state

`testplan.py` has `Testplan.serialize()` / `Testplan.from_bytes()` and
`NcdbWriter`/`NcdbReader` embed the plan as `testplan.json` inside the `.cdb`
ZIP.  The serialisation only covers the flat model.

### Work required

`Testplan.to_dict()` and `from_dict()` will be updated in §1.  The NCDB
reader/writer do not need changes because they call `serialize()`/`from_bytes()`
which delegate to `to_dict()`/`from_dict()`.  Verify that a round-trip through
NCDB preserves all new fields.

### Test strategy

Extend `tests/ncdb/test_testplan.py` or add a dedicated
`tests/ncdb/test_testplan_ncdb_roundtrip.py`:

- `TestNcdbRoundTrip` — write a `Testplan` with goals, coverage bindings, and
  `custom` dicts to an in-memory or temp NCDB file; read it back; assert every
  field is preserved.

---

## 9. Documentation (Sphinx)

### Current state

`docs/source/` contains `reference/formats/` and `reference/python-api/`.
No testplan documentation exists in Sphinx.

### Work required

#### `docs/source/reference/formats/testplan.rst`

A reference page for the testplan file format.  Sections:

1. **Overview** — link to `testplan-schema.md`, summarise the format.
2. **Top-level structure** — table of all top-level keys, types, and defaults.
3. **Goals** — fields table, status semantics.
4. **Testpoints** — fields table, wildcard expansion, coverage binding types
   table.
5. **Covergroups** — fields table.
6. **Imports and substitutions** — cartesian expansion, transitive imports,
   circular import detection.
7. **Extensibility** — `custom` dict namespacing convention.
8. **File format** — YAML vs JSON vs Hjson; accepted extensions.
9. **Compatibility** — table linking to the four compatibility readers.

#### `docs/source/reference/formats/testplan-compatibility.rst`

A page per compatibility reader:

1. **OpenTitan Hjson** — mapping table, known limitations.
2. **Cadence vManager VPF** — mapping table, status-value mapping table.
3. **Synopsys VC Planner** — mapping table, CSV vs XML differences.
4. **Siemens Questa Visualizer** — mapping table, coverage path binding
   behaviour.

#### `docs/source/reference/python-api/testplan.rst`

Auto-generated API reference using `.. autoclass::` / `.. autofunction::` for:

- `Testplan`
- `Goal`
- `Testpoint`
- `CoverageBinding`
- `CoverpointEntry`
- `CovergroupEntry`
- `RequirementLink`
- `ImportEntry`
- `load_testplan` (new canonical reader)
- `import_hjson`
- `import_vpf`
- `import_vc_planner`
- `import_questa`
- `compute_closure`
- `compute_coverage_binding`
- `stage_gate_status`
- `export_junit_xml`
- `export_github_annotations`
- `export_summary_markdown`

#### `docs/source/getting-started/testplan-authoring.rst`

A how-to guide covering:

1. Writing your first testplan (YAML example).
2. Using goals for hierarchy.
3. Binding testpoints to coverage DB paths.
4. Wildcard expansion and plan-level substitutions.
5. Splitting large plans with imports.
6. Importing an existing OpenTitan testplan.
7. Running closure in Python and in CI (JUnit XML, GitHub Actions).

#### `docs/source/index.rst`

Add the new pages to the toctree under `reference/formats/` and
`getting-started/`.

---

## 10. Dependency changes (`pyproject.toml`)

| Package | Change | Reason |
|---|---|---|
| `pyyaml` | add to `dependencies` | YAML parsing in new reader |
| `jsonschema` | add to `optional-dependencies[validate]` | schema validation helper |
| `hjson` | add to `optional-dependencies[hjson]` | already recommended; formalise |

---

## Implementation order and dependencies

The items above have the following dependency graph:

```
1 (data model)
├─► 2 (YAML reader)
│     └─► 3 (import resolver)     [2 depends on 3]
├─► 4a (hjson update)
├─► 4b (VPF reader)
├─► 4c (VC Planner reader)
├─► 4d (Questa reader)
├─► 5 (JSON Schema)
├─► 6 (closure update)           [also depends on 2]
│     └─► 7 (export updates)
└─► 8 (NCDB embedding)
9 (docs)                         [depends on all of 1–8]
10 (pyproject.toml)              [should be done alongside 2]
```

Recommended delivery order: **1 → 10 → 2 → 3 → 4a → 5 → 6 → 7 → 8 → 4b → 4c → 4d → 9**

Items 4b–4d (vendor compatibility readers) are independent of each other and
can be developed in parallel.

---

## Test coverage summary

| Test file | New test classes / cases |
|---|---|
| `tests/ncdb/test_testplan.py` | `TestGoal`, `TestCoverageBinding`, `TestPlanMetadata`, `TestPlanExtended`, `TestIterTestpoints`, `TestNcdbRoundTrip` |
| `tests/ncdb/test_testplan_yaml.py` | `TestLoadYaml`, `TestLoadJson`, `TestSubstitutionExpansion`, `TestCoverageBindingLoad`, `TestParseErrors` |
| `tests/ncdb/test_testplan_imports.py` | `TestBasicImport`, `TestSubstitutionOverride`, `TestTransitiveImport`, `TestDeduplication`, `TestCircularImport`, `TestMissingFile`, `TestNameCollision` |
| `tests/ncdb/test_testplan_hjson.py` | `TestImportTestplans`, `TestPlanLevelSubstitutions`, `TestRequirementsPreserved` |
| `tests/ncdb/test_testplan_vpf.py` | `TestVpfImport`, `TestVpfStatusMapping`, `TestVpfCoverPoint` |
| `tests/ncdb/test_testplan_vc_planner.py` | `TestVcPlannerCsv`, `TestVcPlannerXml`, `TestVcPlannerNestedGroups` |
| `tests/ncdb/test_testplan_questa.py` | `TestQuestaXml`, `TestQuestaMetricTypes`, `TestQuestaTags` |
| `tests/ncdb/test_testplan_schema.py` | `TestSchemaValid`, `TestSchemaMissingRequiredFields`, `TestSchemaInvalidCoverageType`, `TestSchemaCustomPassthrough`, `TestSchemaRecursiveGoal` |
| `tests/ncdb/test_testplan_closure.py` | `TestGoalAwareClosure`, `TestCoverageBindingResult`, `TestGlobBinding`, `TestStageGateGoalAware` |
| `tests/ncdb/test_testplan_export.py` | `TestJUnitCoverageProperties`, `TestMarkdownCoverageSection`, `TestGithubNoticeAnnotation` |
