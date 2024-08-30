import bpy, operator
import os
import bpy.utils.previews
from bpy.props import StringProperty, BoolProperty
from ..funcs.utils import func_object_utils, func_custom_props_utils
from ..assign_prop_panel.op_assign_prop import OBJECT_OT_mizore_assign_prop


custom_icons = {}


class OBJECT_OT_mizore_automerge_assign_group(bpy.types.Operator):
    bl_idname = "object.mizore_automerge_assign_group"
    bl_label = "Assign Prop"
    bl_description = "Assign/Unassign the property to the object"
    bl_options = {'REGISTER', 'UNDO'}

    obj_name: StringProperty(name="Object")
    name: StringProperty(name="Prop Name")
    assign: BoolProperty(name="Assign", default=True)

    @classmethod
    def description(cls, context, event):
        name = getattr(event, "name", "Prop Name")
        assign = getattr(event, "assign", True)
        if assign:
            return bpy.app.translations.pgettext(OBJECT_OT_mizore_assign_prop.bl_idname + ".assign.true.desc").format(name)
        else:
            return bpy.app.translations.pgettext(OBJECT_OT_mizore_assign_prop.bl_idname + ".assign.false.desc").format(name)


    def execute(self, context):
        obj = bpy.data.objects[self.obj_name]
        targets = [obj]
        wm = bpy.context.window_manager
        if wm.mizore_utilspanel_include_children:
            targets = func_object_utils.get_children_recursive(targets, contains_self=True)
        func_custom_props_utils.assign_bool_prop(
            target=targets,
            prop_name=self.name,
            value=self.assign,
            remove_if_false=True
        )
        return {'FINISHED'}


class OBJECT_PT_mizores_automerge_list_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mizore"
    bl_label = "Object List (WIP)"
    bl_options = {"DEFAULT_CLOSED"}

    @staticmethod
    def draw_recursive(obj, layout, indent: int,
                       merge: bool = False,
                       dont_export: bool = False,
                       always_export: bool = False):
        split = layout.split(align=True, factor=0.7)
        if indent <= 0:
            indent = 1
        split_indent = split.split(align=True, factor=0.05 * indent)
        if obj.select_get():
            split_indent.label(text="-")
        else:
            split_indent.label(text="")
        split_indent.label(text=obj.name, icon='OUTLINER_OB_' + obj.type, translate=False)

        row = split.row(align=True)

        dont_export = func_custom_props_utils.prop_is_true(obj, 'DontExport')
        always_export = func_custom_props_utils.prop_is_true(obj, 'AlwaysExport')

        global custom_icons
        icon_table = custom_icons["object_list"]
        icon_empty = icon_table["icon_empty"].icon_id
        icon_automerge_parent = icon_table["icon_automerge_parent"].icon_id
        icon_automerge_child = icon_table["icon_automerge_child"].icon_id
        icon_dont_export = icon_table["icon_dont_export"].icon_id
        icon_always_export = icon_table["icon_always_export"].icon_id
        if merge:
            row.label(icon_value=icon_automerge_child)

        is_merge_root = func_custom_props_utils.prop_is_true(obj, 'MergeGroup')
        if is_merge_root:
            merge = True
        
        # --- auto merge
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon_value=icon_automerge_parent, text="", depress=is_merge_root)
        op.obj_name = obj.name
        op.name = 'MergeGroup'
        op.assign = not is_merge_root
        # ---
        # --- dont_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon_value=icon_dont_export, text="", depress=dont_export)
        op.obj_name = obj.name
        op.name = 'DontExport'
        op.assign = not dont_export
        # ---
        # --- always_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon_value=icon_always_export, text="", depress=always_export)
        op.obj_name = obj.name
        op.name = 'AlwaysExport'
        op.assign = not always_export
        # ---

        if dont_export:
            return
        children = func_object_utils.get_children_objects(obj)
        for child in children:
            OBJECT_PT_mizores_automerge_list_panel.draw_recursive(child, layout, indent=indent + 1,
                                                                  merge=merge,
                                                                  dont_export=dont_export,
                                                                  always_export=always_export
                                                                  )

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager

        layout.prop(wm, "mizore_utilspanel_include_children")

        roots = [v for v in bpy.context.window.view_layer.objects if v.parent is None]
        roots = sorted(roots, key=operator.attrgetter('name'))
        for obj in roots:
            OBJECT_PT_mizores_automerge_list_panel.draw_recursive(obj, layout, indent=0)


classes = [
    OBJECT_OT_mizore_automerge_assign_group,
    OBJECT_PT_mizores_automerge_list_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    previews = bpy.utils.previews.new()
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    icons_dir = os.path.join(root_dir, "icons")
    files = os.listdir(icons_dir)
    for f in files:
        name = os.path.splitext(f)[0]
        previews.load(name, os.path.join(icons_dir, f), 'IMAGE')
    custom_icons["object_list"] = previews


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    for p in custom_icons.values():
        bpy.utils.previews.remove(p)
