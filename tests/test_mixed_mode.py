import fixtures

import dnfile


def is_mixed_mode(dn: dnfile.dnPE):
    if dn.net is None or dn.net.mdtables is None:
        # no .NET metdata, must be a native PE.
        # therefore, not mixed-mode.
        return False

    if dn.net.Flags and (not dn.net.Flags.CLR_ILONLY):
        return True

    methods = dn.net.mdtables.MethodDef
    assert methods is not None

    for method in methods:
        if method.ImplFlags.miNative:
            # it has a .NET header but also has a native method,
            # so its a mixed-mode assembly.
            return True

    return False


def test_empty_class():
    path = fixtures.DATA / "mixed-mode" / "EmptyClass" / "bin" / "EmptyClass_x86.exe"

    dn = dnfile.dnPE(path)

    assert is_mixed_mode(dn) is True


def test_empty_class_dll():
    path = fixtures.DATA / "mixed-mode" / "EmptyClassDll" / "bin" / "EmptyClass_x86.dll"

    dn = dnfile.dnPE(path)

    assert is_mixed_mode(dn) is True


def test_module_code():
    path = fixtures.DATA / "mixed-mode" / "ModuleCode" / "bin" / "ModuleCode_x86.exe"

    dn = dnfile.dnPE(path)

    assert is_mixed_mode(dn) is True


def test_ilonly():
    path = fixtures.DATA / "hello-world" / "hello-world.exe"

    dn = dnfile.dnPE(path)

    assert is_mixed_mode(dn) is False
