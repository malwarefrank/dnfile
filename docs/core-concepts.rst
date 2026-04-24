==============
Core Concepts
==============

The object model is intentionally layered so you can move from a PE file to the
CLR details without manual offset handling.

Entry point
===========

Use :class:`dnfile.dnPE <dnfile.dnPE>` from the package root. After parsing, the
CLR data is available through :attr:`dnfile.dnPE.net <dnfile.dnPE.net>`.

.. code-block:: python

   import dnfile

   pe = dnfile.dnPE("path/to/managed.exe")
   net = pe.net

Parsing errors
==============

If the file does not contain CLR data, the :attr:`dnPE.net <dnfile.dnPE.net>`
attribute will be ``None``.
If the file contains CLR data but it is malformed, then further objects may be
``None`` or have missing attributes. The library is designed to be resilient to
malformed data, so it will attempt to parse as much as possible and provide
access to any valid data that it can find.

Raw attribute values
====================

Many of the objects in the object model have a ``struct`` attribute which
contains the raw values of the underlying structure. For example, the CLR
directory entry object is accessible from the ``net`` attribute of a
:class:`dnfile.dnPE <dnfile.dnPE>` object, and its raw structure values are
stored in the ``struct`` attribute of that object, for example
``pe.net.struct``. This pattern is mostly consistent across the object model,
so you can access the raw values of any object by referencing its ``struct``
attribute.

CLR data
========

The CLR directory is available for access through the :attr:`dnPE.net <dnfile.dnPE.net>`
attribute. It exposes a ``struct`` attribute which contains the raw values of the
CLR header. It also provides shortcuts to metadata, strings, user strings,
GUIDs, blobs, tables, streams, and resources.

Typical shortcuts include:

* :attr:`pe.net.metadata.streams <dnfile.ClrMetaData.streams>`
* :attr:`pe.net.strings <dnfile.ClrData.strings>`
* :attr:`pe.net.user_strings <dnfile.ClrData.user_strings>`
* :attr:`pe.net.guids <dnfile.ClrData.guids>`
* :attr:`pe.net.blobs <dnfile.ClrData.blobs>`
* :attr:`pe.net.mdtables <dnfile.ClrData.mdtables>`
* :attr:`pe.net.resources <dnfile.ClrData.resources>`

Metadata streams
================

The metadata header is parsed into :attr:`dnPE.net.metadata <dnfile.ClrData.metadata>`.
The streams are accessible both as an ordered list and as a dictionary keyed
by stream name, so callers can iterate in file order or look up a specific
stream directly.

Metadata tables
===============

The metadata tables stream is exposed as :attr:`dnPE.net.mdtables <dnfile.ClrData.mdtables>`.
This shortcut provides multiple ways to access the underlying tables. First,
the tables are available as an ordered list in the ``tables_list`` attribute.
Second, the tables are available as a dictionary in the ``tables`` attribute,
keyed by the ECMA-335 table number. Finally, the tables are available as
individual attributes named after the table type, for example
``pe.net.mdtables.TypeDef`` for the TypeDef table.

Resources
=========

Managed resources, *not* PE32 resources, are exposed through
:attr:`dnPE.net.resources <dnfile.ClrData.resources>` as a list. Each resource
has a ``data`` attribute which may be a simple byte stream or a
:class:`dnfile.resource.ResourceSet <dnfile.resource.ResourceSet>` object. The
``ResourceSet`` object is a .NET-specific datatype which contains a list of
entries, and each entry has a ``data`` attribute which may be a simple byte
stream or another ``ResourceSet``. This allows for nested resources, which are
commonly used for localization. The library is designed to handle this nesting
and provide access to all resources regardless of their depth in the hierarchy.