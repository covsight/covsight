##################
Importing Coverage
##################

covsight reads coverage from several simulator and verification framework formats and
converts them all into the same internal model. Once imported, every tool in
covsight works identically regardless of the original source.

Supported Sources
=================

.. list-table::
   :header-rows: 1
   :widths: 30 25 25 20

   * - Source
     - ``--input-format``
     - File extension
     - Guide
   * - Verilator
     - ``vltcov``
     - ``.dat``
     - :doc:`verilator`
   * - cocotb-coverage (XML)
     - ``cocotb-xml``
     - ``.xml``, ``.cov``
     - :doc:`cocotb`
   * - cocotb-coverage (YAML)
     - ``cocotb-yaml``
     - ``.yml``, ``.yaml``
     - :doc:`cocotb`
   * - AVL (JSON)
     - ``avl-json``
     - ``.json``
     - :doc:`avl`
   * - UCIS XML
     - ``xml`` *(default)*
     - ``.xml``
     - —
   * - UCIS YAML
     - ``yaml``
     - ``.yaml``
     - —

.. toctree::
   :maxdepth: 1

   verilator
   cocotb
   avl
