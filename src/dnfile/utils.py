# -*- coding: utf-8 -*-

import copy as _copymod
import struct
import logging
import functools as _functools
from typing import Tuple, Optional

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
    Given bytes, read a compressed (optionally signed) integer per
    spec ECMA-335 II.23.2 Blobs and signatures.
    Returns tuple: value, number of bytes read or None on error.
    """
    if not data:
        return None

    if not signed:
        b1 = data[0]
        if b1 & 0x80 == 0:
            return struct.unpack(">B", bytes((b1, )))[0], 1
        elif b1 & 0x40 == 0:
            return struct.unpack(">H", bytes((b1 & 0x7F, data[1])))[0], 2
        elif b1 & 0x20 == 0:
            return struct.unpack(">I", bytes((b1 & 0x3F, data[1], data[2], data[3])))[0], 4
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
