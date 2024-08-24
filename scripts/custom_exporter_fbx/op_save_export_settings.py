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
from .. import preferences_scene

class OBJECT_OT_mizore_save_export_settings(bpy.types.Operator):
    bl_idname = "object.mizore_save_export_settings"
    bl_label = "Save Export Settings"
    bl_description = "Remove export settings saved in this blend file"
    bl_options = {'REGISTER'}

    operator = None

    def execute(self, context):
        ignore_key = ["reset_path"]
        if not self.operator.save_path:
            ignore_key.append("filepath")
        preferences_scene.clear_export_props()
        preferences_scene.save_scene_prefs(operator=self.operator, ignore_key=ignore_key)
        return {'FINISHED'}
    
def register():
    bpy.utils.register_class(OBJECT_OT_mizore_save_export_settings)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mizore_save_export_settings)