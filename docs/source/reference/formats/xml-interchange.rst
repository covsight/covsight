######################
XML Interchange Format
######################

The Accelera UCIS Standard specifies an XML interchange format. While the
XML document structure has some similarities with the data model accessed
via the UCIS C API, there are also significant differences.

``covsight`` can import and export the UCIS XML interchange format using
the ``covsight convert`` command:

.. code-block:: bash

   # Convert XML to NCDB
   covsight convert coverage.xml coverage.cdb

   # Export NCDB to XML
   covsight convert coverage.cdb coverage.xml

.. contents::
   :local:
   :depth: 2

Functional Coverage
===================

Functional coverage data is stored in ``cgInstance`` sections within a
``covergroupCoverage`` scope.

Covergroup instance/type linkage
---------------------------------

The ``cgId`` section inside ``cgInstance`` specifies the associated
covergroup type:

.. code-block:: xml

   <cgInstance name="top.cg_i1" key="0">
     <options/>
     <cgId cgName="my_covergroup" moduleName="top">
       <cginstSourceId file="1" line="1" inlineCount="1"/>
       <cgSourceId file="1" line="1" inlineCount="1"/>
     </cgId>
   </cgInstance>

This covergroup instance name is ``top.cg_i1``, associated with a
covergroup type ``top::my_covergroup``.

Covergroup instance and type data
----------------------------------

The UCIS data model represents covergroup type coverage (the merge of all
covergroup instances of a given type) as a scope containing sub-scopes that
hold per-instance coverage data. The XML interchange format does not provide
such a hierarchy.

When instance coverage is being recorded, all ``cgInstance`` sections
associated with a given covergroup type contain instance data. The reader
is responsible for reconstructing type coverage.

When instance coverage is not being recorded, only a single ``cgInstance``
section is written containing type data.

Coverage Instance Options
--------------------------

The following coverage options are significant when reading XML:

- ``per_instance`` — Whether per-instance data is recorded
- ``merge_instances`` — Whether to produce type coverage from merged instance data

Both are boolean: ``true``, ``false``, ``0``, or ``1`` are accepted.

When writing XML, covsight emits ``auto_bin_max=0`` because covsight
represents all coverpoint bins explicitly. Some consumers attempt to
create auto-bins if this option is not explicitly set to 0.

Coverpoint Bins
----------------

.. code-block:: xml

   <coverpoint name="cp1" key="0">
       <options/>
       <coverpointBin name="a[0]" type="bins" key="0">
           <range from="-1" to="-1">
               <contents coverageCount="1"/>
           </range>
       </coverpointBin>
   </coverpoint>

The bin type is one of ``bins``, ``ignore``, ``illegal``.

Only the following options are interpreted:

- ``weight``
- ``at_least``

Cross Bins
-----------

.. code-block:: xml

   <cross name="cp1Xcp2" key="0">
       <options/>
       <crossExpr>cp1</crossExpr>
       <crossExpr>cp2</crossExpr>
       <crossBin name="&lt;a[0],a[0]&gt;" key="0">
           <index>0</index>
           <index>0</index>
           <contents coverageCount="1"/>
       </crossBin>
   </cross>

Cross bins follow the :doc:`../best-practices` naming convention
(``<bin_a,bin_b>``). Bin-index information is reconstructed from bin names.
For ``ignore`` or ``illegal`` bins all indices are ``-1``.

Coverage Options Support
=========================

Supported Covergroup Options (``CGINST_OPTIONS``)
---------------------------------------------------

- ``weight`` — Relative weight for coverage calculation
- ``goal`` — Coverage goal percentage (default: 100)
- ``at_least`` — Minimum hit count for coverage (default: 1)
- ``per_instance`` — Track per-instance coverage
- ``merge_instances`` — Merge instance coverage into type coverage
- ``get_inst_coverage`` — Enable instance coverage retrieval
- ``auto_bin_max`` — Maximum auto-generated bins (set to 0 on write)
- ``detect_overlap`` — Detect overlapping bins
- ``strobe`` — Strobe sampling mode

