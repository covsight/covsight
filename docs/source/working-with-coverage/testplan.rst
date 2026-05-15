.. _testplan:

####################
Testplan Integration
####################

covsight can embed a structured *testplan* inside each NCDB ``.cdb`` file.
A testplan describes the verification tasks (testpoints) and functional
coverage groups expected for a design. Together with the binary test
history (see :ref:`test-history`) it enables:

* **Closure reporting** — did every testpoint's tests actually pass?
* **Stage gate evaluation** — are all V1/V2/V3 testpoints closed?
* **Merge propagation** — the testplan travels with the database so
  reports always use the correct plan.

.. contents:: On this page
   :local:
   :depth: 2

-----------

**********************
Quick-start
**********************

Author a testplan in YAML::

    # uart.yaml
    $schema: "https://schema.covsight.io/testplan/v1"
    format_version: 1
    name: uart
    owner: dv-team
    goals:
      - id: functional
        title: Functional verification
        status: in_progress
        goals:
          - id: reset
            title: Reset behaviour
            status: complete
            testpoints:
              - name: uart_reset
                stage: V1
                tests: [uart_smoke, uart_reset_test]
                coverage:
                  - type: covergroup
                    path: uart_env.uart_reset_cg

Validate and inspect it::

    covsight testplan validate uart.yaml
    covsight testplan show uart.yaml

Embed it in a database and compute closure::

    covsight testplan import coverage.cdb uart.yaml
    covsight testplan closure coverage.cdb

Export a JUnit report for CI::

    covsight testplan export-junit coverage.cdb --out results.xml

-----------

**********************
Testplan format
**********************

The preferred format is **YAML** (``$schema`` field enables editor validation).
JSON and Hjson are also accepted by all commands.

A minimal example::

    $schema: "https://schema.covsight.io/testplan/v1"
    format_version: 1
    name: uart
    goals:
      - id: functional
        title: Functional verification
        testpoints:
          - name: uart_reset
            stage: V1
            tests: [uart_smoke, uart_reset_test]
            coverage:
              - type: covergroup
                path: uart_env.uart_reset_cg

Stages follow the V1 → V2 → V2S → V3 hierarchy; custom strings are also
accepted and sort after V3 in gate evaluation.

-----------

**************************
Authoring and substitutions
**************************

Testplans support ``{key}`` substitution in test name templates.
A list value generates the cartesian product of all combinations::

    substitutions:
      intf: [a, b, c]

    testpoints:
      - name: uart_init_{intf}
        tests: ["uart_init_{intf}_test"]

This expands into three testpoints, one per interface value.
Substitution values can also be supplied on the CLI::

    covsight testplan show uart.yaml --sub intf=a

-----------

**********************
Validating
**********************

Run validation before embedding a testplan::

    covsight testplan validate uart.yaml

Validates against the JSON Schema **and** applies semantic checks
(e.g. weight must be ≥ 1, binding types). Exits non-zero on any error.
Multiple files can be validated in one invocation::

    covsight testplan validate plan_v1.yaml plan_v2.yaml

Use ``--strict`` to promote semantic warnings to errors::

    covsight testplan validate uart.yaml --strict

Machine-readable output for CI::

    covsight testplan validate uart.yaml -of json | jq .passed

-----------

**********************
Inspecting
**********************

Display the testplan tree::

    covsight testplan show uart.yaml

Filter by stage, goal status, owner, or tag::

    covsight testplan show uart.yaml --stage V1
    covsight testplan show uart.yaml --status in_progress
    covsight testplan show uart.yaml --owner alice

Limit depth and show coverage bindings::

    covsight testplan show uart.yaml -d 2 --show-coverage

Show only a section (``goals``, ``testpoints``, ``covergroups``)::

    covsight testplan show uart.yaml -s goals

Output as YAML or JSON for scripting::

    covsight testplan show uart.yaml -of yaml
    covsight testplan show uart.yaml -of json | jq .goals

-----------

**********************
Stats
**********************

Print a summary of testpoint counts, coverage bindings, and goals::

    covsight testplan stats uart.yaml

JSON output for dashboards::

    covsight testplan stats uart.yaml -of json

-----------

**********************
Converting
**********************

Convert between YAML, JSON, and Hjson formats::

    covsight testplan convert uart.hjson                  # → YAML (default)
    covsight testplan convert uart.yaml -of json          # → JSON
    covsight testplan convert uart.yaml -o out.json       # write to file

Preserve ``imports`` without resolving them::

    covsight testplan convert uart.yaml --no-resolve-imports

-----------

**********************
Closure computation
**********************

:func:`~covsight.core.ncdb.testplan_closure.compute_closure` evaluates each
testpoint against the test history stored in the database:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status
     - Meaning
   * - ``CLOSED``
     - All mapped tests have at least one passing run
   * - ``PARTIAL``
     - Some passing, some failing
   * - ``FAILING``
     - All mapped tests failed
   * - ``NOT_RUN``
     - None of the mapped tests appear in the database
   * - ``N/A``
     - Testpoint has ``na = True``
   * - ``UNIMPLEMENTED``
     - Testpoint has an empty ``tests`` list

Test name matching uses exact match, seed-suffix strip, and wildcard prefix strategies.

CLI closure output with goal tree and coverage::

    covsight testplan closure coverage.cdb --show-goals --show-coverage

Filter by closure status::

    covsight testplan closure coverage.cdb --filter-status NOT_RUN FAILING

-----------

**********************
Stage gate evaluation
**********************

:func:`~covsight.core.ncdb.testplan_closure.stage_gate_status` determines whether
a regression is ready to advance to the next stage::

    gate = stage_gate_status(results, "V2", plan)
    if gate["passed"]:
        print("Ready to tape-out!")
    else:
        for r in gate["blocking"]:
            print(f"  BLOCKING: {r.testpoint.name}")

The gate passes when all testpoints at the target stage **and all stages
below it** (V1 < V2 < V2S < V3) are CLOSED or N/A.

-----------

**********************
Embedding and extracting
**********************

Embed a testplan in a ``.cdb`` (accepts YAML, JSON, or Hjson)::

    covsight testplan import coverage.cdb uart.yaml

Extract the embedded testplan back to a file::

    covsight testplan export coverage.cdb -o uart_extracted.yaml
    covsight testplan export coverage.cdb -of json

-----------

**********************
Waivers
**********************

Coverage and test failures can be suppressed with a
:class:`~covsight.core.ncdb.waivers.WaiverSet`::

    from covsight.core.ncdb.waivers import Waiver, WaiverSet

    ws = WaiverSet([
        Waiver(
            id="W-001",
            scope_pattern="top/uart/**",
            bin_pattern="reset_*",
            rationale="Reset coverage deferred to V2",
            approver="eng",
            approved_at="2025-01-01T00:00:00",
            expires_at="2026-01-01T00:00:00",
        )
    ])

    db.setWaivers(ws)
    NcdbWriter().write(db, "coverage.cdb")

.. seealso::

   * :ref:`test-history` — Binary test history API
   * :ref:`ncdb-format` — NCDB binary format specification
