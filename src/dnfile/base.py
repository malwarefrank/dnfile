# -*- coding: utf-8 -*-
"""
.NET base classes

Copyright (c) 2020-2024 MalwareFrank
"""
import abc
import enum
import struct as _struct
import logging
import datetime
import functools as _functools
import itertools as _itertools
from typing import TYPE_CHECKING, Any, Dict, List, Type, Tuple, Union, Generic, TypeVar, Optional, Sequence

from pefile import Structure

from . import enums, errors
from .utils import LazyList as _LazyList
from .utils import read_compressed_int as _read_compressed_int

if TYPE_CHECKING:
    from . import stream


logger = logging.getLogger(__name__)


class CompressedInt(int):
    raw_size: int
    __data__: bytes
    value: int
    rva: Optional[int] = None

    def to_bytes(self):
        return self.__data__

    @classmethod
    def read(cls, data: bytes, rva: Optional[int] = None) -> Optional["CompressedInt"]:
        result = _read_compressed_int(data)
        if result is None:
            return None
        ci = CompressedInt(result[0])
        ci.raw_size = result[1]
        ci.value = result[0]
        ci.__data__ = data[:result[1]]
        ci.rva = rva
        return ci


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
        self.file_offset: Optional[int] = None
        self.__data__: bytes = stream_data
        self._stream_table_entry_size = stream_struct.sizeof()
        self._data_size = len(stream_data)

    def parse(self, streams: List, lazy_load: bool = False):
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

    def get_file_offset(self, rva=None):
        """
        Return the file offset of the given RVA within this stream.
        If no RVA given, then return the file offset of this stream.
        """
        if self.file_offset is not None and rva is not None:
            stream_offset = rva - self.rva
            if stream_offset >= 0:
                return self.file_offset + stream_offset
        return self.file_offset

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


class HeapItem(abc.ABC):
    """
    HeapItem is a base class for items retrieved from any of the
    heap streams, for example #Strings, #US, #GUID, and #Blob.

    It can be used to access the raw underlying data, the RVA
    from which it was retrieved, an optional interpreted value,
    and the bytes representation of the value.

    Each heap stream .get() call returns a subclass with these
    and optionally additional members.
    """

    rva: Optional[int] = None
    # original data from file
    __data__: bytes
    # interpreted value
    value: Any = None

    def __init__(self, data: bytes, rva: Optional[int] = None):
        self.rva = rva
        self.__data__ = data

    def value_bytes(self):
        """
        Return the raw bytes underlying the interpreted value.

        For the base HeapItem, this is the same as the raw_data.
        """
        return self.__data__

    @property
    def raw_size(self):
        """
        Number of bytes read from the stream, including any header,
        value, and footer.
        """
        return len(self.__data__)

    @property
    def raw_data(self):
        """
        The bytes read from the stream, including any header,
        value, and footer
        """
        return self.__data__

    def __eq__(self, other):
        """
        Two HeapItems are equal if their raw data is the same or their
        interpreted values are the same and not Noney.

        A HeapItem is equal to a bytes object if the HeapItem's value as bytes
        is equal to the bytes object.
        """
        if isinstance(other, HeapItem):
            return self.raw_data == other.raw_data or (self.value is not None and self.value == other.value)
        elif isinstance(other, bytes):
            return self.value_bytes() == other
        return False


class ClrHeap(ClrStream):
    @abc.abstractmethod
    def get(self, index: int):
        raise NotImplementedError()


class RowStruct(Structure):
    pass


