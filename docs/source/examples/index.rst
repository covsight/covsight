########
Examples
########

Small SystemVerilog designs run through `Verilator <https://verilator.org>`_
with `dv-flow <https://github.com/dv-flow/dv-flow-mgr>`_, imported and merged
by covsight. Every number and every command output on these pages comes from
running the example when the docs were built, and each run is checked: the
totals must match the example's ``expect.yaml``, and must agree with
``verilator_coverage``.

The sources are in `examples/ <https://github.com/covsight/covsight/tree/main/examples>`_.
To run one yourself (see the README's developer setup for the tools):

.. code-block:: bash

    cd examples/01-code-basics
    dfm run all

.. toctree::
   :maxdepth: 1

   01-code-basics
