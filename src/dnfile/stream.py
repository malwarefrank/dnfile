# -*- coding: utf-8 -*-
"""
.NET Streams

REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123
    ECMA-335 6th Edition, June 2012, Section II.24.2.4 #US and #Blob heaps

Copyright (c) 2020-2024 MalwareFrank
"""

import struct as _struct
import logging
from typing import Dict, List, Tuple, Union, Optional, overload
from binascii import hexlify as _hexlify
from collections.abc import Sequence

from pefile import MAX_STRING_LENGTH, Structure

from . import base, errors, mdtable
from .utils import read_compressed_int

logger = logging.getLogger(__name__)


class GenericStream(base.ClrStream):
    """
    A generic CLR Stream of unknown type.
    """
    pass


class HeapItemString(base.HeapItem):
    """
    A HeapItemString is a HeapItem with an encoding.  The .value member
    is the decoded string or None if there was a UnicodeDecodeError.

    A HeapItemString can be compared directly to a str.
    """
    encoding: Optional[str]

    def __init__(self, data: bytes, rva: Optional[int] = None, encoding="utf-8"):
        super().__init__(data, rva=rva)
        self.encoding = encoding
        try:
            self.value: Optional[str] = self.__data__.decode(encoding)
        except UnicodeDecodeError as e:
            self.value = None

    def __str__(self) -> str:
        return self.value or ""

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)


class HeapItemBinary(base.HeapItem):
    """
    A HeapItemBinary is a HeapItem with an item_size.  The .item_size
    is the parsed compressed integer at the RVA in the binary heap.
    The .value is the bytes following the compressed integer.

    A HeapItemBinary can be compared directly to a bytes object.
    """
    item_size: base.CompressedInt

    def __init__(self, data: bytes, rva: Optional[int] = None):
        self.rva = rva
        # read compressed int, which has a max size of four bytes
        size = base.CompressedInt.read(data[:4], rva)
        if size is None:
            raise ValueError("invalid compressed int")
        self.item_size = size
        base.HeapItem.__init__(self, data[:self.item_size.raw_size + self.item_size], rva)

        # read data
        offset = self.item_size.raw_size
        self.value = self.__data__[offset:offset + self.item_size]

    def value_bytes(self):
        return self.__data__[self.item_size.raw_size:]

    def __eq__(self, other):
        if isinstance(other, base.HeapItem):
            return base.HeapItem.__eq__(self, other)
        if isinstance(other, bytes):
            return self.value == other
        return False


class StringsHeap(base.ClrHeap):
    offset_size = 0

    def get_str(self, index, max_length=MAX_STRING_LENGTH, encoding="utf-8", as_bytes=False):
        """
        Given an index (offset), read a null-terminated UTF-8 (or given encoding) string.
        Returns None on error, or string, or bytes if as_bytes is True.
        """

        item = self.get(index, max_length, encoding)

        if item is None:
            return None

        if as_bytes:
            return item.value_bytes()

        return item.value

    def get(self, index, max_length=MAX_STRING_LENGTH, encoding="utf-8") -> Optional[HeapItemString]:
        """
        Given an index (offset), read a null-terminated UTF-8 (or given encoding) string.
        Returns a HeapItemString, or None on error.
        """
        if not self.__data__ or index is None or not max_length:
            return None

        if index >= len(self.__data__):
            raise IndexError("index out of range")

        offset = index
        end = self.__data__.find(b"\x00", offset)
        if end - offset > max_length:
            return None

        item = HeapItemString(self.__data__[offset:end], rva=self.rva + offset, encoding=encoding)

        return item


class BinaryHeap(base.ClrHeap):
    def get_with_size(self, index: int) -> Optional[Tuple[bytes, int]]:
        try:
            item = self.get(index)
        except IndexError:
            return None

        if item is None:
            return None

        return item.value_bytes(), item.raw_size

    def get_bytes(self, index: int) -> Optional[bytes]:
        try:
            item = self.get(index)
        except IndexError:
            return None

        if item is None:
            return None

        return item.value_bytes()

    def get(self, index: int) -> Optional[HeapItemBinary]:
        if self.__data__ is None:
            logger.warning("stream has no data")
            return None

        if index >= len(self.__data__):
            logger.warning("stream is too small: wanted: 0x%x found: 0x%x", index, len(self.__data__))
            return None

        offset = index

        try:
            item = HeapItemBinary(self.__data__[index:], rva=self.rva + offset)
        except ValueError as e:
            # possible invalid compressed int length, such as invalid leading flags.
            logger.warning(f"stream entry error - {e} @ RVA=0x{hex(self.rva + offset)}")
            return None

        return item


