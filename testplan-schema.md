# CovSight Testplan Schema Design

## Background

Several testplan formats exist across the industry. This document designs a superset
YAML/JSON schema for CovSight that:

- Imports and round-trips the major industry formats
- Exposes standard fields the tool can act on (coverage path binding, stage tracking)
- Is user-extensible without schema changes

### Formats surveyed

| Tool | Format | Structure | Key features |
|---|---|---|---|
| OpenTitan DVSim | Hjson | Flat list | `testpoints[]`, `covergroups[]`, `{wildcard}` expansion, `import_testplans` |
| Cadence vManager (VPF) | XML | Hierarchical | `tpGoal` (nested) → `tpGroup` → `tpTest` / `tpCoverPoint`; `<attributes>` for custom data; `owner`, `status` |
| Synopsys Verdi VC Planner | CSV / XML | Hierarchical | `group`/`test`/`coverpoint` types; `owner`, `status`, `priority`, `weight` |
| Siemens Questa Visualizer | XML / CSV | Hierarchical | `<goal>` → `<metric type="covergroup" coverage="path">` — **explicit coverage-DB path binding** |

### Key design observations

1. **Hierarchy**: all EDA-vendor formats use nested goal/subgoal trees. OpenTitan is flat.
   The schema must support both.
2. **Coverage binding**: Siemens (and vManager) bind goals directly to coverage DB paths.
   This is the feature that allows a tool to compute "% of testpoint covered".
   OpenTitan only names covergroups without paths.
3. **Extensibility**: Cadence uses an `<attributes>` element; Synopsys uses custom CSV columns.
   We need a first-class mechanism, not a workaround.
4. **Composition**: OpenTitan's `import_testplans` + `substitutions` are widely used and
   should be preserved.
5. **Requirements tracing**: not in OpenTitan but present in our existing model and
   common in enterprise flows.

---

## Schema design

### File format

**YAML is the primary authoring format.** YAML supports comments, multiline strings,
and is widely understood — making it the most comfortable format for writing testplans
by hand. JSON is supported as an alternative (useful for programmatic generation).
Hjson (a JSON superset with comments and trailing commas) is accepted for compatibility
with existing OpenTitan flows but is not the recommended authoring format.

Files may use `.yaml`, `.yml`, `.json`, or `.hjson` extensions. `.testplan` is also
accepted as an alias for any of the above.

The schema version is declared with a `$schema` key so validators and parsers can
detect it.

---

### Top-level structure

```jsonc
{
  "$schema": "https://schema.covsight.io/testplan/v1",
  "format_version": 1,

  // Plan identity
  "name":        "uart",
  "description": "UART block verification testplan",
  "owner":       "dv-team",
  "tags":        ["regression", "block"],

  // Composition: import and merge other testplan files
  "imports": [
    {
      "path":          "common/csr_testplan.yaml",
      "substitutions": { "name": "uart", "intf": ["", "_jtag"] }
    }
  ],

  // Default wildcard substitutions for {key} expansion in tests lists
  "substitutions": {
    "name":  "uart",
    "baud":  ["9600", "115200", "460800"]
  },

  // Hierarchical goal tree (see below)
  "goals": [ ... ],

  // Top-level flat testpoints (OpenTitan-compatible shorthand)
  "testpoints": [ ... ],

  // Coverage plan: named covergroups expected in the design
  "covergroups": [ ... ],

  // User-defined plan-level extensions
  "custom": {
    "dv_doc_url": "https://wiki.example.com/uart-dv",
    "block":      "uart"
  }
}
```

`goals` and `testpoints` may coexist. A flat `testpoints` list at top level is
equivalent to a single unnamed root goal containing those testpoints.

---

### Goals (hierarchical)

Goals are the tree nodes borrowed from Cadence/Synopsys/Siemens. They provide
organisational hierarchy: chip → subsystem → block → feature → test.

