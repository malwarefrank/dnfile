# -*- coding: utf-8 -*-
"""
.NET base classes

Copyright (c) 2020-2021 MalwareFrank
"""


import abc
import collections
import struct as _struct
from typing import Tuple, List, Dict, Optional, Type

from pefile import Structure

from . import enums, errors


class StreamStruct(Structure):
    Name: bytes
    Offset: int
    Size: int


class ClrStream(abc.ABC):
    struct: StreamStruct
    rva: int
    __data__: bytes

    def __init__(
        self,
        metadata_rva: int,
        stream_struct: StreamStruct,
        stream_data: bytes,
    ):
        self.struct = stream_struct
        self.rva = metadata_rva + stream_struct.Offset
        self.__data__ = stream_data
        self._stream_table_entry_size = stream_struct.sizeof()
        self._data_size = len(stream_data)

    def parse(self, streams: List):
        """
        Parse the stream.

        NOTE: do not call until all streams have been initialized,
              since we may need info from other streams.
        """
        pass

    def stream_table_entry_size(self):
        """
        Returns the number of bytes occupied by this entry in the Streams table list.
        """
        return self._stream_table_entry_size

    def sizeof(self):
        """
        Return the size of this stream, in bytes.
        """
        return self._data_size

    def get_data_at_offset(self, offset, size):
        if size == 0 or offset >= self.sizeof():
            return b""
        return self.__data__[offset : offset + size]

    def get_data_at_rva(self, rva, size):
        offset = rva - self.rva
        return self.get_data_at_offset(offset, size)

    def get_dword_at_rva(self, rva):
        d = self.get_data_at_rva(rva, 4)
        if len(d) < 4:
            return None
        # Little-endian
        i = _struct.unpack("<I", d)[0]
        return i


class ClrHeap(ClrStream):
    def get(self, index):
        raise NotImplementedError()


class RowStruct(Structure):
    pass


