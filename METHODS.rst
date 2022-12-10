================
dnfile - Methods
================

Here is the high-level design of how to access the .NET methods of a dotnet
executable.

We have tried to remain consistent with ECMA 335 terminology.


Quick Start
-----------

.NET methods are parsed and can be accessed through the dnPE.net.methods
list.  Each item in the list is a subclass of dnfile.Method.

Each InternalMethod has a name, RVA, flags, parameter list, return type,
calling convention, and several attributes copied from the associated
MethodDef row.  The flags are a combination of flags from the MethodDef
row (Flags, ImplFlags) and from the parsed method signature.  The parameter
list contains Param objects.  Each Param object is built from a combation
of information from the MethodDef row's ParamList and the method signature.

.. code-block:: python

    pe = dnfile.dnPE(FILEPATH)

    if pe.net and pe.net.methods:
        print("METHODS:")
        for method in pe.net.methods
            print("    Name:       ", method.name)
            print("    Signature:  ", method.signature)
            if isinstance(method, dnfile.methods.InternalMethod):
                print("    Rva:       ", method.rva)
                print("    Return:    ", method.return_type)
                print("    Convention:", method.calling_convention)
                if method.params:
                    for param in method.params:
                        print("    PARAMETER:")
                        print("        Name:   ", param.name)
                        print("        Type:   ", param.cor_type)


High-level Design
-----------------

