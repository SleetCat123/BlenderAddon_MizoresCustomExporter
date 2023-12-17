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
from ..funcs.utils import func_custom_props_utils


class OBJECT_OT_mizore_assign_group(bpy.types.Operator):
    bl_idname = "object.mizore_assign_group"
    bl_label = "Assign Group"
    bl_description = bpy.app.translations.pgettext(bl_idname + consts.DESC)
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(name="Collection Name", default="")
    assign: bpy.props.BoolProperty(name="Assign", default=True)

    def execute(self, context):
        # func_collection_utils.assign_object_group(group_name=self.name, assign=self.assign)
        # func_collection_utils.hide_collection(context=context, group_name=self.name, hide=True)
        func_custom_props_utils.assign_bool_prop(
            target=bpy.context.selected_objects,
            prop_name=self.name,
            value=self.assign,
            remove_if_false=True
        )
        return {'FINISHED'}


classes = [
    OBJECT_OT_mizore_assign_group,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