class MDTableRow(abc.ABC):
    """
    This is the base class for Metadata Tables' rows.

    A Metadata Table row is a simple structure that holds the
    fields and values.
    """

    struct: RowStruct
    row_size: int = 0

    _format: Tuple
    _tables: Dict[str, int]
    _struct_class = Type[RowStruct]

    # maps from struct attribute to object attribute
    _struct_strings: Dict[str, str] = None
    _struct_guids: Dict[str, str] = None
    _struct_blobs: Dict[str, str] = None
    _struct_asis: Dict[str, str] = None
    _struct_codedindexes: Dict[
        str, Tuple[str, Type["CodedIndex"]]
    ] = None  # also CodedIndex subclass
    _struct_indexes: Dict[str, Tuple[str, str]] = None  # also Metadata table name
    _struct_flags: Dict[
        str, Tuple[str, Type[enums.ClrFlags]]
    ] = None  # also ClrFlags subclass
    _struct_lists: Dict[str, Tuple[str, str]] = None  # also Metadata table name

    def __init__(
        self,
        tables_rowcounts: List[Optional[int]],
        strings_offset_size: int,
        guid_offset_size: int,
        blob_offset_size: int,
        strings_heap: ClrHeap,
        guid_heap: ClrHeap,
        blob_heap: ClrHeap,
    ):
        """
        Given the tables' row counts and heap info.
        Initialize the following attributes:
            row_size    The size, in bytes, of one row.  Calculated from
                        tables_rowcounts, heap info, and self._format

        tables_rowcounts is indexed by table number.  The value is the row count, if it exists, or None.
        """

        self._tables_rowcnt = tables_rowcounts
        self._strings = strings_heap
        self._guids = guid_heap
        self._blobs = blob_heap
        self._str_offsz = strings_offset_size
        self._guid_offsz = guid_offset_size
        self._blob_offsz = blob_offset_size
        self._init_format()
        self.struct = self._struct_class(format=self._format)
        self.row_size = self.struct.sizeof()

    def _init_format(self):
        """
        Initialize the structure format.  This is called by the __init__ function (class constructure)
        and results in the _format Tuple being set according to the tables rowcounts and heap info.
        The _format Tuple is passed to RowStruct instantiations to calcuate the row size and to parse a row.
        """
        pass

    def set_data(self, data: bytes, offset: int = None):
        """
        Parse the data and set struct for this row.

        NOTE that the row is not fully parsed, and attributes not set, until
        parse() is called after all tables have had parse_rows() called on them.
        """
        self._data = data
        self.struct = self._struct_class(format=self._format, file_offset=offset)
        self.struct.__unpack__(data)

    def parse(self, tables: List["ClrMetaDataTable"]):
        """
        Parse the row data and set object attributes.  Should only be called after all rows of all tables
        have been initialized, i.e. parse_rows() has been called on each table in the tables list.
        """
        # if there are any fields to copy as-is
        if self._struct_asis:
            for struct_name, attr_name in self._struct_asis.items():
                setattr(self, attr_name, getattr(self.struct, struct_name, None))
        # if strings
        if self._struct_strings and self._strings:
            for struct_name, attr_name in self._struct_strings.items():
                i = getattr(self.struct, struct_name, None)
                try:
                    s = self._strings.get(i)
                except UnicodeDecodeError:
                    s = self._strings.get(i, as_bytes=True)
                except IndexError:
                    s = None
                    # TODO error/warn
                setattr(self, attr_name, s)
        # if guids
        if self._struct_guids and self._guids:
            for struct_name, attr_name in self._struct_guids.items():
                try:
                    g = self._guids.get(getattr(self.struct, struct_name, None))
                except (IndexError, TypeError):
                    g = None
                    # TODO error/warn
                setattr(self, attr_name, g)
        # if blobs
        if self._struct_blobs and self._blobs:
            for struct_name, attr_name in self._struct_blobs.items():
                try:
                    b = self._blobs.get(getattr(self.struct, struct_name, None))
                except (IndexError, TypeError):
                    b = None
                    # TODO error/warn
                setattr(self, attr_name, b)
        # if coded indexes
        if self._struct_codedindexes and tables:
            for struct_name, (
                attr_name,
                attr_class,
            ) in self._struct_codedindexes.items():
                try:
                    o = attr_class(getattr(self.struct, struct_name, None), tables)
                except (IndexError, TypeError):
                    o = None
                    # TODO error/warn
                setattr(self, attr_name, o)
        # if flags
        if self._struct_flags:
            for struct_name, (attr_name, attr_class) in self._struct_flags.items():
                # Set the flags according to the Flags member
                v = getattr(self.struct, struct_name, None)
                if v is not None:
                    try:
                        flag_object = attr_class(v)
                    except ValueError:
                        flag_object = None
                        # TODO error/warn
                else:
                    flag_object = None
                    # TODO error/warn
                setattr(self, attr_name, flag_object)
        # if indexes
        if self._struct_indexes and tables:
            for struct_name, (attr_name, table_name) in self._struct_indexes.items():
                table_object = None
                for t in tables:
                    if t.name == table_name:
                        table_object = t
                if table_object:
                    i = getattr(self.struct, struct_name, None)
                    if i is not None and i < t.num_rows:
                        row = t.rows[i]
                        setattr(self, attr_name, row)
                    else:
                        setattr(self, attr_name, None)
                        # TODO error/warn
        # if lists
        if self._struct_lists:
            # TODO
            pass

    def _table_name2num(self, name, tables: List["ClrMetaDataTable"]):
        for t in tables:
            if t.name == name:
                return t.number

    def _clr_coded_index_struct_size(self, tag_bits, table_names):
        """
        Given table names and tag bits, checks for the max row count
        size among the given tables and returns "H" if it will fit in
        a word or "I" if not, assuming tag bits number of bits are used
        by tag.

        The returned character can be used in a Structure format or
        passing to struct.pack()
        """
        if not table_names or not self._tables_rowcnt:
            # error
            raise dnFormatError("Problem parsing .NET coded index")
        max_index = 0
        for name in table_names:
            if not name:
                continue
            i = enums.MetadataTables[name].value
            if self._tables_rowcnt[i] > max_index:
                max_index = self._tables_rowcnt[i]
        # if it can fit in a word (minus bits for reference id)
        if max_index <= 2 ** (16 - tag_bits):
            # size is a word
            return "H"
        # otherwise, size is a dword
        return "I"


class MDTablesStruct(Structure):
    Reserved_1: int
    MajorVersion: int
    MinorVersion: int
    HeapOffsetSizes: int
    Reserved_2: int
    MaskValid: int
    MaskSorted: int