class BlobHeap(BinaryHeap):
    pass


class UserString(HeapItemBinary, HeapItemString):
    """
    The #US or UserStrings stream should contain UTF-16 strings.
    Each entry in the stream includes a byte indicating whether
    any Unicode characters require handling beyond that normally
    provided for 8-bit encoding sets.

    Reference ECMA-335, Partition II Section 24.2.4
    """

    flag: Optional[int] = None

    def __init__(self, data: Union[bytes, HeapItemBinary], rva: Optional[int] = None, encoding="utf-16"):
        self.encoding = encoding
        if isinstance(data, bytes):
            HeapItemBinary.__init__(self, data, rva=rva)
        elif isinstance(data, HeapItemBinary):
            HeapItemBinary.__init__(self, data.raw_data, rva=rva or data.rva)

        buf = self.__data__[self.item_size.raw_size:]
        if self.item_size % 2 == 1:
            # > This final byte holds the value 1 if and only if any UTF16
            # > character within the string has any bit set in its top byte,
            # > or its low byte is any of the following:
            # > 0x01–0x08, 0x0E–0x1F, 0x27, 0x2D, 0x7F.
            #
            # via ECMA-335 6th edition, II.24.2.4
            #
            # Trim this trailing flag, which is not part of the string.
            self.flag = buf[-1]
            str_buf = buf[:-1]
            if self.flag == 0x00:
                # > Otherwise, it holds 0.
                #
                # via ECMA-335 6th edition, II.24.2.4
                #
                # *should* be a normal UTF-16 string, but still not
                # make sense.
                pass
            elif self.flag == 0x01:
                # > The 1 signifies Unicode characters that require handling
                # > beyond that normally provided for 8-bit encoding sets.
                #
                # via ECMA-335 6th edition, II.24.2.4
                #
                # these strings are probably best interpreted as bytes.
                pass
            else:
                logger.warning(f"unexpected string flag value: 0x{self.flag:02x}")
        else:
            logger.warning("string missing trailing flag")
            str_buf = buf

        try:
            self.value = str_buf.decode(encoding)
        except UnicodeDecodeError as e:
            logger.warning(f"UserString decode error (rva:0x{self.rva:08x}): {e}")
            self.value = None

    def value_bytes(self):
        if self.flag is None:
            return self.__data__[self.item_size.raw_size:]
        return self.__data__[self.item_size.raw_size:-1]

    def __eq__(self, other):
        return HeapItemString.__eq__(self, other)


class UserStringHeap(BinaryHeap):
    def get_bytes(self, index) -> Optional[bytes]:
        item = self.get(index)

        if item is None:
            return None

        return item.value_bytes()

    def get(self, index, encoding="utf-16") -> Optional[UserString]:
        bin_item = super().get(index)
        if bin_item is None:
            return None

        us_item = UserString(bin_item, encoding=encoding)

        return us_item


class HeapItemGuid(base.HeapItem):

    ITEM_SIZE = 128 // 8  # number of bytes in a guid

    def __init__(self, data: bytes, rva: Optional[int] = None):
        super().__init__(data, rva)

    @property
    def value(self):
        return self.__data__

    def __str__(self):
        data = self.__data__
        parts = _struct.unpack_from("<IHH", data)
        part3 = _hexlify(data[8:10])
        part4 = _hexlify(data[10:16])
        part3 = part3.decode("ascii")
        part4 = part4.decode("ascii")
        return f"{parts[0]:08x}-{parts[1]:04x}-{parts[2]:04x}-{part3}-{part4}"

    def __repr__(self):
        return f"HeapItemGuid(data={self.__data__},rva={self.rva})"


