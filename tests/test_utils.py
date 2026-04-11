# -*- coding: utf-8 -*-
import pytest

import dnfile.utils


def test_compressed_int():
    assert None is dnfile.utils.read_compressed_int(b"")
    assert None is dnfile.utils.read_compressed_int(None)

    assert 0x7f, 1 == dnfile.utils.read_compressed_int(b"\x7f")
    assert 0x3f8f, 2 == dnfile.utils.read_compressed_int(b"\xbf\x8f")
    assert 0x1eadbeef, 4 == dnfile.utils.read_compressed_int(b"\xde\xad\xbe\xef")


def test_compress_int():    # --- 1-byte range: 0x00 to 0x7f ---
    assert dnfile.utils.compress_int(0) == b"\x00"
    assert dnfile.utils.compress_int(1) == b"\x01"
    assert dnfile.utils.compress_int(0x7f) == b"\x7f"

    # --- 2-byte range: 0x80 to 0x3fff ---
    # Lower boundary: 0x80 encodes as 0x8080
    assert dnfile.utils.compress_int(0x80) == b"\x80\x80"
    # Mid-range value
    assert dnfile.utils.compress_int(0x2000) == b"\xa0\x00"
    # Upper boundary: 0x3fff encodes as 0xbfff
    assert dnfile.utils.compress_int(0x3fff) == b"\xbf\xff"

    # --- 4-byte range: 0x4000 to 0x1fffffff ---
    # Lower boundary: 0x4000 encodes as 0xc0004000
    assert dnfile.utils.compress_int(0x4000) == b"\xc0\x00\x40\x00"
    # Mid-range value
    assert dnfile.utils.compress_int(0x100000) == b"\xc0\x10\x00\x00"
    # Upper boundary: 0x1fffffff encodes as 0xdfffffff
    assert dnfile.utils.compress_int(0x1fffffff) == b"\xdf\xff\xff\xff"

    # --- Overflow: value exceeds 0x1fffffff returns None ---
    assert dnfile.utils.compress_int(0x20000000) is None
    assert dnfile.utils.compress_int(0xffffffff) is None

    # --- Error cases ---
    with pytest.raises(ValueError):
        dnfile.utils.compress_int(-1)

    with pytest.raises(TypeError):
        dnfile.utils.compress_int(1.0)

    with pytest.raises(TypeError):
        dnfile.utils.compress_int("42")

    # --- Round-trip: compress_int -> read_compressed_int ---
    for value in (0, 1, 0x7f, 0x80, 0x3fff, 0x4000, 0x1fffffff):
        encoded = dnfile.utils.compress_int(value)
        assert encoded is not None
        result = dnfile.utils.read_compressed_int(encoded)
        assert result is not None
        decoded_value, nbytes = result
        assert decoded_value == value
        assert nbytes == len(encoded)


def test_struct_char():
    assert None is dnfile.utils.num_bytes_to_struct_char(42)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(8)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(5)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(4)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(3)
    assert "H" == dnfile.utils.num_bytes_to_struct_char(2)
    assert "B" == dnfile.utils.num_bytes_to_struct_char(1)
    assert None is dnfile.utils.num_bytes_to_struct_char(0)
