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

"""
シェイプキー操作設定リストの操作オペレーター

UIListの追加/削除/上下移動を提供する。
"""

import bpy
from bpy.props import EnumProperty

# --- ベース変更リスト操作 ---

class OBJECT_OT_mizore_change_base_shapekey_add(bpy.types.Operator):
    bl_idname = "object.mizore_change_base_shapekey_add"
    bl_label = "Add"
    bl_description = "Add a new change base shape key entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        obj.mizore_change_base_shapekeys.add()
        obj.mizore_change_base_shapekeys_index = len(obj.mizore_change_base_shapekeys) - 1
        return {'FINISHED'}


class OBJECT_OT_mizore_change_base_shapekey_remove(bpy.types.Operator):
    bl_idname = "object.mizore_change_base_shapekey_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and len(obj.mizore_change_base_shapekeys) > 0

    def execute(self, context):
        obj = context.object
        idx = obj.mizore_change_base_shapekeys_index
        obj.mizore_change_base_shapekeys.remove(idx)
        obj.mizore_change_base_shapekeys_index = min(
            max(0, idx - 1), len(obj.mizore_change_base_shapekeys) - 1
        )
        return {'FINISHED'}


class OBJECT_OT_mizore_change_base_shapekey_move(bpy.types.Operator):
    bl_idname = "object.mizore_change_base_shapekey_move"
    bl_label = "Move"
    bl_description = "Move the selected entry"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=[('UP', "Up", ""), ('DOWN', "Down", "")],
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and len(obj.mizore_change_base_shapekeys) > 1

    def execute(self, context):
        obj = context.object
        idx = obj.mizore_change_base_shapekeys_index
        max_idx = len(obj.mizore_change_base_shapekeys) - 1

        if self.direction == 'UP' and idx > 0:
            obj.mizore_change_base_shapekeys.move(idx, idx - 1)
            obj.mizore_change_base_shapekeys_index -= 1
        elif self.direction == 'DOWN' and idx < max_idx:
            obj.mizore_change_base_shapekeys.move(idx, idx + 1)
            obj.mizore_change_base_shapekeys_index += 1

        return {'FINISHED'}


# --- 並び替えリスト操作 ---

class OBJECT_OT_mizore_reorder_shapekey_add(bpy.types.Operator):
    bl_idname = "object.mizore_reorder_shapekey_add"
    bl_label = "Add"
    bl_description = "Add a new reorder shape key entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        obj.mizore_reorder_shapekeys.add()
        obj.mizore_reorder_shapekeys_index = len(obj.mizore_reorder_shapekeys) - 1
        return {'FINISHED'}


class OBJECT_OT_mizore_reorder_shapekey_remove(bpy.types.Operator):
    bl_idname = "object.mizore_reorder_shapekey_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and len(obj.mizore_reorder_shapekeys) > 0

    def execute(self, context):
        obj = context.object
        idx = obj.mizore_reorder_shapekeys_index
        obj.mizore_reorder_shapekeys.remove(idx)
        obj.mizore_reorder_shapekeys_index = min(
            max(0, idx - 1), len(obj.mizore_reorder_shapekeys) - 1
        )
        return {'FINISHED'}


class OBJECT_OT_mizore_reorder_shapekey_move(bpy.types.Operator):
    bl_idname = "object.mizore_reorder_shapekey_move"
    bl_label = "Move"
    bl_description = "Move the selected entry"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=[('UP', "Up", ""), ('DOWN', "Down", "")],
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and len(obj.mizore_reorder_shapekeys) > 1

    def execute(self, context):
        obj = context.object
        idx = obj.mizore_reorder_shapekeys_index
        max_idx = len(obj.mizore_reorder_shapekeys) - 1

        if self.direction == 'UP' and idx > 0:
            obj.mizore_reorder_shapekeys.move(idx, idx - 1)
            obj.mizore_reorder_shapekeys_index -= 1
        elif self.direction == 'DOWN' and idx < max_idx:
            obj.mizore_reorder_shapekeys.move(idx, idx + 1)
            obj.mizore_reorder_shapekeys_index += 1

        return {'FINISHED'}


classes = [
    OBJECT_OT_mizore_change_base_shapekey_add,
    OBJECT_OT_mizore_change_base_shapekey_remove,
    OBJECT_OT_mizore_change_base_shapekey_move,
    OBJECT_OT_mizore_reorder_shapekey_add,
    OBJECT_OT_mizore_reorder_shapekey_remove,
    OBJECT_OT_mizore_reorder_shapekey_move,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
