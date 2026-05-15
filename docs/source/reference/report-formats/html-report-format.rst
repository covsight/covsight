###########################
HTML Coverage Report Format
###########################

The HTML coverage report format generates a single-file, interactive HTML
report for visualization and analysis of coverage data. The report can be
opened directly in any modern web browser without a web server or external
dependencies.

**Key Features:**

* **Single-File Portability** — All data, code, and styles embedded in one HTML file
* **Interactive Navigation** — Expandable hierarchical tree with filtering and search
* **D3.js Visualizations** — Pie charts, bar charts, and treemaps for coverage analysis
* **Coverpoint Bin Details** — View individual bins with hit counts, goals, and status
* **Zero Dependencies** — JavaScript libraries loaded from CDN (works offline if cached)
* **Responsive Design** — Professional UI that works on desktop and tablet

Generating HTML Reports
=======================

Command Line
------------

Use ``covsight report`` with the ``-of html`` option:

.. code-block:: bash

   # Basic HTML report
   covsight report coverage.cdb -of html -o report.html

   # Open in default browser
   xdg-open report.html    # Linux
   open report.html        # macOS

CI/CD Integration
-----------------

.. code-block:: bash

   #!/bin/bash
   # Run tests and collect coverage
   run_tests.sh

   # Generate HTML report
   covsight report coverage.cdb -of html -o coverage_report.html

   # Archive as build artifact
   cp coverage_report.html $ARTIFACTS_DIR/

Report Features
===============

Summary Dashboard
-----------------

* **Total Coverage Percentage** — Overall coverage across all items
* **Total / Covered / Uncovered Items** — Counts by bin
* **Coverage by Type** — Breakdown by functional, line, branch, toggle, etc.
* **Progress Bar** — Visual representation of overall coverage

Hierarchical Navigation
-----------------------

The hierarchy view displays the complete design/verification structure:

* **Expandable/Collapsible Nodes** — Click arrows to show/hide children
* **Type-Specific Icons** — Visual distinction between modules, covergroups, coverpoints
* **Coverage Indicators** — Color-coded percentages (green ≥80%, orange 50–80%, red <50%)

**Filtering:**

* **Search** — Real-time text search across scope names
* **Status Filter** — Filter by all / covered / uncovered / partial coverage
* **Coverage Threshold** — Show only scopes meeting a minimum percentage

Coverpoint Bin Details
-----------------------

Clicking a coverpoint displays a table with:

1. **Bin Name** — Identifier (monospace font)
2. **Type** — ``bin`` (blue) / ``ignore_bin`` (orange) / ``illegal_bin`` (red)
3. **Hits** — Hit count (formatted with thousands separators)
4. **Goal** — Target hit count (``at_least`` threshold)
5. **Status** — ``covered`` (green) / ``uncovered`` (red) / ``ignored`` (gray) / ``illegal`` (red/ok)
6. **Coverage** — Mini progress bar with percentage

Interactive Visualizations
---------------------------

The Charts tab provides three D3.js-powered views:

* **Pie Chart: Coverage by Type** — Breakdown by coverage type with hover tooltips
* **Bar Chart: Top Coverage Gaps** — The 10 scopes with the lowest coverage
* **Treemap: Hierarchical Coverage** — Nested rectangles sized by weight, colored by coverage

Technical Details
=================

File Structure
--------------

The HTML report is completely self-contained:

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       <style>/* Embedded CSS (~15 KB) */</style>
   </head>
   <body>
       <!-- Application HTML structure -->
       <script id="coverage-data" type="application/json">
       { "metadata": {...}, "summary": {...}, "scopes": [...] }
       </script>
       <script>/* Embedded JavaScript + Alpine.js + D3.js (~20 KB) */</script>
       <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
       <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
   </body>
   </html>

Embedded Data Format
---------------------

.. code-block:: json

   {
       "metadata": {
           "generator": "covsight",
           "timestamp": "2024-02-12 02:00:00",
           "database": "coverage.cdb"
       },
       "summary": {
           "total_coverage": 73.5,
           "total_items": 1250,
           "covered_items": 919,
           "uncovered_items": 331,
           "coverage_by_type": {
               "functional": 68.0,
               "line": 82.5,
               "branch": 71.2
           }
       },
       "scopes": [
           {
               "id": "scope_1",
               "name": "top",
               "type": "DU_MODULE",
               "coverage": 73.5,
               "weight": 1,
               "children": [],
               "bins": []
           }
       ]
   }

Technologies
------------

* **Alpine.js v3** — Lightweight reactive framework
* **D3.js v7** — Data visualization library
* **ES6+ JavaScript** — Modern browser features required (Chrome 90+, Firefox 88+, Safari 14+)

File Size
---------

* **Template + Code**: ~50–60 KB
* **Data**: Variable based on coverage database size
* **Total**: Usually 100–500 KB for typical projects

Limitations
===========

* **Read-Only** — Cannot modify coverage data from the report
* **No Real-Time Updates** — Static snapshot at generation time
* **CDN Dependency** — Requires internet for first library load
* **Very Large Data** — Databases of 100 MB+ may load slowly in browser

.. seealso::

   * :doc:`json-report-format` — Machine-readable report format
   * :doc:`../formats/ncdb-format` — Primary storage format
