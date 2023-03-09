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
from .. import func_addon_link


class MIZORE_FBX_PT_export_shapekeysutil(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "[Addon]ShapeKey Utils"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx" and func_addon_link.shapekey_util_is_found()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "enable_apply_modifiers_with_shapekeys")
        layout.prop(operator, "enable_separate_lr_shapekey")

        box = layout.box()
        box.label(text=bpy.app.translations.pgettext("box_warning_slow_method_1"))
        box.label(text=bpy.app.translations.pgettext("box_warning_slow_method_2"))
        box.label(text=bpy.app.translations.pgettext("box_warning_slow_method_3"))


def register():
    bpy.utils.register_class(MIZORE_FBX_PT_export_shapekeysutil)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_shapekeysutil)
