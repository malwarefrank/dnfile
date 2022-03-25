import pytest
import fixtures

import dnfile
from dnfile.mdtable import TypeRefRow, AssemblyRefRow


def test_metadata():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None
    assert dn.net.metadata is not None

    dn.net.metadata.struct.Signature == 0x424A5342
    dn.net.metadata.struct.MajorVersion == 1
    dn.net.metadata.struct.MinorVersion == 1
    dn.net.metadata.struct.Version == "v4.0.30319"
    dn.net.metadata.struct.Flags == 0x0
    dn.net.metadata.struct.NumberOfStreams == 5


def test_streams():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None
    assert dn.net.metadata is not None

    assert b"#~" in dn.net.metadata.streams
    assert hasattr(dn.net, "metadata")

    # strings used by #~
    assert b"#Strings" in dn.net.metadata.streams
    assert hasattr(dn.net, "strings")

    # "user strings"
    assert b"#US" in dn.net.metadata.streams
    assert hasattr(dn.net, "user_strings")

    assert b"#GUID" in dn.net.metadata.streams
    assert hasattr(dn.net, "guids")

    assert b"#Blob" in dn.net.metadata.streams
    assert hasattr(dn.net, "blobs")

    assert b"#Foo" not in dn.net.metadata.streams
    assert not hasattr(dn.net, "foo")


def test_tables():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    for table in ["Module", "TypeRef", "TypeDef", "MethodDef", "Param", "MemberRef", "CustomAttribute", "Assembly", "AssemblyRef"]:
        assert hasattr(dn.net.mdtables, table)

    assert not hasattr(dn.net.mdtables, "foo")

    tables = dict()
    tables["Module"] = {
        "RVA": 0x2110,
        "TableName": "Module",
        "TableNumber": 0,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 10,
        }
    tables["TypeRef"] = {
        "RVA": 0x211a,
        "TableName": "TypeRef",
        "TableNumber": 1,
        "IsSorted": False,
        "NumRows": 6,
        "RowSize": 6,
        }
    tables["TypeDef"] = {
        "RVA": 0x213e,
        "TableName": "TypeDef",
        "TableNumber": 2,
        "IsSorted": False,
        "NumRows": 2,
        "RowSize": 14,
        }
    tables["MethodDef"] = {
        "RVA": 0x215a,
        "TableName": "MethodDef",
        "TableNumber": 6,
        "IsSorted": False,
        "NumRows": 2,
        "RowSize": 14,
        }
    tables["Param"] = {
        "RVA": 0x2176,
        "TableName": "Param",
        "TableNumber": 8,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 6,
        }
    tables["MemberRef"] = {
        "RVA": 0x217c,
        "TableName": "MemberRef",
        "TableNumber": 10,
        "IsSorted": False,
        "NumRows": 5,
        "RowSize": 6,
        }
    tables["CustomAttribute"] = {
        "RVA": 0x219a,
        "TableName": "CustomAttribute",
        "TableNumber": 12,
        "IsSorted": True,
        "NumRows": 3,
        "RowSize": 6,
        }
    tables["Assembly"] = {
        "RVA": 0x21ac,
        "TableName": "Assembly",
        "TableNumber": 32,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 22,
        }
    tables["AssemblyRef"] = {
        "RVA": 0x21c2,
        "TableName": "AssemblyRef",
        "TableNumber": 35,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 20,
        }

    for table in dn.net.mdtables.tables_list:
        table: dnfile.base.ClrMetaDataTable
        ref_table = tables[table.name]
        assert table.name in tables
        assert table.rva == ref_table.get("RVA", None)
        assert table.name == ref_table.get("TableName", None)
        assert table.number == ref_table.get("TableNumber", None)
        assert table.is_sorted == ref_table.get("IsSorted", None)
        assert table.num_rows == ref_table.get("NumRows", None)
        assert table.row_size == ref_table.get("RowSize", None)


def test_module():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    assert dn.net.mdtables.Module[0].Name == "1-hello-world.exe"


def test_typedef_extends():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    typedefs = dn.net.mdtables.TypeDef
    assert typedefs[0].TypeName == "<Module>"
    assert typedefs[1].TypeName == "HelloWorld"

    #   .class public auto ansi beforefieldinit HelloWorld
    #      extends [mscorlib]System.Object

    extends = typedefs[1].Extends
    assert extends.table is not None
    assert extends.table.name == "TypeRef"
    assert extends.row_index == 5

    superclass = extends.row
    assert isinstance(superclass, TypeRefRow)
    assert superclass.TypeNamespace == "System"
    assert superclass.TypeName == "Object"

    assert superclass.ResolutionScope.table is not None
    assert superclass.ResolutionScope.table.name == "AssemblyRef"
    assembly = superclass.ResolutionScope.row
    assert isinstance(assembly, AssemblyRefRow)
    assert assembly.Name == "mscorlib"


def test_typedef_members():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    typedefs = dn.net.mdtables.TypeDef
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
    assert dn.net is not None

    methods = dn.net.mdtables.MethodDef
    assert methods[0].Name == "Main"
    assert methods[1].Name == ".ctor"

    # default void Main (string[] args)  cil managed
    assert len(methods[0].ParamList) == 1
    # instance default void '.ctor' ()  cil managed
    assert len(methods[1].ParamList) == 0

    assert methods[0].ParamList[0].row is not None
    assert methods[0].ParamList[0].row.Name == "args"


def test_ignore_NumberOfRvaAndSizes():
    # .NET loaders ignores NumberOfRvaAndSizes, so attempt to parse anyways
    path = fixtures.DATA / "1d41308bf4148b4c138f9307abc696a6e4c05a5a89ddeb8926317685abb1c241"
    if not path.exists():
        raise pytest.xfail("test file 1d41308bf41... (DANGER: malware) not found in test fixtures")

    dn = dnfile.dnPE(path)
    assert hasattr(dn, "net") and dn.net is not None
    assert hasattr(dn.net, "metadata") and dn.net.metadata is not None


def test_flags():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    # class HelloWorld
    cls = dn.net.mdtables.TypeDef.get_with_row_index(2)

    # these are enums from CorTypeSemantics
    assert cls.Flags.tdClass is True
    assert cls.Flags.tdInterface is False

    # these are flags from CorTypeAttrFlags
    assert cls.Flags.tdBeforeFieldInit is True
    assert cls.Flags.tdAbstract is False
