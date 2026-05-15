######################
JSON Coverage Report
######################

The JSON coverage-report format simplifies post-processing of a covsight
coverage report. It is easily read by Python and JSON libraries in other
languages, and is a direct transcription of the Coverage Report Object API.

Generating JSON Reports
=======================

.. code-block:: bash

   covsight report coverage.cdb -of json -o report.json

Python API
==========

You can build a coverage report object programmatically using the
``CoverageReportBuilder`` class from ``covsight.core``:

.. autoclass:: covsight.core.report.CoverageReportBuilder
   :members: build

CoverageReport Object
======================

The ``CoverageReport`` object is a tree of covergroups and coverpoints.

.. autoclass:: covsight.core.report.CoverageReport
   :members: covergroups, coverage

.. autoclass:: covsight.core.report.CoverageReport.Covergroup
   :members:

.. autoclass:: covsight.core.report.CoverageReport.CoverItem
   :members:

.. autoclass:: covsight.core.report.CoverageReport.Coverpoint
   :show-inheritance:
   :inherited-members:
   :members:

.. autoclass:: covsight.core.report.CoverageReport.Cross
   :show-inheritance:
   :inherited-members:
   :members:

JSON Schema Overview
====================

The top-level JSON object has a ``covergroups`` array and a ``coverage``
percentage field:

.. code-block:: json

   {
     "coverage": 73.5,
     "covergroups": [
       {
         "name": "my_covergroup",
         "coverage": 68.0,
         "instances": [
           {
             "name": "top.cg_i1",
             "coverage": 68.0,
             "coverpoints": [
               {
                 "name": "cp1",
                 "coverage": 50.0,
                 "bins": [
                   {"name": "a", "count": 5, "at_least": 1, "covered": true},
                   {"name": "b", "count": 0, "at_least": 1, "covered": false}
                 ]
               }
             ],
             "crosses": []
           }
         ]
       }
     ]
   }

.. seealso::

   * :doc:`html-report-format` — Interactive HTML report
   * :doc:`../formats/ncdb-format` — Primary storage format
