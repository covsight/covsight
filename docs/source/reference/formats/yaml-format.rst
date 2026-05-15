#########################
YAML Coverage Data Format
#########################

The YAML coverage-data format is used to represent functional coverage
data in a manner that is accurate and relatively easy for humans and
tools to create and process. covsight can import YAML coverage files
using ``covsight convert``:

.. code-block:: bash

   covsight convert coverage.yaml coverage.cdb

Format Overview
===============

Every coverage-data document has a ``coverage`` element as its root with
a list of covergroup types.

.. code-block:: yaml

   coverage:
     - type: my_covergroup
       instances:
         - name: top.cg_i1
           coverpoints:
             - name: cp1
               atleast: 1
               bins:
                 - {name: "a", count: 5}
                 - {name: "b", count: 0}
           crosses: []

Top-Level Structure
-------------------

The document root is a mapping with a single ``coverage`` key whose
value is a list of **covergroup type** objects.

Covergroup Type
---------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``type``
     - string
     - Covergroup type name
   * - ``instances``
     - list
     - List of covergroup instance objects

Covergroup Instance
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Hierarchical instance name (e.g. ``top.cg_i1``)
   * - ``coverpoints``
     - list
     - List of coverpoint objects
   * - ``crosses``
     - list
     - List of cross objects (optional)

Coverpoint
----------

A coverpoint lists the bins it monitors. Each coverpoint may specify
an ``atleast`` count (default: 1) that a bin must reach to count as covered.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Coverpoint name
   * - ``atleast``
     - integer
     - Minimum hit count for coverage (default: 1)
   * - ``bins``
     - list
     - List of bin objects

Cross
-----

A cross lists the coverpoints from which it is composed and its cross bins.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Cross name
   * - ``coverpoints``
     - list of strings
     - Names of the crossed coverpoints
   * - ``atleast``
     - integer
     - Minimum hit count for coverage (default: 1)
   * - ``bins``
     - list
     - List of cross bin objects (same structure as coverpoint bins)

Coverage Bin
------------

A coverage bin associates a bin name with its hit count.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``name``
     - string
     - Bin name
   * - ``count``
     - integer
     - Number of times the bin was hit

.. seealso::

   * :doc:`xml-interchange` — XML interchange format
   * :doc:`ncdb-format` — NCDB binary format (primary storage)
