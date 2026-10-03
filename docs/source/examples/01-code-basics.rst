######################
01 — Code coverage
######################

Line, branch and expression coverage of a small design: one test that
leaves a hole, finding the hole with the CLI, and a second test that
closes it.

The design
==========

A saturating accumulator: ``op`` holds, adds, subtracts (stopping at zero)
or clears, and an add that overflows saturates the output.

.. literalinclude:: ../../../examples/01-code-basics/design.sv
   :language: systemverilog
   :linenos:

The testbench drives operations and checks every result against a model.
``+TEST=basic`` adds, subtracts and clears with small values;
``+TEST=full`` also overflows an add and subtracts more than the
accumulator holds. The testbench turns coverage off for its own code
(``// verilator coverage_off``), so the numbers below are the design's.

.. literalinclude:: ../../../examples/01-code-basics/tb.sv
   :language: systemverilog
   :lines: 5-
   :linenos:
   :lineno-start: 5

The flow
========

``flow.yaml`` builds the design once with ``cov: code`` (Verilator's
``--coverage-line --coverage-expr``; branch points come with line coverage),
runs both tests, imports each ``coverage.dat`` into an NCDB database, and
merges them. ``basic.cdb`` holds ``t_basic`` alone; ``merged.cdb`` both tests.

.. literalinclude:: ../../../examples/01-code-basics/flow.yaml
   :language: yaml
   :lines: 9-

One test: finding the hole
==========================

After ``t_basic`` alone, line, branch and expression coverage are each one
point short:

.. covsight-transcript:: 01-code-basics/show_basic
   :commands: 1

``show hierarchy`` breaks that down by scope. Each branch and expression
point is a scope named for its source location, so the incomplete ones
point straight at the code:

.. covsight-transcript:: 01-code-basics/show_basic
   :commands: 2

- ``design.sv:20 [branch]`` — the ``?:`` on line 20 never took its first
  arm: no subtract asked for more than the accumulator held.
- ``design.sv:30:24 [expr]`` — in ``op == ADD && next[W]``, the term
  ``next[W]`` was never 1: no add overflowed.
- ``block`` — one line point unhit: the saturating arm of the ``if`` on
  line 30.

All three are the same gap in the test: it never pushes the accumulator
past either end of its range.

Two tests: closing it
=====================

``t_full`` adds an overflowing add and an oversized subtract. Merged with
``t_basic``:

.. covsight-transcript:: 01-code-basics/show_merged

.. covsight-download:: 01-code-basics/merged.cdb

Checked against Verilator
=========================

``covsight.Check`` holds the merged numbers to ``expect.yaml``

.. literalinclude:: ../../../examples/01-code-basics/expect.yaml
   :language: yaml

and compares them with ``verilator_coverage --report summary`` over the two
runs' ``coverage.dat`` files:

.. covsight-parity:: 01-code-basics
