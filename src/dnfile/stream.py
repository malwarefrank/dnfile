# -*- coding: utf-8 -*-
"""
.NET Streams

REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123

Copyright (c) 2020-2021 MalwareFrank
"""

import copy as _copymod
import struct as _struct
from binascii import hexlify as _hexlify

from pefile import Structure
from pefile import DataContainer
from pefile import MAX_STRING_LENGTH

from typing import Dict, List, Tuple

from . import errors, mdtable, base
from .utils import read_compressed_int


class GenericStream(base.ClrStream):
    """
    A generic CLR Stream of unknown type.
    """
    pass


class StringsHeap(base.ClrHeap):
    offset_size = 0

    def get(self, index, max_length=MAX_STRING_LENGTH, encoding="utf-8", as_bytes=False):
        """
        Given an index (offset), read a null-terminated UTF-8 (or given encoding) string.
        Returns None on error, or string, or bytes if as_bytes is True.
        """

        if not self.__data__ or index is None or not max_length:
            return None

        if index >= len(self.__data__):
            raise IndexError("index out of range")

        offset = index
        end = self.__data__.find(b"\x00", offset)
        if end - offset > max_length:
            return None
        data = self.__data__[offset:end]
        if as_bytes:
            return data
        s = data.decode(encoding)
        return s


class BinaryHeap(base.ClrHeap):
    def get_with_size(self, index) -> Tuple[bytes, int]:
        if index >= len(self.__data__):
            raise IndexError("index out of range")

        offset = index
        # read compressed int length
        data_length, length_size = read_compressed_int(
            self.__data__[offset : offset + 4]
        )
        # read data
        offset = offset + length_size
        data = self.__data__[offset : offset + data_length]
        return data, length_size + data_length

    def get(self, index) -> bytes:
        data, _ = self.get_with_size(index)
        return data


class BlobHeap(BinaryHeap):
    pass


class UserString(object):
    """
    The #US or UserStrings stream should contain UTF-16 strings.
    Each entry in the stream includes a byte indicating whether
    any Unicode characters require handling beyond that normally
    provided for 8-bit encoding sets.

    Reference ECMA-335, Partition II Section 24.2.4
    """
    value: str = None
    Flag: int = None

    __data__: bytes = None

    def __init__(self, data: bytes, encoding="utf-16"):
        self.__data__ = data
        if len(data) % 2 == 1:
            self.Flag = data[-1]
            data = data[:-1]
        else:
            # TODO error/warn
            pass
        self.value = data.decode(encoding)


class UserStringHeap(BinaryHeap):
    def get_us(self, index, max_length=MAX_STRING_LENGTH, encoding="utf-16") -> UserString:
        data = self.get(index)
        return UserString(data)


