###########################################
01 — Code coverage: lines, branches, terms
###########################################

Code coverage records which parts of the RTL a simulation exercised. It
needs no extra testbench code, only a build option, so it is usually the
first coverage a project collects. It cannot tell you that the design is
right; it tells you where the tests have not looked yet.

This example measures a small accumulator with one test, finds what that
test missed by reading the annotated source, and closes the gap with a
second test. Along the way it shows:

- what Verilator counts as a line, a branch and an expression point;
- how to read ``covsight show code-coverage`` and ``covsight show source``;
- why a single number such as "88.89% line coverage" says little until you
  look at *which* line;
- how merging two tests' databases combines their coverage.

The design
==========

``acc`` is an 8-bit accumulator. On each clock edge, ``op`` decides what
happens to the output ``q``:

========= =============================================================
``op``    Effect on ``q``
========= =============================================================
HOLD (0)  unchanged
ADD (1)   ``q + din``; if that overflows 8 bits, ``q`` saturates at 255
SUB (2)   ``q - din``; if ``din`` is larger than ``q``, ``q`` stops at 0
CLEAR (3) 0
========= =============================================================

``sat`` is 1 while ``q`` is at 255.

.. literalinclude:: ../../../examples/01-code-basics/design.sv
   :language: systemverilog
   :linenos:

The interesting behaviour is at the two ends of the range. ``next`` is one
bit wider than ``q`` so the carry out of an add lands in ``next[W]``
(line 15). Line 20 stops a subtract at zero, and line 31 saturates an add
that carried. Everything else is ordinary arithmetic. The end cases are
where bugs tend to be, and they are also where a quickly written test does
not go.

What Verilator measures in it
-----------------------------

The build uses Verilator's ``--coverage-line --coverage-expr``. That gives
three kinds of points in ``acc``; the testbench's own code is excluded with
``// verilator coverage_off``.

**Line points (9).** A line point is a block of statements that always run
together, and its count is how many times the block ran. One point can span
several lines: lines 17–18 are one block (entering the ``always_comb``), and
so are lines 20–21, the SUB arm of the ``case``. Each arm of a ``case`` and
each arm of the ``if`` chain on lines 27–34 is its own block. The line that
holds an arm's condition belongs to that arm's block. Line 31 therefore
counts how often the saturate arm *ran*, not how often its condition was
tested.

**Branch points (1, with 2 arms).** The ``if``/``else`` on line 20 is
recorded as a branch with an ``if`` arm and an ``else`` arm, each counting
how often it was taken. A branch is covered only when every arm has been
taken. The ``if`` chain in the ``always_ff`` is measured by its line points,
one per arm.

**Expression points (2, with 5 rows).** For a condition built with logical
operators (``&&``, ``||``, ``!``), Verilator lists the combinations of term values
that decide the result, one row each, and counts how often each occurred
when the condition was evaluated:

- line 27, ``!rst_n``: rows for ``rst_n`` at 0 (result 1) and at 1
  (result 0);
- line 31, ``op == ADD && next[W]``: ``op == ADD`` false decides 0;
  ``next[W]`` false decides 0; both true gives 1. Verilator spells
  ``next[W]`` as ``next[W[3:0]+:1]``.

A row is covered when that combination happened at least once. Rows can
overlap: when ``op`` is not ADD and there is no carry, both "decides 0"
rows count. Their counts don't add up to the number of evaluations.

Expression coverage asks more than line or branch coverage. A test can run
every arm of the ``if`` chain without ever having the condition on line 31
be true *because* ``next[W]`` was 1. If that term were wrong, say the wrong
bit of ``next``, such a test would not notice.

So the totals are 9 line points, 2 branch arms and 5 expression rows.

The testbench
=============

The testbench drives one operation per clock, changing inputs on the
falling edge, and after each rising edge checks ``q`` and ``sat`` against a
model in the testbench. A mismatch stops the run with ``$fatal``, and the
flow then reports the test as failed. ``+TEST=`` selects how much it does:

- ``basic``: two adds, a hold, a subtract and a clear, all with small
  values. This is the sort of first test that checks that every operation
  works.
- ``full``: the same, then an add that overflows (200 + 100), a subtract
  of 255 from 255, and a subtract of 9 from 3.

