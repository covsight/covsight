############################
Importing Verilator Coverage
############################

Verilator writes coverage data in the **SystemC::Coverage-3** text format
(usually ``coverage.dat``). covsight imports both functional coverage
(covergroups, coverpoints, bins) and code coverage (line, branch,
expression, toggle, FSM).

Basic Import
============

.. code-block:: bash

    covsight convert --input-format vltcov coverage.dat -o coverage.ncdb

Merging Multiple Runs
=====================

Convert each run, then merge the NCDB files:

.. code-block:: bash

    for t in test1 test2 test3; do
        covsight convert $t/coverage.dat -o $t.ncdb --test-name $t
    done
    covsight merge test1.ncdb test2.ncdb test3.ncdb -o merged.ncdb

Converting first records each run under its own test name.
``covsight merge`` also accepts ``coverage.dat`` files directly
(``--input-format vltcov``); the merged data is the same either way.

Generating Verilator Coverage
==============================

Build the simulation with coverage instrumentation, then run it. The run
writes ``coverage.dat`` to the working directory:

.. code-block:: bash

    verilator --binary --timing --coverage --top-module tb design.sv tb.sv
    ./obj_dir/Vtb

``--coverage`` turns on every kind below. To choose kinds, use the
individual flags instead:

==============================  ==============================================
Flag                            Effect
==============================  ==============================================
``--coverage-line``             Line and branch (block) coverage
``--coverage-toggle``           Toggle coverage of signals and ports
``--coverage-expr``             Expression term coverage
``--coverage-fsm``              FSM state and arc coverage
``--coverage-user``             ``cover property`` and other user coverage
``--coverage-underscore``       Also cover signals whose names start with ``_``
``--coverage-max-width <n>``    Widest signal that gets toggle coverage
``--coverage-expr-max <n>``     Most term combinations per expression
``--coverage-per-instance``     Separate counters per instance, not per module
==============================  ==============================================

Covergroups in the design are recorded in the same ``coverage.dat``.

Next Steps
==========

* :doc:`../working-with-coverage/merging` — combine runs into a single database
* :doc:`../working-with-coverage/analyzing` — analyze gaps and hotspots
* :doc:`../reporting/html-report` — generate an HTML report
