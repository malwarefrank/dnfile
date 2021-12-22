#!/usr/bin/python3
#
# References:
#   https://ntcore.com/files/manifestres.htm

import hashlib
from typing import List, Optional

import magic
from pefile import Structure

from . import base, utils, errors, mdtable


RESOURCE_MAGIC = 0xbeefcace
CLR_RESOURCE_TYPESTR = "Mono/.Net resource"


class ClrResourceEntry(object):
    Type: Optional[bytes]
    Hash: Optional[int]
    Name: Optional[bytes]
    NamePtr: Optional[int]
    DataOffset: Optional[int]
    data: Optional[bytes]

    def __init__(self):
        self.Type = None
        self.Hash = None
        self.Name = None
        self.NamePtr = None
        self.DataOffset = None
        self.data = None


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
    entries: List[ClrResourceEntry]
    resource_types: List[bytes]

    _format = [
        "IMAGE_CLR_RESOURCE",
        [
            "I,Magic",
            "I,NumberOfReaders",
            "I,SizeOfReaderTypes",
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
        self.entries: List[ClrResourceEntry] = list()
        self.resource_types: List[bytes] = list()
        self.struct = None

    def valid(self):
        if len(self._data) < self._valid_size:
            # if not enough data
            return False
        # read magic value
        i4 = int.from_bytes(self._data[:4], byteorder="little")
        # if not expected
        if i4 != RESOURCE_MAGIC:
            # invalid
            return False
        return True

    def parse(self):
        # parse initial structure
        tmp_struct = ClrResourceStruct(format=self.__class__._format)
        tmp_struct.__unpack__(self._data)
        # calculate and add additional fields
        self._format[1].append("{}s,ReaderTypes".format(tmp_struct.SizeOfReaderTypes))
        self._format[1].append("I,Version")
        self._format[1].append("I,NumberOfResources")
        self._format[1].append("I,NumberOfResourceTypes")
        # parse more
        self.struct = ClrResourceStruct(format=self._format)
        self.struct.__unpack__(self._data)
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
            e = ClrResourceEntry()
            e.Hash = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            self.entries.append(e)
            # next
            offset += 4
        for e in self.entries:
            e.NamePtr = int.from_bytes(self._data[offset:offset+4], byteorder="little")
            # next
            offset += 4
        self.struct.DataSectionOffset = int.from_bytes(self._data[offset:offset+4], byteorder="little")
        offset += 4
        self.table_of_names_offset = offset
        for e in self.entries:
            offset = self.table_of_names_offset + e.NamePtr
            x = utils.read_compressed_int(self._data[offset:offset+4])
            if x is None:
                # TODO warn/error
                return
            size = x[0]
            offset += x[1]
            e.Name = self._data[offset:offset+size]
            offset += size
            e.DataOffset = int.from_bytes(self._data[offset:offset+4], byteorder="little")


class ResourceData(object):
    data: bytes
    size: int
    sha256: Optional[str]
    sha1: Optional[str]
    md5: Optional[str]
    magic: Optional[str]
    clr_resource: Optional[ClrResource]

    def __init__(self, rva: int, data: bytes):
        self._rva = rva
        self.data = data
        self.size = len(data)
        if data:
            self.sha256 = hashlib.sha256(data).hexdigest()
            self.sha1 = hashlib.sha1(data).hexdigest()
            self.md5 = hashlib.md5(data).hexdigest()
            rsrc = ClrResource(data)
            if rsrc.valid():
                self.magic = CLR_RESOURCE_TYPESTR
                self.clr_resource = rsrc
            else:
                self.magic = magic.from_buffer(data)
        else:
            self.magic = None
            self.sha256 = None
            self.sha1 = None
            self.md5 = None
            self.clr_resource = None

    def parse(self):
        if self.clr_resource:
            self.clr_resource.parse()
            for entry in self.clr_resource.entries:
                offset = self.clr_resource.struct.DataSectionOffset + entry.DataOffset
                entry.Type = self.data[offset]
                offset += 1
                x = utils.read_compressed_int(self.data[offset:offset+4])
                if x is None:
                    # TODO warn/error
                    return
                size = x[0]
                offset += x[1]
                entry.data = self.data[offset:offset+size]
