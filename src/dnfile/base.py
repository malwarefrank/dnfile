# -*- coding: utf-8 -*-
"""
.NET base classes

Copyright (c) 2020-2022 MalwareFrank
"""
import abc
import enum
import struct as _struct
import typing
import logging
from typing import TYPE_CHECKING, Dict, List, Type, Tuple, Union, Generic, TypeVar, Optional, Sequence

from pefile import Structure

from . import enums, errors

if TYPE_CHECKING:
    from . import stream


logger = logging.getLogger(__name__)


class StreamStruct(Structure):
    Name: bytes
    Offset: int
    Size: int


class ClrStream(abc.ABC):
    def __init__(
        self,
        metadata_rva: int,
        stream_struct: StreamStruct,
        stream_data: bytes,
    ):
        self.struct: StreamStruct = stream_struct
        self.rva: int = metadata_rva + stream_struct.Offset
        self.__data__: bytes = stream_data
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
        return self.__data__[offset:offset + size]

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
    @abc.abstractmethod
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
    #
    # required properties for subclasses.
    #
    # subclasses must define this property,
    # or __init__ will raise an exception.
    #
    # for example:
    #
    #   class ModuleRow(MDTableRow):
    #       _struct_class = ModuleRowStruct
    #
    _struct_class: Type[RowStruct]

    #
    # optional properties for subclasses.
    #
    # when a subclass defines one of these properties,
    # the given fields will be parsed with the appropriate strategy.
    # these strategy defintions:
    #   - map from underlying raw struct (e.g. RowStruct class)
    #   - map to the high-level property (e.g. MDTableRow subclass)
    #
    # for example:
    #
    #   class ModuleRow(MDTableRow):
    #       Name: str
    #       _struct_class = ModuleRowStruct
    #       _struct_strings = {
    #           "Name_StringIndex": "Name",
    #       }
    #
    # this strategy causes the parser to:
    #   1. parse the raw row using `ModuleRowStruct`
    #   2. fetch field `ModuleRowStruct.Name_StringIndex`
    #   3. resolve it as a string (due to strategy name)
    #   4. assign it to field `ModuleRow.Name`
    #
    # valid strategies are:
    #  - asis: map data as-is, possibly change the field name
    #  - strings: resolve via UserString table
    #  - guids: resolve via GUID table
    #  - blobs: resolve via Blob table
    #  - flags: resolve via given flags
    #  - enums: resolve via given enums
    #  - indexes: resolve via given table name
    #  - lists: resolve many items via given table name
    #  - codedindexes: resolve via candidate list of tables
    _struct_strings: Dict[str, str]
    _struct_guids: Dict[str, str]
    _struct_blobs: Dict[str, str]
    _struct_asis: Dict[str, str]
    _struct_codedindexes: Dict[str, Tuple[str, Type["CodedIndex"]]]  # also CodedIndex subclass
    _struct_indexes: Dict[str, Tuple[str, str]]                      # also Metadata table name
    _struct_flags: Dict[str, Tuple[str, Type[enums.ClrFlags]]]       # also ClrFlags subclass
    _struct_enums: Dict[str, Tuple[str, Type[enum.IntEnum]]]         # also enum.IntEnum subclassA
    _struct_lists: Dict[str, Tuple[str, str]]                        # also Metadata table name

    def __init__(
        self,
        tables_rowcounts: List[Optional[int]],
        strings_offset_size: int,
        guid_offset_size: int,
        blob_offset_size: int,
        strings_heap: Optional["stream.StringsHeap"],
        guid_heap: Optional["stream.GuidHeap"],
        blob_heap: Optional["stream.BlobHeap"],
    ):
        """
        Given the tables' row counts and heap info.

        Initialize the following attributes:
            row_size    The size, in bytes, of one row.  Calculated from
                         tables_rowcounts, heap info, and self._format
            struct      The class used to parse the data.

        tables_rowcounts is indexed by table number.  The value is the row count, if it exists, or None.
        """
        assert hasattr(self.__class__, "_struct_class")

        self._tables_rowcnt = tables_rowcounts
        self._strings: Optional["stream.StringsHeap"] = strings_heap
        self._guids: Optional["stream.GuidHeap"] = guid_heap
        self._blobs: Optional["stream.BlobHeap"] = blob_heap
        self._str_offsz = strings_offset_size
        self._guid_offsz = guid_offset_size
        self._blob_offsz = blob_offset_size
        self._format = self._compute_format()
        self._data: bytes = b""

        # we are cheating here: this isn't technically a RowStruct, but actually a RowStruct subclass.
        # but few users will likely reach in here, so ATM its not worth fully type annotating.
        self.struct: RowStruct = self.__class__._struct_class(format=self._format)
        self.row_size: int = self.struct.sizeof()

    @abc.abstractmethod
    def _compute_format(self) -> Tuple[str, Sequence[str]]:
        """
        Compute the structure format.
        This will be passed to RowStruct instances to calcuate the row size and to parse a row.

        This may raise an exception when the offsets to referenced streams is too large (>4 bytes).
        """
        ...

    def set_data(self, data: bytes, offset: int = None):
        """
        Parse the data and set struct for this row.

        NOTE that the row is not fully parsed, and attributes not set, until
        parse() is called after all tables have had parse_rows() called on them.
        """
        self._data = data
        self.struct = self.__class__._struct_class(format=self._format, file_offset=offset)
        self.struct.__unpack__(data)

    def parse(self, tables: List["ClrMetaDataTable"], next_row: Optional["MDTableRow"]):
        """
        Parse the row data and set object attributes.  Should only be called after all rows of all tables
        have been initialized, i.e. parse_rows() has been called on each table in the tables list.

            next_row    the next row in the table, used for row lists (e.g. FieldList, MethodList)
        """
        # if there are any fields to copy as-is
        if hasattr(self.__class__, "_struct_asis"):
            for struct_name, attr_name in self.__class__._struct_asis.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, getattr(self.struct, struct_name, None))

        # if strings
        if hasattr(self.__class__, "_struct_strings"):
            for struct_name, attr_name in self.__class__._struct_strings.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)
                if self._strings is None:
                    logger.warning("failed to fetch string: no strings table")
                    continue

                i = getattr(self.struct, struct_name, None)
                try:
                    s = self._strings.get(i)
                    setattr(self, attr_name, s)
                except UnicodeDecodeError:
                    s = self._strings.get(i, as_bytes=True)
                    logger.warning("string: invalid encoding")
                    setattr(self, attr_name, s)
                except IndexError:
                    logger.warning("failed to fetch string: unable to parse data")

        # if guids
        if hasattr(self.__class__, "_struct_guids"):
            for struct_name, attr_name in self.__class__._struct_guids.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)
                if self._guids is None:
                    logger.warning("failed to fetch guid: no guid table")
                    continue

                try:
                    g = self._guids.get(getattr(self.struct, struct_name, None))
                    setattr(self, attr_name, g)
                except (IndexError, TypeError):
                    logger.warning("failed to fetch guid: unable to parse data")

        # if blobs
        if hasattr(self.__class__, "_struct_blobs"):
            for struct_name, attr_name in self.__class__._struct_blobs.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)
                if self._blobs is None:
                    logger.warning("failed to fetch blob: no blob table")
                    continue
                try:
                    b = self._blobs.get(getattr(self.struct, struct_name, None))
                    setattr(self, attr_name, b)
                except (IndexError, TypeError):
                    logger.warning("failed to fetch blob: unable to parse data")

        # if coded indexes
        if hasattr(self.__class__, "_struct_codedindexes") and tables:
            for struct_name, (
                attr_name,
                attr_class,
            ) in self.__class__._struct_codedindexes.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)
                try:
                    o = attr_class(getattr(self.struct, struct_name, None), tables)
                    setattr(self, attr_name, o)
                except (IndexError, TypeError):
                    logger.warning("failed to fetch coded index: unable to parse data")

        # if flags
        if hasattr(self.__class__, "_struct_flags"):
            for struct_name, (attr_name, flag_class) in self.__class__._struct_flags.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)
                # Set the flags according to the Flags member
                v = getattr(self.struct, struct_name, None)
                if v is None:
                    logger.warning("failed to fetch flag: no data")
                    continue

                try:
                    setattr(self, attr_name, flag_class(v))
                except ValueError:
                    logger.warning("failed to fetch flag: invalid flag data")

        # if enums
        if hasattr(self.__class__, "_struct_enums"):
            for struct_name, (attr_name, enum_class) in self.__class__._struct_enums.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)
                # Set the value according to the Enum member
                v = getattr(self.struct, struct_name, None)
                if v is None:
                    logger.warning("failed to fetch enum: no data")
                    continue

                try:
                    setattr(self, attr_name, enum_class(v))
                except ValueError:
                    logger.warning("failed to fetch enum: invalid enum data")

        # if indexes
        if hasattr(self.__class__, "_struct_indexes") and tables:
            for struct_name, (attr_name, table_name) in self.__class__._struct_indexes.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, None)

                table = None
                for t in tables:
                    if t.name == table_name:
                        table = t
                if table:
                    i = getattr(self.struct, struct_name, None)
                    if i is not None and i > 0 and i <= table.num_rows:
                        setattr(self, attr_name, MDTableIndex(table, i))
                    else:
                        logger.warning("failed to fetch index reference: unable to parse data")

        # if lists
        if hasattr(self.__class__, "_struct_lists") and tables:
            for struct_name, (attr_name, table_name) in self.__class__._struct_lists.items():

                table = None
                for t in tables:
                    if t.name == table_name:
                        table = t

                run: List[MDTableIndex] = []
                # always define attribute, even if failed to parse
                setattr(self, attr_name, run)

                if not table:
                    # target table is not present,
                    # such as is there is no Field table in hello-world.exe,
                    # so the references below must, by defintion, be empty.
                    continue

                run_start_index = getattr(self.struct, struct_name, None)
                if run_start_index is not None:
                    max_row = table.num_rows
                    if next_row is not None:
                        # then we read from the target table,
                        # from the row referenced by this row,
                        # until the row referenced by the next row (`next_row`),
                        # or the end of the table.
                        next_row_reference = getattr(next_row.struct, struct_name, None)
                        run_end_index = max_row
                        if next_row_reference is not None:
                            run_end_index = min(next_row_reference, max_row)

                    else:
                        # then we read from the target table,
                        # from the row referenced by this row,
                        # until the end of the table.
                        run_end_index = max_row

                    # when this run starts at the last index,
                    # start == end and end == max_row.
                    # otherwise, if start == end, then run is empty.
                    if (run_start_index != run_end_index) or (run_end_index == max_row):
                        # row indexes are 1-indexed, so our range goes to end+1
                        for row_index in range(run_start_index, run_end_index + 1):
                            run.append(MDTableIndex(table, row_index))

                setattr(self, attr_name, run)

    def _table_name2num(self, name, tables: List["ClrMetaDataTable"]):
        for t in tables:
            if t.name == name:
                return t.number

    def _clr_coded_index_struct_size(self, tag_bits: int, table_names: Sequence[str]) -> str:
        """
        Given table names and tag bits, checks for the max row count
        size among the given tables and returns "H" if it will fit in
        a word or "I" if not, assuming tag bits number of bits are used
        by tag.

        The returned character can be used in a Structure format or
        passing to struct.pack()
        """
        max_index = 0
        for name in table_names:
            if not name:
                continue

            table_index = enums.MetadataTables[name].value
            table_rowcnt = self._tables_rowcnt[table_index]
            if table_rowcnt is None:
                # the requested table is not present,
                # so it effectively has zero rows.
                table_rowcnt = 0

            max_index = max(max_index, table_rowcnt)

        # if it can fit in a word (minus bits for reference id)
        if max_index <= 2 ** (16 - tag_bits):
            # size is a word
            return "H"
        else:
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


