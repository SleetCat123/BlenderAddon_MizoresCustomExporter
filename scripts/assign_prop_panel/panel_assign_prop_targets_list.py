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
from . import func_get_target_objects
from .. import consts


class OBJECT_PT_mizores_assign_prop_targets_list_panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_mizores_assign_prop_targets_list_" + consts.ADDON_NAME.lower()
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Assign (Mizore)"
    bl_label = "Targets"
    bl_order = 500

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        return wm.mizore_utilspanel_prop_panel_users[0] == consts.ADDON_NAME

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager
        # 選択中のオブジェクトを表示
        targets = func_get_target_objects.get_target_objects()
        layout.label(text="Objects: ")
        layout.prop(wm, "mizore_utilspanel_include_children")
        for obj in targets:
            layout.label(text=obj.name)
