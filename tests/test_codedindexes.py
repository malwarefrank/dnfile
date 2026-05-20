import fixtures

import dnfile
from dnfile import codedindex
from dnfile.mdtable import (AssemblyRow, FieldRow, MemberRefRow, PropertyRow,
                            TypeDefRow, TypeRefRow)


def _assert_coded_index_target(index, table_name, row_index, row_type):
    # Verify both the resolved table metadata and the concrete row type.
    assert index.table is not None
    assert index.table.name == table_name
    assert index.row_index == row_index
    assert isinstance(index.row, row_type)


class _FakeTable:
    # Tiny stand-in for the real table objects used by the resolver.
    def __init__(self, name, rows):
        self.name = name
        self._rows = rows

    # Mirror the lookup API that coded-index resolution expects.
    def get_with_row_index(self, row_index):
        return self._rows[row_index]


def test_coded_indexes_in_hello_world():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    # TypeDef.Extends should point at the TypeRef entry for System.Object.
    typedef = dn.net.mdtables.TypeDef[1]
    _assert_coded_index_target(typedef.Extends, "TypeRef", 5, TypeRefRow)

    # MemberRef.Class is another TypeRef-backed coded index.
    member_ref = dn.net.mdtables.MemberRef[0]
    _assert_coded_index_target(member_ref.Class, "TypeRef", 1, TypeRefRow)

    # CustomAttribute rows carry both parent and constructor-type references.
    custom_attribute = dn.net.mdtables.CustomAttribute[0]
    _assert_coded_index_target(custom_attribute.Parent, "Assembly", 1, AssemblyRow)
    _assert_coded_index_target(custom_attribute.Type, "MemberRef", 1, MemberRefRow)


def test_coded_indexes_in_module_code():
    path = fixtures.get_data_path_by_name("ModuleCode_x86.exe")

    dn = dnfile.dnPE(path)
    assert dn.net is not None

    # Constant.Parent should resolve back to the field that owns the constant.
    constant = dn.net.mdtables.Constant[0]
    _assert_coded_index_target(constant.Parent, "Field", 53, FieldRow)

    # MethodSemantics.Association links a method semantics row to a property.
    method_semantics = dn.net.mdtables.MethodSemantics[0]
    _assert_coded_index_target(method_semantics.Association, "Property", 1, PropertyRow)

    # This fixture also exercises a different CustomAttribute parent/type pair.
    custom_attribute = dn.net.mdtables.CustomAttribute[2]
    _assert_coded_index_target(custom_attribute.Parent, "TypeDef", 2, TypeDefRow)
    _assert_coded_index_target(custom_attribute.Type, "MemberRef", 2, MemberRefRow)


def test_coded_index_resolution_without_fixture():
    # Use a sentinel so the test can assert identity rather than equality.
    sentinel_row = object()
    # Minimal table stub for exercising the resolver without a PE fixture.
    tables = [_FakeTable("TypeRef", {1: sentinel_row})]

    # Tag 1 selects the TypeRef table in TypeDefOrRef.
    resolved = codedindex.TypeDefOrRef((1 << codedindex.TypeDefOrRef.tag_bits) | 1, tables)
    assert resolved.table is not None
    assert resolved.table.name == "TypeRef"
    assert resolved.row_index == 1
    assert resolved.row is sentinel_row

    # An unknown table tag should leave the table unresolved but preserve the row index.
    unresolved = codedindex.TypeDefOrRef((2 << codedindex.TypeDefOrRef.tag_bits) | 2, tables)
    assert unresolved.table is None
    assert unresolved.row_index == 2
    assert unresolved.row is None
