import bpy, operator
from bpy.props import StringProperty, BoolProperty
from ..funcs.utils import func_object_utils, func_collection_utils


class OBJECT_OT_mizore_automerge_assign_group(bpy.types.Operator):
    bl_idname = "object.mizore_automerge_assign_group"
    bl_label = "Assign Collection"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    obj_name: StringProperty(name="Object")
    name: StringProperty(name="Collection")
    assign: BoolProperty(name="Assign", default=True)
    hide: BoolProperty(name="Hide", default=False)

    def execute(self, context):
        temp_selected_objects = bpy.context.selected_objects
        func_object_utils.deselect_all_objects()
        func_object_utils.select_object(bpy.data.objects[self.obj_name], True)
        func_collection_utils.assign_object_group(group_name=self.name, assign=self.assign)
        if self.hide:
            func_collection_utils.hide_collection(context=context, group_name=self.name, hide=True)
        func_object_utils.select_objects(temp_selected_objects, True)
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

        collection = func_collection_utils.find_collection('DontExport')
        if collection and obj.name in collection.objects:
            dont_export = True

        collection = func_collection_utils.find_collection('AlwaysExport')
        if collection and obj.name in collection.objects:
            always_export = True

        if merge:
            row.label(icon='EMPTY_SINGLE_ARROW')

        is_merge_root = False
        collection = func_collection_utils.find_collection('MergeGroup')
        if collection and obj.name in collection.objects:
            is_merge_root = True
            merge = True

        # --- dont_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon='OUTLINER' if is_merge_root else 'NONE', text="")
        op.obj_name = obj.name
        op.name = 'MergeGroup'
        op.assign = not is_merge_root
        op.hide = True
        # ---
        # --- dont_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon='PANEL_CLOSE' if dont_export else 'NONE', text="")
        op.obj_name = obj.name
        op.name = 'DontExport'
        op.assign = not dont_export
        op.hide = True
        # ---
        # --- always_export
        op_id = OBJECT_OT_mizore_automerge_assign_group.bl_idname
        op = row.operator(op_id, icon='CHECKMARK' if always_export else 'NONE', text="")
        op.obj_name = obj.name
        op.name = 'AlwaysExport'
        op.assign = not always_export
        op.hide = True
        # ---

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
