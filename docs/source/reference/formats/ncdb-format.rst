.. _ncdb-format:

############################
NCDB Coverage File Format
############################

NCDB (*Native Coverage DataBase*) is the primary storage format used by
``covsight``. It is a compact, ZIP-based binary format for storing and
merging UCIS coverage data.

.. note::

   The detailed NCDB format specification — including the binary encodings
   for ``scope_tree.bin``, ``counts.bin``, ``strings.bin``, and all optional
   archive members — is maintained in the **covsight-core** package
   documentation, since covsight-core owns the NCDB reader and writer
   implementation.

   Refer to the covsight-core reference for:

   * Archive structure and member descriptions
   * Primitive encodings (LEB128 varints, string tables)
   * ``manifest.json``, ``history.json``, ``sources.json`` schemas
   * Optional members: ``attrs.bin``, ``toggle.bin``, ``cross.bin``, etc.
   * Same-schema and cross-schema merge algorithms
   * Testplan and waivers JSON members
   * Size and performance benchmarks
   * Complete standalone reader example

Overview
========

An NCDB file uses the ``.cdb`` extension and is a standard ZIP archive.
covsight distinguishes NCDB from legacy SQLite ``.cdb`` files by inspecting
the first 4 bytes: NCDB files begin with the ZIP magic ``PK\x03\x04``
(or ``PK\x05\x06`` for an empty archive), while SQLite files begin with
``SQLite format 3\x00``.

The ``manifest.json`` member at the archive root carries all metadata
needed to read or merge the file, including a ``schema_hash`` that enables
fast same-schema merges without parsing the scope tree.

.. seealso::

   * :doc:`xml-interchange` — XML interchange format (import/export)
   * :doc:`yaml-format` — YAML human-readable format (import)
   * :ref:`working-with-coverage-merging` — How to merge databases using the CLI
