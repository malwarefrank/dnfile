# -*- coding: utf-8 -*-
"""
.NET signature blob parsing.
"""

from dataclasses import dataclass
from typing import List, Optional, Union

from . import errors, utils


@dataclass(frozen=True)
class TypeSignature:
    element_type: str
    inner: Optional["TypeSignature"] = None


@dataclass(frozen=True)
class MethodSignature:
    kind: str
    has_this: bool
    explicit_this: bool
    generic_param_count: int
    parameter_count: int
    return_type: TypeSignature
    parameters: List[TypeSignature]


@dataclass(frozen=True)
class LocalVarSignature:
    kind: str
    locals: List[TypeSignature]


@dataclass(frozen=True)
class UnsupportedSignature:
    kind: str
    raw: bytes
    reason: str


ParsedSignature = Union[MethodSignature, LocalVarSignature, UnsupportedSignature]


class _SignatureReader:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.offset = 0

    def read_byte(self) -> int:
        if self.offset >= len(self.raw):
            raise errors.dnFormatError("unexpected end of signature blob")
        value = self.raw[self.offset]
        self.offset += 1
        return value

    def read_compressed_int(self) -> int:
        result = utils.read_compressed_int(self.raw[self.offset:self.offset + 4])
        if result is None:
            raise errors.dnFormatError("invalid compressed integer in signature")
        value, size = result
        self.offset += size
        return value

    def parse(self) -> Union[MethodSignature, LocalVarSignature]:
        if not self.raw:
            raise errors.dnFormatError("empty signature blob")

        if self.raw[0] == 0x07:
            return self.parse_local_sig()
        return self.parse_method_sig()

    def parse_local_sig(self) -> LocalVarSignature:
        self.read_byte()
        count = self.read_compressed_int()
        locals_ = [self.parse_type() for _ in range(count)]
        return LocalVarSignature(kind="locals", locals=locals_)

    def parse_method_sig(self) -> MethodSignature:
        flags = self.read_byte()
        generic_param_count = 0
        if flags & 0x10:
            generic_param_count = self.read_compressed_int()
        parameter_count = self.read_compressed_int()
        return_type = self.parse_type()
        parameters = [self.parse_type() for _ in range(parameter_count)]
        return MethodSignature(
            kind="method",
            has_this=bool(flags & 0x20),
            explicit_this=bool(flags & 0x40),
            generic_param_count=generic_param_count,
            parameter_count=parameter_count,
            return_type=return_type,
            parameters=parameters,
        )

    def parse_type(self) -> TypeSignature:
        element = self.read_byte()
        if element == 0x01:
            return TypeSignature("VOID")
        if element == 0x08:
            return TypeSignature("I4")
        if element == 0x0E:
            return TypeSignature("STRING")
        if element == 0x1D:
            return TypeSignature("SZARRAY", inner=self.parse_type())
        raise errors.dnFormatError(f"unsupported element type: 0x{element:02x}")


def parse_signature(blob) -> ParsedSignature:
    if blob is None:
        return UnsupportedSignature(kind="unsupported", raw=b"", reason="missing signature")

    raw = blob.value_bytes() if hasattr(blob, "value_bytes") else bytes(blob)
    try:
        return _SignatureReader(raw).parse()
    except errors.dnFormatError as error:
        return UnsupportedSignature(kind="unsupported", raw=raw, reason=str(error))