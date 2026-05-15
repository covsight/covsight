##############
GitHub Actions
##############

The examples below show a complete coverage workflow for GitHub Actions: run tests,
merge coverage, export to Codecov, publish an HTML report artifact, and gate the
build on a minimum coverage threshold.

Full Workflow Example
=====================

.. code-block:: yaml

    name: Coverage

    on:
      push:
        branches: [main]
      pull_request:

    jobs:
      coverage:
        runs-on: ubuntu-latest

        steps:
          - uses: actions/checkout@v4

          - uses: actions/setup-python@v5
            with:
              python-version: "3.11"

          - name: Install covsight
            run: pip install covsight

          - name: Run tests
            run: make run_all_tests   # produces test_*.ncdb or test_*.dat

          - name: Merge coverage
            run: covsight merge -o merged.ncdb test_*.ncdb

          - name: Check coverage threshold
            run: |
              COV=$(covsight show summary merged.ncdb -of json | jq -r '.overall_coverage')
              echo "Coverage: ${COV}%"
              python -c "import sys; sys.exit(0 if float('$COV') >= 80 else 1)" \
                || (echo "Coverage below 80%" && exit 1)

          - name: Export LCOV for Codecov
            run: covsight show code-coverage merged.ncdb --output-format lcov > coverage.info

          - name: Upload to Codecov
            uses: codecov/codecov-action@v4
            with:
              files: ./coverage.info

          - name: Generate HTML report
            run: covsight report merged.ncdb -of html -o coverage_report.html

          - name: Upload HTML report artifact
            uses: actions/upload-artifact@v4
            with:
              name: coverage-report
              path: coverage_report.html

Verilator Projects
==================

Replace the merge step if your tests produce ``.dat`` files:

.. code-block:: yaml

    - name: Merge Verilator coverage
      run: covsight merge --input-format vltcov -o merged.ncdb tests/*/coverage.dat

Cobertura Upload
================

If you prefer Cobertura (e.g. for GitHub code coverage annotations):

.. code-block:: yaml

    - name: Export Cobertura
      run: covsight show code-coverage merged.ncdb --output-format cobertura > coverage.xml
