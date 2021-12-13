import fixtures

import dnfile


def test_duplicate_stream():
    path = fixtures.DATA / "invalid-streams" / "duplicate-stream.exe"

    dn = dnfile.dnPE(path)

    assert "#US" in dn.net.metadata.streams
    assert dn.net.user_strings.get_us(1).value == "BBBBBBBB"