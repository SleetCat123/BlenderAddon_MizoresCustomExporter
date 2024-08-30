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
from .panel_assign_prop_targets_list import OBJECT_PT_mizores_assign_prop_targets_list_panel
from .panel_select_prop_objects import OBJECT_OT_mizore_utilspanel_select_prop_objects
from . import op_assign_prop
from .. import consts


translations_dict = {
    "en_US": {
        ("*", OBJECT_OT_mizore_utilspanel_select_prop_objects.bl_idname + ".select"): "Select",
    },
    "ja_JP": {
        ("*", OBJECT_OT_mizore_utilspanel_select_prop_objects.bl_idname + ".select"): "選択",
        ("*", "Groups not found."): "グループが見つかりませんでした。",
        ("*", "Please install my addon."): "同作者の下記アドオンをインストールしてください。",
        ("*", "Select objects assigned to the property.\nHidden objects are not selected."): "プロパティが割り当てられているオブジェクトを選択します。\n非表示状態のオブジェクトは選択されません",
    },
}


def register():
    bpy.app.translations.register(__name__, translations_dict)
    bpy.utils.register_class(OBJECT_PT_mizores_assign_prop_targets_list_panel)
    bpy.utils.register_class(OBJECT_OT_mizore_utilspanel_select_prop_objects)
    op_assign_prop.register()

    if not hasattr(bpy.types.WindowManager, "mizore_utilspanel_prop_panel_users"):
        bpy.types.WindowManager.mizore_utilspanel_include_children = bpy.props.BoolProperty(name="Include Children", default=False)
        bpy.types.WindowManager.mizore_utilspanel_prop_panel_users = []
    wm = bpy.context.window_manager
    wm.mizore_utilspanel_prop_panel_users.append(consts.ADDON_NAME)
    # print(wm.mizore_utilspanel_prop_panel_users)


def unregister():
    bpy.utils.unregister_class(OBJECT_PT_mizores_assign_prop_targets_list_panel)
    bpy.utils.unregister_class(OBJECT_OT_mizore_utilspanel_select_prop_objects)
    op_assign_prop.unregister()
    bpy.app.translations.unregister(__name__)

    # usersが空になったら削除
    wm = bpy.context.window_manager
    wm.mizore_utilspanel_prop_panel_users.remove(consts.ADDON_NAME)
    # print(wm.mizore_utilspanel_prop_panel_users)
    if len(wm.mizore_utilspanel_prop_panel_users) == 0:
        del bpy.types.WindowManager.mizore_utilspanel_prop_panel_users
        del bpy.types.WindowManager.mizore_utilspanel_include_children

