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
from .op_assign_prop import OBJECT_OT_mizore_assign_prop
from . import func_get_target_objects
from .panel_select_prop_objects import OBJECT_OT_mizore_utilspanel_select_prop_objects


def button_is_enabled(prop_name: str, assign: bool):
    targets = func_get_target_objects.get_target_objects()
    if assign:
        return not all([func_custom_props_utils.prop_is_true(obj, prop_name) for obj in targets])
    else:
        return any([func_custom_props_utils.prop_is_true(obj, prop_name) for obj in targets])


class OBJECT_PT_mizores_assign_group_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Assign (Mizore)"
    bl_label = "Groups"
    bl_order = 1000

    groups = []
    required_addons = []

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager

        id = OBJECT_OT_mizore_assign_prop.bl_idname
        any_group_found = False
        for key in self.groups:
            if not hasattr(wm, key):
                continue
            any_group_found = True
            group_name = getattr(wm, key)
            row = layout.row(align=True)
            row.label(text=group_name)

            column = row.column(align=False)
            column.scale_x = 0.45
            column.enabled = button_is_enabled(group_name, True)
            op = column.operator(id, text=bpy.app.translations.pgettext(OBJECT_OT_mizore_assign_prop.bl_idname + ".set"))
            op.name = group_name
            op.assign = True

            column = row.column(align=False)
            column.scale_x = 0.45
            column.enabled = button_is_enabled(group_name, False)
            op = column.operator(id, text=bpy.app.translations.pgettext(OBJECT_OT_mizore_assign_prop.bl_idname + ".unset"))
            op.name = group_name
            op.assign = False

            column = row.column(align=False)
            column.scale_x = 0.4
            select_op_id = OBJECT_OT_mizore_utilspanel_select_prop_objects.bl_idname
            op = column.operator(select_op_id, text=bpy.app.translations.pgettext(OBJECT_OT_mizore_utilspanel_select_prop_objects.bl_idname + ".select"))
            op.name = group_name
        if not any_group_found:
            layout.label(text="Groups not found.")
            layout.label(text="Please install my addon.")
        layout.separator()
        for addon in self.required_addons:
            layout.label(text=addon, translate=False)
