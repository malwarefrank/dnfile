# -*- coding: utf-8 -*-

import enum as _enum
from typing import Dict, Type, Iterable

########
# Most developers may just use the Clr* classes to automatically parse the
# flags defined in winsdk corhdr.h
#
# The definitions in winsdk corhdr.h may be accesses through the Cor* classes.


def _getvars(o):
    for attr in dir(o):
        if not callable(getattr(o, attr)) and not attr.startswith("_"):
            yield attr


class ClrMetaDataEnum(object):
    """
    Base class for CorHdr.h metadata enumerations.
    """
    pass


class ClrFlags(object):
    """
    Base class for CLR MetaData Tables' Flags.

    When instantiated, this class takes a value and sets member vars to True according to IntEnum's in _masks and _flags.

    Note that _flags are bitmasks that match on single bits, whereas _masks are enum values that match exact value.

    :var corhdr_enum:   the class that defines values from winsdk corhdr.h, likely not needed by most developers.
    :var _masks:        a dictionary that defines the masks and associated values (classes) to check and set if matching exactly.
    :var _flags:        an iterable of classes defining bit flags to check and set if set.
    """

    corhdr_enum: Type[ClrMetaDataEnum]
    _masks: Dict[str, Type[_enum.IntEnum]]
    _flags: Iterable[Type[_enum.IntEnum]]

    def __init__(self, value):

        for mask_name, enum_class in getattr(self, "_masks", {}).items():
            mask = getattr(self.corhdr_enum, mask_name)
            masked_value = mask & value
            enum_entry = enum_class(masked_value)
            for candidate_enum_entry in enum_class:
                setattr(self, candidate_enum_entry.name, candidate_enum_entry == enum_entry)

        for value_class in getattr(self, "_flags", {}):
            for m in value_class:
                setattr(self, m.name, (m.value & value) != 0)

    def __iter__(self):
        for name in _getvars(self):
            val = getattr(self, name)
            if isinstance(val, bool):
                yield name, val

    def __repr__(self):
        return '\n'.join(["{:<40}{:>8}".format(n, str(v)) for n, v in self])


class CorHeaderEnum(_enum.IntEnum):
    CLR_ILONLY          = 0x00000001
    CLR_32BITREQUIRED   = 0x00000002
    CLR_IL_LIBRARY      = 0x00000004
    CLR_STRONGNAMESIGNED    = 0x00000008
    CLR_NATIVE_ENTRYPOINT   = 0x00000010
    CLR_TRACKDEBUGDATA      = 0x00010000
    CLR_PREFER_32BIT        = 0x00020000


class ClrHeaderFlags(object):
    corhdr_enum = CorHeaderEnum

    CLR_ILONLY              = False
    CLR_32BITREQUIRED       = False
    CLR_IL_LIBRARY          = False
    CLR_STRONGNAMESIGNED    = False
    CLR_NATIVE_ENTRYPOINT   = False
    CLR_TRACKDEBUGDATA      = False
    CLR_PREFER_32BIT        = False

    def __init__(self, value):
        """
        Given a value, instantiates self with members set to True according to value.
        """
        for m in CorHeaderEnum:
            setattr(self, m.name, (m.value & value) != 0)

    def __iter__(self):
        for name in _getvars(self):
            if name.startswith("CLR_"):
                yield name, getattr(self, name)

    def __repr__(self):
        return '\n'.join(["{:<40}{:>8}".format(n, str(v)) for n, v in self])


####
# https://docs.microsoft.com/en-us/dotnet/framework/unmanaged-api/metadata/cortypeattr-enumeration

class CorTypeVisibility(_enum.IntEnum):
    tdNotPublic             =   0x00000000
    tdPublic                =   0x00000001
    tdNestedPublic          =   0x00000002
    tdNestedPrivate         =   0x00000003
    tdNestedFamily          =   0x00000004
    tdNestedAssembly        =   0x00000005
    tdNestedFamANDAssem     =   0x00000006
    tdNestedFamORAssem      =   0x00000007


class CorTypeLayout(_enum.IntEnum):
    tdAutoLayout            =   0x00000000
    tdSequentialLayout      =   0x00000008
    tdExplicitLayout        =   0x00000010


