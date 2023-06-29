# -*- coding: utf-8 -*-
"""
.NET Metadata Tables


REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123
    ECMA-335, 6th Edition


Copyright (c) 2020-2022 MalwareFrank
"""
from typing import TYPE_CHECKING, Dict, List, Type, Optional

from . import enums, utils, errors, codedindex
from .base import RowStruct, MDTableRow, MDTableIndex, ClrMetaDataTable

if TYPE_CHECKING:
    from . import stream


def checked_offset_format(offset: int):
    """
    compute the format specifier needed for the given offset value.
    raises an exception if the offset cannot be represented.
    """

    # implementation: this exception will propagate up
    # `_compute_format` to `MDTableRow.__init__`
    # and halt population of a table's row.
    format = utils.num_bytes_to_struct_char(offset)
    if format is None:
        raise errors.dnFormatError("invalid offset: value too large")
    return format


#### Module Table
#


class ModuleRowStruct(RowStruct):
    #
    # these are type hints for properties dynamically set during structure parsing.
    #
    Generation: int
    Name_StringIndex: int
    Mvid_GuidIndex: int
    EncId_GuidIndex: int
    EncBaseId_GuidIndex: int


class ModuleRow(MDTableRow):
    #
    # these are type hints for properties dynamically set during structure parsing.
    #
    Generation: Optional[int]
    Name: Optional[str]
    Mvid: Optional[str]
    EncId: Optional[str]
    EncBaseId: Optional[str]

    #
    # raw structure definition
    #
    _struct_class = ModuleRowStruct

    #
    # parsing strategies
    #
    _struct_asis = {"Generation": "Generation"}
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_guids = {
        "Mvid_GuidIndex": "Mvid",
        "EncId_GuidIndex": "EncId",
        "EncBaseId_GuidIndex": "EncBaseId",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        guid_ind_size = checked_offset_format(self._guid_offsz)
        return (
            "CLR_METADATA_TABLE_MODULE",
            (
                "H,Generation",
                str_ind_size + ",Name_StringIndex",
                guid_ind_size + ",Mvid_GuidIndex",
                guid_ind_size + ",EncId_GuidIndex",
                guid_ind_size + ",EncBaseId_GuidIndex",
            ),
        )


class Module(ClrMetaDataTable[ModuleRow]):
    name = "Module"
    number = 0

    _row_class = ModuleRow


#### TypeRef Table
#


class TypeRefRowStruct(RowStruct):
    ResolutionScope_CodedIndex: int
    TypeName_StringIndex: int
    TypeNamespace_StringIndex: int


class TypeRefRow(MDTableRow):
    ResolutionScope: codedindex.ResolutionScope
    TypeName: str
    TypeNamespace: str

    _struct_class = TypeRefRowStruct

    _struct_strings = {
        "TypeName_StringIndex": "TypeName",
        "TypeNamespace_StringIndex": "TypeNamespace",
    }
    _struct_codedindexes = {
        "ResolutionScope_CodedIndex": ("ResolutionScope", codedindex.ResolutionScope),
    }

    def _compute_format(self):
        resolutionscope_size = self._clr_coded_index_struct_size(
            codedindex.ResolutionScope.tag_bits,
            codedindex.ResolutionScope.table_names,
        )
        str_ind_size = checked_offset_format(self._str_offsz)
        return (
            "CLR_METADATA_TABLE_TYPEREF",
            (
                resolutionscope_size + ",ResolutionScope_CodedIndex",
                str_ind_size + ",TypeName_StringIndex",
                str_ind_size + ",TypeNamespace_StringIndex",
            ),
        )


class TypeRef(ClrMetaDataTable[TypeRefRow]):
    name = "TypeRef"
    number = 1

    _row_class = TypeRefRow


#### TypeDef Table
#


class TypeDefRowStruct(RowStruct):
    Flags: int
    TypeName_StringIndex: int
    TypeNamespace_StringIndex: int
    Extends_CodedIndex: int
    FieldList_Index: int
    MethodList_Index: int


class TypeDefRow(MDTableRow):
    Flags: enums.ClrTypeAttr
    TypeName: str
    TypeNamespace: str
    Extends: codedindex.TypeDefOrRef
    FieldList: List[MDTableIndex["FieldRow"]]
    MethodList: List[MDTableIndex["MethodDefRow"]]

    _struct_class = TypeDefRowStruct

    _struct_strings = {
        "TypeName_StringIndex": "TypeName",
        "TypeNamespace_StringIndex": "TypeNamespace",
    }
    _struct_flags = {
        "Flags": ("Flags", enums.ClrTypeAttr),
    }
    _struct_codedindexes = {
        "Extends_CodedIndex": ("Extends", codedindex.TypeDefOrRef),
    }
    _struct_lists = {
        "FieldList_Index": ("FieldList", "Field"),
        "MethodList_Index": ("MethodList", "MethodDef"),
    }

    def _compute_format(self):
        extends_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        str_ind_size = checked_offset_format(self._str_offsz)
        fieldlist_size = self._clr_coded_index_struct_size(0, ("Field",))
        methodlist_size = self._clr_coded_index_struct_size(0, ("MethodDef",))
        return (
            "CLR_METADATA_TABLE_TYPEDEF",
            (
                "I,Flags",
                str_ind_size + ",TypeName_StringIndex",
                str_ind_size + ",TypeNamespace_StringIndex",
                extends_size + ",Extends_CodedIndex",
                fieldlist_size + ",FieldList_Index",
                methodlist_size + ",MethodList_Index",
            ),
        )


class TypeDef(ClrMetaDataTable[TypeDefRow]):
    name = "TypeDef"
    number = 2

    _row_class = TypeDefRow


#### FieldPtr Table
#


class FieldPtrRowStruct(RowStruct):
    Field_Index: int


class FieldPtrRow(MDTableRow):
    Field: MDTableIndex["FieldRow"]

    _struct_class = FieldPtrRowStruct

    _struct_indexes = {
        "Field_Index": ("Field", "Field"),
    }

    def _compute_format(self):
        field_size = self._clr_coded_index_struct_size(0, ("Field",))
        return (
            "CLR_METADATA_TABLE_FIELDPTR",
            (field_size + ",Field_Index", ),
        )


class FieldPtr(ClrMetaDataTable):
    name = "FieldPtr"
    number = 3

    _row_class = FieldPtrRow


#### Field Table
#


class FieldRowStruct(RowStruct):
    Flags: int
    Name_StringIndex: int
    Signature_BlobIndex: int


class FieldRow(MDTableRow):
    Flags: enums.ClrFieldAttr
    Name: str
    Signature: bytes

    _struct_class = FieldRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrFieldAttr),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_FIELD",
            (
                "H,Flags",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",Signature_BlobIndex",
            ),
        )


