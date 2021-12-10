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
    us: dnfile.stream.UserStringHeap = dn.net.metadata.streams.get("#US", None)
    if us:
        # get size of the stream
        size = us.sizeof()
        # First entry (first byte in stream) is empty string, so skip it
        offset = 1
        # while there is still data in the stream
        while offset < size:
            # read the raw string bytes, and provide number of bytes read (includes encoded length)
            buf, readlen = us.get_with_size(offset)
            # convert to a UserString object
            s = dnfile.stream.UserString(buf)
            # display the decoded string
            print(s.value)
            # continue to next entry
            offset += readlen


# for each filepath provided on command-line
for fname in sys.argv[1:]:
    show_strings(fname)
