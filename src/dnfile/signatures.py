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
    number: Optional[int] = None
    type_token: Optional[int] = None
    generic_kind: Optional[str] = None
    arguments: Optional[List["TypeSignature"]] = None
    inner: Optional["TypeSignature"] = None
    kind: str = "type"


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


@dataclass(frozen=True)
class MethodSpecInstantiation:
    kind: str
    argument_count: int
    arguments: List[TypeSignature]


ParsedSignature = Union[MethodSignature, LocalVarSignature, TypeSignature, UnsupportedSignature]


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
            return TypeSignature(element_type="VOID")
        if element == 0x02:
            return TypeSignature(element_type="BOOLEAN")
        if element == 0x03:
            return TypeSignature(element_type="CHAR")
        if element == 0x05:
            return TypeSignature(element_type="U1")
        if element == 0x08:
            return TypeSignature(element_type="I4")
        if element == 0x0E:
            return TypeSignature(element_type="STRING")
        if element == 0x11:
            return TypeSignature(element_type="VALUETYPE", type_token=self.read_compressed_int())
        if element == 0x12:
            return TypeSignature(element_type="CLASS", type_token=self.read_compressed_int())
        if element == 0x13:
            return TypeSignature(element_type="VAR", number=self.read_compressed_int())
        if element == 0x15:
            generic_kind = self.read_byte()
            if generic_kind == 0x11:
                generic_kind_name = "VALUETYPE"
            elif generic_kind == 0x12:
                generic_kind_name = "CLASS"
            else:
                raise errors.dnFormatError(f"unsupported genericinst kind: 0x{generic_kind:02x}")
            type_token = self.read_compressed_int()
            argument_count = self.read_compressed_int()
            arguments = [self.parse_type() for _ in range(argument_count)]
            return TypeSignature(
                element_type="GENERICINST",
                generic_kind=generic_kind_name,
                type_token=type_token,
                arguments=arguments,
            )
        if element == 0x1D:
            return TypeSignature(element_type="SZARRAY", inner=self.parse_type())
        if element == 0x1E:
            return TypeSignature(element_type="MVAR", number=self.read_compressed_int())
        raise errors.dnFormatError(f"unsupported element type: 0x{element:02x}")


def parse_type_signature(blob) -> ParsedSignature:
    if blob is None:
        return UnsupportedSignature(kind="unsupported", raw=b"", reason="missing signature")

    raw = blob.value_bytes() if hasattr(blob, "value_bytes") else bytes(blob)
    try:
        return _SignatureReader(raw).parse_type()
    except errors.dnFormatError as error:
        return UnsupportedSignature(kind="unsupported", raw=raw, reason=str(error))


def parse_method_spec_instantiation(blob) -> Union[MethodSpecInstantiation, UnsupportedSignature]:
    if blob is None:
        return UnsupportedSignature(kind="unsupported", raw=b"", reason="missing signature")

    raw = blob.value_bytes() if hasattr(blob, "value_bytes") else bytes(blob)
    try:
        reader = _SignatureReader(raw)
        prefix = reader.read_byte()
        if prefix != 0x0A:
            raise errors.dnFormatError(f"unsupported methodspec prefix: 0x{prefix:02x}")
        argument_count = reader.read_compressed_int()
        arguments = [reader.parse_type() for _ in range(argument_count)]
        return MethodSpecInstantiation(kind="methodspec", argument_count=argument_count, arguments=arguments)
    except errors.dnFormatError as error:
        return UnsupportedSignature(kind="unsupported", raw=raw, reason=str(error))


def parse_signature(blob) -> ParsedSignature:
    if blob is None:
        return UnsupportedSignature(kind="unsupported", raw=b"", reason="missing signature")

    raw = blob.value_bytes() if hasattr(blob, "value_bytes") else bytes(blob)
    try:
        return _SignatureReader(raw).parse()
    except errors.dnFormatError as error:
        return UnsupportedSignature(kind="unsupported", raw=raw, reason=str(error))