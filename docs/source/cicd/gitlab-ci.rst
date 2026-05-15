##########
GitLab CI
##########

The example below shows a complete coverage workflow for GitLab CI: merge
coverage, export Cobertura for the GitLab coverage visualization, and publish
an HTML report as a job artifact.

Full Workflow Example
=====================

.. code-block:: yaml

    stages:
      - test
      - coverage

    run_tests:
      stage: test
      script:
        - make run_all_tests   # produces test_*.ncdb
      artifacts:
        paths:
          - test_*.ncdb

    coverage:
      stage: coverage
      script:
        - pip install covsight

        # Merge
        - covsight merge -o merged.ncdb test_*.ncdb

        # Coverage gate
        - |
          COV=$(covsight show summary merged.ncdb -of json | jq -r '.overall_coverage')
          echo "Coverage: ${COV}%"
          python3 -c "import sys; sys.exit(0 if float('$COV') >= 80 else 1)" \
            || (echo "Coverage below 80%" && exit 1)

        # Export Cobertura for GitLab coverage widget
        - covsight show code-coverage merged.ncdb --output-format cobertura > coverage.xml

        # Generate shareable HTML report
        - covsight report merged.ncdb -of html -o coverage_report.html

      coverage: '/Coverage:\s+(\d+\.\d+)%/'

      artifacts:
        reports:
          coverage_report:
            coverage_format: cobertura
            path: coverage.xml
        paths:
          - coverage_report.html
        expire_in: 1 week

Verilator Projects
==================

.. code-block:: yaml

    - covsight merge --input-format vltcov -o merged.ncdb tests/*/coverage.dat
