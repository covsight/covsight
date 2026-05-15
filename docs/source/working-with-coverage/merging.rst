###############
Merging Coverage
###############

Coverage from multiple test runs must be merged into a single database before
you can report on the full regression. Use ``covsight merge``:

.. code-block:: bash

    covsight merge -o merged.ncdb test1.ncdb test2.ncdb test3.ncdb

Common Options
==============

``--input-format`` / ``-if``
    Source format. Specify once and it applies to all inputs.
    Defaults to auto-detection. Use ``vltcov``, ``cocotb-xml``, etc. to merge
    directly from simulator output without a prior convert step.

    .. code-block:: bash

        covsight merge --input-format vltcov -o merged.ncdb \
            test1/coverage.dat test2/coverage.dat

``--output-format`` / ``-of``
    Output format. Defaults to ``ncdb``.

    .. code-block:: bash

        covsight merge --output-format ncdb -o merged.ncdb \
            test1.ncdb test2.ncdb test3.ncdb

NCDB — Fast, Compact Merging
==============================

The **NCDB** format offers the best merge performance and the smallest disk
footprint (typically 100–200× smaller than SQLite). Use ``ncdb`` as the output
format to accumulate per-test ``.cdb`` files:

.. code-block:: bash

    # Per-test run (convert after simulation)
    covsight convert -if vltcov -of ncdb -o test_42.cdb coverage.dat

    # Merge all per-test NCDB files into one
    covsight merge --input-format ncdb --output-format ncdb \
        -o regression.cdb tests/test_*.cdb

When all input files share the same scope-tree structure, NCDB uses a
*same-schema fast-merge* path that reduces the merge to element-wise integer
addition over a flat array — no SQL overhead, no scope-tree parsing.
See :doc:`../reference/formats/ncdb-format` for technical details.

Typical Regression Workflow
============================

.. code-block:: bash

    # 1. Run tests (each produces a coverage file)
    make run_all_tests   # produces test_*.ncdb

    # 2. Merge
    covsight merge -o regression.ncdb test_*.ncdb

    # 3. Analyze or report
    covsight show summary regression.ncdb
    covsight report regression.ncdb -of html -o regression_report.html

Next Steps
==========

* :doc:`analyzing` — summarize, find gaps, identify hotspots
* :doc:`../reporting/html-report` — generate a shareable HTML report