class Field(ClrMetaDataTable):
    name = "Field"
    number = 4

    _row_class = FieldRow


#### MethodPtr Table
#


class MethodPtrRowStruct(RowStruct):
    Method_Index: int


class MethodPtrRow(MDTableRow):
    Method: MDTableIndex["MethodDefRow"]

    _struct_class = MethodPtrRowStruct

    _struct_indexes = {
        "Method_Index": ("Method", "MethodDef"),
    }

    def _compute_format(self):
        method_size = self._clr_coded_index_struct_size(0, ("MethodDef",))
        return (
            "CLR_METADATA_TABLE_METHODPTR",
            (method_size + ",Method_Index", ),
        )


class MethodPtr(ClrMetaDataTable):
    name = "MethodPtr"
    number = 5

    _row_class = MethodPtrRow


#### MethodDef Table
#


class MethodDefRowStruct(RowStruct):
    Rva: int
    ImplFlags: int
    Flags: int
    Name_StringIndex: int
    Signature_BlobIndex: int
    ParamList_Index: int


class MethodDefRow(MDTableRow):
    Rva: int
    ImplFlags: enums.ClrMethodImpl
    Flags: enums.ClrMethodAttr
    Name: str
    Signature: bytes
    ParamList: List[MDTableIndex["ParamRow"]]

    _struct_class = MethodDefRowStruct

    _struct_asis = {
        "Rva": "Rva",
    }
    _struct_flags = {
        "ImplFlags": ("ImplFlags", enums.ClrMethodImpl),
        "Flags": ("Flags", enums.ClrMethodAttr),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }
    _struct_lists = {
        "ParamList_Index": ("ParamList", "Param"),
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        paramlist_size = self._clr_coded_index_struct_size(0, ("Param",))
        return (
            "CLR_METADATA_TABLE_METHODDEF",
            (
                "I,Rva",
                "H,ImplFlags",
                "H,Flags",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",Signature_BlobIndex",
                paramlist_size + ",ParamList_Index",
            ),
        )


class MethodDef(ClrMetaDataTable[MethodDefRow]):
    name = "MethodDef"
    number = 6

    _row_class = MethodDefRow


#### ParamPtr Table
#


class ParamPtrRowStruct(RowStruct):
    Param_Index: int


class ParamPtrRow(MDTableRow):
    Param: MDTableIndex["ParamRow"]

    _struct_class = ParamPtrRowStruct

    _struct_indexes = {
        "Param_Index": ("Param", "Param"),
    }

    def _compute_format(self):
        param_size = self._clr_coded_index_struct_size(0, ("Param",))
        return (
            "CLR_METADATA_TABLE_PARAMPTR",
            (param_size + ",Param_Index", ),
        )


class ParamPtr(ClrMetaDataTable):
    name = "ParamPtr"
    number = 7

    _row_class = ParamPtrRow


#### Param Table
#


class ParamRowStruct(RowStruct):
    Flags: int
    Sequence: int
    Name_StringIndex: int


class ParamRow(MDTableRow):
    Flags: enums.ClrParamAttr
    Sequence: int
    Name: str

    _struct_class = ParamRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrParamAttr),
    }
    _struct_asis = {
        "Sequence": "Sequence",
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        return (
            "CLR_METADATA_TABLE_PARAM",
            (
                "H,Flags",
                "H,Sequence",
                str_ind_size + ",Name_StringIndex",
            ),
        )


class Param(ClrMetaDataTable[ParamRow]):
    name = "Param"
    number = 8

    _row_class = ParamRow


#### InterfaceImpl Table
#


class InterfaceImplRowStruct(RowStruct):
    Class_Index: int
    Interface_CodedIndex: int


class InterfaceImplRow(MDTableRow):
    Class: MDTableIndex[TypeDefRow]
    Interface: codedindex.TypeDefOrRef

    _struct_class = InterfaceImplRowStruct

    _struct_indexes = {
        "Class_Index": ("Class", "TypeDef"),
    }
    _struct_codedindexes = {
        "Interface_CodedIndex": ("Interface", codedindex.TypeDefOrRef),
    }

    def _compute_format(self):
        interface_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        class_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        return (
            "CLR_METADATA_TABLE_INTERFACEIMPL",
            (class_size + ",Class_Index", interface_size + ",Interface_CodedIndex"),
        )


class InterfaceImpl(ClrMetaDataTable[InterfaceImplRow]):
    name = "InterfaceImpl"
    number = 9

    _row_class = InterfaceImplRow


#### MemberRef Table
#


class MemberRefRowStruct(RowStruct):
    Class_CodedIndex: int
    Name_StringIndex: int
    Signature_BlobIndex: int


class MemberRefRow(MDTableRow):
    Class: codedindex.MemberRefParent
    Name: str
    Signature: bytes

    _struct_class = MemberRefRowStruct

    _struct_codedindexes = {
        "Class_CodedIndex": ("Class", codedindex.MemberRefParent),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }

    def _compute_format(self):
        class_size = self._clr_coded_index_struct_size(
            codedindex.MemberRefParent.tag_bits,
            codedindex.MemberRefParent.table_names,
        )
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_MEMBERREF",
            (
                class_size + ",Class_CodedIndex",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",Signature_BlobIndex",
            ),
        )


class MemberRef(ClrMetaDataTable[MemberRefRow]):
    name = "MemberRef"
    number = 10

    #### MemberRef (aka MethodRef) Table

    _row_class = MemberRefRow


