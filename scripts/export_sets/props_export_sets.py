import bpy
import os
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .shapekey_order_override import props as shapekey_order_override_props

_EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED = 0
_LEGACY_PRIMARY_ARMATURE_KEY = "is_primary_armature"


def suspend_export_set_item_target_sync():
    global _EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED
    _EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED += 1


def resume_export_set_item_target_sync():
    global _EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED
    _EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED = max(0, _EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED - 1)


def _find_export_set_for_item(item, context):
    scene = getattr(context, "scene", None) or getattr(item, "id_data", None)
    props = getattr(scene, "mizore_export_sets", None)
    if props is None:
        return None

    target_pointer = item.as_pointer()
    for export_set in props.export_sets:
        for candidate in export_set.items:
            if candidate.as_pointer() == target_pointer:
                return export_set
    return None


def update_export_set_item_targets(self, context):
    if _EXPORT_SET_ITEM_TARGET_SYNC_SUPPRESSED > 0:
        return
    if context is None:
        return
    if getattr(context, "window", None) is None:
        return

    export_set = _find_export_set_for_item(self, context)
    if export_set is None:
        return

    from .shapekey_order_override import storage as shapekey_override_storage

    shapekey_override_storage.sync_override_entries(export_set)

def poll_any_object(_self, obj):
    return obj is not None


def poll_armature_object(_self, obj):
    return obj is not None and obj.type == 'ARMATURE'


def get_export_set_raw_filename(export_set) -> str:
    filename = export_set.filename.strip()
    if filename:
        return filename
    return export_set.name.strip()


def get_export_set_display_name(export_set) -> str:
    filename = get_export_set_raw_filename(export_set)
    if not filename:
        return "ExportSet"
    stem, _ext = os.path.splitext(filename)
    return stem or filename


def update_export_set_filename(self, _context):
    self.name = get_export_set_display_name(self)


def _resolve_legacy_primary_target(item):
    armature_object = getattr(item, "armature_object", None)
    if armature_object is not None and getattr(armature_object, "type", None) == 'ARMATURE':
        return armature_object

    root_object = getattr(item, "root_object", None)
    if root_object is not None and getattr(root_object, "type", None) == 'ARMATURE':
        return root_object

    return None


def migrate_legacy_export_set_data(scene):
    props = getattr(scene, "mizore_export_sets", None)
    if props is None:
        return

    for export_set in getattr(props, "export_sets", []):
        migrated_target = None
        if getattr(export_set, "target_armature", None) is not None:
            migrated_target = export_set.target_armature

        for item in getattr(export_set, "items", []):
            legacy_primary = bool(item.get(_LEGACY_PRIMARY_ARMATURE_KEY, False))
            if migrated_target is None and legacy_primary:
                migrated_target = _resolve_legacy_primary_target(item)
            if _LEGACY_PRIMARY_ARMATURE_KEY in item.keys():
                del item[_LEGACY_PRIMARY_ARMATURE_KEY]

        if migrated_target is not None and getattr(export_set, "target_armature", None) is None:
            export_set.target_armature = migrated_target


def migrate_all_scenes_legacy_export_set_data():
    scenes = getattr(bpy.data, "scenes", None)
    if scenes is None:
        return
    for scene in scenes:
        migrate_legacy_export_set_data(scene)


@persistent
def _migrate_legacy_export_set_data_on_load(_dummy):
    migrate_all_scenes_legacy_export_set_data()


class MIZORE_ExportSetItem(bpy.types.PropertyGroup):
    enabled: BoolProperty(name="Enabled", default=True, update=update_export_set_item_targets)
    include_children: BoolProperty(name="Include Children", default=True, update=update_export_set_item_targets)
    root_object: PointerProperty(
        name="Root Object",
        type=bpy.types.Object,
        poll=poll_any_object,
        update=update_export_set_item_targets,
    )
    armature_object: PointerProperty(
        name="Armature",
        type=bpy.types.Object,
        poll=poll_armature_object,
        description="Armature that belongs to this root and will be merged when Merge Armatures is enabled; if empty, it is inferred from the root object's armature modifier or parent armature when possible",
    )
    attach_to_bone: StringProperty(
        name="Attach To Bone",
        default="",
        description="Bone name on the primary armature where this armature should be attached; leave empty to infer from the current bone parent",
    )


