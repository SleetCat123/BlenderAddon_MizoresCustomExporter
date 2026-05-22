# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy


class MIZORE_FBX_PT_export_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        scale_col = layout.column(align=False)
        scale_col.label(text="Scale")
        scale_props = scale_col.column(align=False)
        scale_props.prop(operator, "global_scale")
        scale_props.prop(operator, "scale_value_mode")
        scale_props.prop(operator, "scale_pivot")
        scale_props.prop(operator, "apply_scale_options")

        axis_col = layout.column(align=False)
        axis_col.label(text="Axes")
        axis_props = axis_col.column(align=False)
        axis_props.prop(operator, "axis_forward")
        axis_props.prop(operator, "axis_up")

        transform_col = layout.column(align=False)
        transform_col.label(text="Transform")
        transform_props = transform_col.column(align=False)
        transform_props.prop(operator, "apply_unit_scale")
        transform_props.prop(operator, "use_space_transform")
        row = transform_props.row()
        row.prop(operator, "bake_space_transform")
        row.label(text="", icon='ERROR')


def register():
    bpy.utils.register_class(MIZORE_FBX_PT_export_transform)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_transform)
