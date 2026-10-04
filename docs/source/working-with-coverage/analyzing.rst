######################
Analyzing Coverage
######################

The ``covsight show`` sub-commands extract coverage data from any supported
database and print it in text or JSON format. Use them for quick checks,
scripting, and CI/CD gates.

Recommended Workflow
====================

Work through these commands in order for an efficient analysis session:

1. Get an overall health check
2. Find what is not covered
3. Prioritize where to work next
4. Drill down into specific items

Step 1 — Summary
================

.. code-block:: bash

    covsight show summary coverage.ncdb

Prints overall coverage percentage and a breakdown by type (functional, code,
assertion, toggle). Add ``--output-format json`` for machine-readable output:

.. code-block:: bash

    covsight show summary coverage.ncdb --output-format json | jq '.overall_coverage'

Step 2 — Gaps
=============

.. code-block:: bash

    covsight show gaps coverage.ncdb

Lists every item below 100% coverage. Use ``--threshold`` to show only items
below a specific percentage, and ``--limit`` to cap the output:

.. code-block:: bash

    covsight show gaps coverage.ncdb --threshold 80 --limit 20

Step 3 — Hotspots
=================

.. code-block:: bash

    covsight show hotspots coverage.ncdb

Provides prioritized recommendations (P0/P1/P2) based on coverage percentage
and potential impact. The ``--target`` option sets the goal:

.. code-block:: bash

    covsight show hotspots coverage.ncdb --target 90

Step 4 — Drill Down
===================

.. rubric:: Covergroups

.. code-block:: bash

    covsight show covergroups coverage.ncdb
    covsight show covergroups coverage.ncdb --pattern "alu_*"

.. rubric:: Bins

.. code-block:: bash

    covsight show bins coverage.ncdb --covergroup addr_cg
    covsight show bins coverage.ncdb --status missed   # only uncovered bins

.. rubric:: Tests

.. code-block:: bash

    covsight show tests coverage.ncdb

Shows per-test pass/fail status and test-specific coverage contribution.

.. rubric:: Hierarchy

.. code-block:: bash

    covsight show hierarchy coverage.ncdb --depth 3

.. rubric:: Code coverage on the source

.. code-block:: bash

    covsight show code-coverage coverage.ncdb -of text   # totals per kind, instance, file
    covsight show source coverage.ncdb -sr .             # each line with its hit count
    covsight show source coverage.ncdb -sr . -u          # only lines with something missed

``show source`` prints each source line with its hit count, and under the
line the branch arms and expression rows that start on it. ``#`` marks a
line, arm or row never hit; ``~`` a line that ran but has an arm or row
under it that did not. ``--source-root`` / ``-sr`` is the directory the
recorded source paths are read from; ``--file`` / ``-f`` picks files.
:doc:`../examples/01-code-basics` walks through reading it.

.. rubric:: Assertions and Toggle

.. code-block:: bash

    covsight show assertions coverage.ncdb
    covsight show toggle coverage.ncdb

Other Options
=============

All ``show`` commands accept:

* ``--output-format`` / ``-of`` — ``json``, ``text`` (default varies by command)
* ``--out`` / ``-o`` — write output to a file instead of stdout
* ``--input-format`` / ``-if`` — source format (default: auto-detected)

Coverage Gate Script
====================

Check whether coverage meets a threshold in CI/CD:

.. code-block:: bash

    #!/bin/bash
    COVERAGE=$(covsight show summary coverage.ncdb -of json | jq -r '.overall_coverage')
    THRESHOLD=80
    if (( $(echo "$COVERAGE < $THRESHOLD" | bc -l) )); then
        echo "Coverage ${COVERAGE}% is below ${THRESHOLD}%"
        exit 1
    fi

See the full parameter reference in :doc:`../reference/cli`.

Next Steps
==========

* :doc:`comparing` — compare two databases to detect regressions
* :doc:`../reporting/exporting` — export to Cobertura or LCOV
* :doc:`../cicd/index` — ready-to-use CI/CD pipeline examples