class LoadState(enum.Enum):
    Unloaded = 0
    LazyLoaded = 1
    Loaded = 2


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

        self._loaded = LoadState.Unloaded

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

    def set_data(self, data: bytes, file_offset: Optional[int] = None):
        """
        Parse the data and set struct for this row.

        NOTE that the row is not fully parsed, and attributes not set, until
        parse() is called after all tables have had parse_rows() called on them.
        """
        self._data = data
        self.struct = self.__class__._struct_class(format=self._format, file_offset=file_offset)
        self.struct.__unpack__(data)

    # can be safely parsed without all tables being initialized
    CLASS_ATTRS = (
        "_struct_asis", "_struct_strings", "_struct_guids",
        "_struct_blobs", "_struct_flags", "_struct_enums",

    )
    # cannot be fully parsed without all tables being initialized
    CLASS_ATTRS_TABLES = (
        "_struct_codedindexes", "_struct_indexes", "_struct_lists"
    )

    def setup_lazy_load(self, full_loader):
        """Mark this row for lazy-loading.

        `full_loader` will be called if a property is requested that requires
        loading all mdtables before it can be parsed.
        """
        if not self._loaded == LoadState.Unloaded:
            return
        self._loaded = LoadState.LazyLoaded
        self._full_loader = full_loader
        # Retrieve the properties that this row *could* have, along with
        # their associated struct type. These are used to determine what
        # _parse function needs to be called to load the property.
        self._class_struct_attrs, self._class_struct_attrs_tables = (
            _row_class_struct_attrs(self.__class__)
        )

    def __getattr__(self, attr):
        """If this row is marked for lazy-loading, attempt to load the struct
        that contains the requested property and try again.

        If the requested property requires data from other
        mdtables, all tables will be loaded.
        """
        if self._loaded == LoadState.LazyLoaded:
            if attr in self._class_struct_attrs:
                loader = getattr(self, "_parse" + self._class_struct_attrs[attr])
                loader()
                # If something were to go wrong with loading the correct struct, this
                # would cause a StackOverflow from recursive __getattr__ calls.
                if hasattr(self, attr):
                    return getattr(self, attr)
            elif attr in self._class_struct_attrs_tables:
                # This property requires data from other tables, trigger a full load.
                self._full_loader()
                if hasattr(self, attr):
                    return getattr(self, attr)
        # TODO: more descriptive exception?
        raise AttributeError(attr)

    def parse(self, tables: List["ClrMetaDataTable"], next_row: Optional["MDTableRow"]):
        """
        Parse the row data and set object attributes.  Should only be called after all rows of all tables
        have been initialized, i.e. parse_rows() has been called on each table in the tables list.

            next_row    the next row in the table, used for row lists (e.g. FieldList, MethodList)
        """
        self._parse_struct_asis()
        self._parse_struct_strings()
        self._parse_struct_guids()
        self._parse_struct_blobs()
        self._parse_struct_flags()
        self._parse_struct_enums()
        self._parse_struct_codedindexes(tables, next_row)
        self._parse_struct_indexes(tables, next_row)
        self._parse_struct_lists(tables, next_row)
        self._loaded = LoadState.Loaded

    def _parse_struct_asis(self):
        # if there are any fields to copy as-is
        if hasattr(self.__class__, "_struct_asis"):
            for struct_name, attr_name in self.__class__._struct_asis.items():
                # always define attribute, even if failed to parse
                setattr(self, attr_name, getattr(self.struct, struct_name, None))

    def _parse_struct_strings(self):
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

    def _parse_struct_guids(self):
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

    def _parse_struct_blobs(self):
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

    def _parse_struct_codedindexes(self, tables, next_row):
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

    def _parse_struct_flags(self):
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

    def _parse_struct_enums(self):
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

    def _parse_struct_indexes(self, tables, next_row):
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

    def _parse_struct_lists(self, tables, next_row):
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
                            # row end index is inclusive so row end index must equal next row index minus 1, if less than max row
                            run_end_index = min(next_row_reference - 1, max_row)

                    else:
                        # then we read from the target table,
                        # from the row referenced by this row,
                        # until the end of the table.
                        run_end_index = max_row

                    # when this run starts at the last index,
                    # start == end and end == max_row.
                    # otherwise, if start == end, then run is empty.
                    if run_start_index <= run_end_index:
                        # row indexes are inclusive, so our range goes to end+1
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


