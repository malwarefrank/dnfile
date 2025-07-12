# -*- coding: utf-8 -*-
"""
dnfile, .NET Executable file parser


REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html
    https://asmresolver.readthedocs.io/en/latest/peimage/dotnet.html#metadata-streams


Copyright (c) 2020-2022 MalwareFrank
"""

__author__ = """MalwareFrank"""
__version__ = "0.16.4"

import copy as _copymod
import codecs
import struct as _struct
import logging
from typing import Dict, List, Optional

from pefile import PE as _PE
from pefile import DIRECTORY_ENTRY, MAX_SYMBOL_EXPORT_COUNT, Dump, Structure, DataContainer, PEFormatError

from . import base, enums, errors, stream, resource

logger = logging.getLogger(__name__)
CLR_METADATA_SIGNATURE = 0x424A5342


# These come from the great article[1] which contains great insights on
# working with unicode in both Python 2 and 3.
# [1]: http://python3porting.com/problems.html
def handler(err):
    start = err.start
    end = err.end
    values = [
        ("\\u{0:04x}" if ord(err.object[i]) > 255 else "\\x{0:02x}", ord(err.object[i]))
        for i in range(start, end)
    ]
    return (u"".join([elm[0].format(elm[1]) for elm in values]), end)


codecs.register_error("backslashreplace_", handler)


class dnPE(_PE):
    def add_warning(self, msg):
        self._warnings.append(msg)

    def __init__(
        self,
        name=None,
        data=None,
        fast_load=None,
        max_symbol_exports=MAX_SYMBOL_EXPORT_COUNT,
        clr_lazy_load=False,
    ):
        self._warnings = list()
        self.clr_lazy_load = clr_lazy_load
        super().__init__(name, data, fast_load)

    def dump_info(self, dump=None, encoding="utf-8"):
        """
        Dump all the PE and CLR header information into human readable string.
        """
        if dump is None:
            dump = Dump()

        super().dump_info(dump, encoding)

        if not hasattr(self, "net") or not self.net:
            return dump.get_text()

        #### CLR
        # directory entry
        dump.add_header("CLR (.NET)")
        dump.add_lines(self.net.struct.dump())
        dump.add_newline()

        # metadata
        if hasattr(self.net, "metadata") and self.net.metadata:
            dump.add_lines(self.net.metadata.struct.dump(), indent=2)
            dump.add_newline()
            # Streams
            if (
                hasattr(self.net.metadata, "streams_list")
                and self.net.metadata.streams_list
            ):
                for stream_ in self.net.metadata.streams_list:
                    dump.add_lines(stream_.struct.dump(), indent=4)
                    dump.add_newline()

        # Metadata Tables
        if hasattr(self.net, "mdtables") and self.net.mdtables:
            dump.add_header("CLR (.NET) Metadata Tables")
            for s in self.net.metadata.streams_list:
                if isinstance(s, stream.MetaDataTables):
                    s: stream.MetaDataTables
                    dump.add_lines(s.struct.dump())
                    dump.add_newline()
                    if hasattr(s, "tables_list") and s.tables_list:
                        for t in s.tables_list:
                            for label, value in (
                                ("RVA", hex(t.rva)),
                                ("TableName", t.name),
                                ("TableNumber", t.number),
                                ("IsSorted", t.is_sorted),
                                ("NumRows", t.num_rows),
                                ("RowSize", t.row_size),
                            ):
                                dump.add_line(
                                    "{0:<20}{1}".format(label  + ":", str(value)),
                                    indent=2,
                                )
                            dump.add_newline()

        return dump.get_text()

    def get_warnings(self):
        """
        Returns a copy of the list of warning messages.
        """
        result = _copymod.deepcopy(super().get_warnings())
        result.extend(self._warnings)
        return result

    def __parse__(self, fname, data, fast_load):
        super().__parse__(fname, data, fast_load)

        # NOTE: .NET loaders ignores NumberOfRvaAndSizes
        #   We check this elsewhere, but note it here.
        #   example: 1d41308bf4148b4c138f9307abc696a6e4c05a5a89ddeb8926317685abb1c241

    def parse_data_directories(
        self, directories=None, forwarded_exports_only=False, import_dllnames_only=False
    ):
        super().parse_data_directories(
            directories, forwarded_exports_only, import_dllnames_only
        )

        directory_parsing = (
            ("IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR", self.parse_clr_structure),
        )

        # Indicate no .NET object parsed
        self.net = None

        if self.__data__ is None:
            logger.warning("not a .NET module: failed to read data")
            return

        opt_header = getattr(self, "OPTIONAL_HEADER", None)
        if opt_header is None:
            logger.warning("not a .NET module: no optional header")
            return

        if directories is not None:
            if not isinstance(directories, (tuple, list)):
                directories = [directories]

        for entry in directory_parsing:
            try:
                directory_index = DIRECTORY_ENTRY[entry[0]]
                dir_entry = opt_header.DATA_DIRECTORY[directory_index]
            except IndexError:
                break

            # Only process all the directories if no individual ones have
            # been chosen
            #
            if directories is None or directory_index in directories:

                if dir_entry.VirtualAddress:
                    value = entry[1](dir_entry.VirtualAddress, dir_entry.Size)
                    if value:
                        setattr(self, entry[0][6:], value)
                        if entry[0] == "IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR":
                            # create shortcut for .NET/CLR data
                            self.net = value

            if (
                (directories is not None)
                and isinstance(directories, list)
                and (entry[0] in directories)
            ):
                directories.remove(directory_index)

        # NOTE: .NET loaders ignores NumberOfRvaAndSizes, so attempt to parse anyways
        #   example: 1d41308bf4148b4c138f9307abc696a6e4c05a5a89ddeb8926317685abb1c241
        attr_name = "DIRECTORY_ENTRY_COM_DESCRIPTOR"
        if not hasattr(self, attr_name):
            dir_entry_size = Structure(self.__IMAGE_DATA_DIRECTORY_format__).sizeof()
            dd_offset = (
                opt_header.get_file_offset() + opt_header.sizeof()
            )
            clr_entry_offset = dd_offset + (
                DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"] * dir_entry_size
            )
            data = self.__data__[clr_entry_offset:clr_entry_offset + dir_entry_size]
            dir_entry = self.__unpack_data__(
                self.__IMAGE_DATA_DIRECTORY_format__, data, file_offset=clr_entry_offset
            )

            # if COM entry appears valid
            if dir_entry is not None and dir_entry.VirtualAddress:
                # try to parse the .NET CLR directory
                value = self.parse_clr_structure(
                    dir_entry.VirtualAddress, dir_entry.Size
                )
                if value:
                    setattr(self, attr_name, value)
                    # create shortcut for .NET/CLR data
                    self.net = value

    def parse_clr_structure(self, rva, size) -> Optional["ClrData"]:
        try:
            return ClrData(self, rva, size, self.clr_lazy_load)
        except errors.dnFormatError as e:
            logger.warning("failed to parse CLR data: %s",  e)
            return None


