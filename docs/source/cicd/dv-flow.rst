########
dv-flow
########

covsight ships a `dv-flow <https://github.com/dv-flow/dv-flow-mgr>`_ package,
``covsight``, so a flow can import, merge, inspect and check coverage next to
the simulation tasks from dv-flow-libhdlsim. Installing covsight registers the
package; a flow imports it by name:

.. code-block:: yaml

    package:
      name: my_tb
      imports: [{name: hdlsim}, {name: covsight}]

Tasks
=====

.. list-table::
   :header-rows: 1
   :widths: 18 32 50

   * - Task
     - Takes
     - Does
   * - ``covsight.Import``
     - hdlsim ``TestResult`` / ``SimRunResult`` / ``SuiteResult``, or a
       ``simCovDb`` FileSet
     - Converts each coverage database (Verilator ``coverage.dat``) to an
       NCDB file (filetype ``covsightNCDB``), recording the test's name, seed
       and verdict. Reconverts only when the source or the importer changes.
   * - ``covsight.Merge``
     - ``covsightNCDB`` FileSets
     - Merges them into one NCDB (``output``, default ``merged.cdb``).
   * - ``covsight.Show``
     - one ``covsightNCDB``
     - Runs covsight commands on the database and keeps each one's output
       (filetype ``covsightTranscript``: one ``.txt`` per command and a
       ``transcript.json`` index).
   * - ``covsight.Check``
     - one ``covsightNCDB``; the runs; the image
     - Checks the run against an ``expect.yaml`` file (below) and fails with
       one marker per difference. Writes ``check.json``.

Parameters
----------

``covsight.Import``
  ``test_name``, ``seed``, ``status`` override what the simulation results
  say. ``on_unsupported`` (``error``/``warn``/``skip``) handles a database in a
  format covsight cannot read. ``include_std`` keeps coverage of Verilator's
  built-in ``std`` package (dropped by default).

``covsight.Merge``
  ``output``: the merged file's name.

``covsight.Show``
  ``commands``: covsight commands without the database, for example
  ``show code-coverage -of text``. The database name goes after the
  subcommand words, or in place of ``{db}``. When ``commands`` is empty, the
  ``transcript`` list in the ``expect`` file is used.

``covsight.Check``
  ``expect`` (default ``expect.yaml``, relative to the flow's directory);
  ``parity`` (default true) compares with ``verilator_coverage``;
  ``include_std`` must match ``covsight.Import``'s.

Example
=======

One Verilator image, two seeds, merged, then shown and checked:

.. code-block:: yaml

    package:
      name: ex
      imports: [{name: hdlsim}, {name: covsight}]
      tasks:
      - name: rtl
        uses: std.FileSet
        with: {type: systemVerilogSource, include: "*.sv"}
      - name: img
        uses: hdlsim.vlt.SimImage
        needs: [rtl]
        with: {top: [tb], cov: full}
      - name: seed1
        uses: hdlsim.vlt.SimRun
        needs: [img]
        with: {plusargs: ["verilator+seed+1"]}
      - name: seed2
        uses: hdlsim.vlt.SimRun
        needs: [img]
        with: {plusargs: ["verilator+seed+2"]}
      - name: cov
        uses: covsight.Import
        needs: [seed1, seed2]
      - name: merged
        uses: covsight.Merge
        needs: [cov]
      - root: show
        uses: covsight.Show
        needs: [merged]
        with: {expect: expect.yaml}
      - root: check
        uses: covsight.Check
        needs: [merged, seed1, seed2, img]

.. code-block:: bash

    dfm run check     # fails if a number moved
    dfm run show      # transcripts in rundir/ex.show/

``covsight.Check`` needs the merged database, the runs (for their
``coverage.dat`` files) and the image (for its ``build.log``), so list all
three in ``needs``.

``expect.yaml``
===============

.. code-block:: yaml

    totals:            # covered/total per kind; kinds left out are not checked
      line: 11/11
      branch: 7/8
      covergroup: 3/4
    transcript:        # commands covsight.Show runs, in order
      - show summary -of text
      - show code-coverage -of text
    parity:            # known differences from verilator_coverage, explained
      covergroup: Verilator counts the default bin
    warnings:          # Verilator build warnings expected (regular expressions)
      - "COVERIGN"

Kinds are ``line``, ``branch``, ``expression``, ``condition``, ``toggle``,
``fsm_state``, ``fsm_transition``, ``block``, ``covergroup``, ``cover`` and
``assertion``. Errors in the file are reported with its name and line number.
A JSON Schema for editors ships as ``covsight/dvflow/expect.schema.json``.

The three checks:

``totals``
  The merged database's covered/total for each listed kind must equal the
  value given.

``parity``
  covsight's numbers are compared with ``verilator_coverage --report summary``
  over the runs' ``coverage.dat`` files, after removing Verilator's ``std``
  package points (which covsight drops). Any kind that differs needs a
  ``parity`` entry giving the reason; an entry for a kind that agrees also
  fails, so notes are removed once the difference goes away.

``warnings``
  Each pattern must match at least one ``%Warning-`` line in the image's
  ``build.log``, and every warning there must match a pattern. A new
  Verilator warning therefore fails the check until it is listed.
