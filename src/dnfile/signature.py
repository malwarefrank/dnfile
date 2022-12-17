"""
Parse signatures used to describe methods and other types.

These are found in #Blob entries as raw binary data.
They decode to things like: calling convention, return type, parameter types.
Some fields may include tokens that can be resolved via .NET header metadata;
however, this module does not rely on .NET metadata headers.

Tokens are captured as-is, as numbers with associated masks and shifts.
Its up to the user to resolve the reference to a row.
This is because we expect the user to know how they want to interpret/format data,
we couldn't guess at all the uses for interacting with signatures.

The best references for this parsing are:
  - ECMA-335 6th Edition, II.23.1 and II.23.2
  - https://github.com/0xd4d/dnlib/blob/master/src/DotNet/SignatureReader.cs
  - https://github.com/jimschubert/clr-profiler/blob/master/src/ILRewrite10Source/ILRewriteProfiler/sigparse.inl
"""

import io
import abc
import enum
import struct
from typing import Any, List, Union, Optional, Sequence

from dnfile.utils import ror

CALLING_CONVENTION_MASK = 0x0F


class CallingConvention(enum.Enum):
    DEFAULT  = 0x00

    # unmanaged cdecl is the calling convention used by Standard C
    C        = 0x1

    # unmanaged stdcall specifies a standard C++ call
    STDCALL  = 0x2

    # unmanaged thiscall is a C++ call that passes a this pointer to the method
    THISCALL = 0x3

    # unmanaged fastcall is a special optimized C++ calling convention
    FASTCALL = 0x4
    VARARG   = 0x5

    FIELD        = 0x6
    LOCALSIG     = 0x7
    PROPERTY     = 0x8
    # Unmanaged calling convention encoded as modopts
    UNMANAGED    = 0x9
    GENERICINST  = 0xA
    # used ONLY for 64bit vararg PInvoke calls
    NATIVEVARARG = 0xB

    def __str__(self):
        # II.15.3
        if self == CallingConvention.DEFAULT:
            # default is not displayed, by default :-)
            return ""
        elif self == CallingConvention.C:
            return "unmanaged cdelc"
        elif self == CallingConvention.FASTCALL:
            return "unmanaged fastcall"
        elif self == CallingConvention.STDCALL:
            return "unmanaged stdcall"
        elif self == CallingConvention.THISCALL:
            return "unmanaged thiscall"
        elif self == CallingConvention.VARARG:
            return "vararg"
        elif self == CallingConvention.FIELD:
            return ""
        else:
            # TODO: LOCALSIG
            # TODO: PROPERTY
            # TODO: UNMANAGED
            # TODO: GENERICINST
            # TODO: NATIVEVARARG
            raise NotImplementedError("calling convention: " + repr(self))


SIGNATURE_FLAGS_MASK = 0xF0


class SignatureFlags(enum.IntFlag):
    GENERIC = 0x10
    # > If the attribute instance is present,
    # > it indicates that a this pointer shall be passed to the method.
    # > This attribute shall be used for both instance and virtual methods.
    # via II.15.3
    HAS_THIS = 0x20
    # > When the combination instance explicit is specified, however,
    # > the first type in the subsequent parameter list specifies
    # > the type of the this pointer and subsequent entries specify
    # > the types of the parameters themselves.
    # via II.15.3
    EXPLICIT_THIS = 0x40


