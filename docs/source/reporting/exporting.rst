################################
Exporting to CI/CD Formats
################################

``covsight show code-coverage`` exports code coverage data in industry-standard
formats consumed by CI/CD platforms and code-quality tools.

Format Overview
===============

.. list-table::
   :header-rows: 1
   :widths: 20 45 35

   * - Format
     - Consumed by
     - Command flag
   * - **LCOV**
     - genhtml, Codecov, Coveralls, GitLab CI
     - ``--output-format lcov``
   * - **Cobertura**
     - Jenkins, GitLab CI, SonarQube, Azure DevOps
     - ``--output-format cobertura``
   * - **JaCoCo**
     - Maven, Gradle, SonarQube, Bamboo
     - ``--output-format jacoco``
   * - **Clover**
     - Bamboo, Jenkins (Clover plugin), IntelliJ
     - ``--output-format clover``

Usage
=====

.. code-block:: bash

    # LCOV
    covsight show code-coverage coverage.ncdb --output-format lcov > coverage.info

    # Cobertura
    covsight show code-coverage coverage.ncdb --output-format cobertura > coverage.xml

    # JaCoCo
    covsight show code-coverage coverage.ncdb --output-format jacoco > jacoco.xml

    # Clover
    covsight show code-coverage coverage.ncdb --output-format clover > clover.xml

Choosing a Format
=================

* If you use **Codecov or Coveralls**, use LCOV.
* If you use **Jenkins** with the Cobertura plugin, use Cobertura.
* If you use **SonarQube**, Cobertura and JaCoCo are both supported; check your
  scanner configuration.
* If you use **Bamboo**, use Clover.
* If you are unsure, Cobertura has the broadest tool support.

For complete per-platform pipeline examples see :doc:`../cicd/index`.

See :doc:`../reference/cli` for the full ``show code-coverage`` option reference.
