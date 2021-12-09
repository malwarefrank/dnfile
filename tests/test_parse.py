import dnfile

import fixtures


def test_metadata():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    assert hasattr(dn, "net")

    dn.net.metadata.struct.Signature == 0x424A5342
    dn.net.metadata.struct.MajorVersion == 1
    dn.net.metadata.struct.MinorVersion == 1
    dn.net.metadata.struct.Version == "v4.0.30319"
    dn.net.metadata.struct.Flags == 0x0
    dn.net.metadata.struct.NumberOfStreams == 5


def test_streams():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    assert b"#~" in dn.net.metadata.streams
    assert hasattr(dn.net, "metadata")

    # strings used by #~
    assert b"#Strings" in dn.net.metadata.streams
    assert hasattr(dn.net, "strings")

    # "user strings"
    assert b"#US" in dn.net.metadata.streams
    # not sure where these are accessible yet

    assert b"#GUID" in dn.net.metadata.streams
    assert hasattr(dn.net, "guids")

    assert b"#Blob" in dn.net.metadata.streams
    assert hasattr(dn.net, "blobs")

    assert b"#Foo" not in dn.net.metadata.streams
    assert not hasattr(dn.net, "foo")


def test_tables():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    for table in ["Module", "TypeRef", "TypeDef", "MethodDef", "Param", "MemberRef", "CustomAttribute", "Assembly", "AssemblyRef"]:
        assert hasattr(dn.net.mdtables, table)

    assert not hasattr(dn.net.mdtables, "foo")


def test_module():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    assert dn.net.mdtables.Module.rows[0].Name == "1-hello-world.exe"

