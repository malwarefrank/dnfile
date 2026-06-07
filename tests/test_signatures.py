import fixtures

import dnfile


def test_methoddef_signature_is_decoded_for_hello_world():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))

    main_method = dn.net.mdtables.MethodDef[0]
    signature = main_method.ParsedSignature

    assert signature.kind == "method"
    assert signature.has_this is False
    assert signature.generic_param_count == 0
    assert signature.parameter_count == 1
    assert signature.return_type.element_type == "VOID"
    assert signature.parameters[0].element_type == "SZARRAY"
    assert signature.parameters[0].inner.element_type == "STRING"


def test_memberref_signature_is_decoded_for_ctor_reference():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))

    ctor_ref = next(
        row
        for row in dn.net.mdtables.MemberRef.rows
        if row.Name == ".ctor" and row.Signature == bytes.fromhex("200001")
    )
    signature = ctor_ref.ParsedSignature

    assert signature.kind == "method"
    assert signature.has_this is True
    assert signature.parameter_count == 0
    assert signature.return_type.element_type == "VOID"


def test_standalonesig_locals_are_decoded_for_module_code():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    local_sig = dn.net.mdtables.StandAloneSig[4].ParsedSignature

    assert local_sig.kind == "locals"
    assert [local.element_type for local in local_sig.locals] == [
        "I4",
        "I4",
        "I4",
        "I4",
        "I4",
    ]