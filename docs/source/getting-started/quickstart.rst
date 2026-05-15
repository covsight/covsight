##########
Quickstart
##########

This page walks through the most common workflow: import a coverage file from your
simulator, inspect it, and generate a shareable HTML report.

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

Step 3 — Generate a Shareable Report
=====================================

.. code-block:: bash

    covsight report coverage.ncdb -of html -o report.html

Open ``report.html`` in any browser — it is a single self-contained file that can
be emailed, archived, or hosted on a web server without any extra dependencies.

Step 4 — Merge Multiple Runs (optional)
========================================

If you have coverage from several test runs, merge them before reporting:

.. code-block:: bash

    covsight merge -o merged.ncdb test1.ncdb test2.ncdb test3.ncdb
    covsight report merged.ncdb -of html -o merged_report.html

Next Steps
==========

* :doc:`../importing/index` — more on importing from different sources
* :doc:`../working-with-coverage/analyzing` — analyze gaps and hotspots from the CLI
* :doc:`../reporting/exporting` — export to LCOV, Cobertura, or JaCoCo for CI/CD tools
* :doc:`../cicd/index` — ready-to-use CI/CD pipeline examples
