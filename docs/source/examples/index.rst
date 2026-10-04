########
Examples
########

Small SystemVerilog designs run through `Verilator <https://verilator.org>`_
with `dv-flow <https://github.com/dv-flow/dv-flow-mgr>`_, imported and merged
by covsight. Each page follows the same arc:

1. **The design and testbench**, in full, and what each coverage point in
   the design measures.
2. **One test, and its coverage report**: the totals, then the coverage laid
   over the source, with what was missed highlighted.
3. **Why each gap is there**, read from that report, and what it would take
   to close it.
4. **A second test that closes it**, and the merged report.

Every number and every command output on these pages comes from running the
example when the docs were built, and each run is checked: the totals must
match the example's ``expect.yaml``, and must agree with
``verilator_coverage``.

=================================== ==========================================
Example                             Shows
=================================== ==========================================
:doc:`01-code-basics`               Line, branch and expression coverage of a
                                    saturating accumulator; a first test that
                                    never reaches either end of the range
=================================== ==========================================

The sources are in `examples/ <https://github.com/covsight/covsight/tree/main/examples>`_.
To run one yourself (see the README's developer setup for the tools):

.. code-block:: bash

    cd examples/01-code-basics
    dfm run all

.. toctree::
   :maxdepth: 1

   01-code-basics
