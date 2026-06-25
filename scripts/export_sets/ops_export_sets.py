import os

import bpy
from bpy.props import EnumProperty

from .props_export_sets import (
    get_export_set_display_name,
    get_export_set_raw_filename,
    resume_export_set_item_target_sync,
    suspend_export_set_item_target_sync,
)
from .shapekey_order_override import storage as shapekey_override_storage


def _ensure_unique_name(collection, base_name: str) -> str:
    existing = {get_export_set_display_name(item) for item in collection}
    if base_name not in existing:
        return base_name

    index = 2
    while True:
        candidate = f"{base_name} {index}"
        if candidate not in existing:
            return candidate
        index += 1


def _build_duplicate_filename(collection, source_set) -> str:
    raw_filename = get_export_set_raw_filename(source_set) or "New Export Set"
    stem, ext = os.path.splitext(raw_filename)
    if not stem:
        stem = raw_filename
        ext = ""

    unique_stem = _ensure_unique_name(collection, stem)
    return unique_stem + ext


def _copy_export_set_item(target_item, source_item):
    target_item.enabled = source_item.enabled
    target_item.include_children = source_item.include_children
    target_item.root_object = source_item.root_object
    target_item.armature_object = source_item.armature_object
    target_item.attach_to_bone = source_item.attach_to_bone
    for source_rule in source_item.uv_transform_rules:
        target_rule = target_item.uv_transform_rules.add()
        _copy_export_set_uv_transform_rule(target_rule, source_rule)
    target_item.active_uv_transform_rule_index = source_item.active_uv_transform_rule_index


def _copy_export_set_vertex_color_replace_rule(target_rule, source_rule):
    target_rule.enabled = source_rule.enabled
    target_rule.layer_name = source_rule.layer_name
    target_rule.source_color = source_rule.source_color
    target_rule.target_color = source_rule.target_color
    target_rule.tolerance = source_rule.tolerance


def _copy_export_set_object_replace_rule(target_rule, source_rule):
    target_rule.enabled = source_rule.enabled
    target_rule.source_object = source_rule.source_object
    target_rule.replacement_object = source_rule.replacement_object
    target_rule.include_children = source_rule.include_children


def _copy_export_set_uv_transform_rule(target_rule, source_rule):
    target_rule.enabled = source_rule.enabled
    target_rule.uv_layer_name = source_rule.uv_layer_name
    target_rule.offset = source_rule.offset
    target_rule.scale = source_rule.scale
    target_rule.pivot = source_rule.pivot


def _copy_export_set(target_set, source_set, collection):
    suspend_export_set_item_target_sync()
    try:
        target_set.enabled = source_set.enabled
        target_set.filename = _build_duplicate_filename(collection, source_set)
        target_set.join_meshes_to_one = source_set.join_meshes_to_one
        target_set.merge_armatures = source_set.merge_armatures
        target_set.target_armature = source_set.target_armature
        for source_rule in source_set.object_replace_rules:
            target_rule = target_set.object_replace_rules.add()
            _copy_export_set_object_replace_rule(target_rule, source_rule)
        target_set.active_object_replace_rule_index = source_set.active_object_replace_rule_index
        for source_rule in source_set.vertex_color_replace_rules:
            target_rule = target_set.vertex_color_replace_rules.add()
            _copy_export_set_vertex_color_replace_rule(target_rule, source_rule)
        target_set.active_vertex_color_replace_rule_index = source_set.active_vertex_color_replace_rule_index
        for source_override in source_set.shapekey_reorder_overrides:
            target_override = target_set.shapekey_reorder_overrides.add()
            target_override.target_object = source_override.target_object
            target_override.override_enabled = source_override.override_enabled
            for source_row in source_override.rows:
                target_row = target_override.rows.add()
                target_row.final_name = source_row.final_name
                target_row.kinds_label = source_row.kinds_label
                target_row.source_objects_label = source_row.source_objects_label
                target_row.source_detail_label = source_row.source_detail_label
                target_row.match_tokens_serialized = source_row.match_tokens_serialized
                target_row.state_label = source_row.state_label
                target_row.is_basis = source_row.is_basis
                target_row.is_resolved = source_row.is_resolved
            target_override.active_row_index = source_override.active_row_index
        target_set.active_shapekey_reorder_override_index = source_set.active_shapekey_reorder_override_index

        for source_item in source_set.items:
            target_item = target_set.items.add()
            _copy_export_set_item(target_item, source_item)

        target_set.active_item_index = source_set.active_item_index
    finally:
        resume_export_set_item_target_sync()

    shapekey_override_storage.sync_override_entries(target_set)


def _move_index(collection, index, direction):
    if direction == 'UP':
        if index <= 0:
            return index
        new_index = index - 1
    else:
        if index >= len(collection) - 1:
            return index
        new_index = index + 1

    collection.move(index, new_index)
    return new_index


