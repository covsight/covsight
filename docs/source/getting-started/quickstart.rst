##########
Quickstart
##########

This page walks through the most common workflow: import a coverage file from your
simulator, inspect it, and look at code coverage per instance and per file.

Step 1 — Import
===============

Convert your simulator's native coverage output to the NCDB format:

.. tab-set::

   .. tab-item:: Verilator

      .. code-block:: bash

          covsight convert --input-format vltcov coverage.dat -o coverage.ncdb

   .. tab-item:: cocotb-coverage

      .. code-block:: bash

          covsight convert --input-format cocotb-xml coverage.xml -o coverage.ncdb
          # or for YAML output from cocotb-coverage:
          covsight convert --input-format cocotb-yaml coverage.yml -o coverage.ncdb

   .. tab-item:: AVL

      .. code-block:: bash

          covsight convert --input-format avl-json coverage.json -o coverage.ncdb

See :doc:`../importing/index` for more detail on each source.

Step 2 — Check the Summary
===========================

Get an instant overview without generating a report file:

.. code-block:: bash

    covsight show summary coverage.ncdb

This prints the overall coverage percentage and a breakdown by type (functional,
code, assertion, toggle).

Step 3 — Look at Code Coverage
===============================

.. code-block:: bash

    covsight show code-coverage coverage.ncdb -of text

This prints tables of line, branch, expression and toggle coverage: totals,
then per instance, then per file. A single-file HTML report
(``covsight report -of html``) is planned; see :doc:`../reporting/html-report`.

Step 4 — Merge Multiple Runs (optional)
========================================

If you have coverage from several test runs, merge them, then inspect the
merged database the same way:

.. code-block:: bash

    covsight merge -o merged.ncdb test1.ncdb test2.ncdb test3.ncdb
    covsight show code-coverage merged.ncdb -of text

Next Steps
==========

* :doc:`../importing/index` — more on importing from different sources
* :doc:`../working-with-coverage/analyzing` — analyze gaps and hotspots from the CLI
* :doc:`../reporting/exporting` — export to Cobertura or LCOV for CI/CD tools
* :doc:`../cicd/index` — ready-to-use CI/CD pipeline examples
