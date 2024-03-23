import pytest
import fixtures

import dnfile


def test_unpaired_surrogate():
    path = fixtures.DATA / "invalid-strings" / "unpaired-surrogate.exe"

    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.metadata is not None
    assert dn.net.user_strings is not None

    assert b"#US" in dn.net.metadata.streams
    item = dn.net.user_strings.get(1)
    assert item is not None
    assert item.flag == 0x01
    assert item.value_bytes() == b"\xD0\xDD"
    assert item.value is None


def test_raw_binary():
    path = fixtures.DATA / "invalid-strings" / "raw-binary.exe"

    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.metadata is not None
    assert dn.net.user_strings is not None

    # short MZ header
    assert b"#US" in dn.net.metadata.streams
    s = dn.net.user_strings.get(1)
    assert s is not None
    # somehow this is valid utf-16
    assert s.value == b"\x4D\x5A\x90\x00".decode("utf-16")
    assert s.value_bytes() == b"\x4D\x5A\x90\x00"


def test_string_decoder():
    path = fixtures.DATA / "invalid-strings" / "string-decoder.exe"

    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.metadata is not None
    assert dn.net.user_strings is not None

    # "Hello World" ^ 0xFF
    assert b"#US" in dn.net.metadata.streams
    item = dn.net.user_strings.get(1)
    assert item is not None
    assert item.raw_data == b"\x17\xb7\xff\x9a\xff\x93\xff\x93\xff\x90\xff\xdf\xff\xa8\xff\x90\xff\x8d\xff\x93\xff\x9b\xff\x01"
    assert item.flag == 0x01
    assert item.value_bytes() ==  b"\xb7\xff\x9a\xff\x93\xff\x93\xff\x90\xff\xdf\xff\xa8\xff\x90\xff\x8d\xff\x93\xff\x9b\xff"

    # somehow this is valid utf-16
    s = dn.net.user_strings.get(1)
    assert s is not None