#### Constant Table
#


class ConstantRowStruct(RowStruct):
    Type: int
    Padding: int
    Parent_CodedIndex: int
    Value_BlobIndex: int


class ConstantRow(MDTableRow):
    Type: int
    Padding: int
    Parent: codedindex.HasConstant
    Value: bytes

    _struct_class = ConstantRowStruct

    _struct_asis = {
        "Type": "Type",
        "Padding": "Padding",
    }
    _struct_codedindexes = {
        "Parent_CodedIndex": ("Parent", codedindex.HasConstant),
    }
    _struct_blobs = {
        "Value_BlobIndex": "Value",
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasConstant.tag_bits,
            codedindex.HasConstant.table_names,
        )
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_CONSTANT",
            (
                "B,Type",
                "B,Padding",
                parent_size + ",Parent_CodedIndex",
                blob_ind_size + ",Value_BlobIndex",
            ),
        )


class Constant(ClrMetaDataTable[ConstantRow]):
    name = "Constant"
    number = 11

    #### Constant Table

    _row_class = ConstantRow


#### CustomAttribute Table
#


class CustomAttributeRowStruct(RowStruct):
    Parent_CodedIndex: int
    Type_CodedIndex: int
    Value_BlobIndex: int


class CustomAttributeRow(MDTableRow):
    Parent: codedindex.HasCustomAttribute
    Type: codedindex.CustomAttributeType
    Value: bytes

    _struct_class = CustomAttributeRowStruct

    _struct_codedindexes = {
        "Parent_CodedIndex": ("Parent", codedindex.HasCustomAttribute),
        "Type_CodedIndex": ("Type", codedindex.CustomAttributeType),
    }
    _struct_blobs = {
        "Value_BlobIndex": "Value",
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasCustomAttribute.tag_bits,
            codedindex.HasCustomAttribute.table_names,
        )
        type_size = self._clr_coded_index_struct_size(
            codedindex.CustomAttributeType.tag_bits,
            codedindex.CustomAttributeType.table_names,
        )
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_CUSTOMATTRIBUTE",
            (
                parent_size + ",Parent_CodedIndex",
                type_size + ",Type_CodedIndex",
                blob_ind_size + ",Value_BlobIndex",
            ),
        )


class CustomAttribute(ClrMetaDataTable[CustomAttributeRow]):
    name = "CustomAttribute"
    number = 12

    _row_class = CustomAttributeRow


#### FieldMarshal Table
#


class FieldMarshalRowStruct(RowStruct):
    Parent_CodedIndex: int
    NativeType_BlobIndex: int


class FieldMarshalRow(MDTableRow):
    Parent: codedindex.HasFieldMarshall
    NativeType: bytes

    _struct_class = FieldMarshalRowStruct

    _struct_codedindexes = {
        "Parent_CodedIndex": ("Parent", codedindex.HasFieldMarshall),
    }
    _struct_blobs = {
        "NativeType_BlobIndex": "NativeType",
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasFieldMarshall.tag_bits,
            codedindex.HasFieldMarshall.table_names,
        )
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_FIELDMARSHAL",
            (
                parent_size + ",Parent_CodedIndex",
                blob_ind_size + ",NativeType_BlobIndex",
            ),
        )


class FieldMarshal(ClrMetaDataTable[FieldMarshalRow]):
    name = "FieldMarshal"
    number = 13

    _row_class = FieldMarshalRow


#### DeclSecurity Table
#


class DeclSecurityRowStruct(RowStruct):
    Action: int
    Parent_CodedIndex: int
    PermissionSet_BlobIndex: int


class DeclSecurityRow(MDTableRow):
    Action: int
    Parent: codedindex.HasDeclSecurity
    PermissionSet: bytes

    _struct_class = DeclSecurityRowStruct

    _struct_asis = {
        "Action": "Action",
    }
    _struct_codedindexes = {
        "Parent_CodedIndex": ("Parent", codedindex.HasDeclSecurity),
    }
    _struct_blobs = {
        "PermissionSet_BlobIndex": "PermissionSet",
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasDeclSecurity.tag_bits,
            codedindex.HasDeclSecurity.table_names,
        )
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_DECLSECURITY",
            (
                "H,Action",
                parent_size + ",Parent_CodedIndex",
                blob_ind_size + ",PermissionSet_BlobIndex",
            ),
        )


class DeclSecurity(ClrMetaDataTable[DeclSecurityRow]):
    name = "DeclSecurity"
    number = 14

    _row_class = DeclSecurityRow


#### ClassLayout Table
#


class ClassLayoutRowStruct(RowStruct):
    PackingSize: int
    ClassSize: int
    Parent_Index: int


class ClassLayoutRow(MDTableRow):
    PackingSize: int
    ClassSize: int
    Parent: MDTableIndex[TypeDefRow]

    _struct_class = ClassLayoutRowStruct

    _struct_asis = {
        "PackingSize": "PackingSize",
        "ClassSize": "ClassSize",
    }
    _struct_indexes = {
        "Parent_Index": ("Parent", "TypeDef"),
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        return (
            "CLR_METADATA_TABLE_CLASSLAYOUT",
            (
                "H,PackingSize",
                "I,ClassSize",
                parent_size + ",Parent_Index",
            ),
        )


class ClassLayout(ClrMetaDataTable[ClassLayoutRow]):
    name = "ClassLayout"
    number = 15

    _row_class = ClassLayoutRow


#### FieldLayout Table
#


class FieldLayoutRowStruct(RowStruct):
    Offset: int
    Field_CodedIndex: int


class FieldLayoutRow(MDTableRow):
    Offset: int
    Field: MDTableIndex[FieldRow]

    _struct_class = FieldLayoutRowStruct

    _struct_asis = {
        "Offset": "Offset",
    }
    # TODO: should this be a codedindex?
    _struct_indexes = {
        "Field_CodedIndex": ("Field", "Field"),
    }

    def _compute_format(self):
        field_size = self._clr_coded_index_struct_size(0, ("Field",))
        return (
            "CLR_METADATA_TABLE_FieldLayout",
            (
                "I,Offset",
                field_size + ",Field_CodedIndex",
            ),
        )


class FieldLayout(ClrMetaDataTable[FieldLayoutRow]):
    name = "FieldLayout"
    number = 16

    _row_class = FieldLayoutRow


#### StandAloneSig Table
#


class StandAloneSigRowStruct(RowStruct):
    Signature_BlobIndex: int


class StandAloneSigRow(MDTableRow):
    Signature: bytes

    _struct_class = StandAloneSigRowStruct

    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }

    def _compute_format(self):
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_STANDALONESIG",
            (blob_ind_size + ",Signature_BlobIndex",),
        )