class SCENE_OT_mizore_add_export_set(bpy.types.Operator):
    bl_idname = "scene.mizore_add_export_set"
    bl_label = "Add Export Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mizore_export_sets
        new_set = props.export_sets.add()
        new_set.filename = _ensure_unique_name(props.export_sets, "New Export Set")
        props.active_export_set_index = len(props.export_sets) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_remove_export_set(bpy.types.Operator):
    bl_idname = "scene.mizore_remove_export_set"
    bl_label = "Remove Export Set"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mizore_export_sets.export_sets) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        index = props.active_export_set_index
        export_set = props.export_sets[index]
        shapekey_override_storage.ensure_override_entries(export_set)
        props.export_sets.remove(index)
        props.active_export_set_index = max(0, min(index, len(props.export_sets) - 1))
        return {'FINISHED'}


class SCENE_OT_mizore_duplicate_export_set(bpy.types.Operator):
    bl_idname = "scene.mizore_duplicate_export_set"
    bl_label = "Duplicate Export Set"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mizore_export_sets.export_sets) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        source_set = props.export_sets[props.active_export_set_index]
        new_set = props.export_sets.add()
        _copy_export_set(new_set, source_set, props.export_sets)
        props.active_export_set_index = len(props.export_sets) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_move_export_set(bpy.types.Operator):
    bl_idname = "scene.mizore_move_export_set"
    bl_label = "Move Export Set"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        return len(context.scene.mizore_export_sets.export_sets) > 1

    def execute(self, context):
        props = context.scene.mizore_export_sets
        props.active_export_set_index = _move_index(
            props.export_sets,
            props.active_export_set_index,
            self.direction,
        )
        return {'FINISHED'}


class SCENE_OT_mizore_add_export_set_item(bpy.types.Operator):
    bl_idname = "scene.mizore_add_export_set_item"
    bl_label = "Add Export Set Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mizore_export_sets.export_sets) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        export_set.items.add()
        export_set.active_item_index = len(export_set.items) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_remove_export_set_item(bpy.types.Operator):
    bl_idname = "scene.mizore_remove_export_set_item"
    bl_label = "Remove Export Set Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.items) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        index = export_set.active_item_index
        export_set.items.remove(index)
        export_set.active_item_index = max(0, min(index, len(export_set.items) - 1))
        shapekey_override_storage.sync_override_entries(export_set)
        return {'FINISHED'}


class SCENE_OT_mizore_duplicate_export_set_item(bpy.types.Operator):
    bl_idname = "scene.mizore_duplicate_export_set_item"
    bl_label = "Duplicate Export Set Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.items) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        source_item = export_set.items[export_set.active_item_index]
        new_item = export_set.items.add()
        _copy_export_set_item(new_item, source_item)
        export_set.active_item_index = len(export_set.items) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_move_export_set_item(bpy.types.Operator):
    bl_idname = "scene.mizore_move_export_set_item"
    bl_label = "Move Export Set Item"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.items) > 1

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        export_set.active_item_index = _move_index(
            export_set.items,
            export_set.active_item_index,
            self.direction,
        )
        return {'FINISHED'}


class SCENE_OT_mizore_add_export_set_vcol_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_add_export_set_vcol_replace_rule"
    bl_label = "Add Vertex Color Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mizore_export_sets.export_sets) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        export_set.vertex_color_replace_rules.add()
        export_set.active_vertex_color_replace_rule_index = len(export_set.vertex_color_replace_rules) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_add_export_set_object_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_add_export_set_object_replace_rule"
    bl_label = "Add Object Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mizore_export_sets.export_sets) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        rule = export_set.object_replace_rules.add()
        if context.object is not None:
            rule.source_object = context.object
        export_set.active_object_replace_rule_index = len(export_set.object_replace_rules) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_remove_export_set_object_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_remove_export_set_object_replace_rule"
    bl_label = "Remove Object Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.object_replace_rules) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        index = export_set.active_object_replace_rule_index
        export_set.object_replace_rules.remove(index)
        export_set.active_object_replace_rule_index = max(
            0,
            min(index, len(export_set.object_replace_rules) - 1),
        )
        return {'FINISHED'}


class SCENE_OT_mizore_duplicate_export_set_object_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_duplicate_export_set_object_replace_rule"
    bl_label = "Duplicate Object Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.object_replace_rules) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        source_rule = export_set.object_replace_rules[export_set.active_object_replace_rule_index]
        new_rule = export_set.object_replace_rules.add()
        _copy_export_set_object_replace_rule(new_rule, source_rule)
        export_set.active_object_replace_rule_index = len(export_set.object_replace_rules) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_move_export_set_object_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_move_export_set_object_replace_rule"
    bl_label = "Move Object Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.object_replace_rules) > 1

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        export_set.active_object_replace_rule_index = _move_index(
            export_set.object_replace_rules,
            export_set.active_object_replace_rule_index,
            self.direction,
        )
        return {'FINISHED'}


class SCENE_OT_mizore_remove_export_set_vcol_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_remove_export_set_vcol_replace_rule"
    bl_label = "Remove Vertex Color Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.vertex_color_replace_rules) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        index = export_set.active_vertex_color_replace_rule_index
        export_set.vertex_color_replace_rules.remove(index)
        export_set.active_vertex_color_replace_rule_index = max(
            0,
            min(index, len(export_set.vertex_color_replace_rules) - 1),
        )
        return {'FINISHED'}


