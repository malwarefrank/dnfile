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
    assert dn.net.user_strings.get(1) == b"\xD0\xDD"
    with pytest.raises(UnicodeDecodeError):
        assert dn.net.user_strings.get_us(1)


def test_raw_binary():
    path = fixtures.DATA / "invalid-strings" / "raw-binary.exe"

    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.metadata is not None
    assert dn.net.user_strings is not None

    # short MZ header
    assert b"#US" in dn.net.metadata.streams
    assert dn.net.user_strings.get(1) == b"\x4D\x5A\x90\x00"

    # somehow this is valid utf-16
    s = dn.net.user_strings.get_us(1)
    assert s is not None
    assert s.value == b"\x4D\x5A\x90\x00".decode("utf-16")


def test_string_decoder():
    path = fixtures.DATA / "invalid-strings" / "string-decoder.exe"

    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.metadata is not None
    assert dn.net.user_strings is not None

    # "Hello World" ^ 0xFF
    assert b"#US" in dn.net.metadata.streams
    assert dn.net.user_strings.get(1) == b"\xb7\xff\x9a\xff\x93\xff\x93\xff\x90\xff\xdf\xff\xa8\xff\x90\xff\x8d\xff\x93\xff\x9b\xff"

    # somehow this is valid utf-16
    s = dn.net.user_strings.get_us(1)
    assert s is not None