class StandAloneSig(ClrMetaDataTable[StandAloneSigRow]):
    name = "StandAloneSig"
    number = 17

    _row_class = StandAloneSigRow


#### EventMap Table
#


class EventMapRowStruct(RowStruct):
    Parent_Index: int
    EventList_Index: int


class EventMapRow(MDTableRow):
    Parent: MDTableIndex[TypeDefRow]
    EventList: List[MDTableIndex["EventRow"]]

    _struct_class = EventMapRowStruct

    _struct_indexes = {
        "Parent_Index": ("Parent", "TypeDef"),
    }

    _struct_lists = {
        "EventList_Index": ("EventList", "Event"),
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        eventlist_size = self._clr_coded_index_struct_size(0, ("Event",))
        return (
            "CLR_METADATA_TABLE_EVENTMAP",
            (
                parent_size + ",Parent_Index",
                eventlist_size + ",EventList_Index",
            ),
        )


class EventMap(ClrMetaDataTable[EventMapRow]):
    name = "EventMap"
    number = 18

    _row_class = EventMapRow


#### EventPtr Table
#


class EventPtr(ClrMetaDataTable):
    name = "EventPtr"
    number = 19
    # TODO


#### Event Table
#


class EventRowStruct(RowStruct):
    EventFlags: int
    Name_StringIndex: int
    EventType_CodedIndex: int


class EventRow(MDTableRow):
    EventFlags: enums.ClrEventAttr
    Name: str
    EventType: codedindex.TypeDefOrRef

    _struct_class = EventRowStruct

    _struct_flags = {
        "EventFlags": ("EventFlags", enums.ClrEventAttr),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_codedindexes = {
        "EventType_CodedIndex": ("EventType", codedindex.TypeDefOrRef),
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        eventtype_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        return (
            "CLR_METADATA_TABLE_EVENT",
            (
                "H,EventFlags",
                str_ind_size + ",Name_StringIndex",
                eventtype_size + ",EventType_CodedIndex",
            ),
        )


class Event(ClrMetaDataTable[EventRow]):
    name = "Event"
    number = 20

    _row_class = EventRow


#### PropertyMap Table
#


class PropertyMapRowStruct(RowStruct):
    Parent_Index: int
    PropertyList_Index: int


class PropertyMapRow(MDTableRow):
    Parent: MDTableIndex[TypeDefRow]
    PropertyList: List[MDTableIndex["PropertyRow"]]

    _struct_class = PropertyMapRowStruct

    _struct_indexes = {
        "Parent_Index": ("Parent", "TypeDef"),
    }

    _struct_lists = {
        "PropertyList_Index": ("PropertyList", "Property"),
    }

    def _compute_format(self):
        parent_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        propertylist_size = self._clr_coded_index_struct_size(0, ("Property",))
        return (
            "CLR_METADATA_TABLE_PROPERTYMAP",
            (
                parent_size + ",Parent_Index",
                propertylist_size + ",PropertyList_Index",
            ),
        )


class PropertyMap(ClrMetaDataTable[PropertyMapRow]):
    name = "PropertyMap"
    number = 21

    _row_class = PropertyMapRow


#### PropertyPtr Table
#


class PropertyPtr(ClrMetaDataTable):
    name = "PropertyPtr"
    number = 22
    # TODO


#### Property Table
#


class PropertyRowStruct(RowStruct):
    Flags: int
    Name_StringIndex: int
    Type_BlobIndex: int


class PropertyRow(MDTableRow):
    Flags: enums.ClrPropertyAttr
    Name: str
    Type: bytes

    _struct_class = PropertyRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrPropertyAttr),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_blobs = {
        "Type_BlobIndex": "Type",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_PROPERTY",
            (
                "H,Flags",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",Type_BlobIndex",
            ),
        )


class Property(ClrMetaDataTable[PropertyRow]):
    name = "Property"
    number = 23

    _row_class = PropertyRow


#### MethodSemantics Table
#


class MethodSemanticsRowStruct(RowStruct):
    Semantics: int
    Method_Index: int
    Association_CodedIndex: int


class MethodSemanticsRow(MDTableRow):
    Semantics: enums.ClrMethodSemanticsAttr
    Method: MDTableIndex[MethodDefRow]
    Association: codedindex.HasSemantics

    _struct_class = MethodSemanticsRowStruct

    _struct_flags = {
        "Semantics": ("Semantics", enums.ClrMethodSemanticsAttr),
    }

    _struct_indexes = {
        "Method_Index": ("Method", "MethodDef"),
    }
    _struct_codedindexes = {
        "Association_CodedIndex": ("Association", codedindex.HasSemantics),
    }

    def _compute_format(self):
        method_size = self._clr_coded_index_struct_size(0, ("MethodDef",))
        association_size = self._clr_coded_index_struct_size(
            codedindex.HasSemantics.tag_bits,
            codedindex.HasSemantics.table_names,
        )
        return (
            "CLR_METADATA_TABLE_METHODSEMANTICS",
            (
                "H,Semantics",
                method_size + ",Method_Index",
                association_size + ",Association_CodedIndex",
            ),
        )


class MethodSemantics(ClrMetaDataTable[MethodSemanticsRow]):
    name = "MethodSemantics"
    number = 24

    _row_class = MethodSemanticsRow


#### MethodImpl Table
#


class MethodImplRowStruct(RowStruct):
    Class_Index: int
    MethodBody_CodedIndex: int
    MethodDeclaration_CodedIndex: int


class MethodImplRow(MDTableRow):
    Class: MDTableIndex[TypeDefRow]
    MethodBody: codedindex.MethodDefOrRef
    MethodDeclaration: codedindex.MethodDefOrRef

    _struct_class = MethodImplRowStruct

    _struct_indexes = {
        "Class_Index": ("Class", "TypeDef"),
    }
    _struct_codedindexes = {
        "MethodBody_CodedIndex": ("MethodBody", codedindex.MethodDefOrRef),
        "MethodDeclaration_CodedIndex": (
            "MethodDeclaration",
            codedindex.MethodDefOrRef,
        ),
    }

    def _compute_format(self):
        class_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        method_size = self._clr_coded_index_struct_size(
            codedindex.MethodDefOrRef.tag_bits,
            codedindex.MethodDefOrRef.table_names,
        )
        return (
            "CLR_METADATA_TABLE_METHODIMPL",
            (
                class_size + ",Class_Index",
                method_size + ",MethodBody_CodedIndex",
                method_size + ",MethodDeclaration_CodedIndex",
            ),
        )


class MethodImpl(ClrMetaDataTable[MethodImplRow]):
    name = "MethodImpl"
    number = 25

    _row_class = MethodImplRow


#### ModuleRef Table
#


class ModuleRefRowStruct(RowStruct):
    Name_StringIndex: int


class ModuleRefRow(MDTableRow):
    Name: str

    _struct_class = ModuleRefRowStruct

    _struct_strings = {
        "Name_StringIndex": "Name",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        return (
            "CLR_METADATA_TABLE_MODULEREF",
            (str_ind_size + ",Name_StringIndex",),
        )


class ModuleRef(ClrMetaDataTable[ModuleRefRow]):
    name = "ModuleRef"
    number = 26

    _row_class = ModuleRefRow


#### TypeSpec Table
#


class TypeSpecRowStruct(RowStruct):
    Signature_BlobIndex: int


class TypeSpecRow(MDTableRow):
    Signature: bytes

    _struct_class = TypeSpecRowStruct

    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }

    def _compute_format(self):
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_TYPESPEC",
            (blob_ind_size + ",Signature_BlobIndex",),
        )


class TypeSpec(ClrMetaDataTable[TypeSpecRow]):
    name = "TypeSpec"
    number = 27

    _row_class = TypeSpecRow


#### ImplMap Table
#


class ImplMapRowStruct(RowStruct):
    MappingFlags: int
    MemberForwarded_CodedIndex: int
    ImportName_StringIndex: int
    ImportScope_Index: int


class ImplMapRow(MDTableRow):
    MappingFlags: enums.ClrPinvokeMap
    MemberForwarded: codedindex.MemberForwarded
    ImportName: str
    ImportScope: MDTableIndex[ModuleRefRow]

    _struct_class = ImplMapRowStruct

    _struct_flags = {
        "MappingFlags": ("MappingFlags", enums.ClrPinvokeMap),
    }
    _struct_codedindexes = {
        "MemberForwarded_CodedIndex": ("MemberForwarded", codedindex.MemberForwarded),
    }
    _struct_strings = {
        "ImportName_StringIndex": "ImportName",
    }
    _struct_indexes = {
        "ImportScope_Index": ("ImportScope", "ModuleRef"),
    }

    def _compute_format(self):
        member_size = self._clr_coded_index_struct_size(
            codedindex.MemberForwarded.tag_bits,
            codedindex.MemberForwarded.table_names,
        )
        str_ind_size = checked_offset_format(self._str_offsz)
        importscope_size = self._clr_coded_index_struct_size(0, ("ModuleRef",))
        return (
            "CLR_METADATA_TABLE_IMPLMAP",
            (
                "H,MappingFlags",
                member_size + ",MemberForwarded_CodedIndex",
                str_ind_size + ",ImportName_StringIndex",
                importscope_size + ",ImportScope_Index",
            ),
        )


class ImplMap(ClrMetaDataTable[ImplMapRow]):
    name = "ImplMap"
    number = 28

    _row_class = ImplMapRow


#### FieldRva Table
#


class FieldRvaRowStruct(RowStruct):
    Rva: int
    Field_Index: int


class FieldRvaRow(MDTableRow):
    Rva: int
    Field: MDTableIndex[FieldRow]

    _struct_class = FieldRvaRowStruct

    _struct_asis = {
        "Rva": "Rva",
    }
    _struct_indexes = {
        "Field_Index": ("Field", "Field"),
    }

    def _compute_format(self):
        field_size = self._clr_coded_index_struct_size(0, ("Field",))
        return (
            "CLR_METADATA_TABLE_FIELDRVA",
            (
                "I,Rva",
                field_size + ",Field_Index",
            ),
        )


class FieldRva(ClrMetaDataTable[FieldRvaRow]):
    name = "FieldRva"
    number = 29

    _row_class = FieldRvaRow


#### EncLog Table
#


class EncLogRowStruct(RowStruct):
    Token: int
    FuncCode: int


class EncLogRow(MDTableRow):
    Token: int
    FuncCode: int

    _struct_class = EncLogRowStruct

    _struct_asis = {
        "Token": "Token",
        "FuncCode": "FuncCode",
    }

    def _compute_format(self):
        return (
            "CLR_METADATA_TABLE_ENCLOG",
            (
                "I,Token",
                "I,FuncCode",
            ),
        )


class EncLog(ClrMetaDataTable):
    name = "EncLog"
    number = 30

    _row_class = EncLogRow


#### EncMap Table
#


class EncLogMapStruct(RowStruct):
    Token: int


class EncMapRow(MDTableRow):
    Token: int

    _struct_class = EncLogMapStruct

    _struct_asis = {
        "Token": "Token",
    }

    def _compute_format(self):
        return (
            "CLR_METADATA_TABLE_ENCMAP",
            (
                "I,Token",
            ),
        )


class EncMap(ClrMetaDataTable):
    name = "EncMap"
    number = 31

    _row_class = EncMapRow


#### Assembly Table
#


class AssemblyRowStruct(RowStruct):
    HashAlgId: int
    MajorVersion: int
    MinorVersion: int
    BuildNumber: int
    RevisionNumber: int
    Flags: int
    PublicKey_BlobIndex: int
    Name_StringIndex: int
    Culture_StringIndex: int


class AssemblyRow(MDTableRow):
    HashAlgId: enums.AssemblyHashAlgorithm
    MajorVersion: int
    MinorVersion: int
    BuildNumber: int
    RevisionNumber: int
    Flags: enums.ClrAssemblyFlags
    PublicKey: bytes
    Name: str
    Culture: str

    _struct_class = AssemblyRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrAssemblyFlags),
    }
    _struct_enums = {
        "HashAlgId": ("HashAlgId", enums.AssemblyHashAlgorithm),
    }
    _struct_asis = {
        "MajorVersion": "MajorVersion",
        "MinorVersion": "MinorVersion",
        "BuildNumber": "BuildNumber",
        "RevisionNumber": "RevisionNumber",
    }
    _struct_blobs = {
        "PublicKey_BlobIndex": "PublicKey",
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
        "Culture_StringIndex": "Culture",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_ASSEMBLY",
            (
                "I,HashAlgId",
                "H,MajorVersion",
                "H,MinorVersion",
                "H,BuildNumber",
                "H,RevisionNumber",
                "I,Flags",
                blob_ind_size + ",PublicKey_BlobIndex",
                str_ind_size + ",Name_StringIndex",
                str_ind_size + ",Culture_StringIndex",
            ),
        )