class CorTypeSemantics(_enum.IntEnum):
    tdClass                 =   0x00000000
    tdInterface             =   0x00000020


class CorTypeStringFormat(_enum.IntEnum):
    tdAnsiClass             =   0x00000000
    tdUnicodeClass          =   0x00010000
    tdAutoClass             =   0x00020000
    tdCustomFormatClass     =   0x00030000


class CorTypeAttrFlags(_enum.IntEnum):
    tdAbstract              =   0x00000080
    tdSealed                =   0x00000100
    tdSpecialName           =   0x00000400
    tdRTSpecialName         =   0x00000800
    tdImport                =   0x00001000
    tdSerializable          =   0x00002000
    tdWindowsRuntime        =   0x00004000
    tdHasSecurity           =   0x00040000
    tdBeforeFieldInit       =   0x00100000
    tdForwarder             =   0x00200000


class CorTypeAttr(ClrMetaDataEnum):
    # https://github.com/dotnet/docs/blob/main/docs/framework/unmanaged-api/metadata/cortypeattr-enumeration.md
    tdVisibilityMask        =   0x00000007
    enumVisibility          =   CorTypeVisibility

    tdLayoutMask            =   0x00000018
    enumLayout              =   CorTypeLayout

    tdClassSemanticsMask    =   0x00000020
    enumClassSemantics      =   CorTypeSemantics

    enumFlags               =   CorTypeAttrFlags

    tdStringFormatMask      =   0x00030000
    enumStringFormat        =   CorTypeStringFormat

    tdCustomFormatMask      =   0x00C00000

    tdReservedMask          =   0x00040800


class ClrTypeAttr(ClrFlags):
    tdNotPublic             = False
    tdPublic                = False
    tdNestedPublic          = False
    tdNestedPrivate         = False
    tdNestedFamily          = False
    tdNestedAssembly        = False
    tdNestedFamANDAssem     = False
    tdNestedFamORAssem      = False

    tdAutoLayout            = False
    tdSequentialLayout      = False
    tdExplicitLayout        = False

    tdClass                 = False
    tdInterface             = False

    tdAbstract              = False
    tdSealed                = False
    tdSpecialName           = False

    tdImport                = False
    tdSerializable          = False
    tdWindowsRuntime        = False

    tdAnsiClass             = False
    tdUnicodeClass          = False
    tdAutoClass             = False
    tdCustomFormatClass     = False

    tdCustomFormatValue     = None

    tdBeforeFieldInit       = False
    tdForwarder             = False

    tdRTSpecialName         = False
    tdHasSecurity           = False

    corhdr_enum = CorTypeAttr
    _masks = {
        "tdVisibilityMask": CorTypeVisibility,
        "tdLayoutMask": CorTypeLayout,
        "tdClassSemanticsMask": CorTypeSemantics,
        "tdStringFormatMask": CorTypeStringFormat,
    }
    _flags = (CorTypeAttrFlags, )


####
# https://www.ntcore.com/files/dotnetformat.htm

class CorFieldAccess(_enum.IntEnum):
    fdPrivateScope              =   0x0000      # Member not referenceable.
    fdPrivate                   =   0x0001      # Accessible only by the parent type.
    fdFamANDAssem               =   0x0002      # Accessible by sub-types only in this Assembly.
    fdAssembly                  =   0x0003      # Accessibly by anyone in the Assembly.
    fdFamily                    =   0x0004      # Accessible only by type and sub-types.
    fdFamORAssem                =   0x0005      # Accessibly by sub-types anywhere, plus anyone in assembly.
    fdPublic                    =   0x0006      # Accessibly by anyone who has visibility to this scope.
    fdUnknown1                  =   0x0007


class CorFieldAttrFlags(_enum.IntEnum):
    fdStatic                    =   0x0010      # Defined on type, else per instance.
    fdInitOnly                  =   0x0020      # Field may only be initialized, not written to after init.
    fdLiteral                   =   0x0040      # Value is compile time constant.
    fdNotSerialized             =   0x0080      # Field does not have to be serialized when type is remoted.

    fdSpecialName               =   0x0200      # field is special. Name describes how.

    # interop attributes
    fdPinvokeImpl               =   0x2000      # Implementation is forwarded through pinvoke.

    # Reserved flags for runtime use only.
    fdHasFieldRVA               =   0x0100      # Field has RVA.
    fdRTSpecialName             =   0x0400      # Runtime(metadata internal APIs) should check name encoding.
    fdHasFieldMarshal           =   0x1000      # Field has marshalling information.
    fdHasDefault                =   0x8000      # Field has default.


