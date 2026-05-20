# -*- coding: utf-8 -*-
import dnfile.utils


def test_lazy_list_getitem_and_iteration():
    calls = []

    def eval_func(index, value):
        calls.append((index, value))
        return index if value is None else value

    items = dnfile.utils.LazyList(eval_func, 3)

    # Raw list access bypasses LazyList.__getitem__.
    assert list.__getitem__(items, 1) is None

    # Accessing through LazyList evaluates and caches the value.
    assert items[1] == 1
    assert calls == [(1, None)]

    calls.clear()
    # Iteration should evaluate each item exactly once.
    assert list(items) == [0, 1, 2]
    assert calls == [(0, None), (1, 1), (2, None)]


def test_lazy_list_repeated_access():
    calls = []

    def eval_func(index, value):
        calls.append((index, value))
        return index if value is None else value

    items = dnfile.utils.LazyList(eval_func, 2)

    # A second access should see the cached value, not None.
    assert items[0] == 0
    assert items[0] == 0
    assert calls == [(0, None), (0, 0)]


def test_lazy_list_slice_access():
    calls = []

    def eval_func(index, value):
        calls.append((index, value))
        if isinstance(index, slice):
            start = index.start or 0
            return [start + i for i in range(len(value))]
        return index if value is None else value

    items = dnfile.utils.LazyList(eval_func, 4)

    # Slice access should evaluate the slice as a single unit.
    assert items[1:3] == [1, 2]
    assert calls == [(slice(1, 3, None), [None, None])]
    # The evaluated slice should be written back into the underlying list.
    assert list.__getitem__(items, 1) == 1
    assert list.__getitem__(items, 2) == 2


def test_lazy_list_eval_all():
    calls = []

    def eval_func(index, value):
        calls.append((index, value))
        return index if value is None else value

    items = dnfile.utils.LazyList(eval_func, 3)

    # eval_all() should force evaluation of every item.
    items.eval_all()
    # Direct list access should now see initialized values.
    assert list.__getitem__(items, 0) == 0
    assert list.__getitem__(items, 1) == 1
    assert list.__getitem__(items, 2) == 2
    assert calls == [(0, None), (1, None), (2, None)]


def test_lazy_list_truncate_and_repr():
    calls = []

    def eval_func(index, value):
        calls.append((index, value))
        return index if value is None else value

    items = dnfile.utils.LazyList(eval_func, 4)

    # truncate() should shrink the list without forcing evaluation.
    items.truncate(2)
    assert len(items) == 2
    assert list.__getitem__(items, 0) is None
    assert list.__getitem__(items, 1) is None

    calls.clear()
    # repr() forces evaluation of the remaining items.
    assert repr(items) == "[0, 1]"
    assert calls == [(0, None), (1, None)]


def test_compressed_int():
    assert None is dnfile.utils.read_compressed_int(b"")
    assert None is dnfile.utils.read_compressed_int(None)

    assert (0x7f, 1) == dnfile.utils.read_compressed_int(b"\x7f")
    assert (0x3f8f, 2) == dnfile.utils.read_compressed_int(b"\xbf\x8f")
    assert (0x1eadbeef, 4) == dnfile.utils.read_compressed_int(b"\xde\xad\xbe\xef")


def test_struct_char():
    assert None is dnfile.utils.num_bytes_to_struct_char(42)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(8)
    assert "Q" == dnfile.utils.num_bytes_to_struct_char(5)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(4)
    assert "I" == dnfile.utils.num_bytes_to_struct_char(3)
    assert "H" == dnfile.utils.num_bytes_to_struct_char(2)
    assert "B" == dnfile.utils.num_bytes_to_struct_char(1)
    assert None is dnfile.utils.num_bytes_to_struct_char(0)