class Assembly(ClrMetaDataTable[AssemblyRow]):
    name = "Assembly"
    number = 32

    _row_class = AssemblyRow


#### AssemblyProcessor Table
#


class AssemblyProcessorRowStruct(RowStruct):
    Processor: int


class AssemblyProcessorRow(MDTableRow):
    Processor: int

    _struct_class = AssemblyProcessorRowStruct

    _format = ("CLR_METADATA_TABLE_ASSEMBLYPROCESSOR", ("I,Processor",))

    _struct_asis = {
        "Processor": "Processor",
    }


class AssemblyProcessor(ClrMetaDataTable[AssemblyProcessorRow]):
    name = "AssemblyProcessor"
    number = 33

    _row_class = AssemblyProcessorRow


#### AssemblyOS Table
#


class AssemblyOSRowStruct(RowStruct):
    OSPlatformID: int
    OSMajorVersion: int
    OSMinorVersion: int


class AssemblyOSRow(MDTableRow):
    OSPlatformID: int
    OSMajorVersion: int
    OSMinorVersion: int

    _struct_class = AssemblyOSRowStruct

    _format = (
        "CLR_METADATA_TABLE_ASSEMBLYPROCESSOR",
        (
            "I,OSPlatformID",
            "I,OSMajorVersion",
            "I,OSMinorVersion",
        ),
    )

    _struct_asis = {
        "OSPlatformID": "OSPlatformID",
        "OSMajorVersion": "OSMajorVersion",
        "OSMinorVersion": "OSMinorVersion",
    }