class CorFieldAttr(ClrMetaDataEnum):
    fdFieldAccessMask           =   0x0007      # member access mask - Use this mask to retrieve accessibility information.
    enumAccess                  =   CorFieldAccess

    enumFlags                       =   CorFieldAttrFlags

    # Reserved flags for runtime use only.
    fdReservedMask              =   0x9500


class ClrFieldAttr(ClrFlags):
    fdPrivateScope              = False         # Member not referenceable.
    fdPrivate                   = False         # Accessible only by the parent type.
    fdFamANDAssem               = False         # Accessible by sub-types only in this Assembly.
    fdAssembly                  = False         # Accessibly by anyone in the Assembly.
    fdFamily                    = False         # Accessible only by type and sub-types.
    fdFamORAssem                = False         # Accessibly by sub-types anywhere, plus anyone in assembly.
    fdPublic                    = False         # Accessibly by anyone who has visibility to this scope.
    # end member access mask

    # field contract attributes.
    fdStatic                    = False         # Defined on type, else per instance.
    fdInitOnly                  = False         # Field may only be initialized, not written to after init.
    fdLiteral                   = False         # Value is compile time constant.
    fdNotSerialized             = False         # Field does not have to be serialized when type is remoted.

    fdSpecialName               = False         # field is special. Name describes how.

    # interop attributes
    fdPinvokeImpl               = False         # Implementation is forwarded through pinvoke.

    # Reserved flags for runtime use only.
    fdRTSpecialName             = False         # Runtime(metadata internal APIs) should check name encoding.
    fdHasFieldMarshal           = False         # Field has marshalling information.
    fdHasDefault                = False         # Field has default.
    fdHasFieldRVA               = False         # Field has RVA.

    corhdr_enum = CorFieldAttr
    _masks = {
        "fdFieldAccessMask": CorFieldAccess,
    }
    _flags = (CorFieldAttrFlags, )


class CorMethodMemberAccess(_enum.IntEnum):
    mdPrivateScope              =   0x0000      # Member not referenceable.
    mdPrivate                   =   0x0001      # Accessible only by the parent type.
    mdFamANDAssem               =   0x0002      # Accessible by sub-types only in this Assembly.
    mdAssem                     =   0x0003      # Accessibly by anyone in the Assembly.
    mdFamily                    =   0x0004      # Accessible only by type and sub-types.
    mdFamORAssem                =   0x0005      # Accessibly by sub-types anywhere, plus anyone in assembly.
    mdPublic                    =   0x0006      # Accessibly by anyone who has visibility to this scope.
    mdUnknown1                  =   0x0007


class CorMethodAttrFlags(_enum.IntEnum):
    # method contract attributes.
    mdStatic                    =   0x0010      # Defined on type, else per instance.
    mdFinal                     =   0x0020      # Method may not be overridden.
    mdVirtual                   =   0x0040      # Method virtual.
    mdHideBySig                 =   0x0080      # Method hides by name+sig, else just by name.

    # method implementation attributes.
    mdCheckAccessOnOverride     =   0x0200      # Overridability is the same as the visibility.
    mdAbstract                  =   0x0400      # Method does not provide an implementation.
    mdSpecialName               =   0x0800      # Method is special. Name describes how.

    # interop attributes
    mdPinvokeImpl               =   0x2000      # Implementation is forwarded through pinvoke.
    mdUnmanagedExport           =   0x0008      # Managed method exported via thunk to unmanaged code.

    # Reserved flags for runtime use only.
    mdRTSpecialName             =   0x1000      # Runtime should check name encoding.
    mdHasSecurity               =   0x4000      # Method has security associate with it.
    mdRequireSecObject          =   0x8000      # Method calls another method containing security code.


class CorMethodVtableLayout(_enum.IntEnum):
    mdReuseSlot                 =   0x0000      # The default.
    mdNewSlot                   =   0x0100      # Method always gets a new slot in the vtable.


