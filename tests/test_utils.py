# -*- coding: utf-8 -*-
import dnfile.utils


def test_compressed_int():
    assert None is dnfile.utils.read_compressed_int(b"")
    assert None is dnfile.utils.read_compressed_int(None)

    assert 0x7f, 1 == dnfile.utils.read_compressed_int(b"\x7f")
    assert 0x3f8f, 2 == dnfile.utils.read_compressed_int(b"\xbf\x8f")
    assert 0x1eadbeef, 4 == dnfile.utils.read_compressed_int(b"\xde\xad\xbe\xef")

    # these are the tests from
    # spec ECMA-335 II.23.2 Blobs and signatures.
    assert 0x03, 1 == dnfile.utils.read_compressed_int(b"\x03")
    assert 0x7F, 1 == dnfile.utils.read_compressed_int(b"\x7F")
    assert 0x80, 2 == dnfile.utils.read_compressed_int(b"\x80\x80")
    assert 0x2E57, 2 == dnfile.utils.read_compressed_int(b"\xAE\x57")
    assert 0x3FFF, 2 == dnfile.utils.read_compressed_int(b"\xBF\xFF")
    assert 0x4000, 4 == dnfile.utils.read_compressed_int(b"\xC0\x00\x40\x00")
    assert 0x1FFFFFFF, 4 == dnfile.utils.read_compressed_int(b"\xDF\xFF\xFF\xFF")

    assert 3, 1 == dnfile.utils.read_compressed_int(b"\x06", signed=True)
    assert -3, 1 == dnfile.utils.read_compressed_int(b"\x7B", signed=True)
    assert 64, 2 == dnfile.utils.read_compressed_int(b"\x80\x80", signed=True)
    assert -64, 1 == dnfile.utils.read_compressed_int(b"\x01", signed=True)
    assert 8192, 4 == dnfile.utils.read_compressed_int(b"\xC0\x00\x40\x00", signed=True)
    assert -8192, 2 == dnfile.utils.read_compressed_int(b"\x80\x01", signed=True)
    assert 268435455, 4 == dnfile.utils.read_compressed_int(b"\xDF\xFF\xFF\xFE", signed=True)
    assert -268435456, 4 == dnfile.utils.read_compressed_int(b"\xC0\x00\x00\x01", signed=True)


def test_struct_char():
    assert None is dnfile.utils.num_bytes_to_struct_char(42)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(8)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(5)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(4)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(3)
    assert "H" == dnfile.utils.num_bytes_to_struct_char(2)
    assert "B" == dnfile.utils.num_bytes_to_struct_char(1)
    assert None is dnfile.utils.num_bytes_to_struct_char(0)
