import bpy

from .shapekey_order_override import ui_panel as shapekey_override_panel

class MIZORE_UL_export_sets(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "filename", text="", emboss=False, translate=False)


class MIZORE_UL_export_set_items(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        target_name = item.root_object.name if item.root_object else "(None)"
        row.label(text=target_name, translate=False)


class MIZORE_UL_export_set_vertex_color_replace_rules(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "source_color", text="")
        row.label(text="to")
        row.prop(item, "target_color", text="")
        layer_text = item.layer_name if item.layer_name else "(All Layers)"
        row.label(text=layer_text, translate=False)


class MIZORE_UL_export_set_object_replace_rules(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        source_name = item.source_object.name if item.source_object else "(None)"
        replacement_name = item.replacement_object.name if item.replacement_object else "(None)"
        row.label(text=source_name, icon='OBJECT_DATA', translate=False)
        row.label(text="→")
        row.label(text=replacement_name, icon='DUPLICATE', translate=False)


def draw_export_sets_editor(layout, context):
    props = context.scene.mizore_export_sets

    row = layout.row()
    row.template_list(
        "MIZORE_UL_export_sets",
        "",
        props,
        "export_sets",
        props,
        "active_export_set_index",
    )
    col = row.column(align=True)
    col.operator("scene.mizore_add_export_set", icon='ADD', text="")
    col.operator("scene.mizore_duplicate_export_set", icon='DUPLICATE', text="")
    move_up = col.operator("scene.mizore_move_export_set", icon='TRIA_UP', text="")
    move_up.direction = 'UP'
    move_down = col.operator("scene.mizore_move_export_set", icon='TRIA_DOWN', text="")
    move_down.direction = 'DOWN'
    col.operator("scene.mizore_remove_export_set", icon='REMOVE', text="")

    if not props.export_sets:
        layout.label(text="No export sets.")
        return

    export_set = props.export_sets[min(props.active_export_set_index, len(props.export_sets) - 1)]

    col = layout.column(align=True)
    col.prop(export_set, "join_meshes_to_one")

    replace_box = layout.box()
    replace_box.label(text="Object Replace", icon='DUPLICATE')
    row = replace_box.row()
    row.template_list(
        "MIZORE_UL_export_set_object_replace_rules",
        "",
        export_set,
        "object_replace_rules",
        export_set,
        "active_object_replace_rule_index",
    )
    col = row.column(align=True)
    col.operator("scene.mizore_add_export_set_object_replace_rule", icon='ADD', text="")
    col.operator("scene.mizore_duplicate_export_set_object_replace_rule", icon='DUPLICATE', text="")
    move_up = col.operator("scene.mizore_move_export_set_object_replace_rule", icon='TRIA_UP', text="")
    move_up.direction = 'UP'
    move_down = col.operator("scene.mizore_move_export_set_object_replace_rule", icon='TRIA_DOWN', text="")
    move_down.direction = 'DOWN'
    col.operator("scene.mizore_remove_export_set_object_replace_rule", icon='REMOVE', text="")

    if export_set.object_replace_rules:
        rule = export_set.object_replace_rules[
            min(
                export_set.active_object_replace_rule_index,
                len(export_set.object_replace_rules) - 1,
            )
        ]
        col = replace_box.column(align=True)
        col.prop(rule, "source_object")
        col.prop(rule, "replacement_object")
        col.prop(rule, "include_children")
    else:
        replace_box.label(text="No object replacement rules.", icon='INFO')

    color_box = layout.box()
    color_box.label(text="Vertex Color Replace", icon='GROUP_VCOL')
    row = color_box.row()
    row.template_list(
        "MIZORE_UL_export_set_vertex_color_replace_rules",
        "",
        export_set,
        "vertex_color_replace_rules",
        export_set,
        "active_vertex_color_replace_rule_index",
    )
    col = row.column(align=True)
    col.operator("scene.mizore_add_export_set_vcol_replace_rule", icon='ADD', text="")
    col.operator("scene.mizore_duplicate_export_set_vcol_replace_rule", icon='DUPLICATE', text="")
    move_up = col.operator("scene.mizore_move_export_set_vcol_replace_rule", icon='TRIA_UP', text="")
    move_up.direction = 'UP'
    move_down = col.operator("scene.mizore_move_export_set_vcol_replace_rule", icon='TRIA_DOWN', text="")
    move_down.direction = 'DOWN'
    col.operator("scene.mizore_remove_export_set_vcol_replace_rule", icon='REMOVE', text="")

    if export_set.vertex_color_replace_rules:
        rule = export_set.vertex_color_replace_rules[
            min(
                export_set.active_vertex_color_replace_rule_index,
                len(export_set.vertex_color_replace_rules) - 1,
            )
        ]
        col = color_box.column(align=True)
        col.prop(rule, "layer_name")
        col.prop(rule, "source_color")
        col.prop(rule, "target_color")
        col.prop(rule, "tolerance")
    else:
        color_box.label(text="No vertex color replacement rules.", icon='INFO')

    merge_box = layout.box()
    merge_box.label(text="Armature Merge", icon='ARMATURE_DATA')
    merge_box.prop(export_set, "merge_armatures", text="Merge Into One Armature")
    if not export_set.merge_armatures:
        merge_box.label(text="Enable Merge Into One Armature to configure armature merge settings.", icon='INFO')

    merge_col = merge_box.column(align=True)
    merge_col.enabled = export_set.merge_armatures
    merge_col.prop(export_set, "target_armature")
    if export_set.merge_armatures and export_set.target_armature is None:
        merge_box.label(text="Target Armature is required when multiple armatures are merged.", icon='INFO')

    layout.separator()

    row = layout.row()
    row.template_list(
        "MIZORE_UL_export_set_items",
        "",
        export_set,
        "items",
        export_set,
        "active_item_index",
    )
    col = row.column(align=True)
    col.operator("scene.mizore_add_export_set_item", icon='ADD', text="")
    col.operator("scene.mizore_duplicate_export_set_item", icon='DUPLICATE', text="")
    move_up = col.operator("scene.mizore_move_export_set_item", icon='TRIA_UP', text="")
    move_up.direction = 'UP'
    move_down = col.operator("scene.mizore_move_export_set_item", icon='TRIA_DOWN', text="")
    move_down.direction = 'DOWN'
    col.operator("scene.mizore_remove_export_set_item", icon='REMOVE', text="")

    if not export_set.items:
        layout.label(text="No items.")
        return

    item = export_set.items[min(export_set.active_item_index, len(export_set.items) - 1)]
    item_box = layout.box()
    item_box.label(text="Selected Item", icon='OBJECT_DATA')
    col = item_box.column(align=True)
    col.prop(item, "root_object", text="Root Object")
    col.prop(item, "include_children")

    armature_col = item_box.column(align=True)
    armature_col.enabled = export_set.merge_armatures
    if item.root_object is None or item.root_object.type != 'ARMATURE':
        armature_col.prop(item, "armature_object")
    armature_col.prop(item, "attach_to_bone")
    if export_set.merge_armatures and item.armature_object is None:
        item_box.label(text="Armature is inferred from the root when possible.", icon='INFO')
        item_box.label(text="Attach To Bone is inferred if empty.", icon='INFO')

    layout.separator()
    shapekey_override_panel.draw_shapekey_reorder_override(layout, context, export_set)


class VIEW3D_PT_mizore_export_sets(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Assign (Mizore)"
    bl_label = "Export Sets"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1200

    def draw(self, context):
        layout = self.layout
        draw_export_sets_editor(layout, context)


classes = [
    MIZORE_UL_export_sets,
    MIZORE_UL_export_set_items,
    MIZORE_UL_export_set_vertex_color_replace_rules,
    MIZORE_UL_export_set_object_replace_rules,
    VIEW3D_PT_mizore_export_sets,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
