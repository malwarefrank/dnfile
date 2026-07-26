import fixtures

import dnfile


def test_tiny_method_header_is_decoded_for_hello_world_main():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("hello-world.exe"))

    main_method = dn.net.mdtables.MethodDef[0]
    body = main_method.Body

    assert body.header_format == "tiny"
    assert body.header_size == 1
    assert body.max_stack == 8
    assert body.code_size == 13
    assert body.local_var_sig_tok == 0
    assert body.code[:4] == bytes.fromhex("00720100")


def test_fat_method_header_and_locals_token_are_decoded_for_module_code():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    method = next(row for row in dn.net.mdtables.MethodDef.rows if row.Name == "rc4_init")
    body = method.Body

    assert body.header_format == "fat"
    assert body.header_size == 12
    assert body.max_stack == 4
    assert body.code_size == 0x6E
    assert body.local_var_sig_tok == 0x11000005
    assert body.local_signature is dn.net.mdtables.StandAloneSig[4].ParsedSignature


def test_exception_handler_sections_are_decoded_for_module_code():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    method = next(
        row for row in dn.net.mdtables.MethodDef.rows if getattr(row.Name, "value", row.Name) == "__get_default_appdomain"
    )
    body = method.Body

    assert len(body.exception_handlers) == 1

    handler = body.exception_handlers[0]
    assert handler.clause_type == "catch"
    assert handler.try_offset == 2
    assert handler.try_length == 39
    assert handler.handler_offset == 41
    assert handler.handler_length == 8
    assert handler.class_token == 0x01000013
    assert handler.exception_type.row.TypeNamespace == "System"
    assert handler.exception_type.row.TypeName == "Exception"


def test_native_method_bodies_return_unsupported_sentinels():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("EmptyClass_x86.exe"))

    native_stub = next(row for row in dn.net.mdtables.MethodDef.rows if row.Name == "_mainCRTStartup")
    body = native_stub.Body

    assert body.kind == "unsupported"
    assert body.rva == native_stub.Rva
    assert body.raw_header == bytes.fromhex("e8")
    assert "unsupported method header format" in body.reason


def test_missing_native_method_body_rvas_return_unsupported_sentinels():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    native_stub = next(row for row in dn.net.mdtables.MethodDef.rows if row.Name == "DecodePointer")
    body = native_stub.Body

    assert body.kind == "unsupported"
    assert body.rva == native_stub.Rva == 0
    assert body.raw_header[:1] == b"M"
    assert "unsupported method header format" in body.reason


def test_unreadable_native_method_rvas_return_unsupported_sentinels():
    dn = dnfile.dnPE(fixtures.get_data_path_by_name("ModuleCode_x86.exe"))

    native_stub = next(row for row in dn.net.mdtables.MethodDef.rows if getattr(row.Name, "value", row.Name) == "_cexit")
    body = native_stub.Body

    assert body.kind == "unsupported"
    assert body.rva == native_stub.Rva
    assert body.raw_header
    assert body.raw_header[:1] == b"\xff"
    assert body.reason.startswith("unsupported fat method header size")
