# -*- coding: utf-8 -*-

import functools as _functools
import copy as _copymod

from pefile import Structure


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


def read_compressed_int(data):
    """
    Given bytes, read a compressed integer per
    spec ECMA-335 II.23.2 Blobs and signatures.
    Returns tuple: value, number of bytes read
    """
    if not data:
        # TODO: error
        return None
    if data[0] & 0x80 == 0:
        # values 0x00 to 0x7f
        return data[0], 1
    elif data[0] & 0x40 == 0:
        # values 0x80 to 0x3fff
        value = (data[0] & 0x7F) << 8
        value |= data[1]
        return value, 2
    elif data[0] & 0x20 == 0:
        # values 0x4000 to 0x1fffffff
        value = (data[0] & 0x3F) << 24
        value |= data[1] << 16
        value |= data[2] << 8
        value |= data[3]
        return value, 4
    # TODO: error


def two_way_dict(pairs):
    return dict([(e[1], e[0]) for e in pairs] + pairs)


def num_bytes_to_struct_char(n: int):
    """
    Given number of bytes, return the struct char that can hold those bytes.

    For example,
        2 = H
        4 = I
    """
    if n > 8:
        return None
    if n > 4:
        return "Q"
    if n > 2:
        return "I"
    if n > 1:
        return "H"
    if n == 1:
        return "B"
    return None
