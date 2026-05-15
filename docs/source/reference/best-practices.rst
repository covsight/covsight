#####################################
Best Practices for Recording Coverage
#####################################

This section offers suggestions on best practices for recording
coverage using the ``covsight.core`` API.

Naming Cross Bins
=================

Most recorded cross bins pertain to auto-cross bins between coverpoints.
Bins have arbitrary names, but downstream tools (especially the XML
interchange format export) depend on being able to determine the
relationship between a cross bin and its associated coverpoint bins.

The suggested name format for a cross bin is:

.. code-block:: text

    <{cp[0].bin},{cp[1].bin},...>

In other words, if the first bin of the first coverpoint is named ``a``
and the first bin of the second coverpoint is named ``b``, the cross bin
for these two bins should be named ``<a,b>``.

This convention is automatically applied by the in-memory backend
(``covsight.core.mem``) when creating cross bins. Follow it when
writing custom simulators or converters that produce NCDB or XML data.
