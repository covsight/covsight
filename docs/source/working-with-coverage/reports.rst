.. _reports:

#############################
Reports and CI/CD Integration
#############################

The :mod:`covsight.core.ncdb.reports` and :mod:`covsight.core.ncdb.testplan_export`
modules provide structured reports for testplan closure, regression delta, and
CI/CD export. Every report function returns a typed dataclass with a ``to_json()``
method; companion ``format_*()`` functions render the dataclass to human-readable text.

.. contents:: On this page
   :local:
   :depth: 2

-----------

**********************
Closure and gate reports
**********************

.. code-block:: python

    from covsight.core.ncdb.ncdb_ucis import NcdbUCIS
    from covsight.core.ncdb.testplan import get_testplan
    from covsight.core.ncdb.testplan_closure import compute_closure
    from covsight.core.ncdb.reports import (
        report_testpoint_closure,
        format_testpoint_closure,
        report_stage_gate,
        format_stage_gate,
    )

    db = NcdbUCIS("coverage.cdb")
    plan = get_testplan(db)
    results = compute_closure(plan, db)

    # Print the closure table
    summary = report_testpoint_closure(results)
    print(format_testpoint_closure(summary))

    # Evaluate a stage gate
    gate = report_stage_gate(results, "V2", plan)
    print(format_stage_gate(gate))

    # Machine-readable JSON
    import json
    data = json.loads(summary.to_json())

Stage-rollup output example::

    Testpoint                          Stage  Status     Pass   Fail
    ----------------------------------------------------------------
    uart_reset                         V1     ✓ CLOSED      5      0
    uart_loopback                      V2     ✗ FAILING     0      3
    ----------------------------------------------------------------

    Stage roll-up:
      V1     [████████████████████] 1/1 (100.0%)
      V2     [░░░░░░░░░░░░░░░░░░░░] 0/1 (0.0%)

    Total: 1/2 closed  (0 N/A)

-----------

**********************
Regression delta
**********************

Compare two closure result sets to find testpoints that changed status::

    from covsight.core.ncdb.reports import report_regression_delta, format_regression_delta

    results_baseline = compute_closure(plan, db_baseline)
    results_current  = compute_closure(plan, db_current)

    delta = report_regression_delta(results_current, results_baseline)
    print(format_regression_delta(delta))

-----------

**********************
JUnit XML export
**********************

Export closure results as a JUnit XML file for CI dashboards::

    from covsight.core.ncdb.testplan_export import export_junit_xml

    export_junit_xml(results, "closure_results.xml")

Or via the CLI::

    covsight testplan export-junit coverage.cdb --out closure_results.xml

The XML maps each testpoint to a ``<testcase>`` element. FAILING and
PARTIAL testpoints become ``<failure>`` elements; NOT_RUN becomes
``<skipped>``.

-----------

**********************
GitHub Annotations
**********************

Emit GitHub Actions workflow commands for inline PR annotations::

    from covsight.core.ncdb.testplan_export import export_github_annotations

    export_github_annotations(results)  # writes to stdout

In a GitHub Actions workflow::

    - name: Compute closure
      run: |
        python -c "
        from covsight.core.ncdb.ncdb_ucis import NcdbUCIS
        from covsight.core.ncdb.testplan import get_testplan
        from covsight.core.ncdb.testplan_closure import compute_closure
        from covsight.core.ncdb.testplan_export import export_github_annotations
        db = NcdbUCIS('coverage.cdb')
        plan = get_testplan(db)
        results = compute_closure(plan, db)
        export_github_annotations(results)
        "

-----------

**********************
GitHub Step Summary
**********************

Write a markdown table to ``$GITHUB_STEP_SUMMARY``::

    import os
    from covsight.core.ncdb.testplan_export import export_summary_markdown

    md = export_summary_markdown(results, stage_gate=gate)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(md)

.. seealso::

   * :ref:`testplan` — Testplan format and closure computation
   * :ref:`test-history` — Binary test history API
