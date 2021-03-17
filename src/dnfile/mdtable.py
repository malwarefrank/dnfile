# -*- coding: utf-8 -*-
"""
.NET Metadata Tables


REFERENCES

    https://www.ntcore.com/files/dotnetformat.htm
    https://referencesource.microsoft.com/System.AddIn/System/Addin/MiniReflection/MetadataReader/Metadata.cs.html#123


Copyright (c) 2020-2021 MalwareFrank
"""


from typing import List, Type

from .base import MDTableRow, ClrMetaDataTable, RowStruct, ClrHeap
from . import utils, codedindex, enums


#### Module Table
#


class ModuleRowStruct(RowStruct):
    Generation: int = None
    Name_StringIndex: int = None
    Mvid_GuidIndex: int = None
    EncId_GuidIndex: int = None
    EncBaseId_GuidIndex: int = None


class ModuleRow(MDTableRow):
    Generation: int
    Name: str
    Mvid: str
    EncId: str
    EncBaseId: str

    struct: ModuleRowStruct
    _struct_class = ModuleRowStruct

    _struct_asis = {"Generation": "Generation"}
    _struct_strings = {
        "Name_StringIndex": "Name",
    }
    _struct_guids = {
        "Mvid_GuidIndex": "Mvid",
        "EncId_GuidIndex": "EncId",
        "EncBaseId_GuidIndex": "EncBaseId",
    }

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        guid_ind_size = utils.num_bytes_to_struct_char(self._guid_offsz)
        self._format = (
            "CLR_METADATA_TABLE_MODULE",
            (
                "H,Generation",
                str_ind_size + ",Name_StringIndex",
                guid_ind_size + ",Mvid_GuidIndex",
                guid_ind_size + ",EncId_GuidIndex",
                guid_ind_size + ",EncBaseId_GuidIndex",
            ),
        )


class Module(ClrMetaDataTable):
    name = "Module"
    number = 0

    _row_class = ModuleRow


#### TypeRef Table
#


class TypeRefRowStruct(RowStruct):
    ResolutionScope_CodedIndex: int = None
    TypeName_StringIndex: int = None
    TypeNamespace_StringIndex: int = None


class TypeRefRow(MDTableRow):
    ResolutionScope: codedindex.ResolutionScope
    TypeName: str
    TypeNamespace: str

    struct: TypeRefRowStruct
    _struct_class = TypeRefRowStruct

    _struct_strings = {
        "TypeName_StringIndex": "TypeName",
        "TypeNamespace_StringIndex": "TypeNamespace",
    }
    _struct_codedindexes = {
        "ResolutionScope_CodedIndex": ("ResolutionScope", codedindex.ResolutionScope),
    }

    def _init_format(self):
        resolutionscope_size = self._clr_coded_index_struct_size(
            codedindex.ResolutionScope.tag_bits,
            codedindex.ResolutionScope.table_names,
        )
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        self._format = (
            "CLR_METADATA_TABLE_TYPEREF",
            (
                resolutionscope_size + ",ResolutionScope_CodedIndex",
                str_ind_size + ",TypeName_StringIndex",
                str_ind_size + ",TypeNamespace_StringIndex",
            ),
        )


class TypeRef(ClrMetaDataTable):
    name = "TypeRef"
    number = 1

    _row_class = TypeRefRow


#### TypeDef Table
#


class TypeDefRowStruct(RowStruct):
    Flags: int = None
    TypeName_StringIndex: int = None
    TypeNamespace_StringIndex: int = None
    Extends_CodedIndex: int = None
    FieldList_Index: int = None
    MethodList_Index: int = None


