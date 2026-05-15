################################
covsight.core Object-Oriented API
################################

The ``covsight.core`` package provides an object-oriented API for
accessing coverage databases. This page documents every class in the
public API, organized from the top of the type hierarchy down to leaf
types.

.. contents::
   :local:
   :depth: 2

Class Hierarchy
===============

.. code-block:: text

    Obj
    ├── UCIS (Scope)          ← database root; use MemFactory
    ├── Scope (Obj)
    │   ├── CovScope
    │   │   └── FuncCovScope
    │   │       └── CvgScope
    │   │           ├── Covergroup
    │   │           │   └── (instances returned by createCovergroup)
    │   │           ├── Coverpoint
    │   │           │   └── Cross
    │   │           ├── CvgBinScope
    │   │           ├── IgnoreBinScope
    │   │           └── IllegalBinScope
    │   ├── DUScope           ← design unit definition
    │   └── InstanceScope     ← design hierarchy instance
    ├── HistoryNode           ← test run / merge record
    └── CoverItem             ← bin (leaf coverage measurement)

    CoverData                 ← data container for a bin's hit count and goal
    SourceInfo                ← (file, line, token) tuple
    TestData                  ← test run metadata passed to createHistoryNode

Creating a Database
===================

All interaction with coverage data starts by obtaining a
:class:`~covsight.core.api.ucis.UCIS` object from one of the backend
factories.

In-Memory Backend
-----------------

.. autoclass:: covsight.core.mem.mem_factory.MemFactory
   :members:
   :member-order: bysource
   :undoc-members:

------------

Core Classes
============

UCIS
----

The database root. Returned by ``MemFactory.create()``.

.. autoclass:: covsight.core.api.ucis.UCIS
   :members:
   :member-order: bysource
   :undoc-members:

Scope
-----

Base class for all hierarchical containers. Every node in the design
hierarchy and the coverage model is a ``Scope``.

.. autoclass:: covsight.core.api.scope.Scope
   :members:
   :member-order: bysource
   :undoc-members:

HistoryNode
-----------

Records one test run or merge operation in the database's provenance tree.
Create via :meth:`~covsight.core.api.ucis.UCIS.createHistoryNode`.

.. autoclass:: covsight.core.api.history_node.HistoryNode
   :members:
   :member-order: bysource
   :undoc-members:

------------

Coverage Scope Hierarchy
=========================

CovScope
--------

Base class for generic coverage scopes (code coverage types such as
branch and toggle).

.. autoclass:: covsight.core.api.cov_scope.CovScope
   :members:
   :member-order: bysource
   :undoc-members:

FuncCovScope
------------

Base class for functional coverage scopes.

.. autoclass:: covsight.core.api.func_cov_scope.FuncCovScope
   :members:
   :member-order: bysource
   :undoc-members:

CvgScope
--------

Base class for covergroup-level scopes (groups, coverpoints, crosses).

.. autoclass:: covsight.core.api.cvg_scope.CvgScope
   :members:
   :member-order: bysource
   :undoc-members:

Covergroup
----------

A SystemVerilog or SystemC covergroup type definition. Contains
:class:`~covsight.core.api.coverpoint.Coverpoint`,
:class:`~covsight.core.api.cross.Cross`, and per-instance coverage children.

.. autoclass:: covsight.core.api.covergroup.Covergroup
   :members:
   :member-order: bysource
   :undoc-members:

Coverpoint
----------

A coverpoint measuring coverage of a single variable or expression.

.. autoclass:: covsight.core.api.coverpoint.Coverpoint
   :members:
   :member-order: bysource
   :undoc-members:

Cross
-----

Cross-product coverage of two or more coverpoints.

.. autoclass:: covsight.core.api.cross.Cross
   :members:
   :member-order: bysource
   :undoc-members:

CvgBinScope
-----------

Normal bin scope for SystemVerilog covergroups.

.. autoclass:: covsight.core.api.cvg_bin_scope.CvgBinScope
   :members:
   :member-order: bysource
   :undoc-members:

IgnoreBinScope
--------------

Scope representing a SystemVerilog ``ignore_bins`` declaration.

.. autoclass:: covsight.core.api.ignore_bin_scope.IgnoreBinScope
   :members:
   :member-order: bysource
   :undoc-members:

IllegalBinScope
---------------

Scope representing a SystemVerilog ``illegal_bins`` declaration.

.. autoclass:: covsight.core.api.illegal_bin_scope.IllegalBinScope
   :members:
   :member-order: bysource
   :undoc-members:

------------

Design Hierarchy Scopes
=======================

DUScope
-------

Design unit (module/entity/package) definition.

.. autoclass:: covsight.core.api.du_scope.DUScope
   :members:
   :member-order: bysource
   :undoc-members:

InstanceScope
-------------

A design hierarchy instance.

.. autoclass:: covsight.core.api.instance_scope.InstanceScope
   :members:
   :member-order: bysource
   :undoc-members:

------------

Cover Items
===========

CoverItem
---------

Base class for bins — the leaf-level coverage measurements within
coverpoints, crosses, and code coverage scopes.

.. autoclass:: covsight.core.api.cover_item.CoverItem
   :members:
   :member-order: bysource
   :undoc-members:

CoverData
---------

Holds the hit count, goal, and status flags for one cover item.

.. autoclass:: covsight.core.api.cover_data.CoverData
   :members:
   :member-order: bysource
   :undoc-members:

------------

Value Objects
=============

SourceInfo
----------

Bundles a file handle with a line number and token offset to identify
where a scope or bin was declared in source.

.. autoclass:: covsight.core.api.source_info.SourceInfo
   :members:
   :member-order: bysource
   :undoc-members:

TestData
--------

Carries test metadata (status, tool, date, seed, …) passed to
:meth:`~covsight.core.api.history_node.HistoryNode.setTestData`.

.. autoclass:: covsight.core.api.test_data.TestData
   :members:
   :member-order: bysource
   :undoc-members:

------------

Enumerations
============

Enumeration classes are defined in ``covsight.core.api.enums``. The most
commonly used are:

* ``ScopeTypeT`` — scope type constants (``DU_MODULE``, ``COVERGROUP``, ``COVERPOINT``, etc.)
* ``CoverTypeT`` — cover-item type constants (``CVGBIN``, ``TOGGLEBIN``, ``STMTBIN``, etc.)
* ``TestStatusT`` — test result codes (``OK``, ``WARNING``, ``ERROR``, ``FATAL``, ``NOTRUN``)
* ``ToggleMetricT`` — toggle metric (``_2STOGGLE``, ``_4STOGGLE``)
* ``ToggleTypeT`` — signal type (``NET``, ``REG``, ``PORT``)

.. automodule:: covsight.core.api.enums
   :members:
   :member-order: bysource
   :undoc-members:
