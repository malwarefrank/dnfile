# -*- coding: utf-8 -*-
"""
.NET Streams

REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123

Copyright (c) 2020-2022 MalwareFrank
"""

import struct as _struct
import logging
from typing import Dict, List, Tuple, Union, Optional
from binascii import hexlify as _hexlify

from pefile import MAX_STRING_LENGTH, Structure

from . import base, errors, mdtable
from .utils import read_compressed_int

logger = logging.getLogger(__name__)


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
    def get_with_size(self, index) -> Optional[Tuple[bytes, int]]:
        if self.__data__ is None:
            logger.warning("stream has no data")
            return None

        if index >= len(self.__data__):
            logger.warning("stream is too small: wanted: 0x%x found: 0x%x", index, len(self.__data__))
            return None

        offset = index

        # read compressed int length
        buf = self.__data__[offset:offset + 4]
        ret = read_compressed_int(buf)
        if ret is None:
            # invalid compressed int length, such as invalid leading flags.
            logger.warning("stream entry has invalid compressed int")
            return None

        data_length, length_size = ret

        # read data
        offset = offset + length_size
        data = self.__data__[offset:offset + data_length]

        return data, length_size + data_length

    def get(self, index) -> Optional[bytes]:
        try:
            ret = self.get_with_size(index)
        except IndexError:
            return None

        if ret is None:
            return None

        data, _ = ret

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
    def __init__(self, data: bytes, encoding="utf-16"):
        self.__data__: bytes = data
        self.value: str = data.decode(encoding)


class UserStringHeap(BinaryHeap):
    def get(self, index) -> Optional[bytes]:
        data = super(UserStringHeap, self).get(index)
        if data is None:
            return None

        flag: int = 0
        if len(data) % 2 == 1:
            # > This final byte holds the value 1 if and only if any UTF16
            # > character within the string has any bit set in its top byte,
            # > or its low byte is any of the following:
            # > 0x01–0x08, 0x0E–0x1F, 0x27, 0x2D, 0x7F.
            #
            # via ECMA-335 6th edition, II.24.2.4
            #
            # Trim this trailing flag, which is not part of the string.
            flag = data[-1]
            if flag == 0x00:
                # > Otherwise, it holds 0.
                #
                # via ECMA-335 6th edition, II.24.2.4
                #
                # *should* be a normal UTF-16 string, but still not
                # make sense.
                pass
            elif flag == 0x01:
                # > The 1 signifies Unicode characters that require handling
                # > beyond that normally provided for 8-bit encoding sets.
                #
                # via ECMA-335 6th edition, II.24.2.4
                #
                # these strings are probably best interpreted as bytes.
                pass
            else:
                logger.warning("unexpected string flag value: 0x%02x", flag)
            data = data[:-1]
        else:
            logger.warning("string missing trailing flag")

        return data

    def get_us(self, index, encoding="utf-16") -> Optional[UserString]:
        """
        Fetch the user string at the given index and attempt to decode it as UTF-16.

        Note: the underlying data is not guaranteed to be well formed UTF-16,
        so this routine may raise a UnicodeDecodeError when encountering such data.
        You can always use `UserStringHeap.get()` to fetch the raw binary data.
        """
        data = self.get(index)
        if data is None:
            return None
        else:
            return UserString(data, encoding=encoding)


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

        data = self.__data__[offset:offset + size]
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

    def parse(self, streams: List[base.ClrStream]):
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

        #### parse each table
        # here, cur_rva points to start of table rows
        for table in self.tables_list:
            if table.row_size > 0 and table.num_rows > 0:
                table_data = self.get_data_at_rva(
                    cur_rva, table.row_size * table.num_rows
                )
                # parse structures (populates .struct for each row)
                table.parse_rows(cur_rva, table_data)
                table.rva = cur_rva
                # move to next set of rows
                cur_rva += table.row_size * table.num_rows
        #### finalize parsing each table
        # For each row, de-references indexes in the .struct and populates row attributes.
        for table in self.tables_list:
            table.parse(self.tables_list)

        # raise warning/error
        if deferred_exceptions:
            raise deferred_exceptions[0]