class ClrMetaDataStruct(Structure):
    Signature: int
    MajorVersion: int
    MinorVersion: int
    Reserved: int
    VersionLength: int
    Version: bytes
    Flags: int
    NumberOfStreams: int


class ClrMetaData(DataContainer):
    """Holds CLR (.NET) MetaData.

    struct:         IMAGE_CLR_METADATA structure
    streams:        Dictionary to access streams by name (bytes)
    streams_list:   List of streams in order of entry in header
    """

    rva: int
    struct: ClrMetaDataStruct
    streams: Dict[bytes, base.ClrStream]
    streams_list: List[base.ClrStream]

    _format = (
        "IMAGE_CLR_METADATA",
        [
            "I,Signature",
            "H,MajorVersion",
            "H,MinorVersion",
            "I,Reserved",
            "I,VersionLength",
            # '?,Version',
            # 'H,Flags',
            # 'H,NumberOfStreams',
        ],
    )
    #### MetaData section
    #
    # dd    Signature
    # dw    MajorVersion
    # dw    MinorVersion
    # dd    Reserved
    # dd    Length
    # var   Version
    # dw    Flags
    # dw    NumberOfStreams
    # var   StreamHeaders

    def __init__(self, pe: dnPE, rva: int, size: int, lazy_load=False):
        """
        Given a dnPE object, MetaData RVA and MetaData Size.
        Raises dnFormatError if encounter problems parsing.
        """
        metadata_rva = rva

        # The metadata RVA, used for stream offsets
        self.rva = rva

        # dynamically create metadata header structure
        struct_format = _copymod.deepcopy(self.__class__._format)
        struct_data = pe.get_data(rva, size)
        if len(struct_data) < size:
            raise errors.dnFormatError(
                "Invalid CLR MetaData Structure size. Can't read %d "
                "bytes at RVA: 0x%x" % (size, rva)
            )
        # check signature
        sig = _struct.unpack_from("<I", struct_data)[0]
        if sig != CLR_METADATA_SIGNATURE:
            raise errors.dnFormatError(
                "Invalid CLR MetaData Signature at 0x%x. Expected 0x%x but "
                "got 0x%x" % (rva, CLR_METADATA_SIGNATURE, sig)
            )
        # parse struct so that we can get the version length
        metadata_struct = ClrMetaDataStruct(
            format=struct_format,
            file_offset=pe.get_offset_from_rva(metadata_rva)
        )
        metadata_struct.__unpack__(struct_data)
        # metadata_struct = pe.__unpack_data__(
        #     struct_format, struct_data, pe.get_offset_from_rva(metadata_rva)
        # )
        # add variable-length version field
        if metadata_struct.VersionLength > 0:
            struct_format[1].append(
                "{0}s,Version".format(metadata_struct.VersionLength)
            )
        # add Flags
        struct_format[1].append("H,Flags")
        # add NumberOfStreams
        struct_format[1].append("H,NumberOfStreams")

        # re-parse metadata header structure
        metadata_struct = ClrMetaDataStruct(
            format=struct_format,
            file_offset=pe.get_offset_from_rva(metadata_rva)
        )
        struct_size = metadata_struct.sizeof()
        struct_data = pe.get_data(metadata_rva, struct_size)
        if len(struct_data) < struct_size:
            raise errors.dnFormatError(
                "unable to read full CLR metadata structure, expected {} got {}".format(
                    struct_size, len(struct_data)
                )
            )
        metadata_struct.__unpack__(struct_data)

        self.struct = metadata_struct

        if metadata_struct.NumberOfStreams > 0:
            # parse the streams table
            streams_table_rva = metadata_rva + struct_size
            self.parse_stream_table(pe, streams_table_rva)

            # parse each stream
            for s in self.streams_list:
                try:
                    s.parse(self.streams_list, lazy_load=lazy_load)
                except (errors.dnFormatError, PEFormatError) as e:
                    # other streams may parse, so add to warnings and continue
                    pe.add_warning("Unable to parse stream {!r}".format(s.struct.Name))
                    pe.add_warning(str(e))
                    logger.warning("unable to parse stream: %s: %s", s.struct.Name, e)

    def parse_stream_table(self, pe: dnPE, streams_table_rva):
        streams_list = list()
        streams_dict = dict()
        # pointer to current stream's table entry
        stream_entry_rva = streams_table_rva
        for i in range(self.struct.NumberOfStreams):
            stream = ClrStreamFactory.createStream(pe, stream_entry_rva, self.rva)
            if not stream:
                logger.warning("Invalid .NET stream: {}".format(i + 1))
                pe.add_warning("Invalid .NET stream: {}".format(i + 1))
                # assume this throws off further parsing, so stop
                break

            streams_list.append(stream)
            name = stream.struct.Name
            if name in streams_dict:
                # if a stream with this name already exists.
                # this is not fatal, just unusual.
                pe.add_warning("Duplicate .NET stream name '{!r}'".format(name))
                logger.warning("Duplicate .NET stream name: %s", name)

            # dotnet uses the last encountered stream with a given name,
            # see: https://github.com/malwarefrank/dnfile/issues/19#issuecomment-992754448
            # and test_invalid_streams.py::test_duplicate_stream
            streams_dict[name] = stream
            # move to next entry in streams table
            stream_entry_rva += stream.stream_table_entry_size()

        self.streams = streams_dict
        self.streams_list = streams_list


