import struct
from typing import List, Optional, Any

from . import base, mdtable, utils, errors

# References:
#   https://ntcore.com/files/manifestres.htm
#   https://github.com/0xd4d/dnlib/tree/master/src/DotNet/Resources


class ExternalResource(base.ClrResource):
    metadata: base.MDTableRow


class FileResource(ExternalResource):
    metadata: mdtable.FileRow


class AssemblyResource(ExternalResource):
    metadata: mdtable.AssemblyRefRow


class InternalResource(base.ClrResource):
    rva: int
    size: int

    def parse(self):
        if not self.data:
            raise errors.rsrcFormatError("No data")
        # attempt to parse as a ResourceSet
        rs = ResourceSet(self.data, self)
        if rs.valid():
            rs.parse()
            self.data = rs
        # otherwise treat as raw resource

class ResourceEntryStruct(object):
    Type: Optional[bytes]
    Hash: Optional[int]
    NamePtr: Optional[int]
    DataOffset: Optional[int]

    def __init__(self):
        self.Type: Optional[bytes] = None
        self.Hash: Optional[int] = None
        self.NamePtr: Optional[int] = None
        self.DataOffset: Optional[int] = None


class ResourceEntry(base.ClrResource):
    struct: ResourceEntryStruct
    type_name: Optional[str]
    value: Optional[Any]

    def __init__(self):
        self.struct = ResourceEntryStruct()
        self.type_name: Optional[str] = None
        self.value: Optional[Any] = None


class ResourceSetStruct(object):
    Magic: int
    NumberOfReaders: int
    SizeOfReaderTypes: int
    ReaderTypes: bytes
    Version: int
    NumberOfResources: int
    NumberOfResourceTypes: int
    DataSectionOffset: int
    TableOfNames: int


