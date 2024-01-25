import bpy, operator
from bpy.props import StringProperty, BoolProperty
from ..funcs.utils import func_object_utils, func_collection_utils, func_custom_props_utils


class OBJECT_OT_mizore_automerge_assign_group(bpy.types.Operator):
    bl_idname = "object.mizore_automerge_assign_group"
    bl_label = "Assign Collection"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    obj_name: StringProperty(name="Object")
    name: StringProperty(name="Collection")
    assign: BoolProperty(name="Assign", default=True)

    def execute(self, context):
        obj = bpy.data.objects[self.obj_name]
        func_custom_props_utils.assign_bool_prop(
            target=[obj],
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
        split = layout.split(align=True, factor=0.8)
        if indent <= 0:
            indent = 1
        split_indent = split.split(align=True, factor=0.05 * indent)
        if obj.select_get():
            split_indent.label(text="-")
        else:
            split_indent.label(text="")
        split_indent.label(text=obj.name, icon='OUTLINER_OB_' + obj.type)

        row = split.row(align=True)

        dont_export = func_custom_props_utils.prop_is_true(obj, 'DontExport')
        always_export = func_custom_props_utils.prop_is_true(obj, 'AlwaysExport')

        if merge:
            row.label(icon='EMPTY_SINGLE_ARROW')

        is_merge_root = func_custom_props_utils.prop_is_true(obj, 'MergeGroup')
        if is_merge_root:
            merge = True
        
        # --- dont_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon='OUTLINER' if is_merge_root else 'NONE', text="")
        op.obj_name = obj.name
        op.name = 'MergeGroup'
        op.assign = not is_merge_root
        # ---
        # --- dont_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon='PANEL_CLOSE' if dont_export else 'NONE', text="")
        op.obj_name = obj.name
        op.name = 'DontExport'
        op.assign = not dont_export
        # ---
        # --- always_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon='CHECKMARK' if always_export else 'NONE', text="")
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
        print("draw panel_object_list")
        layout = self.layout

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


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
