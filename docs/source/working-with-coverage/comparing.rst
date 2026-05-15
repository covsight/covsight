##########################
Comparing Coverage Databases
##########################

``covsight show compare`` compares two coverage databases and reports what changed.
Use it in nightly regressions to detect coverage regressions before they accumulate.

Basic Usage
===========

.. code-block:: bash

    covsight show compare baseline.ncdb current.ncdb

Output (text format) shows:

* Items whose coverage **increased**
* Items whose coverage **decreased** (regressions)
* New items present in ``current`` but absent from ``baseline``
* Removed items present in ``baseline`` but absent from ``current``
* Bin-level changes for any changed coverpoint

JSON Output
===========

.. code-block:: bash

    covsight show compare baseline.ncdb current.ncdb --output-format json \
        | jq '.regressions'

Typical Regression Integration
===============================

Save the previous run's database as the baseline, then compare after each run:

.. code-block:: bash

    # After tests pass
    cp regression.ncdb regression_baseline.ncdb
    make run_all_tests
    covsight merge -o regression.ncdb test_*.ncdb

    # Check for regressions
    covsight show compare regression_baseline.ncdb regression.ncdb

For a full CI/CD example see :doc:`../cicd/github-actions`.

Next Steps
==========

* :doc:`../reporting/html-report` — generate a detailed visual report
* :doc:`../cicd/index` — automate comparison in your pipeline