class TypeDefRow(MDTableRow):
    Flags: enums.ClrTypeAttr
    TypeName: str
    TypeNamespace: str
    Extends: codedindex.TypeDefOrRef
    FieldList: List
    MethodList: List

    struct: TypeDefRowStruct
    _struct_class = TypeDefRowStruct

    _struct_strings = {
        "TypeName_StringIndex": "TypeName",
        "TypeNamespace_StringIndex": "TypeNamespace",
    }
    _struct_flags = {
        "Flags": ("Flags", enums.ClrTypeAttr),
    }

    def _init_format(self):
        extends_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        fieldlist_size = self._clr_coded_index_struct_size(0, ("Field",))
        methodlist_size = self._clr_coded_index_struct_size(0, ("MethodDef",))
        self._format = (
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


class TypeDef(ClrMetaDataTable):
    name = "TypeDef"
    number = 2

    _row_class = TypeDefRow


#### FieldPtr Table
#


class FieldPtr(ClrMetaDataTable):
    name = "FieldPtr"
    number = 3
    # TODO


#### Field Table
#


class FieldRowStruct(RowStruct):
    Flags: int = None
    Name_StringIndex: int = None
    Signature_BlobIndex: int = None


class FieldRow(MDTableRow):
    Flags: enums.ClrFieldAttr
    Name: str
    Signature: bytes

    struct: FieldRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
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


class MethodPtr(ClrMetaDataTable):
    name = "MethodPtr"
    number = 5
    # TODO


#### MethodDef Table
#


class MethodDefRowStruct(RowStruct):
    Rva: int = None
    ImplFlags: int = None
    Flags: int = None
    Name_StringIndex: int = None
    Signature_BlobIndex: int = None
    ParamList_Index: int = None


class MethodDefRow(MDTableRow):
    Rva: int
    ImplFlags: enums.ClrMethodImpl
    Flags: enums.ClrMethodAttr
    Name: str
    Signature: bytes
    ParamList: List["ParamRow"]

    struct: MethodDefRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        paramlist_size = self._clr_coded_index_struct_size(0, ("Param",))
        self._format = (
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


class MethodDef(ClrMetaDataTable):
    name = "MethodDef"
    number = 6

    _row_class = MethodDefRow


#### ParamPtr Table
#


class ParamPtr(ClrMetaDataTable):
    name = "ParamPtr"
    number = 7
    # TODO


#### Param Table
#


class ParamRowStruct(RowStruct):
    Flags: int = None
    Sequence: int = None
    Name_StringIndex: int = None


class ParamRow(MDTableRow):
    Flags: enums.ClrParamAttr
    Sequence: int
    Name: str

    struct: ParamRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        self._format = (
            "CLR_METADATA_TABLE_PARAM",
            (
                "H,Flags",
                "H,Sequence",
                str_ind_size + ",Name_StringIndex",
            ),
        )


class Param(ClrMetaDataTable):
    name = "Param"
    number = 8

    _row_class = ParamRow


#### InterfaceImpl Table
#


class InterfaceImplRowStruct(RowStruct):
    Class_Index: int = None
    Interface_CodedIndex: int = None


class InterfaceImplRow(MDTableRow):
    Class: TypeDefRow
    Interface: codedindex.TypeDefOrRef

    struct: InterfaceImplRowStruct
    _struct_class = InterfaceImplRowStruct

    _struct_indexes = {
        "Class_Index": ("Class", "TypeDef"),
    }
    _struct_codedindexes = {
        "Interface_CodedIndex": ("Interface", codedindex.TypeDefOrRef),
    }

    def _init_format(self):
        interface_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        class_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        self._format = (
            "CLR_METADATA_TABLE_INTERFACEIMPL",
            (class_size + ",Class_Index", interface_size + ",Interface_CodedIndex"),
        )


class InterfaceImpl(ClrMetaDataTable):
    name = "InterfaceImpl"
    number = 9

    _row_class = InterfaceImplRow


#### MemberRef Table
#


class MemberRefRowStruct(RowStruct):
    Class_CodedIndex: int = None
    Name_StringIndex: int = None
    Signature_BlobIndex: int = None


class MemberRefRow(MDTableRow):
    Class: codedindex.MemberRefParent
    Name: str
    Signature: bytes

    struct: MemberRefRowStruct
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

    def _init_format(self):
        class_size = self._clr_coded_index_struct_size(
            codedindex.MemberRefParent.tag_bits,
            codedindex.MemberRefParent.table_names,
        )
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_MEMBERREF",
            (
                class_size + ",Class_CodedIndex",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",Signature_BlobIndex",
            ),
        )


class MemberRef(ClrMetaDataTable):
    name = "MemberRef"
    number = 10

    #### MemberRef (aka MethodRef) Table

    _row_class = MemberRefRow


#### Constant Table
#


class ConstantRowStruct(RowStruct):
    Type: int = None
    Padding: int = None
    Parent_CodedIndex: int = None
    Value_BlobIndex: int = None


class ConstantRow(MDTableRow):
    Type: int
    Padding: int
    Parent: codedindex.HasConstant
    Value: bytes

    struct: ConstantRowStruct
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

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasConstant.tag_bits,
            codedindex.HasConstant.table_names,
        )
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_CONSTANT",
            (
                "B,Type",
                "B,Padding",
                parent_size + ",Parent_CodedIndex",
                blob_ind_size + ",Value_BlobIndex",
            ),
        )


class Constant(ClrMetaDataTable):
    name = "Constant"
    number = 11

    #### Constant Table

    _row_class = ConstantRow


#### CustomAttribute Table
#


class CustomAttributeRowStruct(RowStruct):
    Parent_CodedIndex: int = None
    Type_CodedIndex: int = None
    Value_BlobIndex: int = None


