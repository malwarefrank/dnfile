from typing import TYPE_CHECKING, List, Optional, Union

from . import enums, signature as _sig

# References:
#   https://www.ntcore.com/files/dotnetformat.htm
#   ECMA-335 6th Edition


class MethodFlags(object):

    # member access attributes
    PrivateScope        = False  # Member not referenceable.
    Private             = False  # Accessible only by the parent type.
    FamANDAssem         = False  # Accessible by sub-types only in this Assembly.
    Assem               = False  # Accessibly by anyone in the Assembly.
    Family              = False  # Accessible only by type and sub-types.
    FamORAssem          = False  # Accessibly by sub-types anywhere, plus anyone in assembly.
    Public              = False  # Accessibly by anyone who has visibility to this scope.

    # method contract attributes
    Static              = False  # Defined on type, else per instance.
    Final               = False  # Method may not be overridden.
    Virtual             = False  # Method virtual.
    HideBySig           = False  # Method hides by name+sig, else just by name.

    # vtable layout
    ReuseSlot           = False  # The default.
    NewSlot             = False  # Method always gets a new slot in the vtable.

    # method implementation attributes
    CheckAccessOnOverride   = False  # Overridability is the same as the visibility.
    Abstract                = False  # Method does not provide an implementation.
    SpecialName             = False  # Method is special. Name describes how.

    # interop attributes
    PinvokeImpl         = False  # Implementation is forwarded through pinvoke.
    UnmanagedExport     = False  # Managed method exported via thunk to unmanaged code.

    # Reserved flags for runtime use only
    RTSpecialName       = False  # Runtime should check name encoding.
    HasSecurity         = False  # Method has security associate with it.
    RequireSecObject    = False  # Method calls another method containing security code.

    # code implementation flags
    IL              = False  # Method impl is IL.
    Native          = False  # Method impl is native.
    OPTIL           = False  # Method impl is OPTIL
    Runtime         = False  # Method impl is provided by the runtime.

    # managed mask
    Unmanaged       = False  # Method impl is unmanaged, otherwise managed.
    Managed         = False  # Method impl is managed.

    # implementation info and interop
    ForwardRef = (
        False  # Indicates method is defined; used primarily in merge scenarios.
    )
    PreserveSig = (
        False  # Indicates method sig is not to be mangled to do HRESULT conversion.
    )

    InternalCall        = False  # Reserved for internal use.

    Synchronized        = False  # Method is single threaded through the body.
    NoInlining          = False  # Method may not be inlined.

    MaxMethodImplVal    = False  # Range check value

    # method signature flags, ECMA-335 I.8.6.1.5
    Generic             = False  #
    HasThis             = False
    ExplicitThis        = False

    def __iter__(self):
        for name in enums._getvars(self):
            val = getattr(self, name)
            if isinstance(val, bool):
                yield name, val

    def __repr__(self):
        return "\n".join(["{:<40}{:>8}".format(n, str(v)) for n, v in self])


class ParamFlags(object):
    Input       = False
    Output      = False
    Optional    = False

    def __iter__(self):
        for name in enums._getvars(self):
            val = getattr(self, name)
            if isinstance(val, bool):
                yield name, val

    def __repr__(self):
        return "\n".join(["{:<40}{:>8}".format(n, str(v)) for n, v in self])


class Param:
    """
    See ECMA-335 6th Edition II.22.33
    """
    sequence: Optional[int]
    name: Optional[str]
    flags: Optional[ParamFlags]
    # value: Optional[Any]
    cor_type: Optional[_sig.Element]
    type_str: Optional[str]
    prefix: Optional[str]

    def __init__(
        self,
        sequence: Optional[int],
        name: Optional[str],
        is_input: Optional[bool],
        is_output: Optional[bool],
        is_optional: Optional[bool],
    ):
        self.sequence = sequence
        self.name = name
        self.flags = ParamFlags()
        if is_input:
            self.flags.Input = True
        if is_output:
            self.flags.Output = True
        if is_optional:
            self.flags.Optional = True
        self.cor_type = None
        self.type_str = None
        self.prefix = None

    # accessor for type_str, which is derived from cor_type
    @property
    def type_str(self) -> Optional[str]:
        if self.cor_type:
            return str(self.cor_type)
        else:
            return None

    def __str__(self) -> str:
        if self.prefix:
            return f"{self.prefix} {self.cor_type}"
        else:
            return str(self.cor_type)


class Method:
    """
    Each method must have:
    - name, a non-empty string
    - signature, a method signature

    Each method may have:
    - parameters
    - return type (part of signature)
    - constraints (part of signature)
    - number of generics (part of signature)

    See ECMA-335 6th Edition II.22.26
    """

    def __init__(self, name: str, signature: bytes):
        self.name: str = name
        self._sigraw: bytes = signature
        # signature contains the return type, number of generics, and constraints
        self.signature: Optional[_sig.MethodSignature] = None
        # TODO: the MethodDef row ParamList is used for parameter names and flags.
        #       the params in the method signature are used for parameter types.
        self.params: List[Param] = list()   # populated by MethodFactory

    def parse(self) -> None:
        """
        Implemented in subclasses, if needed.
        """
        return


class ExternalMethod(Method):
    # TODO

    def parse(self):
        super().parse()
        # parse _sigraw to signature
        self.signature = _sig.parse_method_signature(self._sigraw)


class InternalMethod(Method):
    """
    Internal methods have name and signature (inherited from base class),
    plus an RVA, owner (TypeDef row), signature flags, and a list of params.
    """

    rva: int
    flags: Optional[MethodFlags]

    def __init__(self, name: str, signature: bytes):
        super().__init__(name, signature)
        self.rva: int = 0
        self.flags: Optional[MethodFlags] = None

    def parse(self):
        super().parse()
        ### parse _sigraw to signature
        self.signature = _sig.parse_method_signature(self._sigraw)
        if not self.signature:
            return
        # signature has the return type, number of generics, and constraints,
        # but we need to copy the method name so that it can be str with context
        self.signature.method_name = self.name
        # copy flags from signature
        if self.signature.flags & _sig.SignatureFlags.HAS_THIS:
            self.flags.HasThis = True
        if self.signature.flags & _sig.SignatureFlags.EXPLICIT_THIS:
            self.flags.ExplicitThis = True
        if self.signature.flags & _sig.SignatureFlags.GENERIC:
            self.flags.Generic = True
        # copy types from signature to params
        if self.signature:
            for p in self.params:
                if p.sequence < len(self.signature.params):
                    p.cor_type = self.signature.params[p.sequence].cor_type
        # create dummy list of params same size as signature params
        new_params_list = [None] * len(self.signature.params)
        for p in self.params:
            if p.sequence == 0:
                # TODO: handle sequence=0 (return type)
                continue
            p.cor_type = self.signature.params[p.sequence - 1].cor_type
            new_params_list[p.sequence - 1] = p
        # if we are missing any params, create a dummy param with just the type
        for i in range(len(new_params_list)):
            if new_params_list[i] is None:
                # all we know is sequence and type
                p = Param(i + 1, None, None, None, None)
                p.cor_type = self.signature.params[i].cor_type
                new_params_list[i] = p
        self.params = new_params_list