.. literalinclude:: ../../../examples/01-code-basics/tb.sv
   :language: systemverilog
   :lines: 5-
   :linenos:
   :lineno-start: 5

Running it
==========

.. code-block:: bash

    cd examples/01-code-basics
    dfm run all

The flow (``flow.yaml``, at the end of this page) builds the design once
with coverage enabled and runs each test. It imports each test's
``coverage.dat`` into a covsight database (NCDB). ``basic.cdb`` holds
``t_basic`` alone; ``merged.cdb`` holds both tests. The command output on
this page is that run's, captured when the docs were built.

One test: what ``t_basic`` missed
=================================

The totals after ``t_basic`` alone:

.. covsight-transcript:: 01-code-basics/show_basic
   :commands: 1

Each kind is one short. The percentages say how much is missing but not
where. ``show source`` lays the counts over the code. In the listing below,
red lines never ran, amber lines ran but have a branch arm or expression row
under them that never happened, and each branch and expression point is
listed under the line it is on, with a count per arm or row:

.. covsight-source:: 01-code-basics/show_basic
   :command: 3
   :lines: 15-38

Reading it from the top:

- **Line 20 (amber).** The SUB arm ran 8 times: ``op`` stayed at SUB for 8
  evaluations of the ``always_comb``. Its ``if`` arm was never taken,
  because ``din`` was never larger than ``q`` during a subtract. The test's
  only subtract is 5 from 30. The stop-at-zero logic has never run, so
  nothing has checked it.
- **Line 27** is fully covered: both rows of ``!rst_n`` happened, since
  reset was asserted and then released.
- **Lines 31–32 (red).** The saturate arm never ran. The expression point
  says why: the row where ``op == ADD`` and ``next[W]`` are both 1 has 0
  hits. The condition was tested 5 times, and ``next[W]`` was 0 every time:
  no add carried, since the test's largest sum is 30.

All three gaps are the same omission: ``t_basic`` never drives the
accumulator past either end of its range. That's the boundary behaviour
this design exists for, and the test passed without touching it.

On the command line, ``-u`` lists only the lines that need attention:

.. covsight-transcript:: 01-code-basics/show_basic
   :commands: 2

Two tests: closing the gap
==========================

``t_full`` adds the boundary cases: an add of 100 to 200, which carries and
must saturate at 255; a subtract of 255 from 255; and a subtract of 9 from
3, which must stop at 0. Its checks against the model pass, so the
saturate and stop-at-zero logic now has been exercised *and* checked.

``covsight.Merge`` combines the two tests' databases by summing each
point's counts. A point is covered in the merge if either test covered it:

.. covsight-transcript:: 01-code-basics/show_merged
   :commands: 1

.. covsight-source:: 01-code-basics/show_merged
   :command: 3
   :lines: 15-38

Line 20's ``if`` arm now has hits, and so do lines 31–32 and the
both-true row of line 31's expression. ``show source -u`` has nothing left
to list:

.. covsight-transcript:: 01-code-basics/show_merged
   :commands: 2

The merged database, to try the commands yourself:

.. covsight-download:: 01-code-basics/merged.cdb

.. code-block:: bash

    covsight show source merged.cdb
    covsight show code-coverage merged.cdb -of text

Without ``-sr``, ``show source`` reads the design from the path recorded
when it was built. Point ``-sr`` at a checkout of ``examples/01-code-basics``
to read it from there instead.

Checked against Verilator
=========================

Every docs build reruns this example and checks it with ``covsight.Check``.
The merged totals must equal ``expect.yaml``:

.. literalinclude:: ../../../examples/01-code-basics/expect.yaml
   :language: yaml

They must also agree with Verilator's own ``verilator_coverage --report
summary`` over the two tests' ``coverage.dat`` files:

.. covsight-parity:: 01-code-basics

The flow
========

``flow.yaml`` is a dv-flow package. ``img`` builds the design with
``cov: code``. ``t_basic`` and ``t_full`` run it, and ``check_*`` fail the
flow if a test failed. ``cov_*`` import each test's coverage, ``basic`` and
``merged`` merge them, and ``show_*`` and ``check`` produce the output and
checks used on this page.

.. literalinclude:: ../../../examples/01-code-basics/flow.yaml
   :language: yaml
   :lines: 9-
