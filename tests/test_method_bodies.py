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