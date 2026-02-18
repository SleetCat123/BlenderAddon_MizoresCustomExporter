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
シェイプキー操作設定UIパネル

サイドバー "Assign (Mizore)" カテゴリ内にベース変更・並び替えパネルを表示する。
"""

import bpy

from .op_shapekey_operations import (
    OBJECT_OT_mizore_change_base_shapekey_add,
    OBJECT_OT_mizore_change_base_shapekey_move,
    OBJECT_OT_mizore_change_base_shapekey_remove,
    OBJECT_OT_mizore_reorder_shapekey_add,
    OBJECT_OT_mizore_reorder_shapekey_move,
    OBJECT_OT_mizore_reorder_shapekey_remove,
)

# --- UIList ---

class MIZORE_UL_change_base_shapekey_list(bpy.types.UIList):
    """ベース変更設定のUIList"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_property):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "source_shapekey_name", text="", icon='SHAPEKEY_DATA')
            row.label(text="", icon='FORWARD')
            row.prop(item, "reverse_shapekey_name", text="", icon='LOOP_BACK')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.source_shapekey_name, icon='SHAPEKEY_DATA')


class MIZORE_UL_reorder_shapekey_list(bpy.types.UIList):
    """並び替え設定のUIList"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_property):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "operation_type", text="")
            if item.operation_type == 'SORT_BY_NAME':
                row.label(text="(All)")
            elif item.operation_type == 'MOVE_TO_INDEX':
                row.prop(item, "target_shapekey_name", text="")
                row.prop(item, "destination_index", text="")
            elif item.operation_type == 'SWAP':
                row.prop(item, "target_shapekey_name", text="")
                row.label(text="", icon='UV_SYNC_SELECT')
                row.prop(item, "second_shapekey_name", text="")
            elif item.operation_type == 'MOVE_BEFORE':
                row.prop(item, "target_shapekey_name", text="")
                row.label(text="", icon='FORWARD')
                row.prop(item, "second_shapekey_name", text="")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.operation_type, icon='SORTALPHA')


# --- パネル ---

class OBJECT_PT_mizore_change_base_shapekey(bpy.types.Panel):
    """ベースシェイプキー変更設定パネル"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Assign (Mizore)"
    bl_label = "Change Base ShapeKey (Export)"
    bl_order = 1100
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.data.shape_keys is not None
            and len(obj.data.shape_keys.key_blocks) > 1
        )

    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row()
        row.template_list(
            "MIZORE_UL_change_base_shapekey_list", "",
            obj, "mizore_change_base_shapekeys",
            obj, "mizore_change_base_shapekeys_index",
            rows=3,
        )

        col = row.column(align=True)
        col.operator(OBJECT_OT_mizore_change_base_shapekey_add.bl_idname, icon='ADD', text="")
        col.operator(OBJECT_OT_mizore_change_base_shapekey_remove.bl_idname, icon='REMOVE', text="")
        col.separator()
        op = col.operator(OBJECT_OT_mizore_change_base_shapekey_move.bl_idname, icon='TRIA_UP', text="")
        op.direction = 'UP'
        op = col.operator(OBJECT_OT_mizore_change_base_shapekey_move.bl_idname, icon='TRIA_DOWN', text="")
        op.direction = 'DOWN'

        # 選択中アイテムの詳細
        if obj.mizore_change_base_shapekeys and obj.mizore_change_base_shapekeys_index < len(obj.mizore_change_base_shapekeys):
            item = obj.mizore_change_base_shapekeys[obj.mizore_change_base_shapekeys_index]
            box = layout.box()
            box.prop_search(
                item, "source_shapekey_name",
                obj.data.shape_keys, "key_blocks",
                text="Source",
            )
            box.prop(item, "reverse_shapekey_name", text="Reverse Name")


