import bpy
from bpy.props import StringProperty, PointerProperty, EnumProperty, BoolProperty
from ..ops import op_assign_collection


class OBJECT_PT_mizores_custom_exporter_group_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mizore"
    bl_label = "Assign Groups"

    def draw(self, context):
        layout = self.layout

        layout.label(text=bpy.app.translations.pgettext("mizores_custom_exporter_group_panel_assign"))
        layout.operator(op_assign_collection.OBJECT_OT_specials_assign_dont_export_group.bl_idname).assign = True
        layout.operator(op_assign_collection.OBJECT_OT_specials_assign_always_export_group.bl_idname).assign = True
        try:
            layout.operator("object.automerge_assign_merge_group").assign = True
            layout.operator("object.automerge_assign_dont_merge_to_parent_group").assign = True
        except:
            pass

        layout.label(text=bpy.app.translations.pgettext("mizores_custom_exporter_group_panel_assign"))
        layout.operator(op_assign_collection.OBJECT_OT_specials_assign_dont_export_group.bl_idname).assign = False
        layout.operator(op_assign_collection.OBJECT_OT_specials_assign_always_export_group.bl_idname).assign = False
        try:
            layout.operator("object.automerge_assign_merge_group").assign = False
            layout.operator("object.automerge_assign_dont_merge_to_parent_group").assign = False
        except:
            pass


classes = [
    OBJECT_PT_mizores_custom_exporter_group_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