# Computing this for each class takes some time, especially if it is done for every row,
# but it *should* remain consistent for any given class and therefore can be cached.
@_functools.lru_cache(None)
def _row_class_struct_attrs(cls: Type[MDTableRow]):
    """Retrieve all possible attributes for a `MDTableRow` class,
    along with their associated struct type.

    Attributes are separated based on whether they can be loaded without data from
    any other tables.
    """
    attrs = {
        attr[0] if isinstance(attr, tuple) else attr: struct
        for struct in MDTableRow.CLASS_ATTRS
        for _, attr in getattr(cls, struct, {}).items()
    }
    attrs_tables = {
        attr[0] if isinstance(attr, tuple) else attr: struct
        for struct in MDTableRow.CLASS_ATTRS_TABLES
        for _, attr in getattr(cls, struct, {}).items()
    }
    return attrs, attrs_tables


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
    file_offset: int
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
        lazy_load=False
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

        self._loaded = LoadState.Unloaded

        # default value
        self.rva: int = 0
        self.file_offset = 0

        num_rows = tables_rowcounts[self.number]
        if num_rows is None:
            # the table doesn't exist, so create the instance, but with zero rows.
            num_rows = 0

        self.is_sorted: bool = is_sorted
        self.num_rows: int = num_rows

        def init_row():
            return self._row_class(
                tables_rowcounts,
                strings_offset_size,
                guid_offset_size,
                blob_offset_size,
                strings_heap,
                guid_heap,
                blob_heap,
            )

        self.rows: List[RowType]
        if lazy_load and num_rows > 0:
            self.rows = _LazyList(self._lazy_parse_rows, num_rows)
            try:
                # `_get_row_size` uses the size of the first row.
                self.rows[0] = init_row()
            except errors.dnFormatError:
                logger.warning("failed to construct %s row %d", self.name, 0)
                # "truncate" the list since the following data is assumed invalid.
                self.rows = []
        else:
            self.rows = []
            for e in range(num_rows):
                try:
                    self.rows.append(init_row())
                except errors.dnFormatError:
                    # this may occur when the offset to a stream is too large.
                    # this probably means invalid data.
                    logger.warning("failed to construct %s row %d", self.name, e)

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

    def setup_lazy_load(self, table_rva: int, data: bytes, full_loader):
        """Mark this table for lazy-loading.

        `full_loader` will be called if a row property is requested that requires
        loading all mdtables before it can be parsed.
        """
        if not self._loaded == LoadState.Unloaded:
            return
        self.rva = table_rva
        self._table_data = data
        self._full_loader = full_loader
        if len(data) < self.row_size * self.num_rows:
            logger.warning("not enough data to parse %d rows", self.num_rows)
        self._loaded = LoadState.LazyLoaded

    def _lazy_parse_row(self, row, idx):
        """If the row has not been loaded, return a new lazy-loaded row initialized
        with the proper data for the row index.
        """
        if row and row._loaded != LoadState.Unloaded:
            return row

        try:
            row = self._row_class(
                self._tables_rowcounts,
                self._strings_offset_size,
                self._guid_offset_size,
                self._blob_offset_size,
                self._strings_heap,
                self._guid_heap,
                self._blob_heap,
            )
        except errors.dnFormatError:
            # this may occur when the offset to a stream is too large.
            # this probably means invalid data.
            logger.warning("failed to construct %s row %d", self.name, idx)
            # truncate the row list to the current index since the following data is
            # assumed invalid.
            assert isinstance(self.rows, _LazyList)
            self.rows.truncate(idx)
            return None

        row.setup_lazy_load(self._full_loader)
        offset = self.row_size * idx
        if len(self._table_data) < offset + self.row_size:
            logger.warning("not enough data to parse row %d", idx)
            # we could truncate here as well, but regular loading would still be
            # left with a full-length list in the equivalent situation.
            return row
        row.set_data(self._table_data[offset:offset + self.row_size], file_offset=self.file_offset + offset)
        return row

    def _lazy_parse_rows(self, key, row):
        """Convenience function to handle both indexing and slicing of the LazyList."""
        # Guard if called before setup_lazy_load()
        if self._loaded != LoadState.LazyLoaded:
            return row

        if isinstance(key, slice):
            # normally not knowing the length of the list a slice was taken from
            # would be an issue, but we can just keep going until `row` is exhausted.
            return [
                self._lazy_parse_row(row, i)
                for row, i in zip(row, _itertools.count(key.start or 0, key.step or 1))
            ]

        return self._lazy_parse_row(row, key)

    def parse_rows(self, table_rva: int, data: bytes):
        """
        Given a byte sequence containing the rows, add data to each row in the
        self.rows list.  Note that the rows have not been fully parsed until
        parse() is called, which should not happen until all tables have been
        initialized and parse_rows() called on each.
        """
        if self._loaded == LoadState.LazyLoaded:
            # will be handled by lazy evaluation during parse()
            return

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
                data[offset:offset + self.row_size], file_offset=self.file_offset + offset
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
        self._loaded = LoadState.Loaded

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


class DateTimeStruct(Structure):
    Ticks: int
    Kind: int


class DateTime(object):
    struct: Optional[DateTimeStruct]
    kind: Optional[enums.DateTimeKind]
    value: Optional[datetime.datetime]
    seconds: Optional[int]
    __data__: bytes

    def __init__(self, raw_bytes: bytes, rva: Optional[int] = None):
        self.struct: Optional[DateTimeStruct] = None
        self.kind: Optional[enums.DateTimeKind] = None
        self.value: Optional[datetime.datetime] = None
        self.seconds: Optional[int] = None
        self.__data__: bytes = raw_bytes
        self.rva: Optional[int] = rva

    def parse(self):
        if not self.__data__:
            # TODO: warn/error
            return
        # Should be 64 bits
        if len(self.__data__) != 8:
            # TODO: warn/error
            return
        x = _struct.unpack("<q", self.__data__)[0]
        self.struct = DateTimeStruct()
        self.struct.Ticks = x & 0x3FFFFFFFFFFFFFFF
        # Value is stored in lower 62-bits
        # https://github.com/dotnet/runtime/blob/17c55f1/src/libraries/System.Private.CoreLib/src/System/DateTime.cs#L130-L138
        self.struct.Kind = x >> 62
        # https://stackoverflow.com/questions/3169517/python-c-sharp-binary-datetime-encoding
        self.Seconds = self.struct.Ticks / 10.0 ** 7
        self.Kind = enums.DateTimeKind(self.struct.Kind)
        delta = datetime.timedelta(seconds=self.Seconds)
        if self.Kind == enums.DateTimeKind.Utc:
            self.value = datetime.datetime(1, 1, 1, 0, 0, 0, 0, datetime.timezone.utc) + delta
        else:
            self.value = datetime.datetime(1, 1, 1, 0, 0, 0, 0) + delta

    def __str__(self) -> str:
        return str(self.value)

    def to_datetime(self) -> Optional[datetime.datetime]:
        return self.value
