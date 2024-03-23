#!/usr/bin/env python3
#
# Iterate UserStrings and display one per line.

import sys

import dnfile


def show_strings(fname):
    # parse .NET executable
    dn = dnfile.dnPE(fname)
    # if no CLR data found, do nothing
    if not hasattr(dn, "net"):
        return

    # get the (first) UserStrings stream
    us: dnfile.stream.UserStringHeap = dn.net.metadata.streams.get(b"#US", None)
    if us:
        # get size of the stream
        size = us.sizeof()
        # First entry (first byte in stream) is empty string, so skip it
        offset = 1
        # while there is still data in the stream
        while offset < size:
            # check if we are at padding bytes near end of stream
            if offset + 4 >= size:
                if b"\x00" == dn.get_data(us.rva + offset, 1):
                    break
            # read the raw string bytes, and provide number of bytes read (includes encoded length)
            item = us.get(offset)
            if item is None:
                print(f"Bad string: offset=0x{offset:08x}")
                break

            if item.value is None:
                print(f"Bad string: {item.raw_data}")
            else:
                # display the decoded string
                print(item.value)
            # continue to next entry
            offset += item.raw_size


# for each filepath provided on command-line
for fname in sys.argv[1:]:
    show_strings(fname)