class ClrStruct(Structure):
    cb: int
    MajorRuntimeVersion: int
    MinorRuntimeVersion: int
    MetaDataRva: int
    MetaDataSize: int
    Flags: int
    EntryPointTokenOrRva: int
    ResourcesRva: int
    ResourcesSize: int
    StrongNameSignatureRva: int
    StrongNameSignatureSize: int
    CodeManagerTableRva: int
    CodeManagerTableSize: int
    VTableFixupsRva: int
    VTableFixupsSize: int
    ExportAddressTableJumpsRva: int
    ExportAddressTableJumpsSize: int
    ManagedNativeHeaderRva: int
    ManagedNativeHeaderSize: int


class ClrData(DataContainer):
    """Holds CLR (.NET) header data.

    struct:         IMAGE_NET_DIRECTORY structure
    metadata:       ClrMetaData or None
    strings:        stream.StringsHeap or None
    user_strings:   stream.UserStringsHeap or None
    guids:          stream.GuidHeap or None
    blobs:          stream.BlobHeap or None
    mdtables:       stream.MetaDataTables or None
    Flags:          enums.ClrHeaderFlags or None
    """

    struct: ClrStruct
    metadata: Optional[ClrMetaData]
    strings: Optional[stream.StringsHeap]
    user_strings: Optional[stream.UserStringHeap]
    guids: Optional[stream.GuidHeap]
    blobs: Optional[stream.BlobHeap]
    mdtables: Optional[stream.MetaDataTables]
    Flags: Optional[enums.ClrHeaderFlags]

    _resources: Optional[List[base.ClrResource]]

    @property
    def resources(self) -> List[base.ClrResource]:
        if self._resources is None:
            self._init_resources(getattr(self, "_pe"))
            assert self._resources is not None
        return self._resources

    # Structure description from:
    # http://www.ntcore.com/files/dotnetformat.htm
    _format = (
        "IMAGE_NET_DIRECTORY",
        (
            "I,cb",
            "H,MajorRuntimeVersion",
            "H,MinorRuntimeVersion",
            "I,MetaDataRva",
            "I,MetaDataSize",
            "I,Flags",
            "I,EntryPointTokenOrRva",
            "I,ResourcesRva",
            "I,ResourcesSize",
            "I,StrongNameSignatureRva",
            "I,StrongNameSignatureSize",
            "I,CodeManagerTableRva",
            "I,CodeManagerTableSize",
            "I,VTableFixupsRva",
            "I,VTableFixupsSize",
            "I,ExportAddressTableJumpsRva",
            "I,ExportAddressTableJumpsSize",
            "I,ManagedNativeHeaderRva",
            "I,ManagedNativeHeaderSize",
        ),
    )

    def __init__(self, pe: dnPE, rva: int, size: int, lazy_load: bool):
        """
        Given dnPE object, .NET header RVA and header size.
        Raises dnFormatError if problems parsing.
        """
        data = pe.get_data(rva, size)

        try:
            clr_struct = ClrStruct(
                self._format, file_offset=pe.get_offset_from_rva(rva)
            )
            clr_struct.__unpack__(data)
        except PEFormatError:
            # raise exception because we can't do anything halfway here.
            raise errors.dnFormatError(
                "Invalid CLR Structure information. Can't read "
                "data at RVA: 0x%x" % rva
            )

        # set structure member
        self.struct = clr_struct
        # parse metadata
        metadata_rva = clr_struct.MetaDataRva
        metadata_size = clr_struct.MetaDataSize

        # shortcuts are always defined, even if None, for easier code completion in IDEs
        self.metadata = None
        self.strings = None
        self.user_strings = None
        self.guids = None
        self.blobs = None
        self.mdtables = None
        self._resources = None
        self.Flags = None

        try:
            self.metadata = ClrMetaData(pe, metadata_rva, metadata_size, lazy_load)
        except (errors.dnFormatError, PEFormatError) as e:
            logger.warning("failed to parse .NET metadata: %s", e)
            return

        # create shortcuts for streams
        # dotnet runtime uses the last instance of a type,
        # see: https://github.com/malwarefrank/dnfile/issues/19#issuecomment-992754448
        # and test: test_invalid_streams.py::test_duplicate_stream
        for s in self.metadata.streams_list:
            if isinstance(s, stream.StringsHeap):
                self.strings = s
            elif isinstance(s, stream.UserStringHeap):
                self.user_strings = s
            elif isinstance(s, stream.GuidHeap):
                self.guids = s
            elif isinstance(s, stream.BlobHeap):
                self.blobs = s
            elif isinstance(s, stream.MetaDataTables):
                self.mdtables: stream.MetaDataTables = s

        # Set the flags according to the Flags member
        flags_object = enums.ClrHeaderFlags(clr_struct.Flags)
        self.Flags = flags_object

        if not lazy_load:
            self._init_resources(pe)
        else:
            # store the dnPE reference for lazy-loading
            setattr(self, "_pe", pe)

    def _init_resources(self, pe):
        """Parse and initialize assembly resources.

        This is separate from `ClrData.__init__` to allow for mdtable lazy-loading since
        parsing `ManifestResourceRow.Implementation` requires all tables to be loaded.
        """
        self._resources = []
        # parse the resources
        if self.struct.ResourcesRva > 0 and self.mdtables and self.mdtables.ManifestResource and self.mdtables.ManifestResource.num_rows > 0:
            # for each row
            for row in self.mdtables.ManifestResource.rows:
                # TODO: handle external resources
                if row.Implementation is None:
                    # internal resource, embedded in this file
                    rva = self.struct.ResourcesRva + row.Offset
                    try:
                        buf = pe.get_data(rva, 4)
                    except PEFormatError as e:
                        # warn
                        pe.add_warning("CLR resource parse error, expected more data at rva 0x{:02x}".format(rva))
                        continue
                    if not buf or len(buf) < 4:
                        # warn
                        pe.add_warning("CLR resource parse error, expected at least 4 bytes at rva 0x{:02x}".format(rva))
                        continue
                    size = int.from_bytes(buf, byteorder="little")
                    rsrc_rva = rva + 4
                    try:
                        rdata = pe.get_data(rsrc_rva, size)
                    except PEFormatError as e:
                        # warn
                        pe.add_warning("CLR resource parse error, expected more data at rva 0x{:02x}".format(rsrc_rva))
                        continue
                    if not rdata or len(rdata) < size:
                        pe.add_warning("CLR resource parse error, expected more data at rva 0x{:02x}".format(rsrc_rva))
                        continue
                    res = resource.InternalResource(row.Name, row.Flags.mrPublic, row.Flags.mrPrivate)
                    res.rva = rsrc_rva
                    res.size = size
                    res.data = rdata
                    self._resources.append(res)
            for rsrc in self._resources:
                try:
                    rsrc.parse()
                except errors.dnFormatError as e:
                    if isinstance(rsrc, resource.InternalResource):
                        pe.add_warning("CLR resource parse error for '{}' at 0x{:02x}: {}".format(rsrc.name, rsrc.rva, str(e)))
                    else:
                        pe.add_warning("CLR resource parse error for '{}': {}".format(rsrc.name, str(e)))


