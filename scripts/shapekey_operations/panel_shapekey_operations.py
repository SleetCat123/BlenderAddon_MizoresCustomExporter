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

サイドバー "Assign (Mizore)" カテゴリ内に並び替えパネルを表示する。
"""

import bpy

from .op_shapekey_operations import (
    OBJECT_OT_mizore_clear_export_shapekey_candidate,
    OBJECT_OT_mizore_pick_export_shapekey_candidate,
    OBJECT_OT_mizore_reorder_shapekey_add,
    OBJECT_OT_mizore_reorder_shapekey_move,
    OBJECT_OT_mizore_reorder_shapekey_remove,
)
from . import candidate_utils, reorder_storage_utils


def _is_mesh_object(context):
    obj = context.object
    return obj is not None and obj.type == 'MESH'


def _draw_picker_row(layout, label, value, pick_target_kind, item_index):
    row = layout.row(align=True)
    row.label(text=label)
    row.label(text=value or "(Not selected)", icon='SHAPEKEY_DATA')

    op = row.operator(
        OBJECT_OT_mizore_pick_export_shapekey_candidate.bl_idname,
        text="Pick",
        icon='VIEWZOOM',
    )
    op.target_kind = pick_target_kind
    op.item_index = item_index

    clear_op = row.operator(
        OBJECT_OT_mizore_clear_export_shapekey_candidate.bl_idname,
        text="",
        icon='X',
    )
    clear_op.target_kind = pick_target_kind
    clear_op.item_index = item_index


def _draw_prediction_hint(layout, obj):
    if not candidate_utils.get_shapekey_candidates(obj):
        layout.label(text="No current or predicted shape key candidates found.", icon='INFO')
        return
    layout.label(text="Candidates include current keys and %AS% outputs.", icon='INFO')


class MIZORE_UL_reorder_shapekey_list(bpy.types.UIList):
    """並び替え設定のUIList"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_property):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "operation_type", text="")
            if item.operation_type == 'SORT_BY_NAME':
                row.label(text="(All)")
            elif item.operation_type == 'MOVE_TO_INDEX':
                row.label(text=item.target_shapekey_name or "(Not selected)")
                row.prop(item, "destination_index", text="")
            elif item.operation_type == 'SWAP':
                row.label(text=item.target_shapekey_name or "(Not selected)")
                row.label(text="", icon='UV_SYNC_SELECT')
                row.label(text=item.second_shapekey_name or "(Not selected)")
            elif item.operation_type == 'MOVE_BEFORE':
                row.label(text=item.target_shapekey_name or "(Not selected)")
                row.label(text="", icon='FORWARD')
                row.label(text=item.second_shapekey_name or "(Not selected)")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.operation_type, icon='SORTALPHA')


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
        return _is_mesh_object(context)

    def draw(self, context):
        layout = self.layout
        obj = context.object
        wm = context.window_manager
        reorder_storage_utils.ensure_ui_state_for_object(obj, wm)

        row = layout.row()
        row.template_list(
            "MIZORE_UL_reorder_shapekey_list", "",
            wm, "mizore_reorder_shapekeys_ui",
            wm, "mizore_reorder_shapekeys_ui_index",
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
        if wm.mizore_reorder_shapekeys_ui and wm.mizore_reorder_shapekeys_ui_index < len(wm.mizore_reorder_shapekeys_ui):
            item = wm.mizore_reorder_shapekeys_ui[wm.mizore_reorder_shapekeys_ui_index]
            box = layout.box()
            box.prop(item, "operation_type")
            if item.operation_type in ('MOVE_TO_INDEX', 'SWAP', 'MOVE_BEFORE'):
                _draw_picker_row(
                    box,
                    "Target",
                    item.target_shapekey_name,
                    'REORDER_TARGET',
                    wm.mizore_reorder_shapekeys_ui_index,
                )
            if item.operation_type == 'MOVE_TO_INDEX':
                box.prop(item, "destination_index")
            if item.operation_type in ('SWAP', 'MOVE_BEFORE'):
                _draw_picker_row(
                    box,
                    "Second" if item.operation_type == 'SWAP' else "Before",
                    item.second_shapekey_name,
                    'REORDER_SECOND',
                    wm.mizore_reorder_shapekeys_ui_index,
                )
            _draw_prediction_hint(box, obj)


classes = [
    MIZORE_UL_reorder_shapekey_list,
    OBJECT_PT_mizore_reorder_shapekeys,
]


translations_dict = {
    "ja_JP": {
        ("*", "Reorder ShapeKeys (Export)"): "シェイプキー並び替え (エクスポート用)",
        ("*", "Add a new reorder shape key entry"): "並び替え設定を追加",
        ("*", "Remove the selected entry"): "選択中の設定を削除",
        ("*", "Move the selected entry"): "選択中の設定を移動",
        ("*", "Target shape key name"): "操作対象のシェイプキー名",
        ("*", "Destination index for MOVE_TO_INDEX"): "移動先インデックス",
        ("*", "Second shape key name (for SWAP / MOVE_BEFORE)"): "2つ目のシェイプキー名（SWAP / MOVE_BEFORE用）",
        ("*", "Move to Index"): "インデックス指定移動",
        ("*", "Sort by Name"): "名前でソート",
        ("*", "Pick Shape Key Candidate"): "シェイプキー候補を選択",
        ("*", "Pick from current or predicted export shape key candidates"):
            "現在またはエクスポート時に生成予定のシェイプキー候補から選択",
        ("*", "Move shape key to specified index"): "シェイプキーを指定インデックスに移動",
        ("*", "Sort all shape keys alphabetically"): "全シェイプキーを名前順にソート",
        ("*", "Swap two shape keys"): "2つのシェイプキーを入れ替え",
        ("*", "Move shape key before another"): "シェイプキーを指定の前に移動",
        ("*", "Move Before"): "指定の前に移動",
        ("*", "Pick"): "選択",
        ("*", "(Not selected)"): "未選択",
        ("*", "(Auto)"): "自動",
        ("*", "No current or predicted shape key candidates found."):
            "現在またはエクスポート後に存在するシェイプキー候補が見つかりません",
        ("*", "Candidates include current keys and %AS% outputs."):
            "候補には現在のシェイプキーと %AS% 出力が含まれます",
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
