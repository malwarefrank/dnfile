# -*- coding: utf-8 -*-
"""
.NET Metadata Tables Coded Indexes


REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123


Copyright (c) 2020-2022 MalwareFrank
"""

from typing import TYPE_CHECKING, Union

from .base import CodedIndex

if TYPE_CHECKING:
    from .mdtable import (
        FileRow,
        EventRow,
        FieldRow,
        ParamRow,
        ModuleRow,
        TypeDefRow,
        TypeRefRow,
        AssemblyRow,
        PropertyRow,
        TypeSpecRow,
        MemberRefRow,
        MethodDefRow,
        ModuleRefRow,
        AssemblyRefRow,
        DeclSecurityRow,
        ExportedTypeRow,
        GenericParamRow,
        InterfaceImplRow,
        StandAloneSigRow,
        ManifestResourceRow,
        GenericParamConstraintRow,
    )


class TypeDefOrRef(CodedIndex[Union["TypeDefRow", "TypeRefRow", "TypeSpecRow"]]):
    tag_bits = 2
    table_names = ("TypeDef", "TypeRef", "TypeSpec")
    table_numbers = (2, 1, 27)


class HasConstant(CodedIndex[Union["FieldRow", "ParamRow", "PropertyRow"]]):
    tag_bits = 2
    table_names = ("Field", "Param", "Property")
    table_numbers = (4, 8, 23)


class HasCustomAttribute(
    CodedIndex[
        Union[
            "MethodDefRow",
            "FieldRow",
            "TypeRefRow",
            "TypeDefRow",
            "ParamRow",
            "InterfaceImplRow",
            "MemberRefRow",
            "ModuleRow",
            "DeclSecurityRow",
            "PropertyRow",
            "EventRow",
            "StandAloneSigRow",
            "ModuleRefRow",
            "TypeSpecRow",
            "AssemblyRow",
            "AssemblyRefRow",
            "FileRow",
            "ExportedTypeRow",
            "ManifestResourceRow",
            "GenericParamRow",
            "GenericParamConstraintRow",
        ]
    ]
):
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


class HasFieldMarshall(CodedIndex[Union["FieldRow", "ParamRow"]]):
    tag_bits = 1
    table_names = ("Field", "Param")


class HasDeclSecurity(CodedIndex[Union["TypeDefRow", "MethodDefRow", "AssemblyRow"]]):
    tag_bits = 2
    table_names = ("TypeDef", "MethodDef", "Assembly")


class MemberRefParent(CodedIndex[Union["TypeDefRow", "TypeRefRow", "ModuleRefRow", "MethodDefRow", "TypeSpecRow"]]):
    tag_bits = 3
    table_names = ("TypeDef", "TypeRef", "ModuleRef", "MethodDef", "TypeSpec")


class HasSemantics(CodedIndex[Union["EventRow", "PropertyRow"]]):
    tag_bits = 1
    table_names = ("Event", "Property")


class MethodDefOrRef(CodedIndex[Union["MethodDefRow", "MemberRefRow"]]):
    tag_bits = 1
    table_names = ("MethodDef", "MemberRef")


class MemberForwarded(CodedIndex[Union["FieldRow", "MethodDefRow"]]):
    tag_bits = 1
    table_names = ("Field", "MethodDef")


class Implementation(CodedIndex[Union["FileRow", "AssemblyRefRow", "ExportedTypeRow"]]):
    tag_bits = 2
    table_names = ("File", "AssemblyRef", "ExportedType")


class CustomAttributeType(CodedIndex[Union["MethodDefRow", "MemberRefRow"]]):
    tag_bits = 3
    table_names = ("Unused", "Unused", "MethodDef", "MemberRef", "Unused")


class ResolutionScope(CodedIndex[Union["ModuleRow", "ModuleRefRow", "AssemblyRefRow", "TypeRefRow"]]):
    tag_bits = 2
    table_names = ("Module", "ModuleRef", "AssemblyRef", "TypeRef")


class TypeOrMethodDef(CodedIndex[Union["TypeDefRow", "MethodDefRow"]]):
    tag_bits = 1
    table_names = ("TypeDef", "MethodDef")
