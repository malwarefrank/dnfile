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

    assert hasattr(dn.net.metadata, "streams")
    assert b"#~" in dn.net.metadata.streams
    assert dn.net.metadata.streams[b"#~"].get_file_offset() == 0x2d4

    # strings used by #~
    assert b"#Strings" in dn.net.metadata.streams
    assert hasattr(dn.net, "strings")
    assert dn.net.strings.get_file_offset() == 0x3d8

    # "user strings"
    assert b"#US" in dn.net.metadata.streams
    assert hasattr(dn.net, "user_strings")
    assert dn.net.user_strings.get_file_offset() == 0x4dc

    assert b"#GUID" in dn.net.metadata.streams
    assert hasattr(dn.net, "guids")
    assert dn.net.guids.get_file_offset() == 0x4f8

    assert b"#Blob" in dn.net.metadata.streams
    assert hasattr(dn.net, "blobs")
    assert dn.net.blobs.get_file_offset() == 0x508

    assert b"#Foo" not in dn.net.metadata.streams
    assert not hasattr(dn.net, "foo")


def test_guids():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None
    assert b"#GUID" in dn.net.metadata.streams
    assert hasattr(dn.net, "guids")

    assert dn.net.guids.get(0) is None
    assert isinstance(dn.net.guids.get(1), dnfile.stream.HeapItemGuid)
    assert dn.net.guids.get(1).value == b"\x8c\x8b\xc5\x48\xff\x24\x91\x45\x9e\xc8\x94\xbf\xea\xbd\x9f\x3e"


def test_guids_as_sequence():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None
    assert b"#GUID" in dn.net.metadata.streams
    assert hasattr(dn.net, "guids")

    assert len(dn.net.guids) == 1
    assert dn.net.guids[0] is not None
    assert hasattr(dn.net.guids[0], "value")
    assert dn.net.guids[0].value == b"\x8c\x8b\xc5\x48\xff\x24\x91\x45\x9e\xc8\x94\xbf\xea\xbd\x9f\x3e"


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
        "file_offset": 0x310,
    }
    tables["TypeRef"] = {
        "RVA": 0x211a,
        "TableName": "TypeRef",
        "TableNumber": 1,
        "IsSorted": False,
        "NumRows": 6,
        "RowSize": 6,
        "file_offset": 0x31a,
    }
    tables["TypeDef"] = {
        "RVA": 0x213e,
        "TableName": "TypeDef",
        "TableNumber": 2,
        "IsSorted": False,
        "NumRows": 2,
        "RowSize": 14,
        "file_offset": 0x33e,
    }
    tables["MethodDef"] = {
        "RVA": 0x215a,
        "TableName": "MethodDef",
        "TableNumber": 6,
        "IsSorted": False,
        "NumRows": 2,
        "RowSize": 14,
        "file_offset": 0x35a,
    }
    tables["Param"] = {
        "RVA": 0x2176,
        "TableName": "Param",
        "TableNumber": 8,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 6,
        "file_offset": 0x376,
    }
    tables["MemberRef"] = {
        "RVA": 0x217c,
        "TableName": "MemberRef",
        "TableNumber": 10,
        "IsSorted": False,
        "NumRows": 5,
        "RowSize": 6,
        "file_offset": 0x37c,
    }
    tables["CustomAttribute"] = {
        "RVA": 0x219a,
        "TableName": "CustomAttribute",
        "TableNumber": 12,
        "IsSorted": True,
        "NumRows": 3,
        "RowSize": 6,
        "file_offset": 0x39a,
    }
    tables["Assembly"] = {
        "RVA": 0x21ac,
        "TableName": "Assembly",
        "TableNumber": 32,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 22,
        "file_offset": 0x3ac,
    }
    tables["AssemblyRef"] = {
        "RVA": 0x21c2,
        "TableName": "AssemblyRef",
        "TableNumber": 35,
        "IsSorted": False,
        "NumRows": 1,
        "RowSize": 20,
        "file_offset": 0x3c2,
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
        assert table.file_offset == ref_table.get("file_offset")


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
    path = fixtures.get_data_path_by_name("ModuleCode_x86.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    typedefs = dn.net.mdtables.TypeDef
    assert typedefs[0].TypeName == "<Module>"
    assert typedefs[5].TypeName == "ModuleLoadException"

    assert len(typedefs[0].FieldList) == 52
    assert len(typedefs[5].FieldList) == 1

    assert len(typedefs[0].MethodList) == 76
    assert len(typedefs[5].MethodList) == 3

    assert typedefs[0].MethodList[0].row.Name == "rc4_init"
    assert typedefs[5].MethodList[0].row.Name == ".ctor"


def test_typedef_methodlist():
    path = fixtures.get_data_path_by_name("EmptyClass_x86.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    typedefs = dn.net.mdtables.TypeDef
    assert typedefs[0].TypeName == "<Module>"
    assert typedefs[0].MethodList is not None
    assert len(typedefs[0].MethodList) == 1
    assert typedefs[0].MethodList[0].row.Name == "_mainCRTStartup"


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


def test_heap_items():

    # HeapItem
    buf = b"1234567890"
    item = dnfile.base.HeapItem(b"1234567890")
    assert item.raw_data == b"1234567890"
    assert item.value_bytes() == buf
    assert item == b"1234567890"
    assert item.raw_size == len(b"1234567890")
    assert item.rva is None
    assert item.value is None

    item = dnfile.base.HeapItem(b"1234567890", rva=0x400)
    assert item.rva == 0x400

    # HeapItemString
    buf = b"1234567890"
    buf_decoded = buf.decode("utf-8")
    str_item = dnfile.stream.HeapItemString(buf)
    assert str_item.raw_data == buf
    assert str_item.encoding == "utf-8"
    assert str_item.value == buf_decoded
    assert str_item.value_bytes() == buf
    assert str_item == buf_decoded

    # HeapItemBinary
    buf_with_compressed_int_len = b"\x0a1234567890"
    buf = b"1234567890"
    bin_item = dnfile.stream.HeapItemBinary(buf_with_compressed_int_len)
    assert bin_item.raw_data == buf_with_compressed_int_len
    assert bin_item.raw_size == len(buf_with_compressed_int_len)
    assert bin_item.item_size == len(buf)
    assert bin_item.value_bytes() == buf
    assert bin_item == buf

    # UserString
    buf_with_flag = b"\x151\x002\x003\x004\x005\x006\x007\x008\x009\x000\x00\x00"
    us_str = "1234567890"
    us_item = dnfile.stream.UserString(buf_with_flag)
    assert us_item.raw_data == buf_with_flag
    assert us_item.value_bytes() == buf_with_flag[1:-1]
    assert us_item.value == us_str
    assert us_item == us_str

    # GUID
    guid_bytes = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
    guid_item = dnfile.stream.HeapItemGuid(guid_bytes)
    assert guid_item is not None
    assert guid_item.raw_data == guid_bytes
    assert guid_item.value_bytes() == guid_bytes
    assert guid_item.value == guid_bytes
    assert str(guid_item) == "03020100-0504-0706-0809-0a0b0c0d0e0f"
