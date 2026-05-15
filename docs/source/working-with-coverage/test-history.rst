.. _test-history:

############
Test History
############

covsight stores a rich, time-series history of every test run inside each NCDB
``.cdb`` file. This *binary test history* (NCDB v2) is designed for:

* **Trend analysis** — identify flaky or consistently-failing tests over
  hundreds or thousands of runs.
* **Regression detection** — spot when a test's pass rate drops using a
  CUSUM change-point algorithm.
* **Coverage provenance** — trace exactly which test runs contributed to the
  squashed coverage numbers.

.. contents:: On this page
   :local:
   :depth: 2

-----------

**********************
Quick-start
**********************

Record test results with :meth:`~covsight.core.ncdb.ncdb_ucis.NcdbUCIS.add_test_run`::

    from covsight.core.ncdb.ncdb_ucis import NcdbUCIS
    from covsight.core.ncdb.ncdb_writer import NcdbWriter
    from covsight.core.ncdb.constants import HIST_STATUS_OK, HIST_STATUS_FAIL
    from covsight.core.mem.mem_ucis import MemUCIS

    # Create or open a .cdb
    NcdbWriter().write(MemUCIS(), "coverage.cdb")   # once, to initialise
    db = NcdbUCIS("coverage.cdb")

    # Record runs
    db.add_test_run("uart_smoke", seed="42", status=HIST_STATUS_OK,
                    ts=1700000000, has_coverage=True)
    db.add_test_run("uart_smoke", seed="43", status=HIST_STATUS_FAIL,
                    ts=1700003600, has_coverage=False)

    # Save
    NcdbWriter().write(db, "coverage.cdb")

Query the results::

    db2 = NcdbUCIS("coverage.cdb")

    # All runs for one test
    history = db2.query_test_history("uart_smoke")
    for rec in history:
        print(rec.ts, rec.status)

    # Aggregate statistics
    entry = db2.get_test_stats("uart_smoke")
    print(f"total={entry.total_runs}  pass={entry.pass_count}  fail={entry.fail_count}")

    # Top-flaky across all tests
    for entry in db2.top_flaky_tests(10):
        print(entry.name_id, entry.flakiness_score)

-----------

**********************
Status and flag values
**********************

Status constants (in :mod:`covsight.core.ncdb.constants`):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Constant
     - Meaning
   * - ``HIST_STATUS_OK``
     - Run passed
   * - ``HIST_STATUS_FAIL``
     - Run failed
   * - ``HIST_STATUS_ERROR``
     - Test infrastructure error (not a test-logic failure)
   * - ``HIST_STATUS_TIMEOUT``
     - Run exceeded wall-clock budget
   * - ``HIST_STATUS_SKIP``
     - Run was explicitly skipped

Flag constants (combinable with ``|``):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Constant
     - Meaning
   * - ``HIST_FLAG_HAS_COV``
     - Run produced coverage data (counts.bin was updated)
   * - ``HIST_FLAG_REGRESS``
     - Run is part of a regression sweep
   * - ``HIST_FLAG_RERUN``
     - This is a re-run of a previously recorded test

-----------

**********************
Time-range queries
**********************

:meth:`~covsight.core.ncdb.ncdb_ucis.NcdbUCIS.query_test_history` accepts optional
``ts_from`` and ``ts_to`` Unix-timestamp bounds::

    import time
    yesterday = int(time.time()) - 86400

    # Only runs from the last 24 hours
    recent = db.query_test_history("my_test", ts_from=yesterday)

-----------

**********************
Merging history
**********************

History is merged automatically when two or more ``.cdb`` files are combined
with :class:`~covsight.core.ncdb.ncdb_merger.NcdbMerger`::

    from covsight.core.ncdb.ncdb_merger import NcdbMerger

    NcdbMerger().merge(["run_a.cdb", "run_b.cdb"], "merged.cdb")

The merger performs:

1. **Registry union** — all test names and seed strings from all sources are
   collected into a single merged registry, preserving insertion order.
2. **Stats merge** — per-test aggregate metrics (mean runtime, variance, pass
   rate) are combined using Chan's parallel formula for numerically stable
   Welford-style mean/variance.
3. **Bucket remap** — name_ids in each source's bucket files are remapped to
   the merged registry before being written to the output.
4. **Contrib-index remap** — run_ids in the contribution index are offset by
   the source's base run_id so merged run_ids remain globally unique.

.. note::

   Merging is idempotent: merging a file with itself produces the same
   statistics as the original (though run counts will double).

-----------

**********************
Squash coverage
**********************

Over time a ``.cdb`` accumulates contribution entries for every test run
that produced coverage. Squashing compresses these entries into the main
coverage counts and frees space::

    db.squash_coverage(policy=POLICY_PASS_ONLY)
    NcdbWriter().write(db, "coverage.cdb")

The squash event is recorded in the squash log so that provenance is never
lost. The ``policy`` argument controls which runs are squashed:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Constant
     - Behaviour
   * - ``POLICY_PASS_ONLY``
     - Squash only runs with ``HIST_STATUS_OK``
   * - ``POLICY_ALL``
     - Squash all runs regardless of status

-----------

**********************
Binary format overview
**********************

The v2 test history is stored as several members inside the NCDB ZIP archive.
See :ref:`ncdb-format` for the full technical specification.

.. seealso::

   * :ref:`ncdb-format` — Full NCDB binary format specification
   * :doc:`merging` — How to merge ``.cdb`` files on the command line
   * :doc:`analyzing` — Query and report coverage from the CLI
