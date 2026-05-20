import fixtures

import dnfile


def test_duplicate_stream():
    path = fixtures.DATA / "invalid-streams" / "duplicate-stream.exe"

    dn = dnfile.dnPE(path)

    assert b"#US" in dn.net.metadata.streams
    assert dn.net.user_strings.get(1).value == "BBBBBBBB"


def test_baseline_streams_still_parse():
    path = fixtures.DATA / "invalid-streams" / "aaaaa.exe"

    dn = dnfile.dnPE(path)

    assert dn.net is not None
    assert dn.net.mdtables.Module is not None
    assert dn.net.strings.get(1).value == "<Module>"
    assert dn.net.user_strings is not None


def test_unknown_stream():
    path = fixtures.DATA / "invalid-streams" / "unknown-stream.exe"

    dn = dnfile.dnPE(path)

    assert b"#ZZ" in dn.net.metadata.streams
    assert dn.net.mdtables.Module is not None
    assert dn.net.strings.get(1).value == "<Module>"


def test_invalid_stream_name():
    path = fixtures.DATA / "invalid-streams" / "invalid-stream-name.exe"

    dn = dnfile.dnPE(path)

    assert b"#\x90\x90" in dn.net.metadata.streams
