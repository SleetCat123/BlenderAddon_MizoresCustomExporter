import bpy
from bpy.props import EnumProperty

from . import resolver, storage


def _get_active_export_set(context):
    props = context.scene.mizore_export_sets
    if not props.export_sets:
        return None
    return props.export_sets[min(props.active_export_set_index, len(props.export_sets) - 1)]


def _get_active_entry(context):
    export_set = _get_active_export_set(context)
    if export_set is None:
        return None, None
    entry = storage.get_active_override_entry(export_set)
    return export_set, entry


class SCENE_OT_mizore_shapekey_override_sync_targets(bpy.types.Operator):
    bl_idname = "scene.mizore_shapekey_override_sync_targets"
    bl_label = "Sync Override Targets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _get_active_export_set(context) is not None

    def execute(self, context):
        export_set = _get_active_export_set(context)
        if export_set is None:
            return {'CANCELLED'}

        storage.sync_override_entries(export_set)
        entry = storage.get_active_override_entry(export_set, sync=False)
        if entry is not None and entry.override_enabled:
            resolver.sync_override_entry(entry, context)
        return {'FINISHED'}


class SCENE_OT_mizore_shapekey_override_refresh_entry(bpy.types.Operator):
    bl_idname = "scene.mizore_shapekey_override_refresh_entry"
    bl_label = "Refresh Shape Key Override"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        _export_set, entry = _get_active_entry(context)
        return entry is not None and entry.override_enabled and entry.target_object is not None

    def execute(self, context):
        export_set, entry = _get_active_entry(context)
        if export_set is None or entry is None or entry.target_object is None:
            return {'CANCELLED'}

        resolver.sync_override_entry(entry, context)
        return {'FINISHED'}


class SCENE_OT_mizore_shapekey_override_move_row(bpy.types.Operator):
    bl_idname = "scene.mizore_shapekey_override_move_row"
    bl_label = "Move Shape Key Override Row"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("TOP", "Top", ""),
            ("BOTTOM", "Bottom", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        _export_set, entry = _get_active_entry(context)
        return entry is not None and entry.override_enabled and len(entry.rows) > 1

    def execute(self, context):
        export_set, entry = _get_active_entry(context)
        if export_set is None or entry is None:
            return {'CANCELLED'}

        index = entry.active_row_index
        if index < 0 or index >= len(entry.rows):
            return {'CANCELLED'}
        if entry.rows[index].is_basis:
            return {'CANCELLED'}

        max_index = len(entry.rows) - 1
        if self.direction == "UP":
            target_index = max(1, index - 1)
        elif self.direction == "DOWN":
            target_index = min(max_index, index + 1)
        elif self.direction == "TOP":
            target_index = 1
        else:
            target_index = max_index

        entry.rows.move(index, target_index)
        entry.active_row_index = target_index
        resolver.sync_override_entry(entry, context)
        return {'FINISHED'}


class SCENE_OT_mizore_shapekey_override_sort_rows(bpy.types.Operator):
    bl_idname = "scene.mizore_shapekey_override_sort_rows"
    bl_label = "Sort Shape Key Override Rows"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        _export_set, entry = _get_active_entry(context)
        return entry is not None and entry.override_enabled and len(entry.rows) > 1

    def execute(self, context):
        export_set, entry = _get_active_entry(context)
        if export_set is None or entry is None:
            return {'CANCELLED'}

        rows = list(entry.rows)
        basis = [row for row in rows if row.is_basis]
        resolved = [row for row in rows if not row.is_basis and row.is_resolved]
        unresolved = [row for row in rows if not row.is_basis and not row.is_resolved]
        resolved.sort(key=lambda row: row.final_name.lower())
        ordered_entries = [
            {
                "final_name": row.final_name,
                "match_tokens": [
                    token
                    for token in str(getattr(row, "match_tokens_serialized", "") or "").splitlines()
                    if token
                ],
            }
            for row in [*basis, *resolved, *unresolved]
            if row.final_name
        ]
        resolved_rows = resolver.build_resolved_rows(entry.target_object, ordered_entries, context)
        storage.set_entry_rows(entry, resolver.format_rows_for_entry(resolved_rows))
        return {'FINISHED'}


class SCENE_OT_mizore_shapekey_override_reset_to_base(bpy.types.Operator):
    bl_idname = "scene.mizore_shapekey_override_reset_to_base"
    bl_label = "Reset Override To Base"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        _export_set, entry = _get_active_entry(context)
        return entry is not None and entry.target_object is not None

    def execute(self, context):
        export_set, entry = _get_active_entry(context)
        if export_set is None or entry is None or entry.target_object is None:
            return {'CANCELLED'}

        candidate_rows = resolver.build_candidate_rows(entry.target_object, context)
        candidate_names = [row.final_name for row in candidate_rows]
        base_ordered_names = resolver.get_base_ordered_names(
            entry.target_object,
            candidate_names=candidate_names,
            candidate_rows=candidate_rows,
        )
        resolved_rows = resolver.build_resolved_rows(entry.target_object, base_ordered_names, context)
        storage.set_entry_rows(entry, resolver.format_rows_for_entry(resolved_rows))
        entry.override_enabled = True
        return {'FINISHED'}


class SCENE_OT_mizore_shapekey_override_cleanup_saved_only(bpy.types.Operator):
    bl_idname = "scene.mizore_shapekey_override_cleanup_saved_only"
    bl_label = "Cleanup Saved Only"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        _export_set, entry = _get_active_entry(context)
        return (
            entry is not None
            and entry.override_enabled
            and any(not row.is_basis and not row.is_resolved for row in entry.rows)
        )

    def execute(self, context):
        export_set, entry = _get_active_entry(context)
        if export_set is None or entry is None:
            return {'CANCELLED'}

        kept_entries = [
            {
                "final_name": row.final_name,
                "match_tokens": [
                    token
                    for token in str(getattr(row, "match_tokens_serialized", "") or "").splitlines()
                    if token
                ],
            }
            for row in entry.rows
            if row.final_name and (row.is_basis or row.is_resolved)
        ]
        resolved_rows = resolver.build_resolved_rows(entry.target_object, kept_entries, context)
        storage.set_entry_rows(entry, resolver.format_rows_for_entry(resolved_rows))
        return {'FINISHED'}


classes = [
    SCENE_OT_mizore_shapekey_override_sync_targets,
    SCENE_OT_mizore_shapekey_override_refresh_entry,
    SCENE_OT_mizore_shapekey_override_move_row,
    SCENE_OT_mizore_shapekey_override_sort_rows,
    SCENE_OT_mizore_shapekey_override_reset_to_base,
    SCENE_OT_mizore_shapekey_override_cleanup_saved_only,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