class OBJECT_PT_mizore_reorder_shapekeys(bpy.types.Panel):
    """シェイプキー並び替え設定パネル"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Assign (Mizore)"
    bl_label = "Reorder ShapeKeys (Export)"
    bl_order = 1200
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.data.shape_keys is not None
            and len(obj.data.shape_keys.key_blocks) > 1
        )

    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row()
        row.template_list(
            "MIZORE_UL_reorder_shapekey_list", "",
            obj, "mizore_reorder_shapekeys",
            obj, "mizore_reorder_shapekeys_index",
            rows=3,
        )

        col = row.column(align=True)
        col.operator(OBJECT_OT_mizore_reorder_shapekey_add.bl_idname, icon='ADD', text="")
        col.operator(OBJECT_OT_mizore_reorder_shapekey_remove.bl_idname, icon='REMOVE', text="")
        col.separator()
        op = col.operator(OBJECT_OT_mizore_reorder_shapekey_move.bl_idname, icon='TRIA_UP', text="")
        op.direction = 'UP'
        op = col.operator(OBJECT_OT_mizore_reorder_shapekey_move.bl_idname, icon='TRIA_DOWN', text="")
        op.direction = 'DOWN'

        # 選択中アイテムの詳細
        if obj.mizore_reorder_shapekeys and obj.mizore_reorder_shapekeys_index < len(obj.mizore_reorder_shapekeys):
            item = obj.mizore_reorder_shapekeys[obj.mizore_reorder_shapekeys_index]
            box = layout.box()
            box.prop(item, "operation_type")
            if item.operation_type in ('MOVE_TO_INDEX', 'SWAP', 'MOVE_BEFORE'):
                box.prop_search(
                    item, "target_shapekey_name",
                    obj.data.shape_keys, "key_blocks",
                    text="Target",
                )
            if item.operation_type == 'MOVE_TO_INDEX':
                box.prop(item, "destination_index")
            if item.operation_type in ('SWAP', 'MOVE_BEFORE'):
                box.prop_search(
                    item, "second_shapekey_name",
                    obj.data.shape_keys, "key_blocks",
                    text="Second" if item.operation_type == 'SWAP' else "Before",
                )


classes = [
    MIZORE_UL_change_base_shapekey_list,
    MIZORE_UL_reorder_shapekey_list,
    OBJECT_PT_mizore_change_base_shapekey,
    OBJECT_PT_mizore_reorder_shapekeys,
]


translations_dict = {
    "ja_JP": {
        ("*", "Change Base ShapeKey (Export)"): "ベースシェイプキー変更 (エクスポート用)",
        ("*", "Reorder ShapeKeys (Export)"): "シェイプキー並び替え (エクスポート用)",
        ("*", "Add a new change base shape key entry"): "ベースシェイプキー変更設定を追加",
        ("*", "Add a new reorder shape key entry"): "並び替え設定を追加",
        ("*", "Remove the selected entry"): "選択中の設定を削除",
        ("*", "Move the selected entry"): "選択中の設定を移動",
        ("*", "Source Shape Key"): "ソースシェイプキー",
        ("*", "Shape key to apply as the new Basis"): "新しいBasisとして適用するシェイプキー",
        ("*", "Reverse Shape Key Name"): "逆シェイプキー名",
        ("*", "Name for the reverse shape key (stores original Basis shape)"): "逆シェイプキーの名前（元のBasis形状を保存）",
        ("*", "Target shape key name"): "操作対象のシェイプキー名",
        ("*", "Destination index for MOVE_TO_INDEX"): "移動先インデックス",
        ("*", "Second shape key name (for SWAP / MOVE_BEFORE)"): "2つ目のシェイプキー名（SWAP / MOVE_BEFORE用）",
        ("*", "Move to Index"): "インデックス指定移動",
        ("*", "Sort by Name"): "名前でソート",
        ("*", "Move shape key to specified index"): "シェイプキーを指定インデックスに移動",
        ("*", "Sort all shape keys alphabetically"): "全シェイプキーを名前順にソート",
        ("*", "Swap two shape keys"): "2つのシェイプキーを入れ替え",
        ("*", "Move shape key before another"): "シェイプキーを指定の前に移動",
        ("*", "Move Before"): "指定の前に移動",
    },
}


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.translations.register(__name__, translations_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
