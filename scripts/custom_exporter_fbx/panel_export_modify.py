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


class MIZORE_FBX_PT_export_modify(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Modify"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

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

        layout.prop(operator, "enable_fix_vertex_group_collisions")
        
        # 他のModify系設定（remove_groups_not_bone、remove_unused_groups、convert_uv_tiles_to_single）は
        # オブジェクト固有のカスタムプロパティとして管理されているため、ここには追加しない


def register():
    bpy.utils.register_class(MIZORE_FBX_PT_export_modify)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_modify)