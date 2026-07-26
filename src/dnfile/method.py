# -*- coding: utf-8 -*-
"""
.NET Common Intermediate Language method metadata parsing.
"""

import struct
from dataclasses import dataclass
from typing import List, Optional

from pefile import PEFormatError

from . import base, enums


COR_ILMETHOD_SECT_EH_TABLE = 0x1
COR_ILMETHOD_SECT_FAT_FORMAT = 0x40
COR_ILMETHOD_SECT_MORE_SECTS = 0x80
COR_ILMETHOD_MORE_SECTS = 0x8


@dataclass(frozen=True)
class Method:
    source_row: object

    @property
    def name(self):
        return str(self.source_row.Name)


@dataclass(frozen=True)
class InternalMethod(Method):
    kind: str = "internal"

    @property
    def parsed_signature(self):
        return self.source_row.ParsedSignature

    @property
    def body(self):
        return self.source_row.Body


@dataclass(frozen=True)
class ExternalMethod(Method):
    kind: str = "external"
    body: object = None

    @property
    def parsed_signature(self):
        return self.source_row.ParsedSignature


@dataclass(frozen=True)
class ExceptionHandler:
    clause_type: str
    try_offset: int
    try_length: int
    handler_offset: int
    handler_length: int
    class_token: int
    exception_type: Optional[base.MDTableIndex] = None


@dataclass(frozen=True)
class MethodBody:
    header_format: str
    header_size: int
    max_stack: int
    code_size: int
    local_var_sig_tok: int
    code: bytes
    local_signature: Optional[object] = None
    exception_handlers: List[ExceptionHandler] = None


@dataclass(frozen=True)
class UnsupportedMethodBody:
    kind: str
    rva: int
    raw_header: bytes
    reason: str
    header_format: str = "unsupported"
    header_size: int = 0
    max_stack: int = 0
    code_size: int = 0
    local_var_sig_tok: int = 0
    code: bytes = b""
    local_signature: Optional[object] = None
    exception_handlers: List[ExceptionHandler] = None


def is_method_memberref_signature(blob: bytes) -> bool:
    if not blob:
        return False

    if hasattr(blob, "value_bytes"):
        blob = blob.value_bytes()
    elif hasattr(blob, "value"):
        blob = blob.value
    elif not isinstance(blob, (bytes, bytearray)):
        blob = bytes(blob)

    return (blob[0] & 0x0F) != 0x06


def method_from_methoddef_row(row):
    return InternalMethod(source_row=row)


def method_from_memberref_row(row):
    if not is_method_memberref_signature(row.Signature):
        return None

    return ExternalMethod(source_row=row)


def _resolve_metadata_token(mdtables, token: int) -> Optional[base.MDTableIndex]:
    table_number = token >> 24
    row_index = token & 0x00FFFFFF
    if row_index == 0:
        return None

    try:
        table_name = enums.MetadataTables(table_number).name
    except ValueError:
        return None

    table = getattr(mdtables, table_name, None)
    if table is None:
        return None

    return base.MDTableIndex(table, row_index)


def _unsupported_method_body(method_rva: int, raw_header: bytes, reason: str) -> UnsupportedMethodBody:
    return UnsupportedMethodBody(kind="unsupported", rva=method_rva, raw_header=raw_header, reason=reason)


def _parse_exception_handler_section(data: bytes, mdtables) -> List[ExceptionHandler]:
    kind = data[0]
    data_size = int.from_bytes(data[1:4], "little")
    payload = data[4:data_size]

    if kind & COR_ILMETHOD_SECT_FAT_FORMAT:
        clause_size = 24
        unpacker = lambda chunk: struct.unpack("<IIIIII", chunk)
    else:
        clause_size = 12
        unpacker = lambda chunk: (
            int.from_bytes(chunk[0:2], "little"),
            int.from_bytes(chunk[2:4], "little"),
            chunk[4],
            int.from_bytes(chunk[5:7], "little"),
            chunk[7],
            int.from_bytes(chunk[8:12], "little"),
        )

    handlers = []
    for offset in range(0, len(payload), clause_size):
        chunk = payload[offset:offset + clause_size]
        if len(chunk) < clause_size:
            break

        flags, try_offset, try_length, handler_offset, handler_length, token = unpacker(chunk)
        clause_type = {
            0: "catch",
            1: "filter",
            2: "finally",
            4: "fault",
        }.get(flags, f"unknown:{flags}")
        handlers.append(
            ExceptionHandler(
                clause_type=clause_type,
                try_offset=try_offset,
                try_length=try_length,
                handler_offset=handler_offset,
                handler_length=handler_length,
                class_token=token,
                exception_type=_resolve_metadata_token(mdtables, token) if clause_type == "catch" else None,
            )
        )

    return handlers


