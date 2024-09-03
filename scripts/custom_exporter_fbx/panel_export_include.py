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


class MIZORE_FBX_PT_export_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
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

        sublayout = layout.column(heading="Limit to (Objects)")
        sublayout.enabled = (operator.batch_mode == 'OFF')
        sublayout.prop(operator, "use_selection")
        row = sublayout.row(align=True)
        row.enabled = operator.use_selection
        row.prop(operator, "use_selection_children_objects")

        sublayout = layout.column(heading="Limit to (Collections)")
        sublayout.enabled = (operator.batch_mode == 'OFF')
        sublayout.prop(operator, "use_active_collection")
        row = sublayout.row(align=True)
        row.enabled = operator.use_active_collection
        row.prop(operator, "use_active_collection_children_objects")
        row = sublayout.row(align=True)
        row.enabled = operator.use_active_collection
        row.prop(operator, "use_active_collection_children_collections")

        layout.column().prop(operator, "object_types")
        layout.prop(operator, "use_custom_props")


def register():
    bpy.utils.register_class(MIZORE_FBX_PT_export_include)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_include)
