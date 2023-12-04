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
from .. import consts
from ..funcs.utils import func_collection_utils, func_custom_props_utils


# 選択オブジェクトをDontExportグループに入れたり外したりするクラス
class OBJECT_OT_specials_assign_dont_export_group(bpy.types.Operator):
    bl_idname = "object.assign_dont_export_group"
    bl_label = "Assign Don't-Export Group"
    bl_description = bpy.app.translations.pgettext(bl_idname + consts.DESC)
    bl_options = {'REGISTER', 'UNDO'}

    assign: bpy.props.BoolProperty(name="Assign", default=True)

    def execute(self, context):
        func_collection_utils.assign_object_group(group_name=consts.DONT_EXPORT_GROUP_NAME, assign=self.assign)
        # exclude_collection(context=context, group_name=DONT_EXPORT_GROUP_NAME, exclude=True)
        func_collection_utils.hide_collection(context=context, group_name=consts.DONT_EXPORT_GROUP_NAME, hide=True)
        func_custom_props_utils.assign_bool_prop(
            target=bpy.context.selected_objects,
            prop_name=consts.DONT_EXPORT_GROUP_NAME,
            value=self.assign,
            remove_if_false=True
        )
        return {'FINISHED'}


# 選択オブジェクトをAlwaysExportグループに入れたり外したりするクラス
class OBJECT_OT_specials_assign_always_export_group(bpy.types.Operator):
    bl_idname = "object.assign_always_export_group"
    bl_label = "Assign Always-Export Group"
    bl_description = bpy.app.translations.pgettext(bl_idname + consts.DESC)
    bl_options = {'REGISTER', 'UNDO'}

    assign: bpy.props.BoolProperty(name="Assign", default=True)

    def execute(self, context):
        func_collection_utils.assign_object_group(group_name=consts.ALWAYS_EXPORT_GROUP_NAME, assign=self.assign)
        # exclude_collection(context=context, group_name=ALWAYS_EXPORT_GROUP_NAME, exclude=True)
        func_collection_utils.hide_collection(context=context, group_name=consts.ALWAYS_EXPORT_GROUP_NAME, hide=True)
        func_custom_props_utils.assign_bool_prop(
            target=bpy.context.selected_objects,
            prop_name=consts.ALWAYS_EXPORT_GROUP_NAME,
            value=self.assign,
            remove_if_false=True
        )
        return {'FINISHED'}


classes = [
    OBJECT_OT_specials_assign_dont_export_group,
    OBJECT_OT_specials_assign_always_export_group,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