class CustomAttributeRow(MDTableRow):
    Parent: codedindex.HasCustomAttribute
    Type: codedindex.CustomAttributeType
    Value: bytes

    struct: CustomAttributeRowStruct
    _struct_class = CustomAttributeRowStruct

    _struct_codedindexes = {
        "Parent_CodedIndex": ("Parent", codedindex.HasCustomAttribute),
        "Type_CodedIndex": ("Type", codedindex.CustomAttributeType),
    }
    _struct_blobs = {
        "Value_BlobIndex": "Value",
    }

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasCustomAttribute.tag_bits,
            codedindex.HasCustomAttribute.table_names,
        )
        type_size = self._clr_coded_index_struct_size(
            codedindex.CustomAttributeType.tag_bits,
            codedindex.CustomAttributeType.table_names,
        )
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_CUSTOMATTRIBUTE",
            (
                parent_size + ",Parent_CodedIndex",
                type_size + ",Type_CodedIndex",
                blob_ind_size + ",Value_BlobIndex",
            ),
        )


class CustomAttribute(ClrMetaDataTable):
    name = "CustomAttribute"
    number = 12

    _row_class = CustomAttributeRow


#### FieldMarshal Table
#


class FieldMarshalRowStruct(RowStruct):
    Parent_CodedIndex: int = None
    NativeType_BlobIndex: int = None


class FieldMarshalRow(MDTableRow):
    Parent: codedindex.HasFieldMarshall
    NativeType: bytes

    struct: FieldMarshalRowStruct
    _struct_class = FieldMarshalRowStruct

    _struct_codedindexes = {
        "Parent_CodedIndex": ("Parent", codedindex.HasFieldMarshall),
    }
    _struct_blobs = {
        "NativeType_BlobIndex": "NativeType",
    }

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasFieldMarshall.tag_bits,
            codedindex.HasFieldMarshall.table_names,
        )
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_FIELDMARSHAL",
            (
                parent_size + ",Parent_CodedIndex",
                blob_ind_size + ",NativeType_BlobIndex",
            ),
        )


class FieldMarshal(ClrMetaDataTable):
    name = "FieldMarshal"
    number = 13

    _row_class = FieldMarshalRow


#### DeclSecurity Table
#


class DeclSecurityRowStruct(RowStruct):
    Action: int = None
    Parent_CodedIndex: int = None
    PermissionSet_BlobIndex: int = None


class DeclSecurityRow(MDTableRow):
    Action: int
    Parent: codedindex.HasDeclSecurity
    PermissionSet: bytes

    struct: DeclSecurityRowStruct
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

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(
            codedindex.HasDeclSecurity.tag_bits,
            codedindex.HasDeclSecurity.table_names,
        )
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_DECLSECURITY",
            (
                "H,Action",
                parent_size + ",Parent_CodedIndex",
                blob_ind_size + ",PermissionSet_BlobIndex",
            ),
        )


class DeclSecurity(ClrMetaDataTable):
    name = "DeclSecurity"
    number = 14

    _row_class = DeclSecurityRow


#### ClassLayout Table
#


class ClassLayoutRowStruct(RowStruct):
    PackingSize: int = None
    ClassSize: int = None
    Parent_Index: int = None


class ClassLayoutRow(MDTableRow):
    PackingSize: int
    ClassSize: int
    Parent: TypeDefRow

    struct: ClassLayoutRowStruct
    _struct_class = ClassLayoutRowStruct

    _struct_asis = {
        "PackingSize": "PackingSize",
        "ClassSize": "ClassSize",
    }
    _struct_indexes = {
        "Parent_Index": ("Parent", "TypeDef"),
    }

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        self._format = (
            "CLR_METADATA_TABLE_CLASSLAYOUT",
            (
                "H,PackingSize",
                "I,ClassSize",
                parent_size + ",Parent_Index",
            ),
        )


class ClassLayout(ClrMetaDataTable):
    name = "ClassLayout"
    number = 15

    _row_class = ClassLayoutRow


#### FieldLayout Table
#


class FieldLayoutRowStruct(RowStruct):
    Offset: int = None
    Field_CodedIndex: int = None


class FieldLayoutRow(MDTableRow):
    Offset: int
    Field: FieldRow

    struct: FieldLayoutRowStruct
    _struct_class = FieldLayoutRowStruct

    _struct_asis = {
        "Offset": "Offset",
    }
    _struct_indexes = {
        "Field_CodedIndex": ("Field", "Field"),
    }

    def _init_format(self):
        field_size = self._clr_coded_index_struct_size(0, ("Field",))
        self._format = (
            "CLR_METADATA_TABLE_FieldLayout",
            (
                "I,Offset",
                field_size + ",Field_CodedIndex",
            ),
        )


