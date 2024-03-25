#!/usr/bin/env python3
#
# Iterate GUIDs and display one per line.

import sys

import dnfile


def show_guids(fname):
    # parse .NET executable
    dn = dnfile.dnPE(fname, clr_lazy_load=True)
    # if no CLR data found, do nothing
    if not hasattr(dn, "net"):
        return

    # get the (first) GUID stream
    g: dnfile.stream.GuidHeap = dn.net.metadata.streams.get(b"#GUID", None)
    if g:
        # get size of the stream
        size = g.sizeof() // 16
        print(f"INFO: size={size}")
        offset = 1
        # while there is still data in the stream
        while offset <= size:
            # read the guid
            item = g.get(offset)
            if item is None:
                rva = g.rva + (offset * 16)
                print(f"Bad GUID: rva=0x{rva:08x}")
                break

            print(item)
            # continue to next entry
            offset += 1


# for each filepath provided on command-line
for fname in sys.argv[1:]:
    show_guids(fname)