class GuidHeap(base.ClrHeap, Sequence):
    offset_size = 0

    def get_str(self, index, as_bytes=False):
        item = self.get(index)

        if item is None:
            return None

        if as_bytes:
            return item.value_bytes()

        return str(item)

    def get(self, index: int) -> Optional[HeapItemGuid]:
        if not isinstance(index, int):
            raise IndexError(f"unexpected type: {type(index)}")

        # 1-based indexing
        if index < 1 or index > len(self):
            return None

        # offset into the GUID stream
        offset = (index - 1) * HeapItemGuid.ITEM_SIZE

        item = HeapItemGuid(self.__data__[offset:offset + HeapItemGuid.ITEM_SIZE], self.rva + offset)

        return item

    def __len__(self) -> int:
        return len(self.__data__) // HeapItemGuid.ITEM_SIZE

    @overload
    def __getitem__(self, i: int) -> HeapItemGuid:
        ...

    @overload
    def __getitem__(self, i: slice) -> List[HeapItemGuid]:
        ...

    def __getitem__(self, i):
        if isinstance(i, int):
            if i < 0:
                # convert negative index into positive
                index0 = len(self) + i
            else:
                index0 = i
            item = self.get(index0 + 1)
            if item is None:
                raise IndexError(f"unexpected index: {i}")
            return item
        elif isinstance(i, slice):
            start, stop, step = i.indices(len(self))
            return [self[index] for index in range(start, stop, step)]
        raise IndexError(f"unexpected type '{type(i)}'")


class MDTablesStruct(Structure):
    Reserved_1: int
    MajorVersion: int
    MinorVersion: int
    HeapOffsetSizes: int
    Reserved_2: int
    MaskValid: int
    MaskSorted: int