class FieldLayout(ClrMetaDataTable):
    name = "FieldLayout"
    number = 16

    _row_class = FieldLayoutRow


#### StandAloneSig Table
#


class StandAloneSigRowStruct(RowStruct):
    Signature_BlobIndex: int = None


class StandAloneSigRow(MDTableRow):
    Signature: bytes = None

    struct: StandAloneSigRowStruct
    _struct_class = StandAloneSigRowStruct

    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }

    def _init_format(self):
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_STANDALONESIG",
            (blob_ind_size + ",Signature_BlobIndex",),
        )


class StandAloneSig(ClrMetaDataTable):
    name = "StandAloneSig"
    number = 17

    _row_class = StandAloneSigRow


#### EventMap Table
#


class EventMapRowStruct(RowStruct):
    Parent_Index: int = None
    EventList_Index: int = None


class EventMapRow(MDTableRow):
    Parent: TypeDefRow = None
    EventList: List["EventRow"] = None

    struct: EventMapRowStruct
    _struct_class = EventMapRowStruct

    _struct_indexes = {
        "Parent_Index": ("Parent", "TypeDef"),
    }

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        eventlist_size = self._clr_coded_index_struct_size(0, ("Event",))
        self._format = (
            "CLR_METADATA_TABLE_EVENTMAP",
            (
                parent_size + ",Parent_Index",
                eventlist_size + ",EventList_Index",
            ),
        )


class EventMap(ClrMetaDataTable):
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
    EventFlags: int = None
    Name_StringIndex: int = None
    EventType_CodedIndex: int = None


class EventRow(MDTableRow):
    EventFlags: enums.ClrEventAttr = None
    Name: str = None
    EventType: codedindex.TypeDefOrRef = None

    struct: EventRowStruct = None
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        eventtype_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        self._format = (
            "CLR_METADATA_TABLE_EVENT",
            (
                "H,EventFlags",
                str_ind_size + ",Name_StringIndex",
                eventtype_size + ",EventType_CodedIndex",
            ),
        )


class Event(ClrMetaDataTable):
    name = "Event"
    number = 20

    _row_class = EventRow


#### PropertyMap Table
#


class PropertyMapRowStruct(RowStruct):
    Parent_Index: int = None
    PropertyList_Index: int = None


class PropertyMapRow(MDTableRow):
    Parent: TypeDefRow = None
    PropertyList: List["PropertyRow"] = None

    struct: PropertyMapRowStruct
    _struct_class = PropertyMapRowStruct

    _struct_indexes = {
        "Parent_Index": ("Parent", "TypeDef"),
    }

    def _init_format(self):
        parent_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        propertylist_size = self._clr_coded_index_struct_size(0, ("Property",))
        self._format = (
            "CLR_METADATA_TABLE_PROPERTYMAP",
            (
                parent_size + ",Parent_Index",
                propertylist_size + ",PropertyList_Index",
            ),
        )


class PropertyMap(ClrMetaDataTable):
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
    Flags: int = None
    Name_StringIndex: int = None
    Type_BlobIndex: int = None


class PropertyRow(MDTableRow):
    Flags: enums.ClrPropertyAttr
    Name: str
    Type: bytes

    struct: PropertyRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_PROPERTY",
            (
                "H,Flags",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",Type_BlobIndex",
            ),
        )


class Property(ClrMetaDataTable):
    name = "Property"
    number = 23

    _row_class = PropertyRow


#### MethodSemantics Table
#


class MethodSemanticsRowStruct(RowStruct):
    Semantics: int = None
    Method_Index: int = None
    Association_CodedIndex: int = None


class MethodSemanticsRow(MDTableRow):
    Semantics: enums.ClrMethodSemanticsAttr
    Method: "MethodRow"
    Association: codedindex.HasSemantics

    struct: MethodSemanticsRowStruct
    _struct_class = MethodSemanticsRowStruct

    _struct_flags = {
        "Semantics": ("Semantics", enums.ClrMethodSemanticsAttr),
    }

    _struct_indexes = {
        "Method_Index": ("Method", "Method"),
    }
    _struct_codedindexes = {
        "Association_CodedIndex": ("Association", codedindex.HasSemantics),
    }

    def _init_format(self):
        method_size = self._clr_coded_index_struct_size(0, ("MethodDef",))
        association_size = self._clr_coded_index_struct_size(
            codedindex.HasSemantics.tag_bits,
            codedindex.HasSemantics.table_names,
        )
        self._format = (
            "CLR_METADATA_TABLE_METHODSEMANTICS",
            (
                "H,Semantics",
                method_size + ",Method_Index",
                association_size + ",Association_CodedIndex",
            ),
        )