# This type describes the type of row that a table contains.
# For example, the Module table contains ModuleRows,
# so it inherits like this:
#
#     class Module(ClrMetaDataTable[ModuleRow]):
#         ...
#
# This lets us specify that `dnfile.mdtables.Module[0]` is a ModuleRow
# and therefore has properties Name, Generation, etc.
#
# Instances of these types must be subclasses of MDTableRow.
RowType = TypeVar('RowType', bound=MDTableRow)


class MDTableIndex(Generic[RowType]):
    """
    An index into a Metadata Table.

    Attributes:
        table           Table object.
        row_index       Index number of the row.
        row             The referenced row.
    """
    def __init__(self, table: "ClrMetaDataTable[RowType]", row_index: int):
        self.table: Optional["ClrMetaDataTable[RowType]"] = table
        self.row_index: int = row_index

    @property
    def row(self) -> Optional[RowType]:
        if self.table is None:
            return None
        else:
            return self.table.get_with_row_index(self.row_index)


class CodedIndex(MDTableIndex[RowType]):
    """
    Subclasses should be sure to set the following attributes:
      - tag_bits        Number of bits used to specify the table name index.
      - table_names     Candidate list of table names.
    """
    #
    # required properties for subclasses.
    #
    # subclasses must define this property,
    # or __init__ will raise an exception.
    #
    # for example:
    #
    #   class TypeDefOrRef(CodedIndex[...]):
    #       tag_bits = 2
    #       table_names = ("TypeDef", "TypeRef", "TypeSpec")
    #
    tag_bits: int
    table_names: Sequence[str]

    def __init__(self, value, tables: List["ClrMetaDataTable[RowType]"]):
        assert hasattr(self, "tag_bits")
        assert hasattr(self, "table_names")

        table_name = self.table_names[value & (2 ** self.tag_bits - 1)]
        self.row_index = value >> self.tag_bits

        for t in tables:
            if t.name != table_name:
                continue

            self.table = t
            return

        # this may not be a problem, e.g. when ManifestResource Implementation=0
        self.table = None


