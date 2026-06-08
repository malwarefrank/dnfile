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
    signature: Optional["MethodSignature"] = None
    array_rank: Optional[int] = None
    array_sizes: Optional[List[int]] = None
    array_lower_bounds: Optional[List[int]] = None
    kind: str = "type"

    def to_programmer_string(self) -> str:
        if self.element_type == "VOID":
            return "void"
        if self.element_type == "BOOLEAN":
            return "bool"
        if self.element_type == "CHAR":
            return "char"
        if self.element_type == "I1":
            return "sbyte"
        if self.element_type == "U1":
            return "byte"
        if self.element_type == "I2":
            return "short"
        if self.element_type == "U2":
            return "ushort"
        if self.element_type == "I4":
            return "int"
        if self.element_type == "U4":
            return "uint"
        if self.element_type == "I8":
            return "long"
        if self.element_type == "U8":
            return "ulong"
        if self.element_type == "R4":
            return "float"
        if self.element_type == "R8":
            return "double"
        if self.element_type == "STRING":
            return "string"
        if self.element_type == "TYPEDBYREF":
            return "typedref"
        if self.element_type == "I":
            return "nint"
        if self.element_type == "U":
            return "nuint"
        if self.element_type == "OBJECT":
            return "object"
        if self.element_type == "SENTINEL":
            return "..."
        if self.element_type == "VAR":
            return f"T{self.number}"
        if self.element_type == "MVAR":
            return f"M{self.number}"
        if self.element_type == "VALUETYPE":
            return f"valuetype 0x{self.type_token:x}"
        if self.element_type == "CLASS":
            return f"class 0x{self.type_token:x}"
        if self.element_type == "SZARRAY":
            return f"{self.inner.to_programmer_string()}[]" if self.inner is not None else "[]"
        if self.element_type == "PTR":
            return f"{self.inner.to_programmer_string()}*" if self.inner is not None else "*"
        if self.element_type == "BYREF":
            return f"ref {self.inner.to_programmer_string()}" if self.inner is not None else "ref"
        if self.element_type == "CMOD_REQD":
            modifier = f"modreq(0x{self.type_token:x})"
            return f"{modifier} {self.inner.to_programmer_string()}" if self.inner is not None else modifier
        if self.element_type == "CMOD_OPT":
            modifier = f"modopt(0x{self.type_token:x})"
            return f"{modifier} {self.inner.to_programmer_string()}" if self.inner is not None else modifier
        if self.element_type == "PINNED":
            return f"pinned {self.inner.to_programmer_string()}" if self.inner is not None else "pinned"
        if self.element_type == "GENERICINST":
            arguments = ", ".join(argument.to_programmer_string() for argument in self.arguments or [])
            return f"{self.generic_kind.lower()} 0x{self.type_token:x}<{arguments}>"
        if self.element_type == "ARRAY":
            inner = self.inner.to_programmer_string() if self.inner is not None else "?"
            if not self.array_rank or self.array_rank == 1:
                return f"{inner}[]"
            return f"{inner}[{',' * (self.array_rank - 1)}]"
        if self.element_type == "FNPTR":
            return f"fnptr {self.signature.to_programmer_string() if self.signature is not None else '()'}"
        if self.element_type == "OBJECT":
            return "object"
        return self.element_type.lower()

    def __str__(self) -> str:
        return self.to_programmer_string()


@dataclass(frozen=True)
class MethodSignature:
    kind: str
    has_this: bool
    explicit_this: bool
    generic_param_count: int
    parameter_count: int
    return_type: TypeSignature
    parameters: List[TypeSignature]

    def to_programmer_string(self, name: Optional[str] = None) -> str:
        parameter_text = ", ".join(parameter.to_programmer_string() for parameter in self.parameters)
        if name is None:
            return f"{self.return_type.to_programmer_string()}({parameter_text})"

        if self.generic_param_count:
            generic_arguments = ", ".join(f"T{i}" for i in range(self.generic_param_count))
            name = f"{name}<{generic_arguments}>"

        return f"{self.return_type.to_programmer_string()} {name}({parameter_text})"

    def __str__(self) -> str:
        return self.to_programmer_string()


@dataclass(frozen=True)
class LocalVarSignature:
    kind: str
    locals: List[TypeSignature]

    def __str__(self) -> str:
        locals_text = ", ".join(local.to_programmer_string() for local in self.locals)
        return f"locals({locals_text})"


@dataclass(frozen=True)
class UnsupportedSignature:
    kind: str
    raw: bytes
    reason: str

    def __str__(self) -> str:
        return f"unsupported signature: {self.reason}"


@dataclass(frozen=True)
class MethodSpecInstantiation:
    kind: str
    argument_count: int
    arguments: List[TypeSignature]

    def __str__(self) -> str:
        arguments_text = ", ".join(argument.to_programmer_string() for argument in self.arguments)
        return f"methodspec({arguments_text})"


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

    def _parse_wrapped_type(self, element_type: str, *, type_token: Optional[int] = None) -> TypeSignature:
        return TypeSignature(
            element_type=element_type,
            type_token=type_token,
            inner=self.parse_type(),
        )

    def _parse_array_type(self) -> TypeSignature:
        inner = self.parse_type()
        rank = self.read_compressed_int()
        size_count = self.read_compressed_int()
        sizes = [self.read_compressed_int() for _ in range(size_count)]
        lower_bound_count = self.read_compressed_int()
        lower_bounds = [self.read_compressed_int() for _ in range(lower_bound_count)]
        return TypeSignature(
            element_type="ARRAY",
            number=rank,
            inner=inner,
            array_rank=rank,
            array_sizes=sizes,
            array_lower_bounds=lower_bounds,
        )

    def _parse_fnptr_type(self) -> TypeSignature:
        return TypeSignature(element_type="FNPTR", signature=self.parse_method_sig())

    def parse_type(self) -> TypeSignature:
        element = self.read_byte()
        simple_types = {
            0x01: "VOID",
            0x02: "BOOLEAN",
            0x03: "CHAR",
            0x04: "I1",
            0x05: "U1",
            0x06: "I2",
            0x07: "U2",
            0x08: "I4",
            0x09: "U4",
            0x0A: "I8",
            0x0B: "U8",
            0x0C: "R4",
            0x0D: "R8",
            0x0E: "STRING",
            0x16: "TYPEDBYREF",
            0x18: "I",
            0x19: "U",
            0x1C: "OBJECT",
            0x41: "SENTINEL",
        }
        if element in simple_types:
            return TypeSignature(element_type=simple_types[element])
        if element == 0x0F:
            return self._parse_wrapped_type("PTR")
        if element == 0x10:
            return self._parse_wrapped_type("BYREF")
        if element == 0x11:
            return TypeSignature(element_type="VALUETYPE", type_token=self.read_compressed_int())
        if element == 0x12:
            return TypeSignature(element_type="CLASS", type_token=self.read_compressed_int())
        if element == 0x13:
            return TypeSignature(element_type="VAR", number=self.read_compressed_int())
        if element == 0x14:
            return self._parse_array_type()
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
        if element == 0x1B:
            return self._parse_fnptr_type()
        if element == 0x1D:
            return self._parse_wrapped_type("SZARRAY")
        if element == 0x1E:
            return TypeSignature(element_type="MVAR", number=self.read_compressed_int())
        if element == 0x1F:
            return self._parse_wrapped_type("CMOD_REQD", type_token=self.read_compressed_int())
        if element == 0x20:
            return self._parse_wrapped_type("CMOD_OPT", type_token=self.read_compressed_int())
        if element == 0x45:
            return self._parse_wrapped_type("PINNED")
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