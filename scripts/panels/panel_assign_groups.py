import bpy
from bpy.props import StringProperty, PointerProperty, EnumProperty, BoolProperty
from .. import consts
from ..ops import op_assign_collection
from ..ui import ui_assign_groups


class OBJECT_PT_mizores_custom_exporter_group_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mizore"
    bl_label = "Assign Groups"

    def draw(self, context):
        layout = self.layout
        ui_assign_groups.draw(layout)


classes = [
    OBJECT_PT_mizores_custom_exporter_group_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
