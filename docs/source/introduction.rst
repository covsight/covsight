############
Introduction
############

What is covsight?
=================

covsight is a coverage analysis and reporting toolkit for functional hardware
verification. It ingests coverage data produced by simulators and verification
frameworks, stores it in a unified internal model, and provides tools to explore,
merge, analyze, and report that data.

covsight is built on top of **covsight-core**, a C-extension library that
implements the Accellera Unified Coverage Interoperability Standard (UCIS) data
model. The ``covsight`` package adds the command-line interface, report
formatters, and analysis algorithms on top of that core.

Supported Input Formats
=======================

* **NCDB** — Native Coverage DataBase; compact ZIP-based binary format (default)
* **UCIS XML** — Accellera-defined interchange format
* **UCIS YAML** — Human-readable text format
* **Verilator** — SystemC::Coverage-3 ``.dat`` files (functional + code coverage)
* **cocotb-coverage** — XML or YAML output from cocotb-coverage
* **AVL** — JSON output from the Apheleia Verification Library

Command-Line Tools
==================

The ``covsight`` command provides several sub-commands for coverage analysis:

**Convert**
  Convert coverage data between supported formats::

      covsight convert --input-format vltcov coverage.dat -o coverage.ncdb

**Merge**
  Combine multiple coverage databases into one::

      covsight merge -o merged.ncdb test1.ncdb test2.ncdb

**Show**
  Extract and analyze coverage data in text or JSON format:

  .. list-table::
     :header-rows: 1
     :widths: 30 70

     * - Sub-command
       - Purpose
     * - ``show summary``
       - Overall coverage percentage and per-type breakdown
     * - ``show gaps``
       - Items below 100% coverage
     * - ``show hotspots``
       - Priority-ordered recommendations (P0/P1/P2)
     * - ``show covergroups``
       - Detailed covergroup information
     * - ``show bins``
       - Bin-level hit counts and status
     * - ``show tests``
       - Per-test pass/fail and coverage contribution
     * - ``show hierarchy``
       - Design hierarchy tree
     * - ``show metrics``
       - Statistical analysis
     * - ``show compare``
       - Regression detection against a baseline
     * - ``show code-coverage``
       - Export to LCOV, Cobertura, JaCoCo, or Clover
     * - ``show assertions``
       - SVA/PSL assertion coverage
     * - ``show toggle``
       - Signal toggle coverage

**Report**
  Generate a coverage report in HTML, JSON, or text format::

      covsight report coverage.ncdb -of html -o report.html

**History**
  Query per-test run history stored in NCDB databases.

**Testplan**
  Import, evaluate, and export testplan closure results.

Quick Example
=============

.. code-block:: bash

    # Import Verilator coverage
    covsight convert --input-format vltcov coverage.dat -o coverage.ncdb

    # Merge several runs
    covsight merge -o regression.ncdb test_*.ncdb

    # Check overall coverage
    covsight show summary regression.ncdb

    # Generate an HTML report
    covsight report regression.ncdb -of html -o report.html

Architecture
============

.. code-block:: text

    ┌────────────────────────────────────────┐
    │  covsight  (this package)              │
    │  CLI · report formatters · analysis    │
    └────────────────┬───────────────────────┘
                     │ uses
    ┌────────────────▼───────────────────────┐
    │  covsight-core                         │
    │  UCIS data model · format I/O · merge  │
    │  Python: covsight.core.*               │
    └────────────────────────────────────────┘

The ``covsight.core`` namespace is populated by the ``covsight-core`` package
and is the stable Python API for programmatic access to coverage data.
See :doc:`reference/python-api/index` for the full API reference.