class ClrMetaDataTable(Generic[RowType]):
    """
    An abstract class for Metadata tables.  Rows can be accessed
     directly like a list with bracket [] syntax.
    Use `get_with_row_index` when you have a Rid/token/row_index,
     since these are 1-indexed.
    Use bracket [] syntax when you want 0-indexing.

    Subclasses should make sure to set the following attributes:
        number
        name
        _row_class
    """
    #
    # required properties for subclasses.
    #
    # subclasses must define this property,
    # or __init__ will raise an exception.
    #
    # for example:
    #
    #   class Module(ClrMetaDataTable[ModuleRow]):
    #       name = "Module"
    #       number = 0
    #       _row_class = ModuleRow
    #
    rva: int
    number: int
    name: str
    _row_class: Type[RowType]

    def __init__(
        self,
        tables_rowcounts: List[Optional[int]],
        is_sorted: bool,
        strings_offset_size: int,
        guid_offset_size: int,
        blob_offset_size: int,
        strings_heap: Optional["stream.StringsHeap"],
        guid_heap: Optional["stream.GuidHeap"],
        blob_heap: Optional["stream.BlobHeap"],
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
        assert hasattr(self, "number")
        assert hasattr(self, "name")
        assert hasattr(self, "_row_class")

        # default value
        self.rva: int = 0

        num_rows = tables_rowcounts[self.number]
        if num_rows is None:
            # the table doesn't exist, so create the instance, but with zero rows.
            num_rows = 0

        self.is_sorted: bool = is_sorted
        self.num_rows: int = num_rows

        self.rows: List[RowType] = []
        for i in range(num_rows):
            try:
                self.rows.append(self._row_class(
                    tables_rowcounts,
                    strings_offset_size,
                    guid_offset_size,
                    blob_offset_size,
                    strings_heap,
                    guid_heap,
                    blob_heap,
                ))
            except errors.dnFormatError:
                # this may occur when the offset to a stream is too large.
                # this probably means invalid data.
                logger.warning("failed to construct %s row %d", self.name, i)
                break

        # store heap info
        self._strings_heap: Optional["stream.StringsHeap"] = strings_heap
        self._guid_heap: Optional["stream.GuidHeap"] = guid_heap
        self._blob_heap: Optional["stream.BlobHeap"] = blob_heap
        self._strings_offset_size = strings_offset_size
        self._guid_offset_size = guid_offset_size
        self._blob_offset_size = blob_offset_size
        self._tables_rowcounts = tables_rowcounts

        self._table_data: bytes = b""
        self.row_size: int = self._get_row_size()

    def _get_row_size(self):
        if not self.rows:
            return 0
        r = self.rows[0]
        return r.row_size

    def parse_rows(self, table_rva: int, data: bytes):
        """
        Given a byte sequence containing the rows, add data to each row in the
        self.rows list.  Note that the rows have not been fully parsed until
        parse() is called, which should not happen until all tables have been
        initialized and parse_rows() called on each.
        """
        self._table_data = data
        if len(data) < self.row_size * self.num_rows:
            logger.warning("not enough data to parse %d rows", self.num_rows)
            # we can still try to parse some of the rows...

        offset = 0
        # iterate through rows, stopping at num_rows or when there is not enough data left
        for i in range(self.num_rows):
            if len(data) < offset + self.row_size:
                logger.warning("not enough data to parse row %d", i)
                break

            self.rows[i].set_data(
                data[offset:offset + self.row_size], offset=table_rva + offset
            )
            offset += self.row_size

    def parse(self, tables: List["ClrMetaDataTable"]):
        """
        Fully parse the table, resolving references to heaps, indexes into other
        tables, and coded indexes into other tables.

        NOTE: do not call until ALL tables have been initialized and parse_rows()
        called on each.
        """

        # for each row in table
        for i, row in enumerate(self.rows):
            next_row = None
            if i + 1 < len(self.rows):
                next_row = self.rows[i + 1]

            # fully parse the row
            row.parse(tables, next_row=next_row)

    def __getitem__(self, index: int) -> RowType:
        return self.rows[index]

    def __len__(self):
        """
        the actual number of rows parsed,
        as opposed to self.num_rows, which is the declared row count of the table
        """
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def get_with_row_index(self, row_index: int) -> RowType:
        """
        fetch the row with the given row index.
        remember: row indices, at least those encoded within a .NET file, are 1-based.
        so, you should prefer to use this method when you get a reference to a row.
        use `__getitem__` when you want 0-based indexing.
        """
        return self[row_index - 1]


class ClrResource(abc.ABC):
    def __init__(self, name: str, public: bool = False, private: bool = False):
        self.name: str = name
        self.public: bool = public
        self.private: bool = private
        self.data: Optional[bytes] = None

    def set_data(self, data: bytes):
        self.data = data

    @abc.abstractmethod
    def parse(self):
        raise NotImplementedError()