class ElementType(enum.Enum):
    """
    EMCA-335 6th edition II.23.1.16
    """
    END          = 0x00  # Marks end of a list
    VOID         = 0x01
    BOOLEAN      = 0x02
    CHAR         = 0x03
    I1           = 0x04
    U1           = 0x05
    I2           = 0x06
    U2           = 0x07
    I4           = 0x08
    U4           = 0x09
    I8           = 0x0a
    U8           = 0x0b
    R4           = 0x0c
    R8           = 0x0d
    STRING       = 0x0e
    PTR          = 0x0f  # Followed by type
    BYREF        = 0x10  # Followed by type
    VALUETYPE    = 0x11  # Followed by TypeDef or TypeRef token
    CLASS        = 0x12  # Followed by TypeDef or TypeRef token
    VAR          = 0x13  # Generic parameter in a generic type definition, represented as number (compressed unsigned integer)
    ARRAY        = 0x14  # type rank boundsCount bound1 ... loCount lo1 ...
    GENERICINST  = 0x15  # Generic type instantiation. Followed by type type-arg-count type-1 ... type-n
    TYPEDBYREF   = 0x16
    I            = 0x18  # System.IntPtr
    U            = 0x19  # System.UIntPtr
    FNPTR        = 0x1b  # Followed by full method signature
    OBJECT       = 0x1c  # System.Object
    SZARRAY      = 0x1d  # Single-dim array with 0 lower bound
    MVAR         = 0x1e  # Generic parameter in a generic method definition, represented as number (compressed unsigned integer)
    CMOD_REQD    = 0x1f  # Required modifier : followed by a TypeDef or TypeRef token
    CMOD_OPT     = 0x20  # Optional modifier : followed by a TypeDef or TypeRef token
    INTERNAL     = 0x21  # Implemented within the CLI
    MODIFIER     = 0x40  # Or’d with following element types
    SENTINEL     = 0x41  # Sentinel for vararg method signature
    PINNED       = 0x45  # Denotes a local variable that points at a pinned object
    SYSTEM_TYPE  = 0x50  # Indicates an argument of type System.Type.
    BOXED_OBJECT = 0x51  # Used in custom attributes to specify a boxed object (§II.23.3).
    RESERVED     = 0x52  # Reserved
    FIELD        = 0x53  # Used in custom attributes to indicate a FIELD (§II.22.10, II.23.3).
    PROPERTY     = 0x54  # Used in custom attributes to indicate a PROPERTY (§II.22.10, II.23.3).
    ENUM         = 0x55  # Used in custom attributes to specify an enum (§II.23.3).

    def is_primitive(self):
        return ElementType.VOID.value <= self.value <= ElementType.STRING.value

    def is_simple_type(self):
        # https://referencesource.microsoft.com/mscorlib/system/reflection/emit/signaturehelper.cs.html
        return self.is_primitive() or self.value in (
                ElementType.TYPEDBYREF.value,
                ElementType.I.value,
                ElementType.U.value,
                ElementType.OBJECT.value,
                )


class Element:
    def __init__(self, ty: ElementType, value: Optional[Any] = None):
        self.cor_type = ty
        self.value = value

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Element):
            return False
        if __o.cor_type != self.cor_type:
            return False
        if __o.value != self.value:
            return False
        return True

    def __str__(self):
        if self.cor_type == ElementType.VOID:
            return "void"
        elif self.cor_type == ElementType.BOOLEAN:
            return "boolean"
        elif self.cor_type == ElementType.CHAR:
            return "char"
        elif self.cor_type == ElementType.I1:
            return "sbyte"
        elif self.cor_type == ElementType.U1:
            return "byte"
        elif self.cor_type == ElementType.I2:
            return "int16"
        elif self.cor_type == ElementType.U2:
            return "uint16"
        elif self.cor_type == ElementType.I4:
            return "int32"
        elif self.cor_type == ElementType.U4:
            return "uint32"
        elif self.cor_type == ElementType.I8:
            return "int64"
        elif self.cor_type == ElementType.U8:
            return "uint64"
        elif self.cor_type == ElementType.R4:
            return "single"
        elif self.cor_type == ElementType.R8:
            return "double"
        elif self.cor_type == ElementType.STRING:
            return "string"
        elif self.cor_type == ElementType.OBJECT:
            return "object"
        elif self.cor_type == ElementType.I:
            return "IntPtr"
        elif self.cor_type == ElementType.U:
            return "UIntPtr"
        elif self.cor_type == ElementType.TYPEDBYREF:
            return "TypedReference"
        elif self.cor_type == ElementType.VALUETYPE:
            # a TypeDefOrRefToken, not resolved here.
            # leave it up to some caller to resolve and render as they see fit.
            return f"valuetype {str(self.value)}"
        elif self.cor_type == ElementType.PTR:
            return f"ptr {str(self.value)}"
        elif self.cor_type == ElementType.BYREF:
            return f"byref {str(self.value)}"
        elif self.cor_type == ElementType.SZARRAY:
            return f"{str(self.value)}[]"
        elif self.cor_type == ElementType.CLASS:
            return str(self.value)
        elif self.cor_type == ElementType.VAR or self.cor_type == ElementType.MVAR:
            return f"{str(self.cor_type)} {str(self.value)}"
        elif self.cor_type == ElementType.CMOD_OPT or self.cor_type == ElementType.CMOD_REQD:
            return f"{str(self.cor_type)} {str(self.value)}"
        elif self.cor_type == ElementType.FNPTR:
            return f"FNPTR {str(self.value)}"
        # ARRAY handled by subclass
        # GENERICINST handled by subclass
        else:
            # TODO: INTERNAL
            # TODO: MODIFIER
            # TODO: SENTINEL
            # TODO: PINNED
            # TODO: SYSTEM_TYPE
            # TODO: BOXED_OBJECT
            # TODO: RESERVED
            # TODO: FIELD
            # TODO: PROPERTY
            # TODO: ENUM
            raise NotImplementedError("type: " + repr(self.cor_type))


