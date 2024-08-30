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
from ..funcs.utils import func_custom_props_utils, func_object_utils
from .. import consts


class OBJECT_OT_mizore_utilspanel_select_prop_objects(bpy.types.Operator):
    bl_idname = "object.mizore_panel_select_prop_objects_" + consts.ADDON_NAME.lower()
    bl_label = "Select Prop Assigned Objects"
    bl_description = "Select objects assigned to the property.\nHidden objects are not selected."
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(name="Prop Name", default="")
    force_visible: bpy.props.BoolProperty(name="Force Visible", default=True)

    def execute(self, context):
        func_object_utils.deselect_all_objects()
        targets = [obj for obj in bpy.context.scene.collection.all_objects if func_custom_props_utils.prop_is_true(obj, self.name)]
        print(f"Prop {self.name} assigned: ")
        hidden_count = 0
        for obj in targets:
            log = f"  {obj.name} ({obj.type})"
            is_hidden = obj.hide_viewport or obj.hide_get()
            if is_hidden:
                if self.force_visible:
                    obj.hide_viewport = False
                    obj.hide_set(False)
                else:
                    hidden_count += 1
                    log = "(hidden)" + log
            print(log)
        func_object_utils.select_objects(targets)
        # 非表示状態のオブジェクトをカウント
        count = len(targets)
        if self.force_visible:
            self.report({'INFO'}, f"Selected {len(targets)} objects")
        else:
            self.report({'INFO'}, f"Selected {count-hidden_count} / {len(targets)} objects")
        return {'FINISHED'}
    