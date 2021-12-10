import fixtures

import dnfile


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

    assert "#~" in dn.net.metadata.streams
    assert hasattr(dn.net, "metadata")

    # strings used by #~
    assert "#Strings" in dn.net.metadata.streams
    assert hasattr(dn.net, "strings")

    # "user strings"
    assert "#US" in dn.net.metadata.streams
    # not sure where these are accessible yet

    assert "#GUID" in dn.net.metadata.streams
    assert hasattr(dn.net, "guids")

    assert "#Blob" in dn.net.metadata.streams
    assert hasattr(dn.net, "blobs")

    assert "#Foo" not in dn.net.metadata.streams
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


def test_typedef_extends():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    typedefs = dn.net.mdtables.TypeDef.rows
    assert typedefs[0].TypeName == "<Module>"
    assert typedefs[1].TypeName == "HelloWorld"

    #   .class public auto ansi beforefieldinit HelloWorld
    #      extends [mscorlib]System.Object

    extends = typedefs[1].Extends
    assert extends.table.name == "TypeRef"
    assert extends.row_index == 5

    superclass = extends.row
    assert superclass.TypeNamespace == "System"
    assert superclass.TypeName == "Object"

    assert superclass.ResolutionScope.table.name == "AssemblyRef"
    assembly = superclass.ResolutionScope.row
    assert assembly.Name == "mscorlib"


def test_typedef_members():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    typedefs = dn.net.mdtables.TypeDef.rows
    assert typedefs[0].TypeName == "<Module>"
    assert typedefs[1].TypeName == "HelloWorld"

    # neither class has fields
    assert len(typedefs[0].FieldList) == 0
    assert len(typedefs[1].FieldList) == 0

    # <Module> has no methods
    assert len(typedefs[0].MethodList) == 0
    # HelloWorld has two methods: Main and .ctor
    assert len(typedefs[1].MethodList) == 2

    assert typedefs[1].MethodList[0].row.Name == "Main"
    assert typedefs[1].MethodList[1].row.Name == ".ctor"


def test_method_params():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)

    methods = dn.net.mdtables.MethodDef.rows
    assert methods[0].Name == "Main"
    assert methods[1].Name == ".ctor"

    # default void Main (string[] args)  cil managed
    assert len(methods[0].ParamList) == 1
    # instance default void '.ctor' ()  cil managed
    assert len(methods[1].ParamList) == 0

    methods[0].ParamList[0].row.Name == "args"
