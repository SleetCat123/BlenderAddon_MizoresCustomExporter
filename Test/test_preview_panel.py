"""
エクスポート対象オブジェクトプレビュー表示のテストコード

Blenderのファイルブラウザ（FILE_BROWSER）内のTOOL_PROPSリージョンで
UIList（template_list）が使用可能かどうかを検証します。

テスト方法:
1. Blenderを起動
2. このスクリプトをText Editorで開いて実行
3. File > Export > Mizore's Custom Exporter を開く
4. "Export Preview" パネルが表示されるか確認
"""

import bpy
from bpy.props import IntProperty, CollectionProperty, StringProperty
from bpy.types import PropertyGroup


# テスト用のアイテムプロパティグループ
class MIZORE_ExportPreviewItem(PropertyGroup):
    """エクスポート対象オブジェクトのアイテム"""
    name: StringProperty(name="Name")
    obj_type: StringProperty(name="Type")
    icon: StringProperty(name="Icon", default='OBJECT_DATA')


# UIListクラス
class MIZORE_UL_export_preview_list(bpy.types.UIList):
    """エクスポート対象オブジェクトのリスト表示"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            # オブジェクトタイプに応じたアイコン
            icon_map = {
                'MESH': 'MESH_DATA',
                'ARMATURE': 'ARMATURE_DATA',
                'EMPTY': 'EMPTY_DATA',
                'CURVE': 'CURVE_DATA',
                'CAMERA': 'CAMERA_DATA',
                'LIGHT': 'LIGHT_DATA',
            }
            icon_name = icon_map.get(item.obj_type, 'OBJECT_DATA')
            row.label(text=item.name, icon=icon_name)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OBJECT_DATA')


# ファイルブラウザ内のプレビューパネル
class MIZORE_FBX_PT_export_preview(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Export Preview"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        # オブジェクトリストを更新
        self.update_preview_list(context)

        # 方式1: 単純なラベル一覧
        box = layout.box()
        box.label(text="Method 1: Labels", icon='INFO')
        col = box.column(align=True)
        for obj in bpy.context.selected_objects[:10]:
            row = col.row(align=True)
            icon = 'MESH_DATA' if obj.type == 'MESH' else 'OBJECT_DATA'
            row.label(text=obj.name, icon=icon)
        if len(bpy.context.selected_objects) > 10:
            col.label(text=f"... and {len(bpy.context.selected_objects) - 10} more")

        # 方式2: template_listの使用テスト
        box = layout.box()
        box.label(text="Method 2: template_list", icon='INFO')
        try:
            if hasattr(wm, 'mizore_export_preview_items'):
                box.template_list(
                    "MIZORE_UL_export_preview_list",
                    "",
                    wm,
                    "mizore_export_preview_items",
                    wm,
                    "mizore_export_preview_index",
                    rows=5,
                    maxrows=10
                )
            else:
                box.label(text="Preview list not initialized", icon='ERROR')
        except Exception as e:
            box.label(text=f"Error: {str(e)}", icon='ERROR')

        # 方式3: template_icon_viewの使用テスト（サムネイル表示）
        box = layout.box()
        box.label(text="Method 3: Grid view", icon='INFO')
        try:
            if hasattr(wm, 'mizore_export_preview_items'):
                box.template_list(
                    "MIZORE_UL_export_preview_list",
                    "grid",
                    wm,
                    "mizore_export_preview_items",
                    wm,
                    "mizore_export_preview_index",
                    type='GRID',
                    columns=4,
                    rows=2
                )
        except Exception as e:
            box.label(text=f"Error: {str(e)}", icon='ERROR')

        # サマリ表示
        layout.separator()
        row = layout.row()
        row.label(text=f"Selected: {len(bpy.context.selected_objects)} objects")

    def update_preview_list(self, context):
        """選択オブジェクトでプレビューリストを更新"""
        wm = context.window_manager
        if not hasattr(wm, 'mizore_export_preview_items'):
            return

        # 現在のリストをクリア
        wm.mizore_export_preview_items.clear()

        # 選択オブジェクトを追加（最大50件）
        for obj in bpy.context.selected_objects[:50]:
            item = wm.mizore_export_preview_items.add()
            item.name = obj.name
            item.obj_type = obj.type


# 登録用クラスリスト
classes = [
    MIZORE_ExportPreviewItem,
    MIZORE_UL_export_preview_list,
    MIZORE_FBX_PT_export_preview,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # WindowManagerにプロパティを追加
    bpy.types.WindowManager.mizore_export_preview_items = CollectionProperty(
        type=MIZORE_ExportPreviewItem
    )
    bpy.types.WindowManager.mizore_export_preview_index = IntProperty(
        name="Active Index",
        default=0
    )
    print("Export Preview Panel: Registered")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.mizore_export_preview_items
    del bpy.types.WindowManager.mizore_export_preview_index
    print("Export Preview Panel: Unregistered")


if __name__ == "__main__":
    # 既に登録されている場合は解除してから再登録
    try:
        unregister()
    except:
        pass
    register()