class MethodSemantics(ClrMetaDataTable):
    name = "MethodSemantics"
    number = 24

    _row_class = MethodSemanticsRow


#### MethodImpl Table
#


class MethodImplRowStruct(RowStruct):
    Class_Index: int = None
    MethodBody_CodedIndex: int = None
    MethodDeclaration_CodedIndex: int = None


class MethodImplRow(MDTableRow):
    Class: TypeDefRow
    MethodBody: codedindex.MethodDefOrRef
    MethodDeclaration: codedindex.MethodDefOrRef

    struct: MethodImplRowStruct
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

    def _init_format(self):
        class_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        method_size = self._clr_coded_index_struct_size(
            codedindex.MethodDefOrRef.tag_bits,
            codedindex.MethodDefOrRef.table_names,
        )
        self._format = (
            "CLR_METADATA_TABLE_METHODIMPL",
            (
                class_size + ",Class_Index",
                method_size + ",MethodBody_CodedIndex",
                method_size + ",MethodDeclaration_CodedIndex",
            ),
        )


class MethodImpl(ClrMetaDataTable):
    name = "MethodImpl"
    number = 25

    _row_class = MethodImplRow


#### ModuleRef Table
#


class ModuleRefRowStruct(RowStruct):
    Name_StringIndex: int = None


class ModuleRefRow(MDTableRow):
    Name: str

    struct: ModuleRefRowStruct
    _struct_class = ModuleRefRowStruct

    _struct_strings = {
        "Name_StringIndex": "Name",
    }

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        self._format = (
            "CLR_METADATA_TABLE_MODULEREF",
            (str_ind_size + ",Name_StringIndex",),
        )


class ModuleRef(ClrMetaDataTable):
    name = "ModuleRef"
    number = 26

    _row_class = ModuleRefRow


#### TypeSpec Table
#


class TypeSpecRowStruct(RowStruct):
    Signature_BlobIndex: int = None


class TypeSpecRow(MDTableRow):
    Signature: bytes

    struct: TypeSpecRowStruct
    _struct_class = TypeSpecRowStruct

    _struct_blobs = {
        "Signature_BlobIndex": "Signature",
    }

    def _init_format(self):
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_TYPESPEC",
            (blob_ind_size + ",Signature_BlobIndex",),
        )


class TypeSpec(ClrMetaDataTable):
    name = "TypeSpec"
    number = 27

    _row_class = TypeSpecRow


#### ImplMap Table
#


class ImplMapRowStruct(RowStruct):
    MappingFlags: int = None
    MemberForwarded_CodedIndex: int = None
    ImportName_StringIndex: int = None
    ImportScope_Index: int = None


class ImplMapRow(MDTableRow):
    MappingFlags: enums.ClrPinvokeMap
    MemberForwarded: codedindex.MemberForwarded
    ImportName: str
    ImportScope: ModuleRefRow

    struct: ImplMapRowStruct
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

    def _init_format(self):
        member_size = self._clr_coded_index_struct_size(
            codedindex.MemberForwarded.tag_bits,
            codedindex.MemberForwarded.table_names,
        )
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        importscope_size = self._clr_coded_index_struct_size(0, ("ModuleRef",))
        self._format = (
            "CLR_METADATA_TABLE_IMPLMAP",
            (
                "H,MappingFlags",
                member_size + ",MemberForwarded_CodedIndex",
                str_ind_size + ",ImportName_StringIndex",
                importscope_size + ",ImportScope_Index",
            ),
        )


class ImplMap(ClrMetaDataTable):
    name = "ImplMap"
    number = 28

    _row_class = ImplMapRow


#### FieldRva Table
#


class FieldRvaRowStruct(RowStruct):
    Rva: int = None
    Field_Index: int = None


class FieldRvaRow(MDTableRow):
    Rva: int
    Field: FieldRow

    struct: FieldRvaRowStruct
    _struct_class = FieldRvaRowStruct

    _struct_asis = {
        "Rva": "Rva",
    }
    _struct_indexes = {
        "Field_Index": ("Field", "Field"),
    }

    def _init_format(self):
        field_size = self._clr_coded_index_struct_size(0, ("Field",))
        self._format = (
            "CLR_METADATA_TABLE_FIELDRVA",
            (
                "I,Rva",
                field_size + ",Field_Index",
            ),
        )


class FieldRva(ClrMetaDataTable):
    name = "FieldRva"
    number = 29

    _row_class = FieldRvaRow


class Unused30(ClrMetaDataTable):
    name = "Unused30"
    number = 30


