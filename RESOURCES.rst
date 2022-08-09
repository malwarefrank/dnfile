==================
dnfile - Resources
==================

Here is the high-level design of how to access the .NET resources of a dotnet
file.  Note that dotnet resources are different from the PE rsrc section.

We have tried to remain consistent with ECMA 335 terminology.  For example,
a ResourceSet contains a list() of entries, however we call it a ResourceSet
and *not* a ResourceList.


Quick Start
-----------

.NET resources are parsed and can be accessed through the dnPE.net.resources
list.  Each item in the list is a subclass of ClrResource.  That means either
an ExternalResource or an InternalResource.

For now each ExternalResource data member is None, since the data is outside
the current file.  However metadata is still accessible as part of the
resource, for example resource name and information about the external file
or assembly it references.

Each InternalResource has a data member that is either bytes or a ResourceSet.

.. code-block:: python

    pe = dnfile.dnPE(FILEPATH)

    if pe.net and pe.net.resources:
        print("RESOURCES:")
        for rsrc in pe.net.resources:
            print("    Name:   ", rsrc.name)
            print("    Public: ", rsrc.public)
            print("    Private:", rsrc.private)
            if isinstance(rsrc, dnfile.resources.InternalResource):
                if isinstance(rsrc.data, bytes):
                    print("    Type:   ", "bytes")
                    print("    Length: ", len(rsrc.data))
                elif isinstance(rsrc.data, dnfile.resources.ResourceSet):
                    print("    Type:   ", "resource set")
                    print("    Length: ", rsrc.data.struct.NumberOfResources)
                    if rsrc.data.entries:
                        for entry in rsrc.data.entries:
                            print("    RESOURCE ENTRY:")
                            print("        Name:  ", entry.name)
                            if entry.data:
                                dlen = len(entry.data)
                            else:
                                dlen = 0
                            print("        Length:", dlen)


High-level Design
-----------------

According to ECMA 335 the ManifestResource table contains information about the
dotnet resources.  Each table row contains information pointing to either an
external resource, as in another file, or an internal resource contained within
the same file as the ManifestResource table itself.

External resources can either be a raw data file or a resource defined in
another dotnet assembly.

All resources can either be raw data, such as a JPEG, or a resource set.  A
resource set contains a list of resources of various data types or objects.
Each data type is used to read the associated item within the set and
instantiate an object at runtime.


ManifestResource Design
-----------------------

The ManifestResource table contains zero or more objects of type
ManifestResourceRow.

ManifestResourceRow:

* Offset
* Flags
  * mrPublic
  * mrPrivate
* Name
* Implementation or None (means InternalResource)
  * row: FileRow or AssemblyRefRow

According to ECMA-335:

* Offset shall be a valid offset into the target file, starting from the Resource entry in the CLI header
* If the resource is an index into the File table, Offset shall be zero
* If Implementation is null, then Offset shall be a valid offset in the current file, starting from the Resource entry in the CLI header

These table and rows are parsed automatically and populate the
dnPE.net.resources list.


Resource data types
-------------------

class ClrResource(abc.ABC):

* name: str
* public: bool
* private: bool
* data: Optional[bytes | ResourceSet]

class ExternalResource(ClrResource):

* metadata: MDTableRow

class FileResource(ExternalResource):

* metadata: FileRow

class AssemblyResource(ExternalResource):

* metadata: AssemblyRefRow

class InternalResource(ClrResource):

* rva
* size

class ResourceSet(object):

* parent: ClrResource
* struct
  * Magic: int
  * NumberOfReaders: int
  * SizeOfReaderTypes: int
  * ReaderTypes: bytes
  * Version: int
  * NumberOfResources: int
  * NumberOfResourceTypes: int
  * DataSectionOffset: int
* entries: List[ResourceEntry]
* resource_types

ResourceEntry(ClrResource):

- struct
  - Type: Optional[bytes]
  - Hash: Optional[int]
  - NamePtr: Optional[int]
  - DataOffset: Optional[int]
  - name: Optional[bytes]
- data: Optional[bytes]
