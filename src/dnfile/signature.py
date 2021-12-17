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
  - dnlib SignatureReader.cs
"""

import io
import abc
import enum
import struct
from typing import Any, List, Optional, Sequence

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
        else:
            # TODO: FIELD
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


class Element:
    def __init__(self, ty: ElementType, value: Optional[Any] = None):
        self.ty = ty
        self.value = value

    def __str__(self):
        if self.ty == ElementType.VOID:
            return "void"
        elif self.ty == ElementType.BOOLEAN:
            return "boolean"
        elif self.ty == ElementType.CHAR:
            return "char"
        elif self.ty == ElementType.I1:
            return "int8"
        elif self.ty == ElementType.U1:
            return "uint8"
        elif self.ty == ElementType.I2:
            return "int16"
        elif self.ty == ElementType.U2:
            return "uint16"
        elif self.ty == ElementType.I4:
            return "int32"
        elif self.ty == ElementType.U4:
            return "uint32"
        elif self.ty == ElementType.I8:
            return "int64"
        elif self.ty == ElementType.U8:
            return "uint64"
        elif self.ty == ElementType.R4:
            return "float"
        elif self.ty == ElementType.R8:
            return "double"
        elif self.ty == ElementType.STRING:
            return "string"
        elif self.ty == ElementType.VALUETYPE:
            # a TypeDefOrRefToken, not resolved here.
            # leave it up to some caller to resolve and render as they see fit.
            return f"valuetype {str(self.value)}"
        else:
            # TODO: PTR
            # TODO: BYREF
            # TODO: CLASS
            # TODO: VAR
            # TODO: ARRAY
            # TODO: GENERICINST
            # TODO: TYPEDBYREF
            # TODO: I
            # TODO: U
            # TODO: FNPTR
            # TODO: OBJECT
            # TODO: SZARRAY
            # TODO: MVAR
            # TODO: CMOD_REQD
            # TODO: CMOD_OPT
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
            raise NotImplementedError("type: " + repr(self))


class Signature:
    def __init__(self, flags: SignatureFlags, calling_convention: CallingConvention, ret: Element, params: List[Element]):
        self.flags = flags
        self.calling_convention = calling_convention
        self.ret = ret
        self.params = params

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
            # where do these come from?
            parts.append(">")
            raise NotImplementedError("generic arguments")

        parts.append("(")
        parts.extend(
            ", ".join(map(str, self.params))
        )
        parts.append(")")

        return "".join(parts)


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
    # this class sort-of duplicates dnlib.base.CodedIndex;
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
        return self.read(1)[0]

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
        else:
            # TODO: VAR
            # TODO: ARRAY
            # TODO: GENERICINST
            # TODO: TYPEDBYREF
            # TODO: I
            # TODO: U
            # TODO: FNPTR
            # TODO: OBJECT
            # TODO: SZARRAY
            # TODO: MVAR
            # TODO: CMOD_REQD
            # TODO: CMOD_OPT
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

    def read_method_signature(self) -> Signature:
        b1 = self.read_u8()

        flags = SignatureFlags(b1 & SIGNATURE_FLAGS_MASK)
        calling_convention = CallingConvention(b1 & CALLING_CONVENTION_MASK)

        if flags & SignatureFlags.GENERIC:
            generic_param_count = self.read_compressed_u32()
            raise NotImplementedError("generic calling convention")

        param_count = self.read_compressed_u32()

        ret_type = self.read_type()

        params = []
        for _ in range(param_count):
            param = self.read_type()

            if calling_convention == CallingConvention.VARARG:
                if param.ty == ElementType.SENTINEL:
                    params.append(param)
                    param = self.read_type()

            params.append(param)

        return Signature(flags, calling_convention, ret_type, params)

    def read_signature(self) -> Signature:
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
            raise NotImplementedError("calling convention field")
        elif calling_convention == CallingConvention.LOCALSIG:
            raise NotImplementedError("calling convention localsig")
        elif calling_convention == CallingConvention.PROPERTY:
            raise NotImplementedError("calling convention property")
        elif calling_convention == CallingConvention.GENERICINST:
            raise NotImplementedError("calling convention genericinst")
        else:
            raise ValueError("unexpected calling convention")


def parse_signature(buf: bytes) -> Signature:
    return SignatureReader(buf).read_signature()
