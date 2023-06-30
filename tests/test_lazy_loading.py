import fixtures

import dnfile
from dnfile.utils import LazyList
from dnfile.mdtable import TypeRefRow, MemberRefRow


def test_lazy_loading():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path, clr_lazy_load=True)
    dn.parse_data_directories()

    assert dn.net
    assert dn.net.mdtables

    assert dn.net.mdtables.MemberRef
    assert isinstance(dn.net.mdtables.MemberRef.rows, LazyList)

    assert list.__getitem__(dn.net.mdtables.MemberRef.rows, 1) is None
    memref_row = dn.net.mdtables.MemberRef.rows[1]
    assert isinstance(memref_row, MemberRefRow)
    assert memref_row.Name
    assert "Signature" not in memref_row.__dict__
    assert memref_row.Signature
    assert "Signature" in memref_row.__dict__

    typeref_row = dn.net.mdtables.TypeRef.rows[0]
    assert isinstance(typeref_row, TypeRefRow)
    assert "ResolutionScope" not in typeref_row.__dict__
    assert memref_row.Class
    assert "ResolutionScope" in typeref_row.__dict__

    assert dn.net._resources is None
    assert dn.net.resources is not None
    assert dn.net._resources is not None


def test_non_lazy_loading():
    path = fixtures.get_data_path_by_name("hello-world.exe")

    dn = dnfile.dnPE(path, clr_lazy_load=False)
    dn.parse_data_directories()

    assert dn.net
    assert dn.net.mdtables

    assert dn.net.mdtables.MemberRef
    assert not isinstance(dn.net.mdtables.MemberRef.rows, LazyList)

    memref_row = list.__getitem__(dn.net.mdtables.MemberRef.rows, 1)
    assert isinstance(memref_row, MemberRefRow)
    assert "Signature" in memref_row.__dict__

    typeref_row = dn.net.mdtables.TypeRef.rows[0]
    assert isinstance(typeref_row, TypeRefRow)
    assert "ResolutionScope" in typeref_row.__dict__

    assert dn.net._resources is not None
