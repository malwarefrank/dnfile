#!/usr/bin/env python3

import sys
import hashlib
from binascii import hexlify

import dnfile

for fname in sys.argv[1:]:
    print("===== {}".format(fname))
    # load .NET executable
    pe = dnfile.dnPE(fname)

    w = pe.get_warnings()
    if w:
        print("WARNINGS:")
        for s in w:
            print("    {}".format(s))

    if pe.net and pe.net.resources:
        print("RESOURCES: {}".format(len(pe.net.resources)))
        for rsrc in pe.net.resources:
            print("    {0:<10} {1}".format("Name:", rsrc.name))
            print("    {0:<10} {1}".format("Public:", rsrc.public))
            print("    {0:<10} {1}".format("Private:", rsrc.private))
            if isinstance(rsrc, dnfile.resource.InternalResource):
                if isinstance(rsrc.data, bytes):
                    print("        {0:<10} {1}".format("Type:", "bytes"))
                    print("        {0:<10} {1}".format("Length:", len(rsrc.data)))
                    if rsrc.data:
                        print("        {0:<10} {1}".format("Data[:8]:", hexlify(rsrc.data[:8])))
                        print("        {0:<10} {1}".format("SHA256:", hashlib.sha256(rsrc.data).hexdigest()))
                elif isinstance(rsrc.data, dnfile.resource.ResourceSet):
                    print("        {0:<10} {1}".format("Type:", "resource set"))
                    print("        {0:<10} {1}".format("Length:", rsrc.data.struct.NumberOfResources))
                    if rsrc.data.entries:
                        for entry in rsrc.data.entries:
                            print("        RESOURCE ENTRY:")
                            print("            {0:<10} {1}".format("Name:  ", entry.name))
                            other = dict()
                            if entry.data:
                                dlen = len(entry.data)
                                other["Data[:8]:"] = hexlify(entry.data[:8])
                                other["SHA256:"] = hashlib.sha256(entry.data).hexdigest()
                            else:
                                dlen = 0
                            print("            {0:<10} {1}".format("Length:", dlen))
                            if other:
                                for k, v in other.items():
                                    print("            {0:<10} {1}".format(k, v))
