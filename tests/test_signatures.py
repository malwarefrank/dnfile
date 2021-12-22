import binascii

import pytest

from dnfile.signature import SignatureReader, parse_method_signature, parse_field_signature


def test_signature_reader_u32():
    with pytest.raises(IndexError):
        SignatureReader(b"").read_compressed_u32()

    # these are the tests from
    # spec ECMA-335 II.23.2 Blobs and signatures.
    assert 0x03 == SignatureReader(b"\x03").read_compressed_u32()
    assert 0x7F == SignatureReader(b"\x7F").read_compressed_u32()
    assert 0x80 == SignatureReader(b"\x80\x80").read_compressed_u32()
    assert 0x2E57 == SignatureReader(b"\xAE\x57").read_compressed_u32()
    assert 0x3FFF == SignatureReader(b"\xBF\xFF").read_compressed_u32()
    assert 0x4000 == SignatureReader(b"\xC0\x00\x40\x00").read_compressed_u32()
    assert 0x1FFFFFFF == SignatureReader(b"\xDF\xFF\xFF\xFF").read_compressed_u32()


def test_signature_reader_i32():
    # these are the tests from
    # spec ECMA-335 II.23.2 Blobs and signatures.
    assert 3 == SignatureReader(b"\x06").read_compressed_i32()
    assert -3 == SignatureReader(b"\x7B").read_compressed_i32()
    assert 64 == SignatureReader(b"\x80\x80").read_compressed_i32()
    assert -64 == SignatureReader(b"\x01").read_compressed_i32()
    assert 8192 == SignatureReader(b"\xC0\x00\x40\x00").read_compressed_i32()
    assert -8192 == SignatureReader(b"\x80\x01").read_compressed_i32()
    assert 268435455 == SignatureReader(b"\xDF\xFF\xFF\xFE").read_compressed_i32()
    assert -268435456 == SignatureReader(b"\xC0\x00\x00\x01").read_compressed_i32()


def test_method_signature():
    # instance void class [mscorlib]System.Runtime.CompilerServices.CompilationRelaxationsAttribute::'.ctor'(int32)
    assert str(parse_method_signature(binascii.unhexlify(b"20010108"))) == "instance void f(int32)"

    # instance void class [mscorlib]System.Runtime.CompilerServices.RuntimeCompatibilityAttribute::'.ctor'()
    assert str(parse_method_signature(binascii.unhexlify(b"200001"))) == "instance void f()"

    # instance void class [mscorlib]System.Diagnostics.DebuggableAttribute::'.ctor'(valuetype [mscorlib]System.Diagnostics.DebuggableAttribute/DebuggingModes)
    assert str(parse_method_signature(binascii.unhexlify(b"2001011111"))) == "instance void f(valuetype token(table: TypeRef, row: 4))"

    # void class [mscorlib]System.Console::WriteLine(string)
    assert str(parse_method_signature(binascii.unhexlify(b"0001010e"))) == "void f(string)"

    # instance void object::'.ctor'()
    assert str(parse_method_signature(binascii.unhexlify(b"200001"))) == "instance void f()"

    # void Main(string[] args)
    assert str(parse_method_signature(binascii.unhexlify(b"0001011d0e"))) == "void f(string[])"


def test_field_signature():
    assert str(parse_field_signature(binascii.unhexlify(b"061110"))) == "valuetype token(table: TypeDef, row: 4)"
