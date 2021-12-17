# -*- coding: utf-8 -*-

import copy as _copymod
import logging
import functools as _functools
from typing import List, Tuple, TypeVar, Optional, cast
from collections import deque

logger = logging.getLogger(__name__)


# lru_cache with a shallow copy of the objects returned (list, dicts, ..)
# we don't use deepcopy as it's _really_ slow and the data we retrieved using this is enough with copy.copy
# taken from https://stackoverflow.com/questions/54909357/how-to-get-functools-lru-cache-to-return-new-instances
def lru_cache(maxsize=128, typed=False, copy=False):
    if not copy:
        return _functools.lru_cache(maxsize, typed)

    def decorator(f):
        cached_func = _functools.lru_cache(maxsize, typed)(f)

        @_functools.wraps(f)
        def wrapper(*args, **kwargs):
            # return _copymod.deepcopy(cached_func(*args, **kwargs))
            return _copymod.copy(cached_func(*args, **kwargs))

        return wrapper

    return decorator


def rol(val: int, r_bits: int, max_bits: int) -> int:
    # Rotate left: 0b1001 --> 0b0011
    #
    # via: https://www.falatic.com/index.php/108/python-and-bitwise-rotation
    return (val << r_bits % max_bits) & (2 ** max_bits - 1) \
        | ((val & (2 ** max_bits - 1)) >> (max_bits - (r_bits % max_bits)))


def ror(val: int, r_bits: int, max_bits: int) -> int:
    # Rotate right: 0b1001 --> 0b1100
    #
    # via: https://www.falatic.com/index.php/108/python-and-bitwise-rotation
    return ((val & (2 ** max_bits - 1)) >> r_bits % max_bits) \
        | (val << (max_bits - (r_bits % max_bits)) & (2 ** max_bits - 1))


def read_compressed_int(data: bytes, signed=False) -> Optional[Tuple[int, int]]:
    """
    Given bytes, read a compressed integer per
    spec ECMA-335 II.23.2 Blobs and signatures.
    Returns tuple: value, number of bytes read or None on error.
    """
    if not signed:
        if not data:
            return None
        if data[0] & 0x80 == 0:
            # values 0x00 to 0x7f
            return data[0], 1
        elif len(data) >= 2 and data[0] & 0x40 == 0:
            # values 0x80 to 0x3fff
            value = (data[0] & 0x7F) << 8
            value |= data[1]
            return value, 2
        elif len(data) >= 4 and data[0] & 0x20 == 0:
            # values 0x4000 to 0x1fffffff
            value = (data[0] & 0x3F) << 24
            value |= data[1] << 16
            value |= data[2] << 8
            value |= data[3]
            return value, 4
        else:
            logger.warning("invalid compressed int: leading byte: 0x%02x", data[0])
            return None
    else:
        b1 = data[0]

        if b1 & 0x80 == 0:
            # 7-bit, 1-byte integer
            n = b1

            # rotate right one bit, 7-bit number
            n = ror(n, 1, 7)

            # sign-extend 7-bit number to 8-bits
            if n & (1 << 6):
                n |= (1 << 7)

            # reinterpret as 8-bit, 1-byte, signed, big-endian integer
            return struct.unpack(">b", struct.pack(">B", n))[0], 1
        elif b1 & 0x40 == 0:
            # 14-bit, 2-byte, big-endian integer
            n = struct.unpack(">h", bytes((b1 & 0x7F, data[1])))[0]

            # rotate right one bit, 14-bit number
            n = ror(n, 1, 14)

            # sign-extend 14-bit number to 16-bits
            if n & (1 << 13):
                n |= (1 << 14) | (1 << 15)

            # reinterpret as 16-bit, 2-byte, signed, big-endian integer
            return struct.unpack(">h", struct.pack(">H", n))[0], 2
        elif b1 & 0x20 == 0:
            # 29-bit, three byte, big endian integer
            n = struct.unpack(">i", bytes((b1 & 0x3F, data[1], data[2], data[3])))[0]

            # rotate right one bit, 29-bit number
            n = ror(n, 1, 29)

            # sign-extend 29-bit number to 32-bits
            if n & (1 << 28):
                n |= (1 << 29) | (1 << 30) | (1 << 31)

            # reinterpret as 32-bit, 4-byte, signed, big-endian integer
            return struct.unpack(">i", struct.pack(">I", n))[0], 4
        else:
            logger.warning("invalid compressed int: leading byte: 0x%02x", data[0])
            return None


def compress_int(i: int) -> Optional[bytes]:
    """
    Given integer, return bytes representing a compressed integer per
    spec ECMA-335 II.23.2 Blobs and signatures.
    """

    if not isinstance(i, int):
        raise TypeError(f"expected int, given {type(i)}")
    if i < 0:
        raise ValueError(f"expected positive int, given {i}")

    if i <= 0x7f:
        return int.to_bytes(i, length=1, byteorder="big")
    elif i <= 0x3fff:
        b = int.to_bytes(i, length=2, byteorder="big")
        return bytes((0x80 | b[0], b[1]))
    elif i <= 0x1fffffff:
        b = int.to_bytes(i, length=4, byteorder="big")
        return bytes((0x80 | 0x40 | b[0], b[1], b[2], b[3]))
    else:
        logger.warning(f"invalid int {i}, max value 0x1fffffff")
        return None


def two_way_dict(pairs):
    return dict([(e[1], e[0]) for e in pairs] + pairs)


def num_bytes_to_struct_char(n: int) -> Optional[str]:
    """
    Given number of bytes, return the struct char that can hold those bytes.
    Returns None on invalid value.

    For example,
        2 = H
        4 = I
    """
    if n > 8:
        logger.warning("invalid format specifier: %d > 8", n)
        return None
    elif n > 4:
        return "Q"
    elif n > 2:
        return "I"
    elif n > 1:
        return "H"
    elif n == 1:
        return "B"
    else:
        logger.warning("invalid format specifier: %d", n)
        return None


_ListType = TypeVar("_ListType")


class LazyList(List[_ListType]):
    """A List that transparently initializes each item as it is accessed.

    Note that calling `str` or `repr` with an instance of this class will force
    all items to be initialized.
    """

    def __init__(self, eval_func, initial_size: int):
        """Create a lazily initialized list of the specified size.

        `eval_func` is called with the index and value (or slice and list of values)
        for items retrieved through `__getitem__` *every time they are accessed*.
        """
        self.eval_func = eval_func
        super().__init__(cast(List[_ListType], [None] * initial_size))

    def __getitem__(self, __key):
        __value = super().__getitem__(__key)
        new = self.eval_func(__key, __value)
        if __value != new:
            super().__setitem__(__key, new)
        return new

    def __iter__(self):
        i = 0  # `eval_func` requires an index
        for v in super().__iter__():
            new = self.eval_func(i, v)
            if v != new:
                super().__setitem__(i, new)
            yield new
            i += 1

    def eval_all(self):
        """Ensure all items in the list are initialized by iterating through them."""
        deque(self, maxlen=0)  # Fully consumes iterator without overhead (https://stackoverflow.com/a/50938015)

    def truncate(self, length: int):
        """Truncate the list without evaluating any items."""
        keep = super().__getitem__(slice(0, length))
        self.clear()
        self.extend(keep)

    def __repr__(self) -> str:
        self.eval_all()
        return super().__repr__()
