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
from ..funcs.utils import func_custom_props_utils
from .. import consts

class OBJECT_OT_mizore_assign_prop(bpy.types.Operator):
    bl_idname = "object.mizore_assign_prop_" + consts.ADDON_NAME.lower()
    bl_label = "Assign Prop"
    bl_description = "Set or Unset the selected object(s) to or from the property"
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(
        name="Property Name", 
        default=""
    )
    assign: bpy.props.BoolProperty(
        name="Assign", 
        default=True
    )

    @classmethod
    def description(cls, context, properties):
        if properties.assign:
            return bpy.app.translations.pgettext(cls.bl_idname + ".assign.true.desc").format(properties.name)
        else:
            return bpy.app.translations.pgettext(cls.bl_idname + ".assign.false.desc").format(properties.name)

    def execute(self, context):
        targets = bpy.context.selected_objects
        if context.object:
            targets.append(context.object)
        func_custom_props_utils.assign_bool_prop(
            target=targets,
            prop_name=self.name,
            value=self.assign,
            remove_if_false=True
        )
        return {'FINISHED'}


translations_dict = {
    "en_US": {
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".set"): "Set",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".unset"): "Unset",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".set.format"): "Set {}",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".unset.format"): "Unset {}",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".label"): "Set/Unset {}",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".assign.true.desc"): "Assign the property \"{}\"",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".assign.false.desc"): "Remove the property \"{}\"",
    },
    "ja_JP": {
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".set"): "登録",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".unset"): "解除",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".set.format"): "{}を登録",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".unset.format"): "{}を解除",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".label"): "{}を登録/解除",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".assign.true.desc"): "選択中のオブジェクトに\"{}\"プロパティを設定します",
        ("*", OBJECT_OT_mizore_assign_prop.bl_idname + ".assign.false.desc"): "選択中のオブジェクトから\"{}\"プロパティを解除します",
        
        ("*", "Set or Unset the selected object(s) to or from the property"): "選択中のオブジェクトのプロパティを設定または解除します",
        ("*", "Property Name"): "プロパティ名",
        ("*", "Assign"): "割り当て",
    },
}


classes = [
    OBJECT_OT_mizore_assign_prop,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.translations.register(__name__, translations_dict)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.app.translations.unregister(__name__)