class MetaDataTables(base.ClrStream):
    """Holds CLR (.NET) Metadata Tables.

    struct:     the stream list entry
    header:     IMAGE_CLR_METADATA_TABLES structure
    tables:     dict of tables where table number is key and value is CLRMetaDataTable object
    tables_list:            list of tables, in processing order
    strings_offset_size:    number of bytes
    guids_offset_size:      number of bytes
    blobs_offset_size:      number of bytes
    """

    _format = (
        "IMAGE_CLR_METADATA_TABLES",
        (
            "I,Reserved_1",
            "B,MajorVersion",
            "B,MinorVersion",
            "B,HeapOffsetSizes",
            "B,Reserved_2",
            "Q,MaskValid",
            "Q,MaskSorted",
        ),
    )

    header: Optional[MDTablesStruct]
    tables: Dict[Union[str, int], base.ClrMetaDataTable]
    tables_list: List[base.ClrMetaDataTable]
    strings_offset_size: int
    guids_offset_size: int
    blobs_offset_size: int

    # from https://www.ntcore.com/files/dotnetformat.htm
    # and https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123
    Module:                 Optional[mdtable.Module]
    TypeRef:                Optional[mdtable.TypeRef]
    TypeDef:                Optional[mdtable.TypeDef]
    Field:                  Optional[mdtable.Field]
    MethodDef:              Optional[mdtable.MethodDef]
    Param:                  Optional[mdtable.Param]
    InterfaceImpl:          Optional[mdtable.InterfaceImpl]
    MemberRef:              Optional[mdtable.MemberRef]
    Constant:               Optional[mdtable.Constant]
    CustomAttribute:        Optional[mdtable.CustomAttribute]
    FieldMarshal:           Optional[mdtable.FieldMarshal]
    DeclSecurity:           Optional[mdtable.DeclSecurity]
    ClassLayout:            Optional[mdtable.ClassLayout]
    FieldLayout:            Optional[mdtable.FieldLayout]
    StandAloneSig:          Optional[mdtable.StandAloneSig]
    EventMap:               Optional[mdtable.EventMap]
    Event:                  Optional[mdtable.Event]
    PropertyMap:            Optional[mdtable.PropertyMap]
    Property:               Optional[mdtable.Property]
    MethodSemantics:        Optional[mdtable.MethodSemantics]
    MethodImpl:             Optional[mdtable.MethodImpl]
    ModuleRef:              Optional[mdtable.ModuleRef]
    TypeSpec:               Optional[mdtable.TypeSpec]
    ImplMap:                Optional[mdtable.ImplMap]
    FieldRva:               Optional[mdtable.FieldRva]
    Assembly:               Optional[mdtable.Assembly]
    AssemblyProcessor:      Optional[mdtable.AssemblyProcessor]
    AssemblyOS:             Optional[mdtable.AssemblyOS]
    AssemblyRef:            Optional[mdtable.AssemblyRef]
    AssemblyRefProcessor:   Optional[mdtable.AssemblyRefProcessor]
    AssemblyRefOS:          Optional[mdtable.AssemblyRefOS]
    File:                   Optional[mdtable.File]
    ExportedType:           Optional[mdtable.ExportedType]
    ManifestResource:       Optional[mdtable.ManifestResource]
    NestedClass:            Optional[mdtable.NestedClass]
    GenericParam:           Optional[mdtable.GenericParam]
    GenericParamConstraint: Optional[mdtable.GenericParamConstraint]
    Unused:                 Optional[mdtable.Unused]

    def __init__(self, metadata_rva: int, stream_struct: base.StreamStruct, stream_data: bytes):
        super().__init__(metadata_rva, stream_struct, stream_data)
        self.header = None
        self.tables = dict()
        self.tables_list = list()
        strings_offset_size = 0
        guids_offset_size = 0
        blobs_offset_size = 0
        self.Module: Optional[mdtable.Module] = None
        self.TypeRef: Optional[mdtable.TypeRef] = None
        self.TypeDef: Optional[mdtable.TypeDef] = None
        self.Field: Optional[mdtable.Field] = None
        self.MethodDef: Optional[mdtable.MethodDef] = None
        self.Param: Optional[mdtable.Param] = None
        self.InterfaceImpl: Optional[mdtable.InterfaceImpl] = None
        self.MemberRef: Optional[mdtable.MemberRef] = None
        self.Constant: Optional[mdtable.Constant] = None
        self.CustomAttribute: Optional[mdtable.CustomAttribute] = None
        self.FieldMarshal: Optional[mdtable.FieldMarshal] = None
        self.DeclSecurity: Optional[mdtable.DeclSecurity] = None
        self.ClassLayout: Optional[mdtable.ClassLayout] = None
        self.FieldLayout: Optional[mdtable.FieldLayout] = None
        self.StandAloneSig: Optional[mdtable.StandAloneSig] = None
        self.EventMap: Optional[mdtable.EventMap] = None
        self.Event: Optional[mdtable.Event] = None
        self.PropertyMap: Optional[mdtable.PropertyMap] = None
        self.Property: Optional[mdtable.Property] = None
        self.MethodSemantics: Optional[mdtable.MethodSemantics] = None
        self.MethodImpl: Optional[mdtable.MethodImpl] = None
        self.ModuleRef: Optional[mdtable.ModuleRef] = None
        self.TypeSpec: Optional[mdtable.TypeSpec] = None
        self.ImplMap: Optional[mdtable.ImplMap] = None
        self.FieldRva: Optional[mdtable.FieldRva] = None
        self.Assembly: Optional[mdtable.Assembly] = None
        self.AssemblyProcessor: Optional[mdtable.AssemblyProcessor] = None
        self.AssemblyOS: Optional[mdtable.AssemblyOS] = None
        self.AssemblyRef: Optional[mdtable.AssemblyRef] = None
        self.AssemblyRefProcessor: Optional[mdtable.AssemblyRefProcessor] = None
        self.AssemblyRefOS: Optional[mdtable.AssemblyRefOS] = None
        self.File: Optional[mdtable.File] = None
        self.ExportedType: Optional[mdtable.ExportedType] = None
        self.ManifestResource: Optional[mdtable.ManifestResource] = None
        self.NestedClass: Optional[mdtable.NestedClass] = None
        self.GenericParam: Optional[mdtable.GenericParam] = None
        self.GenericParamConstraint: Optional[mdtable.GenericParamConstraint] = None
        self.Unused: Optional[mdtable.Unused] = None

    def parse(self, streams: List[base.ClrStream], lazy_load=False):
        """
        this may raise an exception if the data cannot be parsed correctly.
        however, `self` may still be partially initialized with *some* data.
        """
        STRINGS_MASK = 0x01
        GUIDS_MASK = 0x02
        BLOBS_MASK = 0x04
        DELTA_ONLY_MASK = 0x20
        EXTRA_DATA_MASK = 0x40
        HAS_DELETE_MASK = 0x80
        MAX_TABLES = 64

        # we may be able to parse some data before reaching corruption.
        # so, we'll keep parsing all we can, which updates `self` in-place,
        # and then raise the first deferred exception captured here.
        deferred_exceptions = list()

        header_len = Structure(self.__class__._format).sizeof()
        if not self.__data__ or len(self.__data__) < header_len:
            logger.warning("unable to read .NET metadata tables")
            raise errors.dnFormatError("Unable to read .NET metadata tables")

        #### parse header
        header_struct = MDTablesStruct(self._format, file_offset=self.file_offset)
        header_struct.__unpack__(self.__data__)
        self.header = header_struct

        #### heaps offsets
        if header_struct.HeapOffsetSizes & STRINGS_MASK:
            strings_offset_size = 4
        else:
            strings_offset_size = 2
        if header_struct.HeapOffsetSizes & GUIDS_MASK:
            guids_offset_size = 4
        else:
            guids_offset_size = 2
        if header_struct.HeapOffsetSizes & BLOBS_MASK:
            blobs_offset_size = 4
        else:
            blobs_offset_size = 2
        self.strings_offset_size = strings_offset_size
        self.guids_offset_size = guids_offset_size
        self.blobs_offset_size = blobs_offset_size

        #### heaps
        strings_heap: Optional[StringsHeap] = None
        guid_heap: Optional[GuidHeap] = None
        blob_heap: Optional[BlobHeap] = None
        for s in streams:
            # Find the last instance of the strings, guid, and blob heaps.
            # If there are multiple instances of a type, dotnet runtime uses last.
            if isinstance(s, StringsHeap):
                strings_heap = s
            elif isinstance(s, GuidHeap):
                guid_heap = s
            elif isinstance(s, BlobHeap):
                blob_heap = s

        #### Parse tables rows list.
        #  It is a variable length array of dwords.  Each dword is
        #  the number of rows in a table.  They are ordered by table
        #  number, smallest first.  Only the tables needed/defined
        #  are listed, thus the variable length and need to parse
        #  the header's MaskValid member.
        cur_rva = self.rva + header_len
        table_rowcounts = []
        # read all row counts
        for i in range(MAX_TABLES):
            # if table bit is set
            if header_struct.MaskValid & 2 ** i != 0:
                # read the row count
                table_rowcounts.append(self.get_dword_at_rva(cur_rva))
                # increment to next dword
                cur_rva += 4
            else:
                table_rowcounts.append(0)

        # consume an extra dword if the extra data bit is set
        if header_struct.HeapOffsetSizes & EXTRA_DATA_MASK == EXTRA_DATA_MASK:
            cur_rva += 4

        # initialize all tables
        for i in range(MAX_TABLES):
            # if table bit is set
            if header_struct.MaskValid & 2 ** i:
                is_sorted = header_struct.MaskSorted & 2 ** i != 0
                try:
                    table = mdtable.ClrMetaDataTableFactory.createTable(
                        i,
                        table_rowcounts,
                        is_sorted,
                        self.strings_offset_size,
                        self.guids_offset_size,
                        self.blobs_offset_size,
                        strings_heap,
                        guid_heap,
                        blob_heap,
                        lazy_load,
                    )
                except errors.dnFormatError as e:
                    table = None
                    deferred_exceptions.append(e)
                    logger.warning(str(e))
                if not table:
                    logger.warning("invalid .NET metadata table list @ %d RVA: 0x%x", i, cur_rva)
                    # Everything up to this point has been saved in the object and is accessible,
                    # but more can be parsed, so we delay raising exception.

                    deferred_exceptions.append(errors.dnFormatError(
                        "Invalid .NET metadata table list @ {} rva:{}".format(
                            i, cur_rva
                        ))
                    )
                    continue
                # table number
                table.number = i
                # add to tables dict
                self.tables[i] = table
                # add to tables list
                self.tables_list.append(table)
                # set member, to allow reference by name
                if table.name:
                    setattr(self, table.name, table)

        if lazy_load:
            self._loaded = False

            def full_loader():
                # Called if a property is accessed that requires data from other tables.
                # This will be called multiple times while parsing tables.
                if not self._loaded:
                    self._loaded = True
                    # parse_rows is redundant for lazy loading
                    for table in self.tables_list:
                        table.parse(self.tables_list)

            # Setup lazy loading for all tables
            for table in self.tables_list:
                if table.row_size > 0 and table.num_rows > 0:
                    table_data = self.get_data_at_rva(
                        cur_rva, table.row_size * table.num_rows
                    )
                    table.setup_lazy_load(cur_rva, table_data, full_loader)
                    table.file_offset = self.get_file_offset(cur_rva)
                    cur_rva += table.row_size * table.num_rows
        else:
            #### parse each table
            # here, cur_rva points to start of table rows
            for table in self.tables_list:
                if table.row_size > 0 and table.num_rows > 0:
                    table_data = self.get_data_at_rva(
                        cur_rva, table.row_size * table.num_rows
                    )
                    table.rva = cur_rva
                    table.file_offset = self.get_file_offset(cur_rva)
                    # parse structures (populates .struct for each row)
                    table.parse_rows(cur_rva, table_data)
                    # move to next set of rows
                    cur_rva += table.row_size * table.num_rows
            #### finalize parsing each table
            # For each row, de-references indexes in the .struct and populates row attributes.
            for table in self.tables_list:
                table.parse(self.tables_list)

        # raise warning/error
        if deferred_exceptions:
            raise deferred_exceptions[0]
