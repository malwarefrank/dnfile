import enum
import struct
import datetime
from typing import Any, List, Tuple, Union, Optional

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
    Name: Optional[bytes]

    def __init__(self):
        self.Type: Optional[bytes] = None
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
    parent: Optional[Union[ExternalResource, InternalResource]]
    struct: ResourceSetStruct
    entries: List[ResourceEntry]
    MAGIC: int = 0xbeefcace
    MAGIC_BYTES: bytes = b"\xCE\xCA\xEF\xBE"

    def __init__(self, data: bytes, parent: base.ClrResource):
        self._data = data
        self._min_valid_size = 7 * 4
        self.entries: List[ResourceEntry] = list()
        self.resource_types: List[bytes] = list()
        self.struct: ResourceSetStruct = None
        self.parent: Optional[Union[ExternalResource, InternalResource]] = parent

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
        for e in self.entries:
            offset = self.struct.TableOfNames + e.struct.NamePtr
            try:
                e.struct.Name, size = self.read_serialized_data(offset)
                e.name = e.struct.Name.decode("utf-16")
            except ValueError:
                raise errors.rsrcFormatError("CLR ResourceSet error: expected more data for entries at '{}' rsrc offset {}".format(self.parent.name, offset))
            except UnicodeDecodeError:
                # entry name is initialized to None, so just ignore
                pass
            offset += size
            e.struct.DataOffset = int.from_bytes(self._data[offset:offset + 4], byteorder="little")
            if self.struct.Version == 1:
                self.read_rsrc_data_v1(self.resource_types, e)
            else:
                self.read_rsrc_data_v2(self.resource_types, e)

    def read_serialized_data(self, offset: int) -> Tuple[Optional[bytes], int]:
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

    def read_serialized_string(self, offset: int, encoding="utf-8") -> Tuple[Optional[str], int]:
        val, n = self.read_serialized_data(offset)
        val = val.decode(encoding)
        return val, n

    def read_rsrc_data_v1(self, userTypes: List[bytes], entry: ResourceEntry):
        edata_start = self.struct.DataSectionOffset + entry.struct.DataOffset
        t = int.from_bytes(self._data[edata_start:edata_start + 4], byteorder="little", signed=False)
        entry.struct.Type = t
        edata_start += 4
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
        # switch on type
        if tn == "System.string":
            try:
                data, n = self.read_serialized_data(edata_start)
            except ValueError:
                raise errors.rsrcFormatError("CLR ResourceSet error: expected more data for serialized data at '{}' rsrc offset {}".format(self.parent.name, offset))
            entry.data = data
            try:
                entry.value = data.decode("utf-8")
            except UnicodeDecodeError:
                # TODO warn/error
                pass
        elif tn == "System.Int32":
            tsize = 4
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif tn == "System.Byte":
            tsize = 1
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = entry.data
        elif tn == "System.SByte":
            tsize = 1
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = entry.data
        elif tn == "System.Int16":
            tsize = 2
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif tn == "System.Int64":
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif tn == "System.UInt16":
            tsize = 2
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif tn == "System.UInt32":
            tsize = 4
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif tn == "System.UInt64":
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif tn == "System.Single":
            tsize = 4
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = struct.unpack("<f", entry.data)[0]
        elif tn == "System.Double":
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = struct.unpack("<d", entry.data)[0]
        elif tn == "System.DateTime":
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            x = struct.unpack("<q", entry.data)[0]
            # https://stackoverflow.com/questions/3169517/python-c-sharp-binary-datetime-encoding
            secs = x / 10.0 ** 7
            delta = datetime.timedelta(seconds=secs)
            ts = datetime.datetime(1, 1, 1) + delta
            entry.value = ts
        elif tn == "System.TimeSpan":
            # TODO return resourceDataFactory.Create(new TimeSpan(reader.ReadInt64()));
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
        elif tn == "System.Decimal":
            # https://referencesource.microsoft.com/mscorlib/system/decimal.cs.html
            sign_mask = 0x80000000
            scale_mask = 0x00FF0000
            tsize = 16
            entry.data = self._data[edata_start:edata_start + tsize]
            low, med, high, flags = struct.unpack("<IIII", entry.data)
            v = low | med << 8 | high << 16
            scale = scale_mask & flags
            if scale > 0:
                v = v / 10**scale
            if sign_mask & flags:
                v = -v
            entry.value = v
        else:
            # TODO
            pass

    def read_rsrc_data_v2(self, userTypes: List[bytes], entry: ResourceEntry):
        # TODO
        edata_start = self.struct.DataSectionOffset + entry.struct.DataOffset
        # dnlib reads four bytes, but it looks like one byte in the files I have
        t = int.from_bytes(self._data[edata_start:edata_start + 1], byteorder="little", signed=True)
        entry.struct.Type = t
        edata_start += 1
        # check for invalid type code
        if t < 0 or t >= ResourceTypeCode.StartOfUserTypes + len(userTypes) - 1:
            # invalid resource type
            # TODO warn/error
            return
        # switch on type
        if t == ResourceTypeCode.Null:
            # Null
            entry.type_name = "Null"
            entry.data = b""
            # entry.value is already None
        elif t == ResourceTypeCode.String:
            entry.type_name = "System.String"
            try:
                data, n = self.read_serialized_data(edata_start)
            except ValueError:
                raise errors.rsrcFormatError("CLR ResourceSet error: expected more data for serialized data at '{}' rsrc offset {}".format(self.parent.name, offset))
            entry.data = data
            try:
                entry.value = data.decode("utf-8")
            except UnicodeDecodeError:
                # TODO warn/error
                pass
        elif t == ResourceTypeCode.Int32:
            entry.type_name = "System.Int32"
            tsize = 4
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif t == ResourceTypeCode.Byte:
            entry.type_name = "System.Byte"
            tsize = 1
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = entry.data
        elif t == ResourceTypeCode.SByte:
            entry.type_name = "System.SByte"
            tsize = 1
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = entry.data
        elif t == ResourceTypeCode.Int16:
            entry.type_name = "System.Int16"
            tsize = 2
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif t == ResourceTypeCode.Int64:
            entry.type_name = "System.Int64"
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif t == ResourceTypeCode.UInt16:
            entry.type_name = "System.UInt16"
            tsize = 2
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif t == ResourceTypeCode.UInt32:
            entry.type_name = "System.UInt32"
            tsize = 4
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif t == ResourceTypeCode.UInt64:
            entry.type_name = "System.UInt64"
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = int.from_bytes(entry.data, byteorder="little", signed=False)
        elif t == ResourceTypeCode.Single:
            entry.type_name = "System.Single"
            tsize = 4
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = struct.unpack("<f", entry.data)[0]
        elif t == ResourceTypeCode.Double:
            entry.type_name = "System.Double"
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            entry.value = struct.unpack("<d", entry.data)[0]
        elif t == ResourceTypeCode.DateTime:
            entry.type_name = "System.DateTime"
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
            x = struct.unpack("<q", entry.data)[0]
            # https://stackoverflow.com/questions/3169517/python-c-sharp-binary-datetime-encoding
            secs = x / 10.0 ** 7
            delta = datetime.timedelta(seconds=secs)
            ts = datetime.datetime(1, 1, 1) + delta
            entry.value = ts
        elif t == ResourceTypeCode.TimeSpan:
            entry.type_name = "System.TimeSpan"
            # TODO return resourceDataFactory.Create(new TimeSpan(reader.ReadInt64()));
            tsize = 8
            entry.data = self._data[edata_start:edata_start + tsize]
        elif t == ResourceTypeCode.Decimal:
            entry.type_name = "System.Decimal"
            # https://referencesource.microsoft.com/mscorlib/system/decimal.cs.html
            sign_mask = 0x80000000
            scale_mask = 0x00FF0000
            tsize = 16
            entry.data = self._data[edata_start:edata_start + tsize]
            low, med, high, flags = struct.unpack("<IIII", entry.data)
            v = low | med << 8 | high << 16
            scale = scale_mask & flags
            if scale > 0:
                v = v / 10**scale
            if sign_mask & flags:
                v = -v
            entry.value = v
        elif t == ResourceTypeCode.ByteArray:
            entry.type_name = "System.ByteArray"
            tsize = 4
            dsize = int.from_bytes(self._data[edata_start:edata_start + tsize], byteorder="little", signed=False)
            entry.data = self._data[edata_start:edata_start + tsize + dsize]
            entry.value = self._data[edata_start + tsize:edata_start + tsize + dsize]
        elif t == ResourceTypeCode.Stream:
            entry.type_name = "System.Stream"
            tsize = 4
            dsize = int.from_bytes(self._data[edata_start:edata_start + tsize], byteorder="little", signed=False)
            entry.data = self._data[edata_start:edata_start + tsize + dsize]
            entry.value = self._data[edata_start + tsize:edata_start + tsize + dsize]
        elif t >= ResourceTypeCode.StartOfUserTypes:
            # TODO
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
