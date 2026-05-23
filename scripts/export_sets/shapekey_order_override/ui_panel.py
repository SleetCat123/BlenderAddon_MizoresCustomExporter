import bpy

from . import resolver, storage, ui_operators


class MIZORE_UL_export_set_shapekey_override_targets(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "override_enabled", text="")
        name = item.target_object.name if item.target_object else "(Missing)"
        row.label(text=name, icon='MESH_DATA', translate=False)


class MIZORE_UL_export_set_shapekey_override_rows(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        icon = 'SHAPEKEY_DATA'
        if item.is_basis:
            icon = 'KEYTYPE_KEYFRAME_VEC'
        elif not item.is_resolved:
            icon = 'ERROR'
        row.label(text=item.final_name or "(Empty)", icon=icon)
        if item.kinds_label:
            row.label(text=item.kinds_label)


def _draw_readonly_rows(layout, rows):
    for row in rows:
        line = layout.row(align=True)
        icon = 'SHAPEKEY_DATA'
        if getattr(row, "is_basis", False):
            icon = 'KEYTYPE_KEYFRAME_VEC'
        elif not getattr(row, "is_resolved", True):
            icon = 'ERROR'
        line.label(text=row.final_name or "(Empty)", icon=icon)
        if getattr(row, "kinds_label", ""):
            line.label(text=row.kinds_label)


def _draw_selected_row_detail(layout, item):
    box = layout.box()
    box.label(text="Selected Row", icon='INFO')
    col = box.column(align=True)
    col.label(text=f"Final Name: {item.final_name or '(Empty)'}", translate=False)
    col.label(text=f"Kind: {item.kinds_label or '-'}")
    col.label(text=f"Source Object: {item.source_objects_label or '-'}", translate=False)
    col.label(text=f"Source Detail: {item.source_detail_label or '-'}", translate=False)
    col.label(text=f"State: {item.state_label or '-'}")


def draw_shapekey_reorder_override(layout, context, export_set):
    box = layout.box()
    box.label(text="ShapeKey Reorder Override", icon='SHAPEKEY_DATA')

    target_objects = storage.get_mesh_targets(export_set)
    if not target_objects:
        box.label(text="No mesh targets in this export set.", icon='INFO')
        return

    if storage.needs_override_sync(export_set, target_objects=target_objects):
        warning_box = box.box()
        warning_box.label(text="Target mesh list changed. Sync before editing.", icon='INFO')
        warning_box.operator(
            ui_operators.SCENE_OT_mizore_shapekey_override_sync_targets.bl_idname,
            text="Sync Override Targets",
            icon='FILE_REFRESH',
        )
        return

    row = box.row()
    row.template_list(
        "MIZORE_UL_export_set_shapekey_override_targets",
        "",
        export_set,
        "shapekey_reorder_overrides",
        export_set,
        "active_shapekey_reorder_override_index",
        rows=4,
    )

    entry = storage.get_active_override_entry(export_set, sync=False)
    if entry is None or entry.target_object is None:
        box.label(text="No target mesh selected.", icon='INFO')
        return

    settings_col = box.column(align=True)
    settings_col.label(text=f"Target: {entry.target_object.name}", translate=False)
    settings_col.prop(entry, "override_enabled")

    if entry.override_enabled:
        if resolver.needs_entry_sync(entry, context):
            refresh_box = box.box()
            refresh_box.label(text="Shape key list changed. Refresh this override.", icon='INFO')
            refresh_box.operator(
                ui_operators.SCENE_OT_mizore_shapekey_override_refresh_entry.bl_idname,
                text="Refresh Shape Key Override",
                icon='FILE_REFRESH',
            )

        split = box.split(factor=0.78)
        split.template_list(
            "MIZORE_UL_export_set_shapekey_override_rows",
            "",
            entry,
            "rows",
            entry,
            "active_row_index",
            rows=6,
        )
        buttons = split.column(align=True)
        buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_refresh_entry.bl_idname, icon='FILE_REFRESH', text="")
        buttons.separator()
        up = buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_move_row.bl_idname, icon='TRIA_UP', text="")
        up.direction = 'UP'
        down = buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_move_row.bl_idname, icon='TRIA_DOWN', text="")
        down.direction = 'DOWN'
        buttons.separator()
        top = buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_move_row.bl_idname, icon='TRIA_UP_BAR', text="")
        top.direction = 'TOP'
        bottom = buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_move_row.bl_idname, icon='TRIA_DOWN_BAR', text="")
        bottom.direction = 'BOTTOM'
        buttons.separator()
        buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_sort_rows.bl_idname, icon='SORTALPHA', text="")
        buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_cleanup_saved_only.bl_idname, icon='TRASH', text="")
        buttons.operator(ui_operators.SCENE_OT_mizore_shapekey_override_reset_to_base.bl_idname, icon='LOOP_BACK', text="")

        if entry.rows:
            item = entry.rows[min(entry.active_row_index, len(entry.rows) - 1)]
            _draw_selected_row_detail(box, item)
            if not item.is_basis and not item.is_resolved:
                box.operator(
                    ui_operators.SCENE_OT_mizore_shapekey_override_cleanup_saved_only.bl_idname,
                    text="Cleanup Saved Only",
                    icon='TRASH',
                )
    else:
        candidate_rows = resolver.build_candidate_rows(entry.target_object, context, allow_write=False)
        candidate_names = [row.final_name for row in candidate_rows]
        base_order = resolver.get_base_ordered_names(
            entry.target_object,
            candidate_names=candidate_names,
            candidate_rows=candidate_rows,
        )
        preview_rows = resolver.format_rows_for_entry(
            resolver.build_resolved_rows(
                entry.target_object,
                base_order,
                context,
                allow_write=False,
            )
        )
        preview_box = box.box()
        preview_box.label(text="Inherited AutoMerge Order", icon='INFO')
        _draw_readonly_rows(preview_box, preview_rows)


classes = [
    MIZORE_UL_export_set_shapekey_override_targets,
    MIZORE_UL_export_set_shapekey_override_rows,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