Supported Coverpoint Options
------------------------------

- ``weight``, ``goal``, ``at_least``, ``auto_bin_max``, ``detect_overlap``

Supported Cross Options
------------------------

- ``weight``, ``goal``, ``at_least``, ``cross_num_print_missing``

Value Normalization
--------------------

When writing XML, certain values are normalized to comply with XSD constraints:

- Negative ``goal`` values → 100 (UCIS default)
- Zero or negative ``at_least`` values → 1 (UCIS default)
- Zero or negative ``auto_bin_max`` values → 64 (UCIS default)

Code Coverage
=============

Statement Coverage
-------------------

.. code-block:: xml

   <blockCoverage>
     <statement id="1" file="1" line="5" inlineCount="1">
       <contents coverageCount="3"/>
     </statement>
   </blockCoverage>

Branch Coverage
----------------

.. code-block:: xml

   <branchCoverage>
     <branch id="1" branchType="if" file="1" line="10">
       <branchBin alias="taken"><contents coverageCount="2"/></branchBin>
       <branchBin alias="not_taken"><contents coverageCount="0"/></branchBin>
     </branch>
   </branchCoverage>

Toggle Coverage
----------------

.. code-block:: xml

   <toggleCoverage>
     <toggleObject name="sig" canonical="sig">
       <toggleBit name="sig[0]">
         <toggle01Bin><contents coverageCount="1"/></toggle01Bin>
         <toggle10Bin><contents coverageCount="1"/></toggle10Bin>
       </toggleBit>
     </toggleObject>
   </toggleCoverage>

FSM Coverage
-------------

.. code-block:: xml

   <fsmCoverage>
     <fsm name="state_machine">
       <state stateName="IDLE">
         <stateBin name="IDLE"><contents coverageCount="5"/></stateBin>
       </state>
       <stateTransition>
         <state>IDLE</state><state>ACTIVE</state>
         <transitionBin name="IDLE->ACTIVE"><contents coverageCount="2"/></transitionBin>
       </stateTransition>
     </fsm>
   </fsmCoverage>

Feature Support Matrix
======================

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Feature
     - Supported
     - Notes
   * - Covergroup Options
     - ✅ Yes
     - Full read/write support
   * - Coverpoint Options
     - ✅ Yes
     - Full read/write support
   * - Cross Coverage
     - ✅ Yes
     - Including multi-way crosses
   * - Statement Coverage
     - ✅ Yes
     - Flat statement mode
   * - Branch Coverage
     - ✅ Yes
     - if/case branching statements
   * - Toggle Coverage
     - ✅ Yes
     - Per-bit 0→1 and 1→0 bins
   * - FSM Coverage
     - ✅ Yes
     - State and transition coverage
   * - Assertion Coverage
     - ✅ Yes
     - cover and assert kinds
   * - User Attributes
     - ✅ Yes
     - Via ``userAttr`` child elements
   * - History Node Hierarchy
     - ✅ Yes
     - Parent/child via ``parentId``
   * - Condition/Expression Coverage
     - ❌ No
     - Not in data model
   * - Instance Weights
     - ❌ No
     - Not in XML schema
   * - Empty Coverpoints
     - ❌ No
     - Schema requires at least one bin
   * - DU Source Info
     - ⚠️ Partial
     - Only via instance references
   * - Tags
     - ❌ No
     - No direct XML representation

Known Format Limitations
=========================

1. **Design Unit Scopes Not Serialized** — Only instance coverages are written.
2. **Instance Weight Not Supported** — The schema has no weight attribute at the instance level.
3. **Mandatory Instance Coverage** — Schema requires at least one ``instanceCoverages`` element.
4. **Coverpoints Require Bins** — Empty coverpoints cannot be serialized.

Schema file: ``ucis.xsd`` (Accelera UCIS Standard, June 2012)
