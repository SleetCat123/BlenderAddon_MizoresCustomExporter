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


def shapekey_util_is_found():
    try:
        return hasattr(bpy.types, bpy.ops.object.shapekeys_util_apply_mod_for_exporter_addon.idname())
    except AttributeError:
        return False


def shapekey_util_iter_is_available():
    """ShapeKeysUtilのジェネレータ取得関数が利用可能かチェック"""
    return hasattr(bpy.types.WindowManager, 'shapekeys_util_get_apply_modifiers_iter')


def auto_merge_is_found():
    try:
        return hasattr(bpy.types, bpy.ops.object.apply_modifier_and_merge_grouped_exporter_addon.idname())
    except AttributeError:
        return False


def auto_merge_iter_is_available():
    """AutoMergeのジェネレータ取得関数が利用可能かチェック"""
    return hasattr(bpy.types.WindowManager, 'automerge_get_merge_iter')


def shapekey_util_change_base_is_available():
    """ShapeKeysUtilのベース変更ジェネレータが利用可能かチェック"""
    return hasattr(bpy.types.WindowManager, 'shapekeys_util_get_change_base_iter')


def shapekey_util_reorder_is_available():
    """ShapeKeysUtilの並び替えジェネレータが利用可能かチェック"""
    return hasattr(bpy.types.WindowManager, 'shapekeys_util_get_reorder_iter')


def update_mesh_deform_addon_is_found():
    try:
        return hasattr(bpy.types, bpy.ops.object.mizore_update_mesh_deform.idname())
    except AttributeError:
        return False