class SCENE_OT_mizore_duplicate_export_set_vcol_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_duplicate_export_set_vcol_replace_rule"
    bl_label = "Duplicate Vertex Color Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.vertex_color_replace_rules) > 0

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        source_rule = export_set.vertex_color_replace_rules[export_set.active_vertex_color_replace_rule_index]
        new_rule = export_set.vertex_color_replace_rules.add()
        _copy_export_set_vertex_color_replace_rule(new_rule, source_rule)
        export_set.active_vertex_color_replace_rule_index = len(export_set.vertex_color_replace_rules) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_move_export_set_vcol_replace_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_move_export_set_vcol_replace_rule"
    bl_label = "Move Vertex Color Replace Rule"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.mizore_export_sets
        if len(props.export_sets) == 0:
            return False
        export_set = props.export_sets[props.active_export_set_index]
        return len(export_set.vertex_color_replace_rules) > 1

    def execute(self, context):
        props = context.scene.mizore_export_sets
        export_set = props.export_sets[props.active_export_set_index]
        export_set.active_vertex_color_replace_rule_index = _move_index(
            export_set.vertex_color_replace_rules,
            export_set.active_vertex_color_replace_rule_index,
            self.direction,
        )
        return {'FINISHED'}


def _get_active_export_set_item(context):
    props = context.scene.mizore_export_sets
    if len(props.export_sets) == 0:
        return None
    export_set = props.export_sets[props.active_export_set_index]
    if len(export_set.items) == 0:
        return None
    return export_set.items[export_set.active_item_index]


class SCENE_OT_mizore_add_export_set_uv_transform_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_add_export_set_uv_transform_rule"
    bl_label = "Add UV Transform Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _get_active_export_set_item(context) is not None

    def execute(self, context):
        item = _get_active_export_set_item(context)
        item.uv_transform_rules.add()
        item.active_uv_transform_rule_index = len(item.uv_transform_rules) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_remove_export_set_uv_transform_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_remove_export_set_uv_transform_rule"
    bl_label = "Remove UV Transform Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        item = _get_active_export_set_item(context)
        return item is not None and len(item.uv_transform_rules) > 0

    def execute(self, context):
        item = _get_active_export_set_item(context)
        index = item.active_uv_transform_rule_index
        item.uv_transform_rules.remove(index)
        item.active_uv_transform_rule_index = max(
            0,
            min(index, len(item.uv_transform_rules) - 1),
        )
        return {'FINISHED'}


class SCENE_OT_mizore_duplicate_export_set_uv_transform_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_duplicate_export_set_uv_transform_rule"
    bl_label = "Duplicate UV Transform Rule"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        item = _get_active_export_set_item(context)
        return item is not None and len(item.uv_transform_rules) > 0

    def execute(self, context):
        item = _get_active_export_set_item(context)
        source_rule = item.uv_transform_rules[item.active_uv_transform_rule_index]
        new_rule = item.uv_transform_rules.add()
        _copy_export_set_uv_transform_rule(new_rule, source_rule)
        item.active_uv_transform_rule_index = len(item.uv_transform_rules) - 1
        return {'FINISHED'}


class SCENE_OT_mizore_move_export_set_uv_transform_rule(bpy.types.Operator):
    bl_idname = "scene.mizore_move_export_set_uv_transform_rule"
    bl_label = "Move UV Transform Rule"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        item = _get_active_export_set_item(context)
        return item is not None and len(item.uv_transform_rules) > 1

    def execute(self, context):
        item = _get_active_export_set_item(context)
        item.active_uv_transform_rule_index = _move_index(
            item.uv_transform_rules,
            item.active_uv_transform_rule_index,
            self.direction,
        )
        return {'FINISHED'}


classes = [
    SCENE_OT_mizore_add_export_set,
    SCENE_OT_mizore_remove_export_set,
    SCENE_OT_mizore_duplicate_export_set,
    SCENE_OT_mizore_move_export_set,
    SCENE_OT_mizore_add_export_set_item,
    SCENE_OT_mizore_remove_export_set_item,
    SCENE_OT_mizore_duplicate_export_set_item,
    SCENE_OT_mizore_move_export_set_item,
    SCENE_OT_mizore_add_export_set_object_replace_rule,
    SCENE_OT_mizore_remove_export_set_object_replace_rule,
    SCENE_OT_mizore_duplicate_export_set_object_replace_rule,
    SCENE_OT_mizore_move_export_set_object_replace_rule,
    SCENE_OT_mizore_add_export_set_vcol_replace_rule,
    SCENE_OT_mizore_remove_export_set_vcol_replace_rule,
    SCENE_OT_mizore_duplicate_export_set_vcol_replace_rule,
    SCENE_OT_mizore_move_export_set_vcol_replace_rule,
    SCENE_OT_mizore_add_export_set_uv_transform_rule,
    SCENE_OT_mizore_remove_export_set_uv_transform_rule,
    SCENE_OT_mizore_duplicate_export_set_uv_transform_rule,
    SCENE_OT_mizore_move_export_set_uv_transform_rule,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
