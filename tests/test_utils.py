# -*- coding: utf-8 -*-
import dnfile.utils


def test_compressed_int():
    assert None is dnfile.utils.read_compressed_int(b"")
    assert None is dnfile.utils.read_compressed_int(None)

    assert 0x7f, 1 == dnfile.utils.read_compressed_int(b"\x7f")
    assert 0x3f8f, 2 == dnfile.utils.read_compressed_int(b"\xbf\x8f")
    assert 0x1eadbeef, 4 == dnfile.utils.read_compressed_int(b"\xde\xad\xbe\xef")


def test_struct_char():
    assert None is dnfile.utils.num_bytes_to_struct_char(42)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(8)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(5)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(4)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(3)
    assert "H" == dnfile.utils.num_bytes_to_struct_char(2)
    assert "B" == dnfile.utils.num_bytes_to_struct_char(1)
    assert None is dnfile.utils.num_bytes_to_struct_char(0)
