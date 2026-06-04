import fixtures

import dnfile


def test_recovers_later_streams_after_invalid_stream_header(tmp_path):
    patched = fixtures.copy_fixture_to_tmp(tmp_path, "hello-world.exe")

    baseline = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))
    bad_header_offset = baseline.net.metadata.streams_list[1].struct.get_file_offset()

    fixtures.patch_bytes(patched, bad_header_offset, b"\xff" * 16)

    dn = dnfile.dnPE(patched)

    assert dn.net is not None
    assert dn.net.metadata is not None
    assert b"#Blob" in dn.net.metadata.streams
    assert b"#GUID" in dn.net.metadata.streams
    assert any("Invalid .NET stream" in warning for warning in dn.get_warnings())


def test_preserves_clr_state_when_metadata_stream_is_damaged(tmp_path):
    patched = fixtures.copy_fixture_to_tmp(tmp_path, "hello-world.exe")

    baseline = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))
    table_stream_offset = baseline.net.mdtables.struct.get_file_offset()

    fixtures.patch_bytes(patched, table_stream_offset + 32, b"\xff\xff\xff\x7f")

    dn = dnfile.dnPE(patched)

    assert dn.net is not None
    assert dn.net.struct is not None
    assert dn.net.Flags is not None
    assert dn.net.metadata is not None
    assert dn.net.mdtables is not None
    assert any("stream" in warning.lower() for warning in dn.get_warnings())


def test_truncated_table_rows_preserve_rows_loaded_before_truncation(tmp_path):
    patched = fixtures.copy_fixture_to_tmp(tmp_path, "hello-world.exe")

    baseline = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))
    typedef_offset = baseline.net.mdtables.TypeDef.file_offset
    row_size = baseline.net.mdtables.TypeDef.row_size
    cut_after_first_row = typedef_offset + row_size
    expected_type_name_index = baseline.net.mdtables.TypeDef[0].struct.TypeName_StringIndex

    fixtures.truncate_file(patched, cut_after_first_row + (row_size // 2))

    dn = dnfile.dnPE(patched)

    assert dn.net is not None
    assert dn.net.mdtables is not None
    assert dn.net.mdtables.TypeDef is not None
    assert len(dn.net.mdtables.TypeDef.rows) >= 1
    assert dn.net.mdtables.TypeDef[0].struct.TypeName_StringIndex == expected_type_name_index


def test_preserves_clr_flags_when_metadata_parse_fails(tmp_path):
    patched = fixtures.copy_fixture_to_tmp(tmp_path, "hello-world.exe")

    baseline = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))
    metadata_offset = baseline.net.metadata.struct.get_file_offset()
    fixtures.patch_bytes(patched, metadata_offset, b"BAD!")

    dn = dnfile.dnPE(patched)

    assert dn.net is not None
    assert dn.net.struct is not None
    assert dn.net.Flags is not None
    assert dn.net.metadata is None
    assert any("failed to parse .NET metadata" in warning for warning in dn.get_warnings())