class ClrMetaDataTable(collections.abc.Sequence):
    """
    An abstract class for Metadata tables.  Rows can be accessed
    directly like a list with bracket [] syntax.

    Subclasses should make sure to set the following attributes:
        number
        name
        _format
        _flags
        _row_class
    """

    number: int = None
    name: str = None
    num_rows: int = 0
    row_size: int = 0
    rows: List[MDTableRow] = None
    is_sorted = False
    rva: int = 0

    _format: Tuple = None
    _flags: Tuple = None
    _row_class: Type[MDTableRow] = None
    _table_data: bytes

    def __init__(
        self,
        tables_rowcounts: List[Optional[int]],
        is_sorted: bool,
        strings_offset_size: int,
        guid_offset_size: int,
        blob_offset_size: int,
        strings_heap: ClrHeap,
        guid_heap: ClrHeap,
        blob_heap: ClrHeap,
    ):
        """
        Given the tables' row counts, sorted flag, and heap info.
        Initialize the following attributes:
            num_rows    The number of rows, according to tables_rowscount.
            row_size    The size, in bytes, of one row.  Calculated from
                        tables_info, tables_rowcounts, and self._format
            is_sorted   Whether the table is sorted, according to tables_info.
            rows        Initialized but not-yet-parsed list of rows.
        """
        self.is_sorted = is_sorted
        self.num_rows = tables_rowcounts[self.number]
        self.rows = list()
        # store heap info
        self._strings_heap = strings_heap
        self._guid_heap = guid_heap
        self._blob_heap = blob_heap
        self._strings_offset_size = strings_offset_size
        self._guid_offset_size = guid_offset_size
        self._blob_offset_size = blob_offset_size
        self._tables_rowcounts = tables_rowcounts
        # init rows
        self._init_rows()
        # get row size
        self.row_size = self._get_row_size()

    def _init_rows(self):
        if self._row_class:
            for i in range(self.num_rows):
                r: MDTableRow
                r = self._row_class(
                    self._tables_rowcounts,
                    self._strings_offset_size,
                    self._guid_offset_size,
                    self._blob_offset_size,
                    self._strings_heap,
                    self._guid_heap,
                    self._blob_heap,
                )
                self.rows.append(r)

    def _get_row_size(self):
        if not self.rows:
            return 0
        r = self.rows[0]
        return r.row_size

    def parse_rows(self, data: bytes):
        """
        Given a byte sequence containing the rows, add data to each row in the
        self.rows list.  Note that the rows have not been fully parsed until
        parse() is called, which should not happen until all tables have been
        initialized and parse_rows() called on each.
        """
        self._table_data = data
        if len(data) < self.row_size * self.num_rows:
            # error/warn
            raise errors.dnFormatError(
                "Error parsing table {}, len(data)={}  row_size={}  num_rows={}".format(
                    self.name, len(data), self.row_size, self.num_rows
                )
            )
        offset = 0
        # iterate through rows, stopping at num_rows or when there is not enough data left
        for i in range(self.num_rows):
            if len(data) < offset + self.row_size:
                # error/warn
                raise errors.dnFormatError(
                    "Error parsing row {} for table {}, len(data)={}  row_size={}  offset={}".format(
                        i, self.name, len(data), self.row_size, offset
                    )
                )
            self.rows[i].set_data(
                data[offset : offset + self.row_size], offset=self.rva + offset
            )
            offset += self.row_size

    def parse(self, l: List["ClrMetaDataTable"]):
        """
        Fully parse the table, resolving references to heaps, indexes into other
        tables, and coded indexes into other tables.

        NOTE: do not call until ALL tables have been initialized and parse_rows()
        called on each.
        """

        # for each row in table
        for r in self.rows:
            # fully parse the row
            r.parse(l)

    def __getitem__(self, index: int):
        return self.rows[index]

    def __len__(self):
        return len(self.rows)


class MDTableIndex(object):
    """
    An index into a Metadata Table.

    Attributes:
        table           Table object.
        row_index       Index number of the row.
    """

    table: ClrMetaDataTable
    row_index: int
    row: MDTableRow

    _table_class: Type[ClrMetaDataTable]

    # TODO: figure out how and when to recursively resolve refs, and detect cycles

    def __init__(self, value, tables_list: List[ClrMetaDataTable]):
        self.row_index = value
        for t in tables_list:
            if isinstance(t, self._table_class):
                self.table = t
                if self.row_index > t.num_rows:
                    # TODO error/warn
                    self.row = None
                    return
                self.row = t.rows[self.row_index - 1]


class CodedIndex(MDTableIndex):
    tag_bits: int
    table_names: Tuple[str]

    def __init__(self, value, tables_list: List[ClrMetaDataTable]):
        table_name = self.table_names[value & (2 ** self.tag_bits - 1)]
        self.row_index = value >> self.tag_bits
        for t in tables_list:
            if t.name == table_name:
                self.table = t
                if self.row_index > t.num_rows:
                    # TODO error/warn
                    self.row = None
                    return
                self.row = t.rows[self.row_index - 1]