class Unused31(ClrMetaDataTable):
    name = "Unused31"
    number = 31


#### Assembly Table
#


class AssemblyRowStruct(RowStruct):
    HashAlgId: int = None
    MajorVersion: int = None
    MinorVersion: int = None
    BuildNumber: int = None
    RevisionNumber: int = None
    Flags: int = None
    PublicKey_BlobIndex: int = None
    Name_StringIndex: int = None
    Culture_StringIndex: int = None


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

    struct: AssemblyRowStruct
    _struct_class = AssemblyRowStruct

    _struct_flags = {
        "HashAlgId": ("HashAlgId", enums.AssemblyHashAlgorithm),
        "Flags": ("Flags", enums.ClrAssemblyFlags),
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
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


class Assembly(ClrMetaDataTable):
    name = "Assembly"
    number = 32

    _row_class = AssemblyRow


#### AssemblyProcessor Table
#


class AssemblyProcessorRowStruct(RowStruct):
    Processor: int = None


class AssemblyProcessorRow(MDTableRow):
    Processor: int

    struct: AssemblyProcessorRowStruct
    _struct_class = AssemblyProcessorRowStruct

    _format = ("CLR_METADATA_TABLE_ASSEMBLYPROCESSOR", ("I,Processor",))

    _struct_asis = {
        "Processor": "Processor",
    }


class AssemblyProcessor(ClrMetaDataTable):
    name = "AssemblyProcessor"
    number = 33

    _row_class = AssemblyProcessorRow


#### AssemblyOS Table
#


class AssemblyOSRowStruct(RowStruct):
    OSPlatformID: int = None
    OSMajorVersion: int = None
    OSMinorVersion: int = None


class AssemblyOSRow(MDTableRow):
    OSPlatformID: int
    OSMajorVersion: int
    OSMinorVersion: int

    struct: AssemblyOSRowStruct
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


class AssemblyOS(ClrMetaDataTable):
    name = "AssemblyOS"
    number = 34

    _row_class = AssemblyOSRow


#### AssemblyRef Table
#


class AssemblyRefRowStruct(RowStruct):
    MajorVersion: int = None
    MinorVersion: int = None
    BuildNumber: int = None
    RevisionNumber: int = None
    Flags: int = None
    PublicKey_BlobIndex: int = None
    Name_StringIndex: int = None
    Culture_StringIndex: int = None
    HashValue_BlobIndex: int = None


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

    struct: AssemblyRefRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
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


class AssemblyRef(ClrMetaDataTable):
    name = "AssemblyRef"
    number = 35

    _row_class = AssemblyRefRow


#### AssemblyRefProcessor Table
#


class AssemblyRefProcessorRowStruct(RowStruct):
    Processor: int = None
    AssemblyRef_Index: int = None


class AssemblyRefProcessorRow(MDTableRow):
    Processor: int
    AssemblyRef: AssemblyRefRow

    struct: AssemblyRefProcessorRowStruct
    _struct_class = AssemblyRefProcessorRowStruct

    _struct_asis = {
        "Processor": "Processor",
    }
    _struct_indexes = {
        "AssemblyRef_Index": ("AssemblyRef", "AssemblyRef"),
    }

    def _init_format(self):
        assemblyref_size = self._clr_coded_index_struct_size(0, ("AssemblyRef",))
        self._format = (
            "CLR_METADATA_TABLE_ASSEMBLYREFPROCESSOR",
            (
                "I,Processor",
                assemblyref_size + ",AssemblyRef_Index",
            ),
        )


class AssemblyRefProcessor(ClrMetaDataTable):
    name = "AssemblyRefProcessor"
    number = 36

    _row_class = AssemblyRefProcessorRow


#### AssemblyRefOS Table
#


class AssemblyRefOSRowStruct(RowStruct):
    OSPlatformId: int = None
    OSMajorVersion: int = None
    OSMinorVersion: int = None
    AssemblyRef_Index: int = None


class AssemblyRefOSRow(MDTableRow):
    OSPlatformId: int
    OSMajorVersion: int
    OSMinorVersion: int
    AssemblyRef: AssemblyRefRow

    struct: AssemblyRefOSRowStruct
    _struct_class = AssemblyRefOSRowStruct

    _struct_asis = {
        "OSPlatformId": "OSPlatformId",
        "OSMajorVersion": "OSMajorVersion",
        "OSMinorVersion": "OSMinorVersion",
    }
    _struct_indexes = {
        "AssemblyRef_Index": ("AssemblyRef", "AssemblyRef"),
    }

    def _init_format(self):
        assemblyref_size = self._clr_coded_index_struct_size(0, ("AssemblyRef",))
        self._format = (
            "CLR_METADATA_TABLE_ASSEMBLYREFOS",
            (
                "I,OSPlatformId",
                "I,OSMajorVersion",
                "I,OSMinorVersion",
                assemblyref_size + ",AssemblyRef_Index",
            ),
        )


class AssemblyRefOS(ClrMetaDataTable):
    name = "AssemblyRefOS"
    number = 37

    _row_class = AssemblyRefOSRow


#### File Table
#


class FileRowStruct(RowStruct):
    Flags: int = None
    Name_StringIndex: int = None
    HashValue_BlobIndex: int = None


class FileRow(MDTableRow):
    Flags: enums.ClrFileFlags
    Name: str
    HashValue: bytes

    struct: FileRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_FILE",
            (
                "I,Flags",
                str_ind_size + ",Name_StringIndex",
                blob_ind_size + ",HashValue_BlobIndex",
            ),
        )


