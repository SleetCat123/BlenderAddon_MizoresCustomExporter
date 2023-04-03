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
from . import preferences_scene


class OBJECT_OT_mizore_remove_export_settings(bpy.types.Operator):
    bl_idname = "object.mizore_remove_export_settings"
    bl_label = "Remove Export Settings"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences_scene.clear_export_props()
        self.report({'INFO'}, "Export settings removed.")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)


class OBJECT_OT_mizore_remove_export_path(bpy.types.Operator):
    bl_idname = "object.mizore_remove_export_path"
    bl_label = "Remove Export Path"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences_scene.remove_str_prop("filepath")
        self.report({'INFO'}, "Export path removed.")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)


classes = [
    OBJECT_OT_mizore_remove_export_settings,
    OBJECT_OT_mizore_remove_export_path,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
