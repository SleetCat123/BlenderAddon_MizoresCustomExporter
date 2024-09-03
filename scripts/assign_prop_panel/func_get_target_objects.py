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
from ..funcs.utils import func_object_utils

def get_target_objects():
    result = []
    selected_objects = bpy.context.selected_objects
    if selected_objects:
        result = selected_objects
    elif bpy.context.object:
        # 選択中のオブジェクトがない場合はcontext.objectを返す
        # 非表示状態のオブジェクトも対象となる
        result = [bpy.context.object]
    wm = bpy.context.window_manager
    if wm.mizore_utilspanel_include_children:
        result = func_object_utils.get_children_recursive(result, contains_self=True)
    return result