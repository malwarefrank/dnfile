======
dnfile
======


.. image:: https://img.shields.io/pypi/v/dnfile.svg
        :target: https://pypi.python.org/pypi/dnfile


Parse .NET executable files.


* Free software: MIT license


Features
--------

* Parse as much as we can, even if the file is partially malformed.
* Easy to use.  Developed with IDE autocompletion in mind.


Quick Start
-----------

.. code-block:: shell

   pip install dnfile

Then create a simple program that loads a .NET binary, parses it, and displays
information about the streams and Metadata Tables.

.. code-block:: python

   import sys
   import dnfile

   filepath = sys.argv[1]

   pe = dnfile.dnPE(filepath)
   pe.print_info()


Everything is an object, and raw structure values are stored in an object's "struct"
attribute.  The CLR directory entry object is accessible from the "net"
attribute of a dnPE object.

.. code-block:: python

    pe = dnfile.dnPE(FILEPATH)

    # access the directory entry raw structure values
    pe.net.struct

    # access the metadata raw structure values
    pe.net.metadata.struct

    # access the streams
    for s in pe.net.metadata.streams_list:
        if isinstance(s, dnfile.stream.MetaDataTables):
            # how many Metadata tables are defined in the binary?
            num_of_tables = len(s.tables_list)

    # the first Metadata tables stream can also be accessed by a shortcut
    num_of_tables = len(pe.net.mdtables.tables_list)



TODO
----

* CI
* Documentation on readthedocs


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
