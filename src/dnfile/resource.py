#!/usr/bin/python3
#
# References:
#   https://ntcore.com/files/manifestres.htm

import hashlib
from typing import Optional, List

import magic
from pefile import Structure

from . import base, errors, mdtable, utils

RESOURCE_MAGIC = 0xbeefcace

"""
rva base of resources from pe.net.struct.ResourcesRva
offset of resource

every Manifest Resource begins with a dword that tells us the size of the actual embedded resource... And that's it... After that, we have our bitmap, zip, PE, .resources file, etc

if it's a ".resources file" - first dword is size, second is signature 0xBEEFCACE (or else it is invalid).  Third dword is number of readers (framework stuff).  Fourth dword is size of reader types, which tells the framework the reader to use for this resources file.  Next dword is version of resources file (e.g. 1 or 2).  Next dword is number of resources.  Next dword is number of resource types.

For each type, there is a 7bit encoded integer that gives size of following string (like #US stream).
Then align to 8-byte base.
Then several dwords (NumberOfResources of them), each containing the hash of a resource.
Then same number of dwords, each containing the offsets of the resource names.
Then dword which is the Data Section Offset.
Then resource names: 7bit encoded integer + unicode string + dword (offset from DataSection to resource data, where data starts with 7bit encoded integer which is type index for the resource)

"""


class ClrResourceEntry(object):
    Type: Optional[bytes]
    Hash: Optional[int]
    Name: Optional[bytes]
    NamePtr: Optional[int]
    DataOffset: Optional[int]

    def __init__(self):
        self.Type = None
        self.Hash = None
        self.Name = None
        self.NamePtr = None
        self.DataOffset = None


class ClrResourceStruct(Structure):
    Magic: int
    NumberOfReaders: int
    SizeOfReaderTypes: int
    ReaderTypes: bytes
    Version: int
    NumberOfResources: int
    NumberOfResourceTypes: int
    DataSectionOffset: int


class ClrResource(object):
    struct: Optional[ClrResourceStruct]
    resources: List[ClrResourceEntry]
    resource_types: List[bytes]

    _format = [
        "IMAGE_CLR_RESOURCE",
        [
            "<I,Magic",
            "<I,NumberOfReaders",
            "<I,SizeOfReaderTypes",
            # reader types string
            # version
            # NumberOfResources
            # NumberOfResourceTypes
            # for x in range(NumberOfResourceTypes)
            #   compressed_int, type_string[compressed_int]
            # align to 8-byte boundary
            # for x in range(NumberOfResources)
            #   read dword (hash)
            # for x in range(NumberOfResources)
            #   read dword (resource name pointer)
            # dword (data section offset)
            # table_of_names = current offset
            # for x in range(NumberOfResources)
            #   get resource name pointer, goto table_of_names + pointer
            #   read compressed_int, resource_name, dword (data offset)
            # if data_offset == 0, then resource data = data[data_section_offset+1 : data_section_offset+1+4]
            # else, 
        ],
    ]

    def __init__(self, data: bytes):
        self._data = data
        self._valid_size = ClrResourceStruct(self._format).sizeof() + 3*4
        self.resources: List[ClrResourceEntry] = list()
        self.resource_types: List[bytes] = list()
        self.struct = None

    def valid(self):
        if len(self._data) < self._valid_size:
            # if not enough data
            return False
        # read magic value
        i4 = int.from_bytes(data[:4], byteorder="little")
        # if not expected
        if i4 != RESOURCE_MAGIC:
            # invalid
            return False
        return True

    def parse(self):
        # parse initial structure
        tmp_struct = ClrResourceStruct(format=self.__class__._format)
        tmp_struct.__unpack__(data)
        # calculate and add additional fields
        self._format[1].append("{}s,ReaderTypes".format(tmp_struct.SizeOfReaderTypes))
        self._format[1].append("<I,Version")
        self._format[1].append("<I,NumberOfResources")
        self._format[1].append("<I,NumberOfResourceTypes")
        # parse more
        self.struct = ClrResourceStruct(format=self._format)
        # keep track of current data offset
        offset = self.struct.sizeof()
        # embedded resources
        for i in range(self.struct.NumberOfResourceTypes):
            # read string length
            x = utils.read_compressed_int(self._data[offset:offset+4])
            if x is None:
                # TODO warn/error
                return
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
            r = ClrResourceEntry()
            r.Hash = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            self.resources.append(r)
            # next
            offset += 4
        for r in self.resources:
            r.NamePtr = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            # next
            offset += 4
        self.struct.DataSectionOffset = int.from_bytes(self._data[offset:offset+4], byteorder="little")
        offset += 4
        self.table_of_names_offset = offset
        for r in self.resources:
            x = utils.read_compressed_int(self._data[offset:offset+4])
            if x is None:
                # TODO warn/error
                return
            size = x[0]
            offset += x[1]
            r.Name = self._data[offset:offset+size]
            offset += size
            r.DataOffset = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            offset += 4


class ManifestResource(object):
    data: bytes
    size: int
    resources: List[ClrResource]
    sha256: Optional[str]
    sha1: Optional[str]
    md5: Optional[str]
    magic: Optional[str]

    def __init__(self, rva: int, data: bytes):
        self._rva = rva
        self.data = data
        self.size = len(data)
        self.resources: List[ClrResource] = list()
        if data:
            self.sha256 = hashlib.sha256(data).hexdigest()
            self.sha1 = hashlib.sha1(data).hexdigest()
            self.md5 = hashlib.md5(data).hexdigest()
            rsrc = ClrResource(data)
            if rsrc.valid():
                self.magic = "Mono/.Net resource"
                self.resources.append(rsrc)
            else:
                self.magic = magic.from_buffer(data)
        else:
            self.magic = None
            self.sha256 = None
            self.sha1 = None
            self.md5 = None

    def parse(self):
        for rsrc in self.resources:
            rsrc.parse()
