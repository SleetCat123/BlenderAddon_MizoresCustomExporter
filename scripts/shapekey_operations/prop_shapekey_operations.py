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
エクスポート時のシェイプキー並び替え設定用PropertyGroup

永続データはObjectのCustom Property(JSON)に保存し、
UI編集用の一時状態はWindowManagerのCollectionPropertyで保持する。
"""

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty

from . import reorder_storage_utils


def _save_reorder_from_context(context):
    obj = getattr(context, "object", None)
    if obj is None or obj.type != 'MESH':
        return
    reorder_storage_utils.save_reorder_ui_state(obj, context.window_manager)


def _on_reorder_updated(self, context):
    _save_reorder_from_context(context)


class ReorderShapekeyItem(bpy.types.PropertyGroup):
    """シェイプキー並び替え操作の1項目"""
    operation_type: EnumProperty(
        name="Operation",
        items=[
            ('MOVE_TO_INDEX', "Move to Index", "Move shape key to specified index"),
            ('SORT_BY_NAME', "Sort by Name", "Sort all shape keys alphabetically"),
            ('SWAP', "Swap", "Swap two shape keys"),
            ('MOVE_BEFORE', "Move Before", "Move shape key before another"),
        ],
        default='SORT_BY_NAME',
        update=_on_reorder_updated,
    )
    target_shapekey_name: StringProperty(
        name="Target",
        description="Target shape key name",
        default="",
        update=_on_reorder_updated,
    )
    destination_index: IntProperty(
        name="Index",
        description="Destination index for MOVE_TO_INDEX",
        default=1,
        min=0,
        update=_on_reorder_updated,
    )
    second_shapekey_name: StringProperty(
        name="Second",
        description="Second shape key name (for SWAP / MOVE_BEFORE)",
        default="",
        update=_on_reorder_updated,
    )


classes = [
    ReorderShapekeyItem,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.mizore_reorder_shapekeys_ui = CollectionProperty(
        type=ReorderShapekeyItem,
    )
    bpy.types.WindowManager.mizore_reorder_shapekeys_ui_index = IntProperty()
    bpy.types.WindowManager.mizore_reorder_shapekeys_ui_object_name = StringProperty(
        default="",
    )
    bpy.types.WindowManager.mizore_reorder_shapekeys_ui_syncing = BoolProperty(
        default=False,
    )


def unregister():
    if hasattr(bpy.types.WindowManager, 'mizore_reorder_shapekeys_ui_syncing'):
        del bpy.types.WindowManager.mizore_reorder_shapekeys_ui_syncing
    if hasattr(bpy.types.WindowManager, 'mizore_reorder_shapekeys_ui_object_name'):
        del bpy.types.WindowManager.mizore_reorder_shapekeys_ui_object_name
    if hasattr(bpy.types.WindowManager, 'mizore_reorder_shapekeys_ui_index'):
        del bpy.types.WindowManager.mizore_reorder_shapekeys_ui_index
    if hasattr(bpy.types.WindowManager, 'mizore_reorder_shapekeys_ui'):
        del bpy.types.WindowManager.mizore_reorder_shapekeys_ui

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
