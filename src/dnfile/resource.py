import enum
import struct
import datetime
from typing import Any, Dict, List, Tuple, Union, Optional

from . import base, utils, errors, mdtable

# References:
#   https://ntcore.com/files/manifestres.htm
#   https://github.com/0xd4d/dnlib/tree/master/src/DotNet/Resources
#   https://referencesource.microsoft.com/mscorlib/system/resources/resourcetypecode.cs.html


class ResourceTypeCode(enum.IntEnum):
    Null        = 0
    String      = 1
    Boolean     = 2
    Char        = 3
    Byte        = 4
    SByte       = 5
    Int16       = 6
    UInt16      = 7
    Int32       = 8
    UInt32      = 9
    Int64       = 0xa
    UInt64      = 0xb
    Single      = 0xc
    Double      = 0xd
    Decimal     = 0xe
    DateTime    = 0xf
    TimeSpan    = 0x10

    # Types with a special representation, like byte[] and Stream
    ByteArray   = 0x20
    Stream      = 0x21

    # User types - serialized using the binary formatter.
    StartOfUserTypes = 0x40


ResourceTypeStrings: Dict[int, str] = {
    ResourceTypeCode.Null:      "Null",
    ResourceTypeCode.String:    "System.String",
    ResourceTypeCode.Boolean:   "System.Boolean",
    ResourceTypeCode.Char:      "System.Char",
    ResourceTypeCode.Byte:      "System.Byte",
    ResourceTypeCode.SByte:     "System.SByte",
    ResourceTypeCode.Int16:     "System.Int16",
    ResourceTypeCode.UInt16:    "System.UInt16",
    ResourceTypeCode.Int32:     "System.Int32",
    ResourceTypeCode.UInt32:    "System.UInt32",
    ResourceTypeCode.Int64:     "System.Int64",
    ResourceTypeCode.UInt64:    "System.UInt64",
    ResourceTypeCode.Single:    "System.Single",
    ResourceTypeCode.Double:    "System.Double",
    ResourceTypeCode.Decimal:   "System.Decimal",
    ResourceTypeCode.DateTime:  "System.DateTime",
    ResourceTypeCode.TimeSpan:  "System.TimeSpan",
    ResourceTypeCode.ByteArray: "System.ByteArray",
    ResourceTypeCode.Stream:    "System.Stream",
}


