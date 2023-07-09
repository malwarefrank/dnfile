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

    # LazyList is initialized as a list of `None`.
    # list.__getitem__ bypasses lazy loading.
    assert list.__getitem__(dn.net.mdtables.MemberRef.rows, 1) is None
    memref_row = dn.net.mdtables.MemberRef.rows[1]
    assert isinstance(memref_row, MemberRefRow)

    assert memref_row.Name
    # __dict__ access bypasses lazy loading.
    assert "Signature" not in memref_row.__dict__
    assert memref_row.Signature
    assert "Signature" in memref_row.__dict__

    # The first item of the rows list is a special case, because it is
    # initialized without data before lazy-loading is setup.
    # Make sure that it behaves the same as any other row when accessed.
    # We can also verify that slicing works, since it too needs to be
    # handled appropriately.
    typeref_row = dn.net.mdtables.TypeRef.rows[:3:2][0]
    assert isinstance(typeref_row, TypeRefRow)

    assert "ResolutionScope" not in typeref_row.__dict__
    # TypeRefRow.Class should trigger a full load of all tables and rows.
    assert memref_row.Class
    # This should not have been lazy-loaded, but will still have been loaded
    # because of accessing the Class attribute.
    assert "ResolutionScope" in typeref_row.__dict__

    # _resources is the underlying lazy-loaded field for the ClrResource list.
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

    # list.__getitem__ would bypass any lazy loading.
    memref_row = list.__getitem__(dn.net.mdtables.MemberRef.rows, 1)
    assert isinstance(memref_row, MemberRefRow)
    # __dict__ access would bypass any lazy loading.
    assert "Signature" in memref_row.__dict__

    typeref_row = dn.net.mdtables.TypeRef.rows[0]
    assert isinstance(typeref_row, TypeRefRow)
    assert "ResolutionScope" in typeref_row.__dict__

    # _resources is the underlying field that would be lazy-loaded.
    assert dn.net._resources is not None