class ClrStreamFactory(object):
    _name_type_map = {
        b"#~": stream.MetaDataTables,
        b"#-": stream.MetaDataTables,
        b"#Schema": stream.MetaDataTables,
        b"#Strings": stream.StringsHeap,
        b"#GUID": stream.GuidHeap,
        b"#Blob": stream.BlobHeap,
        b"#US": stream.UserStringHeap,
    }
    _template_format = (
        "IMAGE_CLR_STREAM",
        [
            "I,Offset",
            "I,Size",
            # '?,Name',
        ],
    )

    @classmethod
    def createStream(
        cls, pe: dnPE, stream_entry_rva: int, metadata_rva: int
    ) -> Optional[base.ClrStream]:
        # start with structure template
        struct_format = _copymod.deepcopy(cls._template_format)
        # read name
        name = pe.get_string_at_rva(stream_entry_rva + 8)
        if name is None:
            logger.warning("failed to read stream name")
            return None

        # round field length up to next 4-byte boundary.  Remember the NULL byte at end.
        name_len = len(name) + (4 - (len(name) % 4))
        # add name field to structure
        struct_format[1].append("{0}s,Name".format(name_len))
        # parse structure
        stream_struct = base.StreamStruct(
            struct_format,
            file_offset=pe.get_offset_from_rva(stream_entry_rva)
        )
        struct_size = stream_struct.sizeof()
        struct_data = pe.get_data(stream_entry_rva, struct_size)
        stream_struct.__unpack__(struct_data)
        # remove trailing NULLs from name
        stream_struct.Name = stream_struct.Name.rstrip(b"\x00")
        stream_rva = metadata_rva + stream_struct.Offset
        stream_data = pe.get_data(
            stream_rva, stream_struct.Size
        )
        name = stream_struct.Name
        # use GenericStream for any non-standard streams
        stream_class = cls._name_type_map.get(name, stream.GenericStream)
        try:
            # construct stream, like stream.StreagsHeap ctor or GenericStream ctor
            s = stream_class(metadata_rva, stream_struct, stream_data)
            s.file_offset = pe.get_offset_from_rva(stream_rva)
        except errors.dnFormatError as e:
            logger.warning("failed to parse stream: %s", e)
            return None
        else:
            return s