class File(ClrMetaDataTable):
    name = "File"
    number = 38

    _row_class = FileRow


#### ExportedType Table
#


class ExportedTypeRowStruct(RowStruct):
    Flags: int = None
    TypeDefId: int = None
    TypeName_StringIndex: int = None
    TypeNamespace_BlobIndex: int = None
    Implementation_CodedIndex: int = None


class ExportedTypeRow(MDTableRow):
    Flags: enums.ClrTypeAttr
    TypeDefId: int
    TypeName: str
    TypeNamespace: bytes
    Implementation: codedindex.Implementation

    struct: ExportedTypeRowStruct
    _struct_class = ExportedTypeRowStruct

    _struct_flags = {
        "Flags": ("Flags", enums.ClrTypeAttr),
    }
    _struct_asis = {
        "TypeDefId": "TypeDefId",
    }
    _struct_strings = {
        "TypeName_StringIndex": "TypeName",
    }
    _struct_blobs = {
        "TypeNamespace_BlobIndex": "TypeNamespace",
    }
    _struct_codedindexes = {
        "Implementation_CodedIndex": ("Implementation", codedindex.Implementation),
    }

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        implementation_size = self._clr_coded_index_struct_size(
            codedindex.Implementation.tag_bits,
            codedindex.Implementation.table_names,
        )
        self._format = (
            "CLR_METADATA_TABLE_EXPORTEDTYPE",
            (
                "I,Flags",
                "I,TypeDefId",
                str_ind_size + ",TypeName_StringIndex",
                blob_ind_size + ",TypeNamespace_BlobIndex",
                implementation_size + ",Implementation_CodedIndex",
            ),
        )


class ExportedType(ClrMetaDataTable):
    name = "ExportedType"
    number = 39

    _row_class = ExportedTypeRow


#### ManifestResource Table
#


class ManifestResourceRowStruct(RowStruct):
    Offset: int = None
    Flags: int = None
    Name_StringIndex: int = None
    Implementation_CodedIndex: int = None


class ManifestResourceRow(MDTableRow):
    Offset: int
    Flags: enums.ClrManifestResourceFlags
    Name: str
    Implementation: codedindex.Implementation

    struct: ManifestResourceRowStruct
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

    def _init_format(self):
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        implementation_size = self._clr_coded_index_struct_size(
            codedindex.Implementation.tag_bits,
            codedindex.Implementation.table_names,
        )
        self._format = (
            "CLR_METADATA_TABLE_MANIFESTRESOURCE",
            (
                "I,Offset",
                "I,Flags",
                str_ind_size + ",Name_StringIndex",
                implementation_size + ",Implementation_CodedIndex",
            ),
        )


class ManifestResource(ClrMetaDataTable):
    name = "ManifestResource"
    number = 40

    _row_class = ManifestResourceRow


#### NestedClass Table
#


class NestedClassRowStruct(RowStruct):
    NestedClass_Index: int = None
    EnclosingClass_Index: int = None


class NestedClassRow(MDTableRow):
    NestedClass: TypeDefRow
    EnclosingClass: TypeDefRow

    struct: NestedClassRowStruct
    _struct_class = NestedClassRowStruct

    _struct_indexes = {
        "NestedClass_Index": ("NestedClass", "TypeDef"),
        "EnclosingClass_Index": ("EnclosingClass", "TypeDef"),
    }

    def _init_format(self):
        class_size = self._clr_coded_index_struct_size(0, ("TypeDef",))
        self._format = (
            "CLR_METADATA_TABLE_NESTEDCLASS",
            (
                class_size + ",NestedClass_Index",
                class_size + ",EnclosingClass_Index",
            ),
        )


class NestedClass(ClrMetaDataTable):
    name = "NestedClass"
    number = 41

    _row_class = NestedClassRow


