from typing import TYPE_CHECKING, List, Optional

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


class Param:
    sequence: Optional[int]
    name: Optional[str]
    is_input: Optional[bool]
    is_output: Optional[bool]
    is_optional: Optional[bool]
    # value: Optional[Any]
    param_type: Optional[_sig.Element]

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
        self.is_input = is_input
        self.is_output = is_output
        self.is_optional = is_optional
        self.param_type = None

    def set_type(self, t: _sig.Element):
        self.param_type = t


class Method:
    """
    Each method must have:
    - name, a non-empty string
    - signature, a method signature

    Each method may have:
    - parameters
    """

    def __init__(self, name: str, signature: bytes):
        self.name: str = name
        self._sigraw: bytes = signature
        self.signature: Optional[_sig.MethodSignature] = None
        # TODO: how is the MethodDef row ParamList used versus
        #       the params in the method signature?  Do either
        #       matter at runtime?  And if there is a
        #       difference, which takes precedence?
        self.params: List[Param] = list()

    def parse(self) -> None:
        return


class ExternalMethod(Method):
    # TODO: parent, parse()

    def parse(self):
        # parse _sigraw to signature
        self.signature = _sig.parse_method_signature(self._sigraw)
        # TODO: parse _row


class InternalMethod(Method):
    """
    Internal methods have name and signature (inherited from base class),
    plus an RVA, owner (TypeDef row), signature flags, and a list of params.
    """

    rva: int
    flags: Optional[MethodFlags]
    params: List[Param]
    # TODO: parse()

    def __init__(self, name: str, signature: bytes):
        super().__init__(name, signature)
        self.rva: int = 0
        self.flags: Optional[MethodFlags] = None
        self.params: List[Param] = list()

    def parse(self):
        ### parse _sigraw to signature
        self.signature = _sig.parse_method_signature(self._sigraw)
        if len(self.params) != len(self.signature.params):
            # TODO: warn or error
            return
        for i in range(len(self.params)):
            # copy type from MethodDefSig to Param object
            p = self.params[i]
            p.set_type(self.signature.params[i])
        
            