class ResourceTypeFactory(object):

    def read_serialized_data(self, data: bytes, offset: int) -> Tuple[bytes, int]:
        """
        Read a serialized data (compressed int size, followed by data of that many bytes).

        Return the data (bytes) and number of bytes read (size + data).
        """
        x = utils.read_compressed_int(data[offset:offset + 4])
        if x is None:
            raise ValueError("CLR resource error: not enough data at offset")
        size = x[0]
        nbytes = x[1]
        offset += nbytes
        value = data[offset:offset + size]
        nbytes += size
        return value, nbytes

    def read_serialized_string(self, data: bytes, offset: int, encoding="utf-8") -> Tuple[str, int]:
        val, n = self.read_serialized_data(data, offset)
        return val.decode(encoding), n

    def read_rsrc_data_v1(self, data: bytes, offset: int, userTypes: List[bytes], entry: "ResourceEntry"):
        t = int.from_bytes(data[offset:offset + 1], byteorder="little", signed=False)
        entry.struct.Type = t
        offset += 4
        # https://github.com/0xd4d/dnlib/blob/master/src/DotNet/Resources/ResourceReader.cs
        if t == -1:
            # Null
            entry.type_name = "Null"
            entry.data = b""
            # entry.value is already None
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
        if entry.type_name:
            d, v = self.type_str_to_type(entry.type_name, data, offset)
            if d is not None:
                entry.data = d
            if v is not None:
                entry.value = v

    def read_rsrc_data_v2(self, data: bytes, offset: int, userTypes: List[bytes], entry: "ResourceEntry"):
        # dnlib reads four bytes, but it looks like one byte in the files I have
        t = int.from_bytes(data[offset:offset + 1], byteorder="little", signed=True)
        entry.struct.Type = t
        offset += 1
        # check for invalid type code
        if t < 0 or t >= ResourceTypeCode.StartOfUserTypes + len(userTypes):
            # invalid resource type
            # TODO warn/error
            return
        # https://github.com/0xd4d/dnlib/blob/master/src/IO/DataReader.cs
        if t in ResourceTypeStrings:
            entry.type_name = ResourceTypeStrings[t]
            d, v = self.type_str_to_type(entry.type_name, data, offset)
            if d is not None:
                entry.data = d
            if v is not None:
                entry.value = v
        elif t >= ResourceTypeCode.StartOfUserTypes:
            # get type string
            ts = userTypes[t - ResourceTypeCode.StartOfUserTypes]
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
        else:
            # TODO
            pass

    def type_str_to_type(self, type_name: str, data: bytes, offset: int) -> Tuple[Optional[bytes], Optional[Any]]:
        """
        Given a type string, data buffer, and offset into that buffer.
        Return a tuple of the raw data and the deserialized value.
        """
        # switch on type
        # https://github.com/0xd4d/dnlib/blob/master/src/IO/DataReader.cs
        final_bytes: Optional[bytes] = None
        final_value: Optional[Any] = None
        if type_name == "Null":
            final_bytes = b""
        elif type_name == "System.String":
            final_bytes, n = self.read_serialized_data(data, offset)
            try:
                final_value = final_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # TODO warn/error
                pass
        elif type_name == "System.Int32":
            tsize = 4
            final_bytes = data[offset:offset + tsize]
            final_value = int.from_bytes(final_bytes, byteorder="little", signed=False)
        elif type_name == "System.Byte":
            tsize = 1
            final_bytes = data[offset:offset + tsize]
            final_value = final_bytes
        elif type_name == "System.SByte":
            tsize = 1
            final_bytes = data[offset:offset + tsize]
            final_value = final_bytes
        elif type_name == "System.Boolean":
            tsize = 1
            final_bytes = data[offset:offset + tsize]
            final_value = final_bytes[0] != 0
        elif type_name == "System.Char":
            tsize = 2
            final_bytes = data[offset:offset + tsize]
            try:
                final_value = final_bytes.decode("utf-16")
            except UnicodeDecodeError:
                # TODO warn/error
                pass
        elif type_name == "System.Int16":
            tsize = 2
            final_bytes = data[offset:offset + tsize]
            final_value = int.from_bytes(final_bytes, byteorder="little", signed=False)
        elif type_name == "System.Int64":
            tsize = 8
            final_bytes = data[offset:offset + tsize]
            final_value = int.from_bytes(final_bytes, byteorder="little", signed=False)
        elif type_name == "System.UInt16":
            tsize = 2
            final_bytes = data[offset:offset + tsize]
            final_value = int.from_bytes(final_bytes, byteorder="little", signed=False)
        elif type_name == "System.UInt32":
            tsize = 4
            final_bytes = data[offset:offset + tsize]
            final_value = int.from_bytes(final_bytes, byteorder="little", signed=False)
        elif type_name == "System.UInt64":
            tsize = 8
            final_bytes = data[offset:offset + tsize]
            final_value = int.from_bytes(final_bytes, byteorder="little", signed=False)
        elif type_name == "System.Single":
            tsize = 4
            final_bytes = data[offset:offset + tsize]
            final_value = struct.unpack("<f", final_bytes)[0]
        elif type_name == "System.Double":
            tsize = 8
            final_bytes = data[offset:offset + tsize]
            final_value = struct.unpack("<d", final_bytes)[0]
        elif type_name == "System.DateTime":
            tsize = 8
            final_bytes = data[offset:offset + tsize]
            dt = base.DateTime(final_bytes)
            dt.parse()
            final_value = dt
        elif type_name == "System.TimeSpan":
            # TODO return resourceDataFactory.Create(new TimeSpan(reader.ReadInt64()));
            tsize = 8
            final_bytes = data[offset:offset + tsize]
        elif type_name == "System.Decimal":
            # https://referencesource.microsoft.com/mscorlib/system/decimal.cs.html
            sign_mask = 0x80000000
            scale_mask = 0x00FF0000
            tsize = 16
            final_bytes = data[offset:offset + tsize]
            low, med, high, flags = struct.unpack("<IIII", final_bytes)
            final_value = low | med << 8 | high << 16
            scale = scale_mask & flags
            if scale > 0:
                final_value = final_value / 10**scale
            if sign_mask & flags:
                final_value = -final_value
        elif type_name == "System.ByteArray":
            tsize = 4
            dsize = int.from_bytes(data[offset:offset + tsize], byteorder="little", signed=False)
            final_bytes = data[offset:offset + tsize + dsize]
            final_value = data[offset + tsize:offset + tsize + dsize]
        elif type_name == "System.Stream":
            tsize = 4
            dsize = int.from_bytes(data[offset:offset + tsize], byteorder="little", signed=False)
            final_bytes = data[offset:offset + tsize + dsize]
            final_value = data[offset + tsize:offset + tsize + dsize]
        else:
            # TODO
            pass
        return final_bytes, final_value


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
            self.data = rs
            rs.parse()
        # otherwise treat as raw resource