class CorMethodAttr(ClrMetaDataEnum):
    # member access mask - Use this mask to retrieve accessibility information.
    mdMemberAccessMask          =   0x0007
    enumAccess                  =   CorMethodMemberAccess

    enumFlags                       =   CorMethodAttrFlags

    # vtable layout mask - Use this mask to retrieve vtable attributes.
    mdVtableLayoutMask          =   0x0100
    enumVtableLayout            =   CorMethodVtableLayout

    # Reserved flags for runtime use only.
    mdReservedMask              =   0xd000


class ClrMethodAttr(ClrFlags):
    mdPrivateScope              = False         # Member not referenceable.
    mdPrivate                   = False         # Accessible only by the parent type.
    mdFamANDAssem               = False         # Accessible by sub-types only in this Assembly.
    mdAssem                     = False         # Accessibly by anyone in the Assembly.
    mdFamily                    = False         # Accessible only by type and sub-types.
    mdFamORAssem                = False         # Accessibly by sub-types anywhere, plus anyone in assembly.
    mdPublic                    = False         # Accessibly by anyone who has visibility to this scope.
    # end member access mask

    # method contract attributes.
    mdStatic                    = False         # Defined on type, else per instance.
    mdFinal                     = False         # Method may not be overridden.
    mdVirtual                   = False         # Method virtual.
    mdHideBySig                 = False         # Method hides by name+sig, else just by name.

    # vtable layout
    mdReuseSlot                 = False         # The default.
    mdNewSlot                   = False         # Method always gets a new slot in the vtable.

    # method implementation attributes.
    mdCheckAccessOnOverride     = False         # Overridability is the same as the visibility.
    mdAbstract                  = False         # Method does not provide an implementation.
    mdSpecialName               = False         # Method is special. Name describes how.

    # interop attributes
    mdPinvokeImpl               = False         # Implementation is forwarded through pinvoke.
    mdUnmanagedExport           = False         # Managed method exported via thunk to unmanaged code.

    # Reserved flags for runtime use only.
    mdRTSpecialName             = False         # Runtime should check name encoding.
    mdHasSecurity               = False         # Method has security associate with it.
    mdRequireSecObject          = False         # Method calls another method containing security code.

    corhdr_enum = CorMethodAttr
    _masks = {
        "mdMemberAccessMask": CorMethodMemberAccess,
        "mdVtableLayoutMask": CorMethodVtableLayout,
    }
    _flags = (CorMethodAttrFlags, )


class CorMethodCodeType(_enum.IntEnum):
    miIL                =   0x0000      # Method impl is IL.
    miNative            =   0x0001      # Method impl is native.
    miOPTIL             =   0x0002      # Method impl is OPTIL
    miRuntime           =   0x0003      # Method impl is provided by the runtime.


class CorMethodManaged(_enum.IntEnum):
    miUnmanaged         =   0x0004      # Method impl is unmanaged, otherwise managed.
    miManaged           =   0x0000      # Method impl is managed.


class CorMethodImplFlags(_enum.IntEnum):
    miForwardRef        =   0x0010      # Indicates method is defined; used primarily in merge scenarios.
    miPreserveSig       =   0x0080      # Indicates method sig is not to be mangled to do HRESULT conversion.

    miInternalCall      =   0x1000      # Reserved for internal use.

    miSynchronized      =   0x0020      # Method is single threaded through the body.
    miNoInlining        =   0x0008      # Method may not be inlined.


class CorMethodImpl(ClrMetaDataEnum):
    # code impl mask
    miCodeTypeMask      =   0x0003      # Flags about code type.
    enumCodeType        =   CorMethodCodeType

    # managed mask
    miManagedMask       =   0x0004      # Flags specifying whether the code is managed or unmanaged.
    enumManaged         =   CorMethodManaged

    enumFlags               =   CorMethodImplFlags

    miMaxMethodImplVal  =   0xffff      # Range check value


