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
from ..ops import op_remove_export_prefs, op_convert_collections
from ..ui import ui_assign_groups


# 右クリックメニューにOperatorを登録
def INFO_MT_object_mizores_exporter_menu(self, context):
    self.layout.menu(VIEW3D_MT_object_mizores_exporter.bl_idname)


class VIEW3D_MT_object_mizores_exporter(bpy.types.Menu):
    bl_label = "Mizore's Custom Exporter"
    bl_idname = "VIEW3D_MT_object_mizores_exporter"

    def draw(self, context):
        layout = self.layout
        ui_assign_groups.draw(layout)

        layout.separator()
        layout.operator(op_remove_export_prefs.OBJECT_OT_mizore_remove_export_settings.bl_idname)
        layout.operator(op_convert_collections.OBJECT_OT_mizore_convert_collections.bl_idname)


def register():
    bpy.utils.register_class(VIEW3D_MT_object_mizores_exporter)
    bpy.types.VIEW3D_MT_object_context_menu.append(INFO_MT_object_mizores_exporter_menu)


def unregister():
    bpy.utils.unregister_class(VIEW3D_MT_object_mizores_exporter)
    bpy.types.VIEW3D_MT_object_context_menu.remove(INFO_MT_object_mizores_exporter_menu)
