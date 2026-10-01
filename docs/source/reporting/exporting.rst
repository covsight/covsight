################################
Exporting to CI/CD Formats
################################

``covsight show code-coverage`` exports line and branch coverage in two
formats read by CI/CD platforms and code-quality tools.

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Format
     - Consumed by
     - Command flag
   * - **Cobertura**
     - GitHub Actions coverage reporters, GitLab, Jenkins, Azure DevOps,
       SonarQube
     - ``--output-format cobertura``
   * - **LCOV**
     - genhtml, Codecov, Coveralls
     - ``--output-format lcov``

.. code-block:: bash

    covsight show code-coverage coverage.ncdb -of cobertura --source-root . -o coverage.xml
    covsight show code-coverage coverage.ncdb -of lcov --source-root . -o coverage.info

What is exported
================

* **Lines**: the executable lines -- every line of every statement or basic
  block, the body lines of each branch arm, and each branch's decision line.
  A decision line is hit as often as its arms in total; any other line shared
  by several statements reports the largest count.
* **Branches**: one record per branch arm (Cobertura reports them per line as
  ``condition-coverage="50% (1/2)"``).  The same branch in several instances
  is reported once, with the hit counts summed.

Neither format represents toggle, expression, condition or FSM coverage; use
``covsight show code-coverage`` (JSON or text), ``show toggle`` and
``show assertions`` for those.

Cobertura groups files into one package per source directory.

Source paths
============

Paths are written as the simulator recorded them, which is often absolute.
``--source-root DIR`` (``-sr``) makes paths under ``DIR`` relative to it --
pass the repository root so that CI tools can match files to the checkout.
Cobertura output lists ``DIR`` as its ``<source>``.

Line-level export needs a source location on each statement.  Databases
written before covsight-core recorded per-item locations
(``coveritem_sources.bin``) produce reports with branch-decision lines only;
re-import the simulator coverage to fix this.

JaCoCo and Clover output are not available.

For complete per-platform pipeline examples see :doc:`../cicd/index`.

See :doc:`../reference/cli` for the full ``show code-coverage`` option reference.