class AssemblyOS(ClrMetaDataTable[AssemblyOSRow]):
    name = "AssemblyOS"
    number = 34

    _row_class = AssemblyOSRow


#### AssemblyRef Table
#


class AssemblyRefRowStruct(RowStruct):
    MajorVersion: int
    MinorVersion: int
    BuildNumber: int
    RevisionNumber: int
    Flags: int
    PublicKey_BlobIndex: int
    Name_StringIndex: int
    Culture_StringIndex: int
    HashValue_BlobIndex: int


class AssemblyRefRow(MDTableRow):
    MajorVersion: int
    MinorVersion: int
    BuildNumber: int
    RevisionNumber: int
    Flags: enums.ClrAssemblyFlags
    PublicKey: bytes
    Name: str
    Culture: str
    HashValue: bytes

    _struct_class = AssemblyRefRowStruct

    _struct_asis = {
        "MajorVersion": "MajorVersion",
        "MinorVersion": "MinorVersion",
        "BuildNumber": "BuildNumber",
        "RevisionNumber": "RevisionNumber",
    }
    _struct_flags = {
        "Flags": ("Flags", enums.ClrAssemblyFlags),
    }
    _struct_blobs = {
        "PublicKey_BlobIndex": "PublicKey",
        "HashValue_BlobIndex": "HashValue",
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
        "Culture_StringIndex": "Culture",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_ASSEMBLYREF",
            (
                "H,MajorVersion",
                "H,MinorVersion",
                "H,BuildNumber",
                "H,RevisionNumber",
                "I,Flags",
                blob_ind_size + ",PublicKey_BlobIndex",
                str_ind_size + ",Name_StringIndex",
                str_ind_size + ",Culture_StringIndex",
                blob_ind_size + ",HashValue_BlobIndex",
            ),
        )


class AssemblyRef(ClrMetaDataTable[AssemblyRefRow]):
    name = "AssemblyRef"
    number = 35

    _row_class = AssemblyRefRow


#### AssemblyRefProcessor Table
#


class AssemblyRefProcessorRowStruct(RowStruct):
    Processor: int
    AssemblyRef_Index: int


class AssemblyRefProcessorRow(MDTableRow):
    Processor: int
    AssemblyRef: MDTableIndex[AssemblyRefRow]

    _struct_class = AssemblyRefProcessorRowStruct

    _struct_asis = {
        "Processor": "Processor",
    }
    _struct_indexes = {
        "AssemblyRef_Index": ("AssemblyRef", "AssemblyRef"),
    }

    def _compute_format(self):
        assemblyref_size = self._clr_coded_index_struct_size(0, ("AssemblyRef",))
        return (
            "CLR_METADATA_TABLE_ASSEMBLYREFPROCESSOR",
            (
                "I,Processor",
                assemblyref_size + ",AssemblyRef_Index",
            ),
        )


class AssemblyRefProcessor(ClrMetaDataTable[AssemblyRefProcessorRow]):
    name = "AssemblyRefProcessor"
    number = 36

    _row_class = AssemblyRefProcessorRow


#### AssemblyRefOS Table
#


class AssemblyRefOSRowStruct(RowStruct):
    OSPlatformId: int
    OSMajorVersion: int
    OSMinorVersion: int
    AssemblyRef_Index: int


