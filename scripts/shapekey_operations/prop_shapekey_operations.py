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
エクスポート時のシェイプキー操作設定用PropertyGroup

オブジェクト単位でベース変更・並び替え設定を保持する。
"""

import bpy
from bpy.props import (
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)


class ChangeBaseShapekeyItem(bpy.types.PropertyGroup):
    """ベースシェイプキー変更設定の1項目"""
    source_shapekey_name: StringProperty(
        name="Source Shape Key",
        description="Shape key to apply as the new Basis",
        default="",
    )
    reverse_shapekey_name: StringProperty(
        name="Reverse Shape Key Name",
        description="Name for the reverse shape key (stores original Basis shape)",
        default="",
    )


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
    )
    target_shapekey_name: StringProperty(
        name="Target",
        description="Target shape key name",
        default="",
    )
    destination_index: IntProperty(
        name="Index",
        description="Destination index for MOVE_TO_INDEX",
        default=1,
        min=0,
    )
    second_shapekey_name: StringProperty(
        name="Second",
        description="Second shape key name (for SWAP / MOVE_BEFORE)",
        default="",
    )


classes = [
    ChangeBaseShapekeyItem,
    ReorderShapekeyItem,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.mizore_change_base_shapekeys = CollectionProperty(
        type=ChangeBaseShapekeyItem,
    )
    bpy.types.Object.mizore_change_base_shapekeys_index = IntProperty()

    bpy.types.Object.mizore_reorder_shapekeys = CollectionProperty(
        type=ReorderShapekeyItem,
    )
    bpy.types.Object.mizore_reorder_shapekeys_index = IntProperty()


def unregister():
    if hasattr(bpy.types.Object, 'mizore_reorder_shapekeys_index'):
        del bpy.types.Object.mizore_reorder_shapekeys_index
    if hasattr(bpy.types.Object, 'mizore_reorder_shapekeys'):
        del bpy.types.Object.mizore_reorder_shapekeys
    if hasattr(bpy.types.Object, 'mizore_change_base_shapekeys_index'):
        del bpy.types.Object.mizore_change_base_shapekeys_index
    if hasattr(bpy.types.Object, 'mizore_change_base_shapekeys'):
        del bpy.types.Object.mizore_change_base_shapekeys

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