class ClrMethodImpl(ClrFlags):
    miIL                = False         # Method impl is IL.
    miNative            = False         # Method impl is native.
    miOPTIL             = False         # Method impl is OPTIL
    miRuntime           = False         # Method impl is provided by the runtime.
    # end code impl mask

    # managed mask
    miUnmanaged         = False         # Method impl is unmanaged, otherwise managed.
    miManaged           = False         # Method impl is managed.
    # end managed mask

    # implementation info and interop
    miForwardRef        = False         # Indicates method is defined; used primarily in merge scenarios.
    miPreserveSig       = False         # Indicates method sig is not to be mangled to do HRESULT conversion.

    miInternalCall      = False         # Reserved for internal use.

    miSynchronized      = False         # Method is single threaded through the body.
    miNoInlining        = False         # Method may not be inlined.

    miMaxMethodImplVal  = False         # Range check value

    corhdr_enum = CorMethodImpl
    _masks = {
        "miCodeTypeMask": CorMethodCodeType,
        "miManagedMask": CorMethodManaged,
    }
    _flags = (CorMethodImplFlags, )


class CorParamAttrFlags(_enum.IntEnum):
    pdIn                        =   0x0001     # Param is [In]
    pdOut                       =   0x0002     # Param is [out]
    pdOptional                  =   0x0010     # Param is optional

    # Reserved flags for runtime use only.
    pdHasDefault                =   0x1000     # Param has default value.
    pdHasFieldMarshal           =   0x2000     # Param has FieldMarshal.


class CorParamAttr(ClrMetaDataEnum):
    enumFlags                       =   CorParamAttrFlags

    # Reserved flags for runtime use only.
    pdReservedMask              =   0xf000

    pdUnused                    =   0xcfe0


class ClrParamAttr(ClrFlags):
    pdIn                        =   False   # Param is [In]
    pdOut                       =   False   # Param is [out]
    pdOptional                  =   False   # Param is optional

    # Reserved flags for Runtime use only.
    pdHasDefault                =   False   # Param has default value.
    pdHasFieldMarshal           =   False   # Param has FieldMarshal.

    corhdr_enum = CorParamAttr
    _flags = (CorParamAttrFlags, )


class CorEventAttrFlags(_enum.IntEnum):
    evSpecialName           =   0x0200     # event is special. Name describes how.
    evRTSpecialName         =   0x0400     # Runtime(metadata internal APIs) should check name encoding.


class CorEventAttr(ClrMetaDataEnum):
    enumFlags                   =   CorEventAttrFlags

    # Reserved flags for Runtime use only.
    evReservedMask          =   0x0400


class ClrEventAttr(ClrFlags):
    evSpecialName           = False     # event is special. Name describes how.

    # Reserved flags for Runtime use only.
    evRTSpecialName         = False     # Runtime(metadata internal APIs) should check name encoding.

    corhdr_enum = CorEventAttr
    _flags = (CorEventAttrFlags, )


class CorPropertyAttrFlags(_enum.IntEnum):
    prSpecialName           =   0x0200     # property is special.  Name describes how.

    # Reserved flags for Runtime use only.
    prRTSpecialName         =   0x0400     # Runtime(metadata internal APIs) should check name encoding.
    prHasDefault            =   0x1000     # Property has default


class CorPropertyAttr(ClrMetaDataEnum):
    enumFlags                   =   CorPropertyAttrFlags

    # Reserved flags for Runtime use only.
    prReservedMask          =   0xf400

    prUnused                =   0xe9ff


class ClrPropertyAttr(ClrFlags):
    prSpecialName           = False     # property is special.  Name describes how.

    # Reserved flags for Runtime use only.
    prRTSpecialName         = False     # Runtime(metadata internal APIs) should check name encoding.
    prHasDefault            = False     # Property has default

    corhdr_enum = CorPropertyAttr
    _flags = (CorPropertyAttrFlags, )


class CorMethodSematicsFlags(_enum.IntEnum):
    msSetter    =   0x0001      # Setter for property
    msGetter    =   0x0002      # Getter for property
    msOther     =   0x0004      # other method for property or event
    msAddOn     =   0x0008      # AddOn method for event
    msRemoveOn  =   0x0010      # RemoveOn method for event
    msFire      =   0x0020      # Fire method for event


class CorMethodSemanticsAttr(ClrMetaDataEnum):
    enumFlags       =   CorMethodSematicsFlags


