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
シェイプキー並び替え設定リストの操作オペレーター

UIListの追加/削除/上下移動を提供する。
"""

import bpy
from bpy.props import EnumProperty, IntProperty

from . import candidate_utils, reorder_storage_utils


PICK_TARGET_ITEMS = [
    ('REORDER_TARGET', "Reorder Target", ""),
    ('REORDER_SECOND', "Reorder Second", ""),
]


def _get_ui_collection_and_index(wm, target_kind):
    if target_kind == 'REORDER_TARGET':
        return wm.mizore_reorder_shapekeys_ui, 'target_shapekey_name'
    if target_kind == 'REORDER_SECOND':
        return wm.mizore_reorder_shapekeys_ui, 'second_shapekey_name'
    raise ValueError(f"Unknown target kind: {target_kind}")


def _get_target_item(wm, target_kind, item_index):
    collection, _ = _get_ui_collection_and_index(wm, target_kind)
    return collection[item_index]


def _candidate_items(self, context):
    obj = context.object
    if obj is None or obj.type != 'MESH':
        return [('__NONE__', "(No candidates)", "")]

    candidates = candidate_utils.get_shapekey_candidates(obj)
    if candidates:
        return [(name, name, "") for name in candidates]
    return [('__NONE__', "(No candidates)", "")]


def _ensure_ui_ready(context):
    obj = context.object
    if obj is None or obj.type != 'MESH':
        return None, None
    wm = context.window_manager
    reorder_storage_utils.ensure_ui_state_for_object(obj, wm)
    return obj, wm


def _get_entry_count(context):
    obj = context.object
    if obj is None or obj.type != 'MESH':
        return 0
    return len(reorder_storage_utils.get_reorder_settings(obj))


class OBJECT_OT_mizore_pick_export_shapekey_candidate(bpy.types.Operator):
    bl_idname = "object.mizore_pick_export_shapekey_candidate"
    bl_label = "Pick Shape Key Candidate"
    bl_description = "Pick from current or predicted export shape key candidates"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "choice"

    target_kind: EnumProperty(items=PICK_TARGET_ITEMS)
    item_index: IntProperty()
    choice: EnumProperty(name="Shape Key", items=_candidate_items)

    def invoke(self, context, event):
        obj, wm = _ensure_ui_ready(context)
        if obj is None:
            return {'CANCELLED'}

        item = _get_target_item(wm, self.target_kind, self.item_index)
        _, prop_name = _get_ui_collection_and_index(wm, self.target_kind)
        current_value = getattr(item, prop_name)

        available = candidate_utils.get_shapekey_candidates(obj)
        if current_value in available:
            self.choice = current_value
        elif available:
            self.choice = available[0]
        else:
            self.choice = '__NONE__'

        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if self.choice == '__NONE__':
            self.report({'WARNING'}, "No shape key candidates available")
            return {'CANCELLED'}

        obj, wm = _ensure_ui_ready(context)
        if obj is None:
            return {'CANCELLED'}

        item = _get_target_item(wm, self.target_kind, self.item_index)
        _, prop_name = _get_ui_collection_and_index(wm, self.target_kind)
        setattr(item, prop_name, self.choice)
        reorder_storage_utils.save_reorder_ui_state(obj, wm)
        return {'FINISHED'}


class OBJECT_OT_mizore_clear_export_shapekey_candidate(bpy.types.Operator):
    bl_idname = "object.mizore_clear_export_shapekey_candidate"
    bl_label = "Clear Shape Key Candidate"
    bl_description = "Clear the selected shape key candidate"
    bl_options = {'REGISTER', 'UNDO'}

    target_kind: EnumProperty(items=PICK_TARGET_ITEMS)
    item_index: IntProperty()

    def execute(self, context):
        obj, wm = _ensure_ui_ready(context)
        if obj is None:
            return {'CANCELLED'}

        item = _get_target_item(wm, self.target_kind, self.item_index)
        _, prop_name = _get_ui_collection_and_index(wm, self.target_kind)
        setattr(item, prop_name, "")
        reorder_storage_utils.save_reorder_ui_state(obj, wm)
        return {'FINISHED'}


class OBJECT_OT_mizore_reorder_shapekey_add(bpy.types.Operator):
    bl_idname = "object.mizore_reorder_shapekey_add"
    bl_label = "Add"
    bl_description = "Add a new reorder shape key entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, wm = _ensure_ui_ready(context)
        if obj is None:
            return {'CANCELLED'}

        wm.mizore_reorder_shapekeys_ui.add()
        wm.mizore_reorder_shapekeys_ui_index = len(wm.mizore_reorder_shapekeys_ui) - 1
        reorder_storage_utils.save_reorder_ui_state(obj, wm)
        return {'FINISHED'}


class OBJECT_OT_mizore_reorder_shapekey_remove(bpy.types.Operator):
    bl_idname = "object.mizore_reorder_shapekey_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and _get_entry_count(context) > 0

    def execute(self, context):
        obj, wm = _ensure_ui_ready(context)
        if obj is None:
            return {'CANCELLED'}

        idx = wm.mizore_reorder_shapekeys_ui_index
        wm.mizore_reorder_shapekeys_ui.remove(idx)
        wm.mizore_reorder_shapekeys_ui_index = min(
            max(0, idx - 1), len(wm.mizore_reorder_shapekeys_ui) - 1
        )
        reorder_storage_utils.save_reorder_ui_state(obj, wm)
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
        return obj and obj.type == 'MESH' and _get_entry_count(context) > 1

    def execute(self, context):
        obj, wm = _ensure_ui_ready(context)
        if obj is None:
            return {'CANCELLED'}

        idx = wm.mizore_reorder_shapekeys_ui_index
        max_idx = len(wm.mizore_reorder_shapekeys_ui) - 1

        if self.direction == 'UP' and idx > 0:
            wm.mizore_reorder_shapekeys_ui.move(idx, idx - 1)
            wm.mizore_reorder_shapekeys_ui_index -= 1
        elif self.direction == 'DOWN' and idx < max_idx:
            wm.mizore_reorder_shapekeys_ui.move(idx, idx + 1)
            wm.mizore_reorder_shapekeys_ui_index += 1

        reorder_storage_utils.save_reorder_ui_state(obj, wm)
        return {'FINISHED'}


classes = [
    OBJECT_OT_mizore_pick_export_shapekey_candidate,
    OBJECT_OT_mizore_clear_export_shapekey_candidate,
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
