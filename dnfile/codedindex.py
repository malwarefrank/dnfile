# -*- coding: utf-8 -*-
"""
.NET Metadata Tables Coded Indexes


REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123


Copyright (c) 2020-2021 MalwareFrank
"""

from typing import Tuple, List

from .base import CodedIndex


# TODO add table_numbers to all


class TypeDefOrRef(CodedIndex):
    tag_bits = 2
    table_names = ("TypeDef", "TypeRef", "TypeSpec")
    table_numbers = (2, 1, 27)


class HasConstant(CodedIndex):
    tag_bits = 2
    table_names = ("Field", "Param", "Property")
    table_numbers = (4, 8, 23)


class HasCustomAttribute(CodedIndex):
    tag_bits = 5
    # TODO this may be an incomplete list
    table_names = (
        "MethodDef",
        "Field",
        "TypeRef",
        "TypeDef",
        "Param",
        "InterfaceImpl",
        "MemberRef",
        "Module",
        "DeclSecurity",
        "Property",
        "Event",
        "StandAloneSig",
        "ModuleRef",
        "TypeSpec",
        "Assembly",
        "AssemblyRef",
        "File",
        "ExportedType",
        "ManifestResource",
        "GenericParam",
        "GenericParamConstraint",
    )


class HasFieldMarshall(CodedIndex):
    tag_bits = 1
    table_names = ("Field", "Param")


class HasDeclSecurity(CodedIndex):
    tag_bits = 2
    table_names = ("TypeDef", "MethodDef", "Assembly")


class MemberRefParent(CodedIndex):
    tag_bits = 3
    table_names = ("TypeDef", "TypeRef", "ModuleRef", "MethodDef", "TypeSpec")


class HasSemantics(CodedIndex):
    tag_bits = 1
    table_names = ("Event", "Property")


class MethodDefOrRef(CodedIndex):
    tag_bits = 1
    table_names = ("MethodDef", "MemberRef")


class MemberForwarded(CodedIndex):
    tag_bits = 1
    table_names = ("Field", "MethodDef")


class Implementation(CodedIndex):
    tag_bits = 2
    table_names = ("File", "AssemblyRef", "ExportedType")


class CustomAttributeType(CodedIndex):
    tag_bits = 3
    table_names = (None, None, "MethodDef", "MemberRef", None)


class ResolutionScope(CodedIndex):
    tag_bits = 2
    table_names = ("Module", "ModuleRef", "AssemblyRef", "TypeRef")


class TypeOrMethodDef(CodedIndex):
    tag_bits = 1
    table_names = ("TypeDef", "MethodDef")