class GenericInstElement(Element):
    """
    This is a special case of Element as it may include type args.
    """
    def __init__(self, ty: ElementType, value: Optional[Any] = None, arg_types: Optional[List[Element]] = None):
        super().__init__(ty, value)
        # GenericInst may have type args
        self.arg_types = arg_types

    def __str__(self):
        if self.cor_type == ElementType.GENERICINST:
            # TODO: test
            ret = f"GENERICINST {str(self.value)}"
            if self.arg_types:
                ret += f"<{str(self.arg_types[0])}"
                for arg_type in self.arg_types[1:]:
                    ret += f", {str(arg_type)}"
                ret += ">"
            return ret
        else:
            return super().__str__()


class ArrayElement(Element):
    """
    This is a special case of Element as it includes rank, bounds, and low_bounds
    """

    def __init__(self, ty: ElementType, value: Optional[Any] = None, rank: Optional[int] = None, bounds: Optional[List[int]] = None, low_bounds: Optional[List[int]] = None):
        super().__init__(ty, value)
        self.rank = rank
        self.bounds = bounds
        self.low_bounds = low_bounds

    def __str__(self):
        if self.cor_type == ElementType.ARRAY:
            # TODO: test
            ret = f"{str(self.value)}"
            for i in range(self.rank):
                if i < len(self.low_bounds):
                    low = self.low_bounds[i]
                    if i < len(self.bounds):
                        size = self.bounds[i]
                    else:
                        size = 0
                    ret += f"[{low}:{size}]"
                elif i < len(self.bounds):
                    ret += f"[{self.bounds[i]}]"
            return ret
        else:
            return super().__str__()


class MethodSignature:
    def __init__(self, flags: SignatureFlags, calling_convention: CallingConvention, ret: Element, params: List[Element], generic_params_count: int = 0):
        self.flags = flags
        self.calling_convention = calling_convention
        self.ret = ret
        self.params = params
        self.generic_params_count: int = generic_params_count

    # TODO: __eq__
    # Equality is complicated, see ECMA-335 I.8.6.1.6:
    #     the calling conventions are identical;
    #     both signatures are either static or instance;
    #     the number of generic parameters is identical, if the method is generic;
    #     for instance signatures the type of the this pointer of the overriding/hiding
    #       signature is assignable-to (I.8.7) the type of the this pointer of the
    #       overridden/hidden signature;
    #     the number and type signatures of the parameters are identical; and
    #     the type signatures for the result are identical. [ Note: This includes void
    #       (II.23.2.11) if no value is returned. end note]
    #     Note: when overriding/hiding the accessibility of items need not be identical

    def __str__(self):
        parts = []

        # II.15.3
        if self.flags & SignatureFlags.HAS_THIS:
            parts.append("instance ")
        if self.flags & SignatureFlags.EXPLICIT_THIS:
            parts.append("explicit ")

        parts.append(str(self.calling_convention))
        if parts[-1]:
            # if calling convention is `default` then nothing is displayed.
            # so, don't add extra spacing
            parts.append(" ")

        parts.append(str(self.ret))
        parts.append(" ")

        parts.append("f")

        if self.flags & SignatureFlags.GENERIC:
            parts.append("<")
            i=0
            for i in range(self.generic_params_count):
                if i>0:
                    parts.append(",")
                parts.append(f"T{i}")
            parts.append(">")

        parts.append("(")
        parts.extend(
            ", ".join(map(str, self.params))
        )
        parts.append(")")

        return "".join(parts)


