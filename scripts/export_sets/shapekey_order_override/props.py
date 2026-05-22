import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, PointerProperty, StringProperty


def poll_mesh_object(_self, obj):
    return obj is not None and obj.type == 'MESH'


def update_override_enabled(self, context):
    if not self.override_enabled or self.target_object is None:
        return

    from . import resolver

    resolver.sync_override_entry(self, context)


class MIZORE_ExportSetShapeKeyOrderRow(bpy.types.PropertyGroup):
    final_name: StringProperty(name="Final Name", default="")
    kinds_label: StringProperty(name="Kinds", default="")
    source_objects_label: StringProperty(name="Source Objects", default="")
    source_detail_label: StringProperty(name="Source Detail", default="")
    match_tokens_serialized: StringProperty(name="Match Tokens Raw", default="")
    state_label: StringProperty(name="State", default="")
    is_basis: BoolProperty(name="Is Basis", default=False)
    is_resolved: BoolProperty(name="Is Resolved", default=True)


class MIZORE_ExportSetShapeKeyReorderOverride(bpy.types.PropertyGroup):
    target_object: PointerProperty(name="Target Object", type=bpy.types.Object, poll=poll_mesh_object)
    override_enabled: BoolProperty(name="Use Override", default=False, update=update_override_enabled)
    rows: CollectionProperty(type=MIZORE_ExportSetShapeKeyOrderRow)
    active_row_index: IntProperty(name="Active Row Index", default=0)


classes = [
    MIZORE_ExportSetShapeKeyOrderRow,
    MIZORE_ExportSetShapeKeyReorderOverride,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