```jsonc
{
  "id":          "uart-functional",       // unique within the plan; string
  "title":       "UART Functional Verification",
  "desc":        "Markdown description …",
  "owner":       "alice",
  "priority":    "high",                  // "high" | "medium" | "low"
  "status":      "planned",              // "planned" | "in_progress" | "complete" | "waived"
  "tags":        ["nightly"],

  // Nested sub-goals (arbitrary depth)
  "goals": [ ... ],

  // Testpoints that belong to this goal
  "testpoints": [ ... ],

  // User extensions
  "custom": { "jira_epic": "UART-10" }
}
```

**Status semantics**
- `planned` — goal defined but no tests written yet
- `in_progress` — some tests written / coverage partially reached
- `complete` — all bound coverage is reached and tests pass
- `waived` — intentionally excluded from pass/fail computation

---

### Testpoints

A testpoint represents one verification intent: a test or group of tests that
exercises a specific feature.

```jsonc
{
  // ── Identity ───────────────────────────────────────────────────────
  "name":    "uart_baud_rate",           // lower_snake_case; unique within plan
  "stage":   "V2",                       // "V1" | "V2" | "V2S" | "V3" | <custom>
  "desc":    "Verify baud-rate divisor across all supported rates.",

  // ── Execution ──────────────────────────────────────────────────────
  // Test names that exercise this testpoint.
  // {key} wildcards are expanded via plan-level substitutions.
  // ["N/A"] marks the testpoint as intentionally unmapped.
  "tests":   ["uart_baud_{baud}_test"],

  // ── Metadata ───────────────────────────────────────────────────────
  "owner":    "bob",
  "priority": "medium",                  // "high" | "medium" | "low"
  "weight":   1,                         // relative importance (positive integer)
  "tags":     ["gls", "fpga"],
  "na":       false,                     // true iff tests: ["N/A"]

  // ── Coverage binding (CovSight-native; tool-actionable) ────────────
  // Explicit links to coverage objects in the DB.
  // CovSight uses these to compute per-testpoint coverage % and
  // to flag unassigned coverage items.
  "coverage": [
    {
      "type": "covergroup",              // see Coverage binding types below
      "path": "uart_env.uart_cg",        // hierarchical path in coverage DB
      "desc": "Main UART functional covergroup"
    },
    {
      "type": "coverpoint",
      "path": "uart_env.uart_cg.baud_rate_cp"
    },
    {
      "type": "assertion",
      "path": "uart_tb.chk_frame_err"
    }
  ],

  // ── Requirements tracing ───────────────────────────────────────────
  "requirements": [
    {
      "system":   "JIRA",
      "project":  "UART",
      "item_id":  "REQ-42",
      "url":      "https://jira.example.com/browse/UART-42"
    }
  ],

  // ── User extensions ────────────────────────────────────────────────
  "custom": {
    "estimated_sim_time_s": 300,
    "triage_owner":         "charlie"
  }
}
```

#### Coverage binding types

| Type | Description |
|---|---|
| `covergroup` | Entire SV covergroup; all coverpoints and crosses within it |
| `coverpoint` | Single coverpoint within a covergroup |
| `cross` | A cross coverage construct |
| `assertion` | SVA / OVA assertion (pass/fail) |
| `expression` | Expression coverage line |
| `toggle` | Toggle coverage on a signal path |
| `line` | Line (statement) coverage |
| `branch` | Branch / condition coverage |
| `functional` | Catch-all for any coverage type identified by DB path |

`path` is the dotted hierarchical path as it appears in the coverage database
(UCIS scope hierarchy). Glob patterns (`*`, `**`) are allowed for bulk binding:

```jsonc
{ "type": "covergroup", "path": "uart_env.uart_cg.*" }
```

---

### Covergroups (coverage plan)

Describes the functional coverage groups expected in the DUT. These are the planned
items; the actual implementation is found in the simulation DB.

```jsonc
{
  "name": "uart_cg",
  "desc": "Covers UART configuration and data path.",

  // Optional: list the individual coverpoints for documentation
  "coverpoints": [
    { "name": "baud_rate_cp", "desc": "Baud rate divisor values",
      "path": "uart_env.uart_cg.baud_rate_cp" },
    { "name": "parity_cp",    "desc": "Parity mode",
      "path": "uart_env.uart_cg.parity_cp" }
  ],

  "custom": {}
}
```