class ClrMethodSemanticsAttr(ClrFlags):
    msSetter    = False     # Setter for property
    msGetter    = False     # Getter for property
    msOther     = False     # other method for property or event
    msAddOn     = False     # AddOn method for event
    msRemoveOn  = False     # RemoveOn method for event
    msFire      = False     # Fire method for event

    corhdr_enum = CorMethodSemanticsAttr
    _flags = (CorMethodSematicsFlags, )


class CorPinvokeMapCharSet(_enum.IntEnum):
    pmCharSetNotSpec    = 0x0000
    pmCharSetAnsi       = 0x0002
    pmCharSetUnicode    = 0x0004
    pmCharSetAuto       = 0x0006


class CorPinvokeBestFit(_enum.IntEnum):
    pmBestFitUseAssem   = 0x0000
    pmBestFitEnabled    = 0x0010
    pmBestFitDisabled   = 0x0020


class CorPinvokeThrowOnUnmappableChar(_enum.IntEnum):
    pmThrowOnUnmappableCharUseAssem   = 0x0000
    pmThrowOnUnmappableCharEnabled    = 0x1000
    pmThrowOnUnmappableCharDisabled   = 0x2000


class CorPinvokeCallConv(_enum.IntEnum):
    pmCallConvWinapi    = 0x0100    # Pinvoke will use native callconv appropriate to target windows platform.
    pmCallConvCdecl     = 0x0200
    pmCallConvStdcall   = 0x0300
    pmCallConvThiscall  = 0x0400    # In M9, pinvoke will raise exception.
    pmCallConvFastcall  = 0x0500
    pmUnknown1          = 0x0600
    pmUnknown2          = 0x0700


class CorPinvokeMapFlags(_enum.IntEnum):
    pmNoMangle          = 0x0001    # Pinvoke is to use the member name as specified.
    pmSupportsLastError = 0x0040    # Information about target function. Not relevant for fields.


class CorPinvokeMap(ClrMetaDataEnum):
    enumFlags               = CorPinvokeMapFlags

    # Use this mask to retrieve the CharSet information.
    pmCharSetMask       = 0x0006
    enumCharSet         = CorPinvokeMapCharSet

    pmBestFitMask       = 0x0030
    enumBestFit         = CorPinvokeBestFit

    pmThrowOnUnmappableCharMask     = 0x3000
    enumThrowOnUnmappableCharMask   = CorPinvokeThrowOnUnmappableChar

    # None of the calling convention flags is relevant for fields.
    pmCallConvMask      = 0x0700
    enumCallConv        = CorPinvokeCallConv

    pmMaxValue          = 0xFFFF


class ClrPinvokeMap(ClrFlags):
    pmNoMangle          = False     # Pinvoke is to use the member name as specified.

    # Use this mask to retrieve the CharSet information.
    pmCharSetNotSpec    = False
    pmCharSetAnsi       = False
    pmCharSetUnicode    = False
    pmCharSetAuto       = False

    pmBestFitUseAssem   = False
    pmBestFitEnabled    = False
    pmBestFitDisabled   = False

    pmThrowOnUnmappableCharUseAssem   = False
    pmThrowOnUnmappableCharEnabled    = False
    pmThrowOnUnmappableCharDisabled   = False

    pmSupportsLastError = False     # Information about target function. Not relevant for fields.

    # None of the calling convention flags is relevant for fields.
    pmCallConvWinapi    = False     # Pinvoke will use native callconv appropriate to target windows platform.
    pmCallConvCdecl     = False
    pmCallConvStdcall   = False
    pmCallConvThiscall  = False     # In M9, pinvoke will raise exception.
    pmCallConvFastcall  = False

    corhdr_enum = CorPinvokeMap
    _masks = {
        "pmCharSetMask": CorPinvokeMapCharSet,
        "pmBestFitMask": CorPinvokeBestFit,
        "pmThrowOnUnmappableCharMask": CorPinvokeThrowOnUnmappableChar,
        "pmCallConvMask": CorPinvokeCallConv,
    }
    _flags = (CorPinvokeMapFlags, )