class ResourceSet(object):
    parent: Optional[ExternalResource | InternalResource]
    struct: ResourceSetStruct
    entries: List[ResourceEntry]
    MAGIC: int = 0xbeefcace
    MAGIC_BYTES: bytes = b"\xCE\xCA\xEF\xBE"

    def __init__(self, data: bytes, parent: base.ClrResource):
        self._data = data
        self._min_valid_size = 7*4
        self.entries: List[ResourceEntry] = list()
        self.resource_types: List[bytes] = list()
        self.struct: ResourceSetStruct = None

    def valid(self):
        if len(self._data) < self._min_valid_size:
            # not enough data
            return False
        # test magic
        if not self._data.startswith(self.MAGIC_BYTES):
            return False
        # we have enough data, and it starts with the right signature
        return True

    def parse(self):
        # parse initial structure
        self.struct = ResourceSetStruct()
        offset = 0
        self.struct.Magic = struct.unpack_from("<I", self._data, offset)[0]
        offset += 4
        self.struct.NumberOfReaders = struct.unpack_from("<I", self._data, offset)[0]
        offset += 4
        self.struct.SizeOfReaderTypes = struct.unpack_from("<I", self._data, offset)[0]
        offset += 4
        # reader types string
        self.struct.ReaderTypes = self._data[offset:offset+self.struct.SizeOfReaderTypes]
        offset += self.struct.SizeOfReaderTypes
        # version
        self.struct.Version = struct.unpack_from("<I", self._data, offset)[0]
        offset += 4
        # NumberOfResources
        self.struct.NumberOfResources = struct.unpack_from("<I", self._data, offset)[0]
        offset += 4
        # NumberofResourceTypes
        self.struct.NumberOfResourceTypes = struct.unpack_from("<I", self._data, offset)[0]
        offset += 4
        # parse more
        for i in range(self.struct.NumberOfResourceTypes):
            # read string length
            x = utils.read_compressed_int(self._data[offset:offset+4])
            if x is None:
                raise errors.rsrcFormatError("CLR ResourceSet error: expected more data for types at '{}' rsrc offset {}".format(self.parent.name, offset))
            size = x[0]
            offset += x[1]
            # read string
            type_string = self._data[offset:offset+size]
            # add to list
            self.resource_types.append(type_string)
            # next
            offset += size
        # align to 8-byte boundary
        over = offset % 8
        if over != 0:
            offset += 8 - over
        for i in range(self.struct.NumberOfResources):
            e = ResourceEntry()
            e.struct.Hash = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            self.entries.append(e)
            # next
            offset += 4
        for e in self.entries:
            e.struct.NamePtr = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            # next
            offset += 4
        # dword (data section offset)
        self.struct.DataSectionOffset = int.from_bytes(self._data[offset:offset+4], byteorder="little")
        offset += 4
        # table_of_names = current offset
        self.struct.TableOfNames = offset
        for e in self.entries:
            offset = self.struct.TableOfNames + e.struct.NamePtr
            x = utils.read_compressed_int(self._data[offset:offset+4])
            if x is None:
                raise errors.rsrcFormatError("CLR ResourceSet error: expected more data for entries at '{}' rsrc offset {}".format(self.parent.name, offset))
            size = x[0]
            offset += x[1]
            e.name = self._data[offset:offset+size]
            offset += size
            e.struct.DataOffset = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            if self.struct.Version == 1:
                self.read_rsrc_data_v1(self.resource_types, e)
            else:
                self.read_rsrc_data_v2(self.resource_types, e)

        def read_rsrc_data_v1(self, userTypes: List[bytes], entry: ResourceEntry):
            t = int.from_bytes(self._data[edata_start:edata_start+4], byteorder="little", signed=True)
            entry.struct.Type = t
            edata_start = self.struct.DataSectionOffset + entry.struct.DataOffset
            # https://github.com/0xd4d/dnlib/blob/master/src/DotNet/Resources/ResourceReader.cs
            if t == -1:
                # Null
                entry.type_name = "Null"
                entry.value = None
            elif t < 0 or t >= len(userTypes):
                # invalid resource type
                # TODO warn/error
                return
            # get type string
            ts = userTypes[t]
            # remove comma postfix
            comma_loc = ts.find(b",")
            if comma_loc > 0:
                ts = ts[:comma_loc]
            try:
                tn = ts.decode("utf-8")
            except UnicodeDecodeError as e:
                # TODO warn/error
                tn = None
            entry.type_name = tn
            # switch on type
            if tn == "System.string":
                # TODO
                pass
            elif tn == "System.Int32":
                # TODO return resourceDataFactory.Create(reader.ReadInt32());
                pass
            elif tn == "System.Byte":
                # TODO return resourceDataFactory.Create(reader.ReadByte());
                pass
            elif tn == "System.SByte":
                # TODO return resourceDataFactory.Create(reader.ReadSByte());
                pass
            elif tn == "System.Int16":
                # TODO return resourceDataFactory.Create(reader.ReadInt16());
                pass
            elif tn == "System.Int64":
                # TODO return resourceDataFactory.Create(reader.ReadInt64());
                pass
            elif tn == "System.UInt16":
                # TODO return resourceDataFactory.Create(reader.ReadUInt16());
                pass
            elif tn == "System.UInt32":
                # TODO return resourceDataFactory.Create(reader.ReadUInt32());
                pass
            elif tn == "System.UInt64":
                # TODO return resourceDataFactory.Create(reader.ReadUInt64());
                pass
            elif tn == "System.Single":
                # TODO return resourceDataFactory.Create(reader.ReadSingle());
                pass
            elif tn == "System.Double":
                # TODO return resourceDataFactory.Create(reader.ReadDouble());
                pass
            elif tn == "System.DateTime":
                # TODO return resourceDataFactory.Create(new DateTime(reader.ReadInt64()));
                pass
            elif tn == "System.TimeSpan":
                # TODO return resourceDataFactory.Create(new TimeSpan(reader.ReadInt64()));
                pass
            elif tn == "System.Decimal":
                # TODO return resourceDataFactory.Create(reader.ReadDecimal());
                pass
            else:
                # TODO
                pass

        def read_rsrc_data_v2(self, userTypes: List[bytes], entry: ResourceEntry):
            # TODO
            pass
