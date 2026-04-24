==========
Quickstart
==========

Install the package and load a .NET binary with :class:`dnfile.dnPE`.

.. code-block:: shell

   pip install dnfile

.. code-block:: python

   import dnfile

   pe = dnfile.dnPE("path/to/managed.exe")
   pe.print_info()

The main entry point is :class:`dnfile.dnPE`, which extends :class:`pefile.PE`
and adds access to the CLR directory, metadata streams, metadata tables, and
resources.