class AssemblyRefOSRow(MDTableRow):
    OSPlatformId: int
    OSMajorVersion: int
    OSMinorVersion: int
    AssemblyRef: MDTableIndex[AssemblyRefRow]

    _struct_class = AssemblyRefOSRowStruct

    _struct_asis = {
        "OSPlatformId": "OSPlatformId",
        "OSMajorVersion": "OSMajorVersion",
        "OSMinorVersion": "OSMinorVersion",
    }
    _struct_indexes = {
        "AssemblyRef_Index": ("AssemblyRef", "AssemblyRef"),
    }

    def _compute_format(self):
        assemblyref_size = self._clr_coded_index_struct_size(0, ("AssemblyRef",))
        return (
            "CLR_METADATA_TABLE_ASSEMBLYREFOS",
            (
                "I,OSPlatformId",
                "I,OSMajorVersion",
                "I,OSMinorVersion",
                assemblyref_size + ",AssemblyRef_Index",
            ),
        )


class AssemblyRefOS(ClrMetaDataTable[AssemblyRefOSRow]):
    name = "AssemblyRefOS"
    number = 37

    _row_class = AssemblyRefOSRow


#### File Table
#


class FileRowStruct(RowStruct):
    Flags: int
    Name_StringIndex: int
    HashValue_BlobIndex: int


class FileRow(MDTableRow):
    Flags: enums.ClrFileFlags
    Name: str
    HashValue: bytes

    _struct_class = FileRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrFileFlags),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_blobs = {
        "HashValue_BlobIndex": "HashValue",
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_FILE",
            (
                "I,Flags",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",HashValue_BlobIndex",
            ),
        )


class File(ClrMetaDataTable[FileRow]):
    name = "File"
    number = 38

    _row_class = FileRow


#### ExportedType Table
#


class ExportedTypeRowStruct(RowStruct):
    Flags: int
    TypeDefId: int
    TypeName_StringIndex: int
    TypeNamespace_StringIndex: int
    Implementation_CodedIndex: int


class ExportedTypeRow(MDTableRow):
    Flags: enums.ClrTypeAttr
    TypeDefId: int
    TypeName: str
    TypeNamespace: str
    Implementation: codedindex.Implementation

    _struct_class = ExportedTypeRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrTypeAttr),
    }
    _struct_asis = {
        "TypeDefId": "TypeDefId",
    }
    _struct_strings = {
        "TypeName_StringIndex": "TypeName",
        "TypeNamespace_StringIndex": "TypeNamespace",
    }
    _struct_codedindexes = {
        "Implementation_CodedIndex": ("Implementation", codedindex.Implementation),
    }

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        blob_ind_size = checked_offset_format(self._blob_offsz)
        implementation_size = self._clr_coded_index_struct_size(
            codedindex.Implementation.tag_bits,
            codedindex.Implementation.table_names,
        )
        return (
            "CLR_METADATA_TABLE_EXPORTEDTYPE",
            (
                "I,Flags",
                "I,TypeDefId",
                str_ind_size + ",TypeName_StringIndex",
                str_ind_size + ",TypeNamespace_StringIndex",
                implementation_size + ",Implementation_CodedIndex",
            ),
        )


class ExportedType(ClrMetaDataTable[ExportedTypeRow]):
    name = "ExportedType"
    number = 39

    _row_class = ExportedTypeRow


#### ManifestResource Table
#


class ManifestResourceRowStruct(RowStruct):
    Offset: int
    Flags: int
    Name_StringIndex: int
    Implementation_CodedIndex: int