class MIZORE_ExportSetVertexColorReplaceRule(bpy.types.PropertyGroup):
    enabled: BoolProperty(name="Enabled", default=True)
    layer_name: StringProperty(
        name="Layer",
        default="",
        description="Vertex color layer to replace; leave empty to apply to all color layers",
    )
    source_color: FloatVectorProperty(
        name="From",
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR',
        description="Replace this vertex color",
    )
    target_color: FloatVectorProperty(
        name="To",
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR',
        description="Use this vertex color instead",
    )
    tolerance: FloatProperty(
        name="Tolerance",
        default=0.001,
        min=0.0,
        max=1.0,
        description="Allowed per-channel difference when matching source vertex colors",
    )


class MIZORE_ExportSetObjectReplaceRule(bpy.types.PropertyGroup):
    enabled: BoolProperty(name="Enabled", default=True)
    source_object: PointerProperty(
        name="Source Object",
        type=bpy.types.Object,
        poll=poll_any_object,
    )
    replacement_object: PointerProperty(
        name="Replacement Object",
        type=bpy.types.Object,
        poll=poll_any_object,
    )
    include_children: BoolProperty(
        name="Include Children",
        default=True,
        description="Replace the source object subtree instead of only the source object itself",
    )


class MIZORE_ExportSet(bpy.types.PropertyGroup):
    enabled: BoolProperty(name="Enabled", default=True)
    name: StringProperty(name="Name", default="New Export Set")
    filename: StringProperty(name="Name", default="New Export Set", update=update_export_set_filename)
    join_meshes_to_one: BoolProperty(name="Join Meshes To One", default=False)
    merge_armatures: BoolProperty(
        name="Merge Into One Armature",
        default=False,
        description="Merge armatures from enabled items into one armature before export",
    )
    target_armature: PointerProperty(
        name="Target Armature",
        type=bpy.types.Object,
        poll=poll_armature_object,
        description="Armature that receives the other armatures when Merge Into One Armature is enabled",
    )
    vertex_color_replace_rules: CollectionProperty(type=MIZORE_ExportSetVertexColorReplaceRule)
    active_vertex_color_replace_rule_index: IntProperty(
        name="Active Vertex Color Replace Rule Index",
        default=0,
    )
    object_replace_rules: CollectionProperty(type=MIZORE_ExportSetObjectReplaceRule)
    active_object_replace_rule_index: IntProperty(
        name="Active Object Replace Rule Index",
        default=0,
    )
    shapekey_reorder_overrides: CollectionProperty(
        type=shapekey_order_override_props.MIZORE_ExportSetShapeKeyReorderOverride
    )
    active_shapekey_reorder_override_index: IntProperty(
        name="Active ShapeKey Reorder Override Index",
        default=0,
    )
    items: CollectionProperty(type=MIZORE_ExportSetItem)
    active_item_index: IntProperty(name="Active Item Index", default=0)


class MIZORE_ExportSetsSceneProps(bpy.types.PropertyGroup):
    export_sets: CollectionProperty(type=MIZORE_ExportSet)
    active_export_set_index: IntProperty(name="Active Export Set Index", default=0)


classes = [
    MIZORE_ExportSetItem,
    MIZORE_ExportSetVertexColorReplaceRule,
    MIZORE_ExportSetObjectReplaceRule,
    MIZORE_ExportSet,
    MIZORE_ExportSetsSceneProps,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mizore_export_sets = PointerProperty(type=MIZORE_ExportSetsSceneProps)
    migrate_all_scenes_legacy_export_set_data()
    if _migrate_legacy_export_set_data_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_migrate_legacy_export_set_data_on_load)


def unregister():
    if _migrate_legacy_export_set_data_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_migrate_legacy_export_set_data_on_load)
    del bpy.types.Scene.mizore_export_sets
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