class ResourceEntryStruct(object):
    Type: Optional[int]
    Hash: Optional[int]
    NamePtr: Optional[int]
    DataOffset: Optional[int]
    Name: Optional[bytes]

    def __init__(self):
        self.Type: Optional[int] = None
        self.Hash: Optional[int] = None
        self.NamePtr: Optional[int] = None
        self.DataOffset: Optional[int] = None
        self.Name: Optional[bytes] = None


class ResourceEntry(object):
    struct: ResourceEntryStruct
    type_name: Optional[str]
    value: Optional[Any]
    data: Optional[bytes]
    name: Optional[str]

    def __init__(self):
        self.struct = ResourceEntryStruct()
        self.type_name: Optional[str] = None
        self.value: Optional[Any] = None
        self.data: Optional[bytes] = None
        self.name: Optional[str] = None


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
    parent: Optional[base.ClrResource]
    struct: Optional[ResourceSetStruct]
    entries: List[ResourceEntry]
    MAGIC: int = 0xbeefcace
    MAGIC_BYTES: bytes = b"\xCE\xCA\xEF\xBE"

    def __init__(self, data: bytes, parent: base.ClrResource):
        self._data = data
        self._min_valid_size = 7 * 4
        self.entries: List[ResourceEntry] = list()
        self.resource_types: List[bytes] = list()
        self.struct: Optional[ResourceSetStruct] = None
        self.parent: Optional[base.ClrResource] = parent

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
        self.struct.ReaderTypes = self._data[offset:offset + self.struct.SizeOfReaderTypes]
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
            try:
                type_string, size = self.read_serialized_data(offset)
            except ValueError:
                raise errors.rsrcFormatError("CLR ResourceSet error: expected more data for types at '{}' rsrc offset {}".format(self.parent.name, offset))
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
            e.struct.Hash = int.from_bytes(self._data[offset:offset + 4], byteorder="little")
            self.entries.append(e)
            # next
            offset += 4
        for e in self.entries:
            e.struct.NamePtr = int.from_bytes(self._data[offset:offset + 4], byteorder="little")
            # next
            offset += 4
        # dword (data section offset)
        self.struct.DataSectionOffset = int.from_bytes(self._data[offset:offset + 4], byteorder="little")
        offset += 4
        # table_of_names = current offset
        self.struct.TableOfNames = offset
        rsrc_factory = ResourceTypeFactory()
        problems = list()
        for e in self.entries:
            offset = self.struct.TableOfNames + e.struct.NamePtr
            try:
                e.struct.Name, size = self.read_serialized_data(offset)
                e.name = e.struct.Name.decode("utf-16")
            except UnicodeDecodeError:
                # entry name is initialized to None, so just ignore
                pass
            except ValueError:
                # further entries may be ok; delay this exception
                problems.append("CLR ResourceSet error: expected more data for entries at '{}' rsrc offset {}".format(self.parent.name, offset))
                continue
            offset += size
            e.struct.DataOffset = int.from_bytes(self._data[offset:offset + 4], byteorder="little")
            if self.struct.DataSectionOffset is None:
                continue
            e_data_offset = self.struct.DataSectionOffset + e.struct.DataOffset
            try:
                if self.struct.Version == 1:
                    rsrc_factory.read_rsrc_data_v1(self._data, e_data_offset, self.resource_types, e)
                else:
                    rsrc_factory.read_rsrc_data_v2(self._data, e_data_offset, self.resource_types, e)
            except ValueError:
                # further entries may be ok; delay this exception
                if self.parent:
                    problems.append("CLR ResourceSet error: expected more data for serialized data at '{}' rsrc offset {}".format(self.parent.name, e_data_offset))
                else:
                    problems.append("CLR ResourceSet error: expected more data for serialized data at unknown rsrc offset {}".format(e_data_offset))
            continue
        for p in problems:
            raise errors.rsrcFormatError(p)

    def read_serialized_data(self, offset: int) -> Tuple[bytes, int]:
        """
        Read a serialized data (compressed int size, followed by data of that many bytes).

        Return the data (bytes) and number of bytes read (size + data).
        """
        x = utils.read_compressed_int(self._data[offset:offset + 4])
        if x is None:
            raise ValueError("CLR resource error: not enough data at offset")
        size = x[0]
        nbytes = x[1]
        offset += nbytes
        value = self._data[offset:offset + size]
        nbytes += size
        return value, nbytes

    def read_serialized_string(self, offset: int, encoding="utf-8") -> Tuple[str, int]:
        val, n = self.read_serialized_data(offset)
        return val.decode(encoding), n