class ManifestResourceRow(MDTableRow):
    Offset: int
    Flags: enums.ClrManifestResourceFlags
    Name: str
    Implementation: Optional[codedindex.Implementation]

    _struct_class = ManifestResourceRowStruct

    _struct_asis = {
        "Offset": "Offset",
    }
    _struct_flags = {
        "Flags": ("Flags", enums.ClrManifestResourceFlags),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_codedindexes = {
        "Implementation_CodedIndex": ("Implementation", codedindex.Implementation),
    }

    def parse(self, tables: List[ClrMetaDataTable], next_row: Optional[MDTableRow]):
        super().parse(tables, next_row)
        if self.struct.Implementation_CodedIndex == 0:
            # Special case per ECMA-335. Resource is in current assembly.
            self.Implementation = None

    def _compute_format(self):
        str_ind_size = checked_offset_format(self._str_offsz)
        implementation_size = self._clr_coded_index_struct_size(
            codedindex.Implementation.tag_bits,
            codedindex.Implementation.table_names,
        )
        return (
            "CLR_METADATA_TABLE_MANIFESTRESOURCE",
            (
                "I,Offset",
                "I,Flags",
                str_ind_size + ",Name_StringIndex",
                implementation_size + ",Implementation_CodedIndex",
            ),
        )


class ManifestResource(ClrMetaDataTable[ManifestResourceRow]):
    name = "ManifestResource"
    number = 40

    _row_class = ManifestResourceRow


#### NestedClass Table
#


class NestedClassRowStruct(RowStruct):
    NestedClass_Index: int
    EnclosingClass_Index: int


class NestedClassRow(MDTableRow):
    NestedClass: MDTableIndex[TypeDefRow]
    EnclosingClass: MDTableIndex[TypeDefRow]

    _struct_class = NestedClassRowStruct

    _struct_indexes = {
        "NestedClass_Index": ("NestedClass", "TypeDef"),
        "EnclosingClass_Index": ("EnclosingClass", "TypeDef"),
    }

    def _compute_format(self):
        class_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        return (
            "CLR_METADATA_TABLE_NESTEDCLASS",
            (
                class_size + ",NestedClass_Index",
                class_size + ",EnclosingClass_Index",
            ),
        )


class NestedClass(ClrMetaDataTable[NestedClassRow]):
    name = "NestedClass"
    number = 41

    _row_class = NestedClassRow


#### GenericParam Table
#


class GenericParamRowStruct(RowStruct):
    Number: int
    Flags: int
    Owner_CodedIndex: int
    Name_StringIndex: int


class GenericParamRow(MDTableRow):
    Number: int
    Flags: enums.ClrGenericParamAttr
    Owner: codedindex.TypeOrMethodDef
    Name: str

    _struct_class = GenericParamRowStruct

    _struct_asis = {
        "Number": "Number",
    }
    _struct_flags = {
        "Flags": ("Flags", enums.ClrGenericParamAttr),
    }
    _struct_codedindexes = {
        "Owner_CodedIndex": ("Owner", codedindex.TypeOrMethodDef),
    }
    _struct_strings = {
        "Name_StringIndex": "Name",
    }

    def _compute_format(self):
        owner_size = self._clr_coded_index_struct_size(
            codedindex.TypeOrMethodDef.tag_bits,
            codedindex.TypeOrMethodDef.table_names,
        )
        str_ind_size = checked_offset_format(self._str_offsz)
        return (
            "CLR_METADATA_TABLE_GENERICPARAM",
            (
                "H,Number",
                "H,Flags",
                owner_size + ",Owner_CodedIndex",
                str_ind_size + ",Name_StringIndex",
            ),
        )


class GenericParam(ClrMetaDataTable[GenericParamRow]):
    name = "GenericParam"
    number = 42

    _row_class = GenericParamRow


#### MethodSpec Table
#


class MethodSpecRowStruct(RowStruct):
    Method_CodedIndex: int
    Instantiation_BlobIndex: int


class MethodSpecRow(MDTableRow):
    Method: codedindex.MethodDefOrRef
    Instantiation: bytes

    _struct_class = MethodSpecRowStruct

    _struct_codedindexes = {
        "Method_CodedIndex": ("Method", codedindex.MethodDefOrRef),
    }
    _struct_blobs = {
        "Instantiation_BlobIndex": "Instantiation",
    }

    def _compute_format(self):
        method_size = self._clr_coded_index_struct_size(
            codedindex.MethodDefOrRef.tag_bits,
            codedindex.MethodDefOrRef.table_names,
        )
        blob_ind_size = checked_offset_format(self._blob_offsz)
        return (
            "CLR_METADATA_TABLE_GENERICMETHOD",
            (
                method_size + ",Method_CodedIndex",
                blob_ind_size + ",Instantiation_BlobIndex",
            ),
        )


class MethodSpec(ClrMetaDataTable[MethodSpecRow]):
    name = "MethodSpec"
    number = 43

    _row_class = MethodSpecRow


#### GenericParamConstraint Table
#


class GenericParamConstraintRowStruct(RowStruct):
    Owner_Index: int
    Constraint_CodedIndex: int


class GenericParamConstraintRow(MDTableRow):
    Owner: MDTableIndex[GenericParamRow]
    Constraint: codedindex.TypeDefOrRef

    _struct_class = GenericParamConstraintRowStruct

    _struct_indexes = {
        "Owner_Index": ("Owner", "GenericParam"),
    }
    _struct_codedindexes = {
        "Constraint_CodedIndex": ("Constraint", codedindex.TypeDefOrRef),
    }

    def _compute_format(self):
        owner_size = self._clr_coded_index_struct_size(0, ("GenericParam",))
        constraint_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        return (
            "CLR_METADATA_TABLE_GENERICPARAMCONSTRAINT",
            (
                owner_size + ",Owner_Index",
                constraint_size + ",Constraint_CodedIndex",
            ),
        )


class GenericParamConstraint(ClrMetaDataTable[GenericParamConstraintRow]):
    name = "GenericParamConstraint"
    number = 44

    _row_class = GenericParamConstraintRow


# Unused
# 45
# 46
# 47
# ...
# 60
# 61
# 62

class Unused(ClrMetaDataTable):
    # placeholder for unused table references.
    # which is referenced by `CustomAttributeType` coded index.
    name = "Unused"
    number = 62


class MaxTable(ClrMetaDataTable):
    name = "MaxTable"
    number = 63


class ClrMetaDataTableFactory(object):
    _table_number_map: Dict[int, Type[ClrMetaDataTable]] = {
        0: Module,
        1: TypeRef,
        2: TypeDef,
        3: FieldPtr,  # Not public
        4: Field,
        5: MethodPtr,  # Not public
        6: MethodDef,
        7: ParamPtr,  # Not public
        8: Param,
        9: InterfaceImpl,
        10: MemberRef,
        11: Constant,
        12: CustomAttribute,
        13: FieldMarshal,
        14: DeclSecurity,
        15: ClassLayout,
        16: FieldLayout,
        17: StandAloneSig,
        18: EventMap,
        19: EventPtr,  # Not public
        20: Event,
        21: PropertyMap,
        22: PropertyPtr,  # Not public
        23: Property,
        24: MethodSemantics,
        25: MethodImpl,
        26: ModuleRef,
        27: TypeSpec,
        28: ImplMap,
        29: FieldRva,
        30: EncLog,
        31: EncMap,
        32: Assembly,
        33: AssemblyProcessor,
        34: AssemblyOS,
        35: AssemblyRef,
        36: AssemblyRefProcessor,
        37: AssemblyRefOS,
        38: File,
        39: ExportedType,
        40: ManifestResource,
        41: NestedClass,
        42: GenericParam,
        43: MethodSpec,
        44: GenericParamConstraint,
        # 45 through 63 are not used
        62: Unused,
        63: MaxTable,
    }

    @classmethod
    def createTable(
        cls,
        number: int,
        tables_rowcounts: List[Optional[int]],
        is_sorted: bool,
        strings_offset_size: int,
        guid_offset_size: int,
        blob_offset_size: int,
        strings_heap: Optional["stream.StringsHeap"],
        guid_heap: Optional["stream.GuidHeap"],
        blob_heap: Optional["stream.BlobHeap"],
        lazy_load=False
    ) -> ClrMetaDataTable:
        if number not in cls._table_number_map:
            raise errors.dnFormatError("invalid table index")

        table = cls._table_number_map[number](
            tables_rowcounts,
            is_sorted,
            strings_offset_size,
            guid_offset_size,
            blob_offset_size,
            strings_heap,
            guid_heap,
            blob_heap,
            lazy_load,
        )
        return table