---

### Imports and substitutions

```jsonc
"imports": [
  {
    // Path relative to the importing file (or absolute)
    "path": "common/csr_testplan.yaml",

    // Substitutions override / extend plan-level substitutions for
    // all testpoints pulled in from this import.
    "substitutions": {
      "name": "uart",
      "intf": ["", "_jtag"]
    }
  }
]
```

`{key}` placeholders in `tests` lists are expanded via cartesian product
(identical to OpenTitan semantics). Substitutions in an import override the
top-level substitutions for testpoints sourced from that import.

**Transitive imports are supported.** This enables the typical chip-level hierarchy:

```
chip_testplan.yaml
  └── subsystem_testplan.yaml
        ├── uart_testplan.yaml
        │     └── common/csr_testplan.yaml   ← shared IP fragment
        └── spi_testplan.yaml
              └── common/csr_testplan.yaml   ← same shared fragment
```

Each file is resolved and merged once, even if referenced from multiple paths
(deduplication by resolved absolute path). **Circular imports are a parse error.**
Name collisions across imports are also a parse error, so each testpoint `name`
must be globally unique across the merged plan.

---

### Extensibility

Every object in the schema — plan, goal, testpoint, covergroup, coverpoint — carries
a `"custom"` dict. Its contents are opaque to CovSight core and are passed through
unchanged to all outputs (HTML reports, JSON exports, API responses).

**Namespacing convention**: use the top-level key within `custom` as a namespace.
This prevents collision with future standard fields and makes ownership clear when
merging testplans from multiple teams:

```jsonc
"custom": {
  "acme": {
    "priority":   1,
    "review_url": "https://review.acme.com/tp/42"
  },
  "chip_team": {
    "silicon_milestone": "MP1"
  }
}
```

Rules:
- Use `custom` — **not** top-level unknown keys — so parsers can validate the known
  schema without false warnings.
- The top-level key within `custom` is the namespace (e.g. `"acme"`, `"chip_team"`).
  Use your organization or project name.
- Namespaced dicts may be arbitrarily nested; arrays and scalar values are also fine.
- CovSight tooling surfaces `custom` dicts in UI and exports them unchanged.

---

## Worked example

```jsonc
{
  "$schema": "https://schema.covsight.io/testplan/v1",
  "format_version": 1,
  "name":  "uart",
  "owner": "dv-team",

  "substitutions": { "name": "uart" },

  "imports": [
    { "path": "common/csr_testplan.yaml", "substitutions": { "name": "uart" } }
  ],

  "goals": [
    {
      "id":    "functional",
      "title": "Functional verification",
      "goals": [
        {
          "id":    "reset",
          "title": "Reset behavior",
          "testpoints": [
            {
              "name":  "uart_reset",
              "stage": "V1",
              "desc":  "Verify the UART recovers cleanly after reset.",
              "tests": ["uart_smoke", "uart_reset_test"],
              "coverage": [
                { "type": "covergroup", "path": "uart_env.uart_reset_cg" }
              ]
            }
          ]
        },
        {
          "id":    "baud",
          "title": "Baud rate",
          "testpoints": [
            {
              "name":     "uart_baud_rate",
              "stage":    "V2",
              "desc":     "All supported baud rates exercised.",
              "tests":    ["uart_baud_{name}_test"],
              "priority": "high",
              "coverage": [
                { "type": "coverpoint", "path": "uart_env.uart_cg.baud_rate_cp" }
              ],
              "requirements": [
                { "system": "JIRA", "project": "UART", "item_id": "REQ-7" }
              ],
              "custom": { "estimated_sim_time_s": 120 }
            }
          ]
        }
      ]
    }
  ],

  "covergroups": [
    {
      "name": "uart_cg",
      "desc": "UART functional coverage",
      "coverpoints": [
        { "name": "baud_rate_cp", "path": "uart_env.uart_cg.baud_rate_cp" },
        { "name": "parity_cp",    "path": "uart_env.uart_cg.parity_cp" }
      ]
    }
  ]
}
```