class FieldSignature:
    def __init__(self, flags: SignatureFlags, calling_convention: CallingConvention, ty: Element):
        self.flags = flags
        self.calling_convention = calling_convention
        self.cor_type = ty

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, FieldSignature):
            return False
        if __o.flags != self.flags:
            return False
        if __o.calling_convention != self.calling_convention:
            return False
        if __o.cor_type != self.cor_type:
            return False
        return True

    def __str__(self):
        parts = []

        # II.15.3
        if self.flags & SignatureFlags.HAS_THIS:
            parts.append("instance ")
        if self.flags & SignatureFlags.EXPLICIT_THIS:
            parts.append("explicit ")

        parts.append(str(self.calling_convention))
        if parts[-1]:
            # if calling convention is `default` then nothing is displayed.
            # so, don't add extra spacing
            parts.append(" ")

        parts.append(str(self.cor_type))
        return "".join(parts)


class LocalSignature:
    def __init__(self, flags: SignatureFlags, calling_convention: CallingConvention, locals: List[Element]):
        self.flags = flags
        self.calling_convention = calling_convention
        self.locals = locals

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, LocalSignature):
            return False
        if __o.flags != self.flags:
            return False
        if __o.calling_convention != self.calling_convention:
            return False
        if len(__o.locals) != len(self.locals):
            return False
        for i in range(len(self.locals)):
            if __o.locals[i] != self.locals[i]:
                return False
        return True

    def __str__(self):
        parts = []

        for i, local in enumerate(self.locals):
            parts.append(f"[{i}] {str(local)}")

        return "(" + ", ".join(parts) + ")"


