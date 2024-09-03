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


class OBJECT_OT_mizore_remove_saved_path(bpy.types.Operator):
    bl_idname = "object.mizore_remove_saved_path"
    bl_label = "Remove Saved Path"
    bl_description = "Remove export destination settings of MizoresCustomExporter saved in this blend file"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences_scene.remove_str_prop("filepath")
        self.report({'INFO'}, "Export path removed.")
        return {'FINISHED'}


translations_dict = {
    "ja_JP": {
        ("*", "Remove Saved Path"): "保存されたパスを削除",
        ("*", "Remove export destination settings of MizoresCustomExporter saved in this blend file"): "現在のblendファイルに保存されているMizoresCustomExporterのエクスポート先の設定を削除します",
    },
}


def register():
    bpy.utils.register_class(OBJECT_OT_mizore_remove_saved_path)
    bpy.app.translations.register(__name__, translations_dict)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mizore_remove_saved_path)
    bpy.app.translations.unregister(__name__)