def _parse_method_sections(pe, method_rva: int, header_size: int, code_size: int, mdtables) -> List[ExceptionHandler]:
    section_rva = method_rva + header_size + code_size
    while section_rva % 4:
        section_rva += 1

    first = pe.get_data(section_rva, 4)
    if len(first) < 4:
        return []

    handlers = []
    more_sections = True
    current_rva = section_rva
    while more_sections:
        header = pe.get_data(current_rva, 4)
        if len(header) < 4:
            break

        kind = header[0]
        data_size = int.from_bytes(header[1:4], "little")
        if data_size < 4:
            break
        section_data = pe.get_data(current_rva, data_size)
        if kind & COR_ILMETHOD_SECT_EH_TABLE:
            handlers.extend(_parse_exception_handler_section(section_data, mdtables))

        more_sections = bool(kind & COR_ILMETHOD_SECT_MORE_SECTS)
        current_rva += data_size
        while current_rva % 4:
            current_rva += 1

    return handlers


def parse_method_body(pe, method_rva, mdtables):
    raw_header = b""
    try:
        raw_header = pe.get_data(method_rva, 12)
        if len(raw_header) < 1:
            return _unsupported_method_body(
                method_rva,
                raw_header,
                f"unable to read method body header at RVA 0x{method_rva:x}",
            )

        first_byte = raw_header[0]
        if first_byte & 0x3 == 0x2:
            code_size = first_byte >> 2
            code = pe.get_data(method_rva + 1, code_size)
            if len(code) != code_size:
                return _unsupported_method_body(
                    method_rva,
                    raw_header[:1],
                    f"truncated tiny method body at RVA 0x{method_rva:x}",
                )
            return MethodBody("tiny", 1, 8, code_size, 0, code, None, [])

        if first_byte & 0x3 != 0x3:
            return _unsupported_method_body(
                method_rva,
                raw_header[:1],
                f"unsupported method header format: 0x{first_byte:02x}",
            )

        if len(raw_header) < 12:
            return _unsupported_method_body(
                method_rva,
                raw_header,
                f"truncated fat method header at RVA 0x{method_rva:x}",
            )

        flags_and_size = int.from_bytes(raw_header[:2], "little")
        header_size = ((flags_and_size >> 12) & 0xF) * 4
        if header_size < 12 or header_size > 60 or header_size % 4:
            return _unsupported_method_body(
                method_rva,
                raw_header,
                f"unsupported fat method header size: {header_size}",
            )

        max_stack = int.from_bytes(raw_header[2:4], "little")
        code_size = int.from_bytes(raw_header[4:8], "little")
        local_var_sig_tok = int.from_bytes(raw_header[8:12], "little")
        code = pe.get_data(method_rva + header_size, code_size)
        if len(code) != code_size:
            return _unsupported_method_body(
                method_rva,
                raw_header,
                f"truncated fat method body at RVA 0x{method_rva:x}",
            )

        local_signature = None
        if local_var_sig_tok >> 24 == 0x11 and getattr(mdtables, "StandAloneSig", None):
            rid = local_var_sig_tok & 0x00FFFFFF
            sig_row = mdtables.StandAloneSig.get_with_row_index(rid)
            if sig_row is not None:
                local_signature = sig_row.ParsedSignature

        exception_handlers = []
        if flags_and_size & COR_ILMETHOD_MORE_SECTS:
            exception_handlers = _parse_method_sections(pe, method_rva, header_size, code_size, mdtables)

        return MethodBody("fat", header_size, max_stack, code_size, local_var_sig_tok, code, local_signature, exception_handlers)
    except PEFormatError as error:
        return _unsupported_method_body(method_rva, raw_header, str(error))