class Token(abc.ABC):
    @property
    @abc.abstractmethod
    def table_index(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def row_index(self) -> int:
        ...

    def __init__(self, value: int):
        self.value: int = value


class CodedToken(Token):
    # this class sort-of duplicates .base.CodedIndex;
    # however, that class requires access to .NET metadata headers,
    # whereas this class doesn't attempt to resolve any tokens to rows.
    #
    # its up to the user to decide how and when to resolve rows.

    # subclasses must override these
    tag_bits: int = 0
    table_indices: Sequence[int] = ()
    table_names: Sequence[str] = ()

    def __init__(self, value: int):
        assert self.__class__.tag_bits != 0
        assert self.__class__.table_indices != ()
        assert self.__class__.table_names != ()
        super(CodedToken, self).__init__(value)

    @property
    def table_index(self):
        return self.table_indices[self.value & (2 ** self.tag_bits - 1)]

    @property
    def table_name(self):
        return self.table_names[self.value & (2 ** self.tag_bits - 1)]

    @property
    def row_index(self):
        return self.value >> self.tag_bits

    def __str__(self):
        return f"token(table: {self.table_name}, row: {self.row_index})"


class TypeDefOrRefToken(CodedToken):
    tag_bits = 2
    table_names = ("TypeDef", "TypeRef", "TypeSpec")
    table_indices = (2, 1, 27)


class SignatureReader(io.BytesIO):
    """
    stateful binary parser that reads structures from a stream of data.
    """

    def peek_u8(self):
        v = self.read_u8()
        self.seek(-1, io.SEEK_CUR)
        return v

    def read_u8(self):
        buf = self.read(1)
        if len(buf) == 0:
            raise ValueError("SignatureReader::read_u8 - Unexpected end of data")
        return buf[0]

    def read_compressed_u32(self):
        """
        Read a compressed, unsigned integer per
        spec ECMA-335 II.23.2 Blobs and signatures (page 283).
        """
        b1 = self.read_u8()
        if b1 & 0x80 == 0:
            return struct.unpack(">B", bytes((b1, )))[0]
        elif b1 & 0x40 == 0:
            return struct.unpack(">H", bytes((b1 & 0x7F, self.read_u8())))[0]
        elif b1 & 0x20 == 0:
            return struct.unpack(">I", bytes((b1 & 0x3F, self.read_u8(), self.read_u8(), self.read_u8())))[0]
        else:
            raise ValueError("invalid compressed int")

    def read_compressed_i32(self):
        """
        Read a compressed, signed integer per
        spec ECMA-335 II.23.2 Blobs and signatures (page 283).
        """
        b1 = self.read_u8()

        if b1 & 0x80 == 0:
            # 7-bit, 1-byte integer
            n = b1

            # rotate right one bit, 7-bit number
            n = ror(n, 1, 7)

            # sign-extend 7-bit number to 8-bits
            if n & (1 << 6):
                n |= (1 << 7)

            # reinterpret as 8-bit, 1-byte, signed, big-endian integer
            return struct.unpack(">b", struct.pack(">B", n))[0]
        elif b1 & 0x40 == 0:
            # 14-bit, 2-byte, big-endian integer
            n = struct.unpack(">h", bytes((b1 & 0x7F, self.read_u8())))[0]

            # rotate right one bit, 14-bit number
            n = ror(n, 1, 14)

            # sign-extend 14-bit number to 16-bits
            if n & (1 << 13):
                n |= (1 << 14) | (1 << 15)

            # reinterpret as 16-bit, 2-byte, signed, big-endian integer
            return struct.unpack(">h", struct.pack(">H", n))[0]
        elif b1 & 0x20 == 0:
            # 29-bit, three byte, big endian integer
            n = struct.unpack(">i", bytes((b1 & 0x3F, self.read_u8(), self.read_u8(), self.read_u8())))[0]

            # rotate right one bit, 29-bit number
            n = ror(n, 1, 29)

            # sign-extend 29-bit number to 32-bits
            if n & (1 << 28):
                n |= (1 << 29) | (1 << 30) | (1 << 31)

            # reinterpret as 32-bit, 4-byte, signed, big-endian integer
            return struct.unpack(">i", struct.pack(">I", n))[0]
        else:
            raise ValueError("invalid compressed int")

    def read_token(self) -> int:
        return self.read_compressed_u32()

    def read_type(self) -> Element:
        ty = ElementType(self.read_u8())
        if ty.is_primitive():
            return Element(ty)
        elif ty.is_simple_type():
            return Element(ty)
        elif ty == ElementType.END:
            return Element(ty)
        elif ty == ElementType.PTR:
            val = self.read_type()
            return Element(ty, val)
        elif ty == ElementType.BYREF:
            val = self.read_type()
            return Element(ty, val)
        elif ty == ElementType.VALUETYPE:
            token = TypeDefOrRefToken(self.read_token())
            return Element(ty, token)
        elif ty == ElementType.CLASS:
            token = TypeDefOrRefToken(self.read_token())
            return Element(ty, token)
        elif ty == ElementType.SZARRAY:
            val = self.read_type()
            return Element(ty, val)
        elif ty == ElementType.GENERICINST:
            # TODO: test
            # type
            val = self.read_type()
            # type-arg-count
            arg_count = self.read_compressed_u32()
            # types
            arg_types = list()
            for _ in range(arg_count):
                arg_types.append(self.read_type())
            return GenericInstElement(ty, val, arg_types)
        elif ty == ElementType.VAR or ty == ElementType.MVAR:
            val = self.read_compressed_u32()  # index into generics/template list?
            return Element(ty, val)
        elif ty == ElementType.ARRAY:
            # TODO: test
            # type
            val = self.read_type()
            # number of dimensions
            rank = self.read_compressed_u32()
            # size
            bound_count = self.read_compressed_u32()
            if bound_count > rank:
                # this shouldn't happen!  TODO: warn
                bound_count = rank
            bounds = list()
            for _ in range(bound_count):
                bound = self.read_compressed_i32()
                bounds.append(bound)
            # lower bounds
            low_bound_count = self.read_compressed_u32()
            if low_bound_count > rank:
                # this shouldn't happen!  TODO: warn
                low_bound_count = rank
            low_bounds = list()
            for _ in range(low_bound_count):
                low_bound = self.read_compressed_i32()
                low_bounds.append(low_bound)
            return ArrayElement(ty, val, rank, bounds, low_bounds)
        elif ty == ElementType.CMOD_OPT or ty == ElementType.CMOD_REQD:
            token = TypeDefOrRefToken(self.read_token())
            return Element(ty, token)
        elif ty == ElementType.FNPTR:
            method_sig = self.read_method_signature()
            return Element(ty, method_sig)
        else:
            # TODO: INTERNAL
            # TODO: MODIFIER
            # TODO: SENTINEL
            # TODO: PINNED
            # TODO: SYSTEM_TYPE
            # TODO: BOXED_OBJECT
            # TODO: RESERVED
            # TODO: FIELD
            # TODO: PROPERTY
            # TODO: ENUM
            raise NotImplementedError(ty)

    def read_method_signature(self) -> MethodSignature:
        b1 = self.read_u8()

        flags = SignatureFlags(b1 & SIGNATURE_FLAGS_MASK)
        calling_convention = CallingConvention(b1 & CALLING_CONVENTION_MASK)

        generic_param_count = 0
        if flags & SignatureFlags.GENERIC:
            generic_param_count = self.read_compressed_u32()

        # TODO: this is complicated, see ECMA-335 I.8.6.1.5

        param_count = self.read_compressed_u32()

        ret_type = self.read_type()

        params = []
        for _ in range(param_count):
            param = self.read_type()

            if calling_convention == CallingConvention.VARARG:
                if param.cor_type == ElementType.SENTINEL:
                    params.append(param)
                    param = self.read_type()

            params.append(param)

        return MethodSignature(flags, calling_convention, ret_type, params, generic_param_count)

    def read_field_signature(self) -> FieldSignature:
        b1 = self.read_u8()

        flags = SignatureFlags(b1 & SIGNATURE_FLAGS_MASK)
        calling_convention = CallingConvention(b1 & CALLING_CONVENTION_MASK)

        assert calling_convention == CallingConvention.FIELD

        ty = self.read_type()

        return FieldSignature(flags, calling_convention, ty)

    def read_local_signature(self) -> LocalSignature:
        b1 = self.read_u8()

        flags = SignatureFlags(b1 & SIGNATURE_FLAGS_MASK)
        calling_convention = CallingConvention(b1 & CALLING_CONVENTION_MASK)

        assert calling_convention == CallingConvention.LOCALSIG

        count = self.read_compressed_u32()

        locals = []
        for _ in range(count):
            locals.append(self.read_type())

        return LocalSignature(flags, calling_convention, locals)

    def read_signature(self) -> Union[MethodSignature, FieldSignature, LocalSignature]:
        b1 = self.peek_u8()

        calling_convention = CallingConvention(b1 & CALLING_CONVENTION_MASK)
        if (calling_convention == CallingConvention.DEFAULT
                or calling_convention == CallingConvention.C
                or calling_convention == CallingConvention.STDCALL
                or calling_convention == CallingConvention.THISCALL
                or calling_convention == CallingConvention.FASTCALL
                or calling_convention == CallingConvention.VARARG
                or calling_convention == CallingConvention.UNMANAGED
                or calling_convention == CallingConvention.NATIVEVARARG):
            return self.read_method_signature()

        elif calling_convention == CallingConvention.FIELD:
            return self.read_field_signature()

        elif calling_convention == CallingConvention.LOCALSIG:
            return self.read_local_signature()

        elif calling_convention == CallingConvention.PROPERTY:
            raise NotImplementedError("calling convention property")
        elif calling_convention == CallingConvention.GENERICINST:
            raise NotImplementedError("calling convention genericinst")
        else:
            raise ValueError("unexpected calling convention")


Signature = Union[MethodSignature, FieldSignature, LocalSignature]


def parse_signature(buf: bytes) -> Signature:
    return SignatureReader(buf).read_signature()


def parse_method_signature(buf: bytes) -> MethodSignature:
    return SignatureReader(buf).read_method_signature()


def parse_field_signature(buf: bytes) -> FieldSignature:
    return SignatureReader(buf).read_field_signature()


def parse_local_signature(buf: bytes) -> LocalSignature:
    return SignatureReader(buf).read_local_signature()
