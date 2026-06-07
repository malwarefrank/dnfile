# -*- coding: utf-8 -*-
"""
.NET Common Intermediate Language method body parsing.
"""

from dataclasses import dataclass
from typing import Optional

from . import errors


@dataclass(frozen=True)
class MethodBody:
    header_format: str
    header_size: int
    max_stack: int
    code_size: int
    local_var_sig_tok: int
    code: bytes
    local_signature: Optional[object] = None


def parse_method_body(pe, method_rva, mdtables):
    first = pe.get_data(method_rva, 1)
    if len(first) != 1:
        raise errors.dnFormatError(f"unable to read method body header at RVA 0x{method_rva:x}")

    first_byte = first[0]
    if first_byte & 0x3 == 0x2:
        code_size = first_byte >> 2
        code = pe.get_data(method_rva + 1, code_size)
        return MethodBody("tiny", 1, 8, code_size, 0, code)

    if first_byte & 0x3 != 0x3:
        raise errors.dnFormatError(f"unsupported method header format: 0x{first_byte:02x}")

    header = pe.get_data(method_rva, 12)
    if len(header) < 12:
        raise errors.dnFormatError(f"truncated fat method header at RVA 0x{method_rva:x}")

    flags_and_size = int.from_bytes(header[:2], "little")
    header_size = ((flags_and_size >> 12) & 0xF) * 4
    max_stack = int.from_bytes(header[2:4], "little")
    code_size = int.from_bytes(header[4:8], "little")
    local_var_sig_tok = int.from_bytes(header[8:12], "little")
    code = pe.get_data(method_rva + header_size, code_size)

    local_signature = None
    if local_var_sig_tok >> 24 == 0x11 and getattr(mdtables, "StandAloneSig", None):
        rid = local_var_sig_tok & 0x00FFFFFF
        sig_row = mdtables.StandAloneSig.get_with_row_index(rid)
        if sig_row is not None:
            local_signature = sig_row.ParsedSignature

    return MethodBody("fat", header_size, max_stack, code_size, local_var_sig_tok, code, local_signature)