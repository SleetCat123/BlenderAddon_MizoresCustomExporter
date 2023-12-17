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
from ..ops import op_remove_export_prefs, op_convert_collections, op_assign_collection
from .. import consts


# 右クリックメニューにOperatorを登録
def INFO_MT_object_mizores_exporter_menu(self, context):
    self.layout.menu(VIEW3D_MT_object_mizores_exporter.bl_idname)


def draw_button(layout, group_name: str, assign: bool):
    assign_collection_id = op_assign_collection.OBJECT_OT_mizore_assign_group.bl_idname
    if assign:
        label = bpy.app.translations.pgettext(assign_collection_id + ".Set_Menu")
    else:
        label = bpy.app.translations.pgettext(assign_collection_id + ".Unset_Menu")
    label = label.format(group_name)
    
    op = layout.operator(assign_collection_id, text=label)
    op.name = group_name
    op.assign = True


class VIEW3D_MT_object_mizores_exporter(bpy.types.Menu):
    bl_label = "Mizore's Custom Exporter"
    bl_idname = "VIEW3D_MT_object_mizores_exporter"

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager
        
        # グループの割り当て
        groups = [
            consts.DONT_EXPORT_GROUP_NAME,
            consts.ALWAYS_EXPORT_GROUP_NAME,
            consts.RESET_POSE_GROUP_NAME,
            consts.RESET_SHAPEKEY_GROUP_NAME,
            consts.ALWAYS_RESET_SHAPEKEY_GROUP_NAME,
            wm.mizore_automerge_collection_name,
            wm.mizore_automerge_dont_merge_to_parent_collection_name
        ]
        for group_name in groups:
            draw_button(layout, group_name, True)
        layout.separator()
        for group_name in groups:
            draw_button(layout, group_name, False)

        layout.separator()
        layout.operator(op_remove_export_prefs.OBJECT_OT_mizore_remove_export_settings.bl_idname)
        layout.operator(op_convert_collections.OBJECT_OT_mizore_convert_collections.bl_idname)


def register():
    bpy.utils.register_class(VIEW3D_MT_object_mizores_exporter)
    bpy.types.VIEW3D_MT_object_context_menu.append(INFO_MT_object_mizores_exporter_menu)


def unregister():
    bpy.utils.unregister_class(VIEW3D_MT_object_mizores_exporter)
    bpy.types.VIEW3D_MT_object_context_menu.remove(INFO_MT_object_mizores_exporter_menu)