---

## Compatibility mapping

### OpenTitan Hjson

| OpenTitan field | CovSight field | Notes |
|---|---|---|
| `testpoints[].name` | `testpoints[].name` | identical |
| `testpoints[].stage` | `testpoints[].stage` | identical |
| `testpoints[].desc` | `testpoints[].desc` | identical |
| `testpoints[].tests` | `testpoints[].tests` | identical; `["N/A"]` → `na: true` |
| `testpoints[].tags` | `testpoints[].tags` | identical |
| `covergroups[].name` | `covergroups[].name` | identical |
| `covergroups[].desc` | `covergroups[].desc` | identical |
| `import_testplans[]` | `imports[].path` | semantics preserved |
| `name` (plan-level substitution key) | `substitutions.name` | moved under explicit key |
| `{intf}` (arbitrary sub keys) | `substitutions.{key}` | same |

Import from OpenTitan Hjson is lossless; no information is dropped.

### Cadence vManager (VPF)

| VPF element/attr | CovSight field | Notes |
|---|---|---|
| `<tpGoal name=…>` (nested) | `goals[].title` + `goals[].goals[]` | hierarchy preserved |
| `<tpGoal id=…>` | `goals[].id` | |
| `<tpGoal owner=…>` | `goals[].owner` | |
| `<tpGoal status=…>` | `goals[].status` | value mapping needed |
| `<tpGroup>` | `goals[]` (leaf goal with no sub-goals) | |
| `<tpTest name=…>` | `testpoints[].name` | |
| `<tpCoverPoint name=…>` | `covergroups[].name` + `testpoints[].coverage[]` | split: declaration → covergroups; binding → coverage |
| `<attributes>` | `custom` | |

### Synopsys Verdi VC Planner

| VC Planner field | CovSight field |
|---|---|
| `name` | `goals[].title` or `testpoints[].name` depending on `type` |
| `type: group` | `goals[]` |
| `type: test` | `testpoints[]` |
| `type: coverpoint` | `covergroups[].coverpoints[]` |
| `owner` | `*.owner` |
| `status` | `*.status` |
| `priority` | `*.priority` |
| `weight` | `testpoints[].weight` |
| `description` | `*.desc` |

### Siemens Questa Visualizer

| Questa field | CovSight field |
|---|---|
| `<goal id=…>` | `goals[].id` |
| `<goal title=…>` | `goals[].title` |
| `<goal description=…>` | `goals[].desc` |
| `<metric type=… coverage=…>` | `testpoints[].coverage[].type` + `[].path` |
| `<tag>` | `*.tags[]` |

---

## Design decisions (resolved)

1. **`goals` vs flat `testpoints`**: Both are first-class. A flat `testpoints` list at
   top level is sugar for a single unnamed root goal. Hierarchical `goals` and flat
   `testpoints` may coexist in the same file.

2. **Coverage `path` format**: Paths use whatever the underlying coverage database
   uses (typically the UCIS dotted-scope hierarchy). No additional grammar is imposed.

3. **Stage values**: Any string is valid. `V1`, `V2`, `V2S`, `V3` are documented as
   the conventional values (inherited from OpenTitan / chip-level verification
   practice) but non-OpenTitan projects may use any stage scheme.

4. **Import depth**: Transitive (recursive) imports are supported. This is a key
   reuse enabler for chip→subsystem→block→shared-IP hierarchies. Circular imports
   are a parse error; duplicate imports (same file referenced via multiple paths) are
   deduplicated by resolved absolute path. See the Imports section for details.

5. **Custom field namespacing**: Top-level keys within the `custom` dict serve as
   namespaces (e.g. `custom: { "acme": { ... } }`). This is cleaner than flat
   `vendor_key` prefixes because it makes ownership explicit and enables clean
   programmatic merging. Convention is documented; the schema does not enforce it
   (enforcement would require a registry and would be over-constraining for ad-hoc use).
