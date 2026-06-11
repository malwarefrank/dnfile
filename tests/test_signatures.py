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


def test_methoddef_signature_can_render_like_a_programmer_would_expect():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))

    main_method = dn.net.mdtables.MethodDef[0]
    signature = main_method.ParsedSignature

    assert signature.to_programmer_string("Main") == "void Main(string[])"
    assert str(signature) == "MethodSignature(kind='method', has_this=False, explicit_this=False, generic_param_count=0, parameter_count=1, return_type=TypeSignature(element_type='VOID', number=None, type_token=None, generic_kind=None, arguments=None, inner=None, signature=None, array_rank=None, array_sizes=None, array_lower_bounds=None, kind='type'), parameters=[TypeSignature(element_type='SZARRAY', number=None, type_token=None, generic_kind=None, arguments=None, inner=TypeSignature(element_type='STRING', number=None, type_token=None, generic_kind=None, arguments=None, inner=None, signature=None, array_rank=None, array_sizes=None, array_lower_bounds=None, kind='type'), signature=None, array_rank=None, array_sizes=None, array_lower_bounds=None, kind='type')])"


def test_methoddef_signature_is_decoded_for_empty_class_native_int_return():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("EmptyClass_x86.exe"))

    main_method = dn.net.mdtables.MethodDef[0]
    signature = main_method.ParsedSignature

    assert signature.kind == "method"
    assert signature.parameter_count == 0
    assert signature.return_type.element_type == "U4"


def test_methoddef_signature_handles_custom_modifiers_and_pointers():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    method = next(row for row in dn.net.mdtables.MethodDef.rows if row.Signature == bytes.fromhex("00032005010f110c0f0508"))
    signature = method.ParsedSignature

    assert signature.kind == "method"
    assert signature.parameter_count == 3
    assert signature.return_type.element_type == "CMOD_OPT"
    assert signature.return_type.type_token == 5
    assert signature.return_type.inner.element_type == "VOID"
    assert [parameter.element_type for parameter in signature.parameters] == ["PTR", "PTR", "I4"]
    assert signature.parameters[0].inner.element_type == "VALUETYPE"
    assert signature.parameters[0].inner.type_token == 12
    assert signature.parameters[1].inner.element_type == "U1"


def test_methoddef_signature_renders_named_types_in_programmer_strings():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    method = next(row for row in dn.net.mdtables.MethodDef.rows if row.Name == "rc4_init")
    signature = method.ParsedSignature

    assert (
        signature.to_programmer_string()
        == "modopt(System.Runtime.CompilerServices.CallConvCdecl) void(RC4_STATE_*, byte*, int)"
    )


def test_memberref_signature_handles_object_parameters():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    member_ref = next(row for row in dn.net.mdtables.MemberRef.rows if row.Signature == bytes.fromhex("0002010e1c"))
    signature = member_ref.ParsedSignature

    assert signature.kind == "method"
    assert signature.parameter_count == 2
    assert [parameter.element_type for parameter in signature.parameters] == ["STRING", "OBJECT"]


def test_methoddef_signature_handles_byref_generic_arguments():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_"
        )
    )

    method = next(row for row in dn.net.mdtables.MethodDef.rows if row.Signature == bytes.fromhex("30010101101e00"))
    signature = method.ParsedSignature

    assert signature.kind == "method"
    assert signature.has_this is True
    assert signature.generic_param_count == 1
    assert signature.parameter_count == 1
    assert signature.return_type.element_type == "VOID"
    assert signature.parameters[0].element_type == "BYREF"
    assert signature.parameters[0].inner.element_type == "MVAR"
    assert signature.parameters[0].inner.number == 0


def test_standalonesig_locals_handle_native_int_and_byref_forms():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "7f4ba9fc95b30baf8922a6933a4ff1c6a7fef41fae487bb31014c4963357770f.dll_"
        )
    )

    local_sig = next(row for row in dn.net.mdtables.StandAloneSig.rows if row.Signature == bytes.fromhex("070210081280b9")).ParsedSignature

    assert local_sig.kind == "locals"
    assert [local.element_type for local in local_sig.locals] == ["BYREF", "CLASS"]
    assert local_sig.locals[0].inner.element_type == "I4"
    assert local_sig.locals[1].type_token == 185


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


def test_typespec_signatures_are_decoded_for_generic_parameters():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_"
        )
    )

    type_var = dn.net.mdtables.TypeSpec[2].ParsedSignature
    method_var = dn.net.mdtables.TypeSpec[3].ParsedSignature

    assert type_var.kind == "type"
    assert type_var.element_type == "VAR"
    assert type_var.number == 0

    assert method_var.kind == "type"
    assert method_var.element_type == "MVAR"
    assert method_var.number == 0


def test_methodspec_instantiation_is_decoded_for_single_string_argument():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_"
        )
    )

    repeat_spec = dn.net.mdtables.MethodSpec[3]
    instantiation = repeat_spec.ParsedInstantiation

    assert instantiation.kind == "methodspec"
    assert instantiation.argument_count == 1
    assert instantiation.arguments[0].element_type == "STRING"


def test_typespec_generic_instance_is_decoded_with_var_argument():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_"
        )
    )

    generic_instance = dn.net.mdtables.TypeSpec[0].ParsedSignature

    assert generic_instance.kind == "type"
    assert generic_instance.element_type == "GENERICINST"
    assert generic_instance.generic_kind == "CLASS"
    assert generic_instance.type_token == 0x10
    assert len(generic_instance.arguments) == 1
    assert generic_instance.arguments[0].element_type == "VAR"
    assert generic_instance.arguments[0].number == 0


def test_methodspec_instantiation_can_decode_class_arguments():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_"
        )
    )

    deserialize_spec = dn.net.mdtables.MethodSpec[2]
    instantiation = deserialize_spec.ParsedInstantiation

    assert instantiation.kind == "methodspec"
    assert instantiation.argument_count == 1
    assert instantiation.arguments[0].element_type == "CLASS"
    assert instantiation.arguments[0].type_token == 0x5C


def test_typespec_generic_instance_can_decode_boolean_arguments():
    dn = dnfile.dnPE(
        fixtures.get_data_path_by_name(
            "7f4ba9fc95b30baf8922a6933a4ff1c6a7fef41fae487bb31014c4963357770f.dll_"
        )
    )

    generic_instance = dn.net.mdtables.TypeSpec[9].ParsedSignature

    assert generic_instance.kind == "type"
    assert generic_instance.element_type == "GENERICINST"
    assert len(generic_instance.arguments) == 2
    assert [argument.element_type for argument in generic_instance.arguments] == ["CHAR", "BOOLEAN"]