class CorAssemblyFlagsEnum(_enum.IntEnum):
    afPublicKey             =   0x0001      # The assembly ref holds the full (unhashed) public key.

    afEnableJITcompileTracking      =   0x8000  # From "DebuggableAttribute".
    afDisableJITcompileOptimizer    =   0x4000  # From "DebuggableAttribute".

    afRetargetable          =   0x0100      # The assembly can be retargeted (at runtime) to an

    afPA_Specified          =   0x0080      # Propagate PA flags to AssemblyRef record


class CorAssemblyFlagsPA(_enum.IntEnum):
    afPA_None               =   0x0000      # Processor Architecture unspecified
    afPA_MSIL               =   0x0010      # Processor Architecture: neutral (PE32)
    afPA_x86                =   0x0020      # Processor Architecture: x86 (PE32)
    afPA_IA64               =   0x0030      # Processor Architecture: Itanium (PE32+)
    afPA_AMD64              =   0x0040      # Processor Architecture: AMD X64 (PE32+)
    afPA_Unknown1           =   0x0050
    afPA_Unknown2           =   0x0060
    afPA_Unknown3           =   0x0070


class CorAssemblyFlags(ClrMetaDataEnum):
    enumFlags = CorAssemblyFlagsEnum

    afPA_Mask               =   0x0070      # Bits describing the processor architecture
    enumPA                  = CorAssemblyFlagsPA

    afPA_FullMask           =   0x00F0      # Bits describing the PA incl. Specified
    afPA_Shift              =   0x0004      # NOT A FLAG, shift count in PA flags <--> index conversion


class ClrAssemblyFlags(ClrFlags):
    afPublicKey             = False         # The assembly ref holds the full (unhashed) public key.

    afPA_None               = False         # Processor Architecture unspecified
    afPA_MSIL               = False         # Processor Architecture: neutral (PE32)
    afPA_x86                = False         # Processor Architecture: x86 (PE32)
    afPA_IA64               = False         # Processor Architecture: Itanium (PE32+)
    afPA_AMD64              = False         # Processor Architecture: AMD X64 (PE32+)
    afPA_Specified          = False         # Propagate PA flags to AssemblyRef record

    afEnableJITcompileTracking   = False     # From "DebuggableAttribute".
    afDisableJITcompileOptimizer = False     # From "DebuggableAttribute".

    # The assembly can be retargeted (at runtime) to an
    # assembly from a different publisher.
    afRetargetable          = False

    corhdr_enum = CorAssemblyFlags
    _masks = {
        "afPA_Mask": CorAssemblyFlagsPA,
    }
    _flags = (CorAssemblyFlagsEnum, )


class CorFileFlagsEnum(_enum.IntEnum):
    ffContainsMetaData      =   0x0000      # This is not a resource file
    ffContainsNoMetaData    =   0x0001      # This is a resource file or other non-metadata-containing file


class CorFileFlags(ClrMetaDataEnum):
    ffContainsMask  =   0x0001
    enumContains    =   CorFileFlagsEnum


class ClrFileFlags(ClrFlags):
    ffContainsMetaData      = False     # This is not a resource file
    ffContainsNoMetaData    = False     # This is a resource file or other non-metadata-containing file

    corhdr_enum = CorFileFlags
    _masks = {
        "ffContainsMask": CorFileFlagsEnum,
    }


class CorManifestResourceVisibility(_enum.IntEnum):
    mrPublic                =   0x0001     # The Resource is exported from the Assembly.
    mrPrivate               =   0x0002     # The Resource is private to the Assembly.
    mrUnknown1              =   0x0003
    mrUnknown2              =   0x0004
    mrUnknown3              =   0x0005
    mrUnknown4              =   0x0006
    mrUnknown5              =   0x0007


class CorManifestResourceFlags(ClrMetaDataEnum):
    mrVisibilityMask        =   0x0007
    enumVisibility          =   CorManifestResourceVisibility


class ClrManifestResourceFlags(ClrFlags):
    mrPublic                = False     # The Resource is exported from the Assembly.
    mrPrivate               = False     # The Resource is private to the Assembly.

    corhdr_enum = CorManifestResourceFlags
    _masks = {
        "mrVisibilityMask": CorManifestResourceVisibility,
    }