class GuidHeap(base.ClrHeap):
    offset_size = 0

    def get(self, index, as_bytes=False):
        if index is None or index < 1:
            return None

        size = 128 // 8  # number of bytes in a guid
        # offset into the GUID stream
        offset = (index - 1) * size

        if offset + size > len(self.__data__):
            raise IndexError("index out of range")

        data = self.__data__[offset : offset + size]
        if as_bytes:
            return data
        # convert to string
        parts = _struct.unpack_from("<IHH", data)
        part3 = _hexlify(data[8:10])
        part4 = _hexlify(data[10:16])
        part3 = part3.decode("ascii")
        part4 = part4.decode("ascii")
        return "{:08x}-{:04x}-{:04x}-{}-{}".format(
            parts[0], parts[1], parts[2], part3, part4
        )


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

    header: MDTablesStruct
    tables: Dict[str, base.ClrMetaDataTable]
    tables_list: List[base.ClrMetaDataTable]
    strings_offset_size: int
    guids_offset_size: int
    blobs_offset_size: int

    # from https://www.ntcore.com/files/dotnetformat.htm
    # and https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123
    Module:                 mdtable.Module = None
    TypeRef:                mdtable.TypeRef = None
    TypeDef:                mdtable.TypeDef = None
    Field:                  mdtable.Field = None
    MethodDef:              mdtable.MethodDef = None
    Param:                  mdtable.Param = None
    InterfaceImpl:          mdtable.InterfaceImpl = None
    MemberRef:              mdtable.MemberRef = None
    Constant:               mdtable.Constant = None
    CustomAttribute:        mdtable.CustomAttribute = None
    FieldMarshal:           mdtable.FieldMarshal = None
    DeclSecurity:           mdtable.DeclSecurity = None
    ClassLayout:            mdtable.ClassLayout = None
    FieldLayout:            mdtable.FieldLayout = None
    StandAloneSig:          mdtable.StandAloneSig = None
    EventMap:               mdtable.EventMap = None
    Event:                  mdtable.Event = None
    PropertyMap:            mdtable.PropertyMap = None
    Property:               mdtable.Property = None
    MethodSemantics:        mdtable.MethodSemantics = None
    MethodImpl:             mdtable.MethodImpl = None
    ModuleRef:              mdtable.ModuleRef = None
    TypeSpec:               mdtable.TypeSpec = None
    ImplMap:                mdtable.ImplMap = None
    FieldRva:               mdtable.FieldRva = None
    Assembly:               mdtable.Assembly = None
    AssemblyProcessor:      mdtable.AssemblyProcessor = None
    AssemblyOS:             mdtable.AssemblyOS = None
    AssemblyRef:            mdtable.AssemblyRef = None
    AssemblyRefProcessor:   mdtable.AssemblyRefProcessor = None
    AssemblyRefOS:          mdtable.AssemblyRefOS = None
    File:                   mdtable.File = None
    ExportedType:           mdtable.ExportedType = None
    ManifestResource:       mdtable.ManifestResource = None
    NestedClass:            mdtable.NestedClass = None
    GenericParam:           mdtable.GenericParam = None
    GenericParamConstraint: mdtable.GenericParamConstraint = None

    def parse(self, streams: List[base.ClrStream]):

        STRINGS_MASK = 0x01
        GUIDS_MASK = 0x02
        BLOBS_MASK = 0x03
        MAX_TABLES = 64

        warnings = list()

        self.tables = dict()
        self.tables_list = list()
        header_len = Structure(self._format).sizeof()
        if not self.__data__ or len(self.__data__) < header_len:
            # warning
            raise errors.dnFileFormat("Unable to read .NET metadata tables")

        #### parse header
        header_struct = MDTablesStruct(self._format, file_offset=self.rva)
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
        strings_heap: StringsHeap = None
        guid_heap: GuidHeap = None
        blob_heap: BlobHeap = None
        for s in streams:
            # find the first instance of the strings, guid, and blob heaps
            # TODO: if there are multiple instances of a type, does dotnet runtime use first?
            if not strings_heap and isinstance(s, StringsHeap):
                strings_heap = s
            elif not guid_heap and isinstance(s, GuidHeap):
                guid_heap = s
            elif not blob_heap and isinstance(s, BlobHeap):
                blob_heap = s

        #### Parse tables rows list.
        #  It is a variable length array of dwords.  Each dword is
        #  the number of rows in a table.  They are ordered by table
        #  number, smallest first.  Only the tables needed/defined
        #  are listed, thus the variable length and need to parse
        #  the header's MaskValid member.
        cur_rva = self.rva + header_len
        # initialize table with zero row counts for all tables
        table_rowcounts = [0] * MAX_TABLES
        # read all row counts
        for i in range(MAX_TABLES):
            # if table bit is set
            if header_struct.MaskValid & 2 ** i != 0:
                # read the row count
                table_rowcounts[i] = self.get_dword_at_rva(cur_rva)
                # increment to next dword
                cur_rva += 4
        # initialize all tables
        for i in range(MAX_TABLES):
            # if table bit is set
            if header_struct.MaskValid & 2 ** i:
                is_sorted = header_struct.MaskSorted & 2 ** i != 0
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
                )
                if not table:
                    # delay error/warning
                    warnings.append(
                        "Invalid .NET metadata table list @ {} rva:{}".format(
                            i, cur_rva
                        )
                    )
                    # Everything up to this point has been saved in the object and is accessible,
                    # but more can be parsed, so we delay raising exception.
                # table number
                table.number = i
                # add to tables dict
                self.tables[i] = table
                # add to tables list
                self.tables_list.append(table)
                # set member, to allow reference by name
                if table.name:
                    setattr(self, table.name, table)

        #### parse each table
        # here, cur_rva points to start of table rows
        for table in self.tables_list:
            if table.row_size > 0 and table.num_rows > 0:
                table_data = self.get_data_at_rva(
                    cur_rva, table.row_size * table.num_rows
                )
                # parse structures (populates .struct for each row)
                table.parse_rows(table_data)
                table.rva = cur_rva
                # move to next set of rows
                cur_rva += table.row_size * table.num_rows
        #### finalize parsing each table
        # For each row, de-references indexes in the .struct and populates row attributes.
        for table in self.tables_list:
            table.parse(self.tables_list)

        # raise warning/error
        if warnings:
            raise errors.dnFormatError(warnings[0])