#### GenericParam Table
#


class GenericParamRowStruct(RowStruct):
    Number: int = None
    Flags: int = None
    Owner_CodedIndex: int = None
    Name_StringIndex: int = None


class GenericParamRow(MDTableRow):
    Number: int
    Flags: enums.ClrGenericParamAttr
    Owner: codedindex.TypeOrMethodDef
    Name: str

    struct: GenericParamRowStruct
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

    def _init_format(self):
        owner_size = self._clr_coded_index_struct_size(
            codedindex.TypeOrMethodDef.tag_bits,
            codedindex.TypeOrMethodDef.table_names,
        )
        str_ind_size = utils.num_bytes_to_struct_char(self._str_offsz)
        self._format = (
            "CLR_METADATA_TABLE_GENERICPARAM",
            (
                "H,Number",
                "H,Flags",
                owner_size + ",Owner_CodedIndex",
                str_ind_size + ",Name_StringIndex",
            ),
        )


class GenericParam(ClrMetaDataTable):
    name = "GenericParam"
    number = 42

    _row_class = GenericParamRow


#### GenericMethod Table
#


class GenericMethodRowStruct(RowStruct):
    Unknown1_CodedIndex: int = None
    Unknown2_BlobIndex: int = None


class GenericMethodRow(MDTableRow):
    Unknown1: codedindex.MethodDefOrRef
    Unknown2: bytes

    struct: GenericMethodRowStruct
    _struct_class = GenericMethodRowStruct

    _struct_codedindexes = {
        "Unknown1_CodedIndex": ("Unknown1", codedindex.MethodDefOrRef),
    }
    _struct_blobs = {
        "Unknown2_BlobIndex": "Unknown2",
    }

    def _init_format(self):
        unknown1_size = self._clr_coded_index_struct_size(
            codedindex.MethodDefOrRef.tag_bits,
            codedindex.MethodDefOrRef.table_names,
        )
        blob_ind_size = utils.num_bytes_to_struct_char(self._blob_offsz)
        self._format = (
            "CLR_METADATA_TABLE_GENERICMETHOD",
            (
                unknown1_size + ",Unknown1_CodedIndex",
                blob_ind_size + ",Unknown2_BlobIndex",
            ),
        )


class GenericMethod(ClrMetaDataTable):
    name = "GenericMethod"
    number = 43

    _row_class = GenericMethodRow


#### GenericParamConstraint Table
#


class GenericParamConstraintRowStruct(RowStruct):
    Owner_Index: int = None
    Constraint_CodedIndex: int = None


class GenericParamConstraintRow(MDTableRow):
    Owner: GenericParamRow
    Constraint: codedindex.TypeDefOrRef

    struct: GenericParamConstraintRowStruct
    _struct_class = GenericParamConstraintRowStruct

    _struct_indexes = {
        "Owner_Index": ("Owner", "GenericParam"),
    }
    _struct_codedindexes = {
        "Constraint_CodedIndex": ("Constraint", codedindex.TypeDefOrRef),
    }

    def _init_format(self):
        owner_size = self._clr_coded_index_struct_size(0, ("GenericParam",))
        constraint_size = self._clr_coded_index_struct_size(
            codedindex.TypeDefOrRef.tag_bits,
            codedindex.TypeDefOrRef.table_names,
        )
        self._format = (
            "CLR_METADATA_TABLE_GENERICPARAMCONSTRAINT",
            (
                owner_size + ",Owner_Index",
                constraint_size + ",Constraint_CodedIndex",
            ),
        )


class GenericParamConstraint(ClrMetaDataTable):
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


class MaxTable(ClrMetaDataTable):
    name = "MaxTable"
    number = 63

    # TODO


class ClrMetaDataTableFactory(object):
    _table_number_map = {
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
        30: Unused30,
        31: Unused31,
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
        43: GenericMethod,
        44: GenericParamConstraint,
        # 45 through 63 are not used
        63: MaxTable,
    }

    @classmethod
    def createTable(
        cls,
        number: int,
        tables_rowcounts: List[int],
        is_sorted: bool,
        strings_offset_size: int,
        guid_offset_size: int,
        blob_offset_size: int,
        strings_heap: ClrHeap,
        guid_heap: ClrHeap,
        blob_heap: ClrHeap,
    ) -> ClrMetaDataTable:
        if number in cls._table_number_map:
            table = cls._table_number_map[number](
                tables_rowcounts,
                is_sorted,
                strings_offset_size,
                guid_offset_size,
                blob_offset_size,
                strings_heap,
                guid_heap,
                blob_heap,
            )
            return table
        else:
            return None