class CorGenericParamVariance(_enum.IntEnum):
    # Variance of type parameters only applicable to generic parameters
    # for generic interfaces and delegates
    gpNonVariant            =   0x0000
    gpCovariant             =   0x0001
    gpContravariant         =   0x0002
    gpUnknown1              =   0x0003


class CorGenericParamSpecialConstraint(_enum.IntEnum):
    # Special constraints applicable to any type parameters
    gpNoSpecialConstraint               =   0x0000
    gpReferenceTypeConstraint           =   0x0004  # type argument must be a reference type
    gpNotNullableValueTypeConstraint    =   0x0008  # type argument must be a value type but not Nullable
    gpDefaultConstructorConstraint      =   0x0010  # type argument must have a public default constructor


class CorGenericParamAttr(ClrMetaDataEnum):
    gpVarianceMask          =   0x0003
    enumVariance            =   CorGenericParamVariance

    gpSpecialConstraintMask     =   0x001C
    enumSpecialConstraint       =   CorGenericParamSpecialConstraint


class ClrGenericParamAttr(ClrFlags):

    # Variance of type parameters only applicable to generic parameters
    # for generic interfaces and delegates
    gpNonVariant            = False
    gpCovariant             = False
    gpContravariant         = False

    # Special constraints applicable to any type parameters
    gpNoSpecialConstraint               = False
    gpReferenceTypeConstraint           = False     # type argument must be a reference type
    gpNotNullableValueTypeConstraint    = False     # type argument must be a value type but not Nullable
    gpDefaultConstructorConstraint      = False     # type argument must have a public default constructor

    corhdr_enum = CorGenericParamAttr
    _masks = {
        "gpVarianceMask": corhdr_enum.enumVariance,
        # "gpSpecialConstraintMask": corhdr_enum.enumSpecialConstraint,
    }
    _flags = (CorGenericParamSpecialConstraint, )


class MetadataTables(_enum.IntEnum):
    Module = 0
    TypeRef = 1
    TypeDef = 2
    FieldPtr = 3  # Not public
    Field = 4
    MethodPtr = 5  # Not public
    MethodDef = 6
    ParamPtr = 7  # Not public
    Param = 8
    InterfaceImpl = 9
    MemberRef = 10
    Constant = 11
    CustomAttribute = 12
    FieldMarshal = 13
    DeclSecurity = 14
    ClassLayout = 15
    FieldLayout = 16
    StandAloneSig = 17
    EventMap = 18
    EventPtr = 19  # Not public
    Event = 20
    PropertyMap = 21
    PropertyPtr = 22  # Not public
    Property = 23
    MethodSemantics = 24
    MethodImpl = 25
    ModuleRef = 26
    TypeSpec = 27
    ImplMap = 28
    FieldRva = 29
    EncLog = 30
    EncMap = 31
    Assembly = 32
    AssemblyProcessor = 33
    AssemblyOS = 34
    AssemblyRef = 35
    AssemblyRefProcessor = 36
    AssemblyRefOS = 37
    File = 38
    ExportedType = 39
    ManifestResource = 40
    NestedClass = 41
    GenericParam = 42
    MethodSpec = 43
    GenericParamConstraint = 44
    # 45 through 63 are not used
    Unused = 62
    MaxTable = 63


class AssemblyHashAlgorithm(_enum.IntEnum):
    """
    Per Microsoft documentation, "Specifies all the hash algorithms used for hashing files and for generating the strong name."

    REFERENCE:
        https://docs.microsoft.com/en-us/dotnet/api/system.configuration.assemblies.assemblyhashalgorithm?view=net-5.0
    """
    NONE    = 0
    MD5     = 0x8003
    SHA1    = 0x8004
    SHA256  = 0x800c
    SHA384  = 0x800d
    SHA512  = 0x800e


class DateTimeKind(_enum.IntEnum):
    """
    Per Microsoft documenation, provide additional context to DateTime instances.

    REFERENCE:
        https://github.com/dotnet/runtime/blob/main/src/libraries/System.Private.CoreLib/src/System/DateTime.cs
        https://github.com/dotnet/runtime/blob/main/src/libraries/System.Private.CoreLib/src/System/DateTimeKind.cs
    """
    Unspecified = 0
    Utc = 1
    Local = 2
    LocalAmbiguousDst = 3
