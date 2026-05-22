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
エクスポート完了ダイアログ

エクスポート結果のサマリをポップアップダイアログで表示します。
"""

import os
import subprocess
import sys

import bpy
from bpy.props import StringProperty

from ..funcs.modal.export_result import ExportResult


# グローバル変数でエクスポート結果を保持
_last_export_result: ExportResult = None


def set_last_export_result(result: ExportResult):
    """エクスポート結果を保存"""
    global _last_export_result
    _last_export_result = result


def get_last_export_result() -> ExportResult:
    """保存されたエクスポート結果を取得"""
    global _last_export_result
    return _last_export_result


class MIZORE_OT_open_export_folder(bpy.types.Operator):
    """エクスポート先フォルダを開く"""
    bl_idname = "mizore.open_export_folder"
    bl_label = "Open Export Folder"
    bl_description = "Open the folder containing exported files"

    folder_path: StringProperty()

    def execute(self, context):
        if not self.folder_path or not os.path.exists(self.folder_path):
            self.report({'WARNING'}, "Folder not found")
            return {'CANCELLED'}

        # OSに応じたファイルマネージャーで開く
        if sys.platform == 'win32':
            os.startfile(self.folder_path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', self.folder_path])
        else:
            subprocess.Popen(['xdg-open', self.folder_path])

        return {'FINISHED'}


class MIZORE_OT_export_result_dialog(bpy.types.Operator):
    """エクスポート結果ダイアログを表示"""
    bl_idname = "mizore.export_result_dialog"
    bl_label = "Export Complete"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        result = get_last_export_result()
        if result is None:
            return {'CANCELLED'}

        # ダイアログの幅を設定
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        result = get_last_export_result()
        if result is None:
            return

        layout = self.layout

        # サマリセクション
        box = layout.box()
        box.label(text="Export Summary", icon='CHECKMARK')

        # 処理時間
        row = box.row()
        row.label(text="Processing Time:")
        row.label(text=result.elapsed_time_formatted)

        # ファイル数
        row = box.row()
        row.label(text="Files Exported:")
        row.label(text=str(result.file_count))

        # 合計サイズ
        row = box.row()
        row.label(text="Total Size:")
        row.label(text=result.total_size_formatted)

        # 処理オブジェクト数
        row = box.row()
        row.label(text="Objects Processed:")
        row.label(text=str(result.processed_objects_count))

        # 警告がある場合
        if result.warning_count > 0:
            box = layout.box()
            box.label(text=f"Warnings ({result.warning_count})", icon='ERROR')
            for warning in result.warnings[:5]:  # 最大5件表示
                row = box.row()
                row.label(text=warning, icon='DOT')
            if result.warning_count > 5:
                box.label(text=f"... and {result.warning_count - 5} more")

        # エラーがある場合
        if result.error_count > 0:
            box = layout.box()
            box.label(text=f"Errors ({result.error_count})", icon='CANCEL')
            for error in result.errors[:5]:
                row = box.row()
                row.label(text=error, icon='DOT')
            if result.error_count > 5:
                box.label(text=f"... and {result.error_count - 5} more")

        # ファイル一覧セクション
        if result.file_count > 0:
            box = layout.box()
            box.label(text="Exported Files", icon='FILE')

            for file_info in result.exported_files[:10]:  # 最大10件表示
                row = box.row()
                row.label(text=file_info.filename, icon='FILE_BLANK')
                row.label(text=file_info.size_formatted)

            if result.file_count > 10:
                box.label(text=f"... and {result.file_count - 10} more files")

            # フォルダを開くボタン
            if result.exported_files:
                folder_path = os.path.dirname(result.exported_files[0].filepath)
                op = layout.operator(
                    MIZORE_OT_open_export_folder.bl_idname,
                    text="Open Export Folder",
                    icon='FILE_FOLDER'
                )
                op.folder_path = folder_path


# 翻訳辞書
translations_dict = {
    "ja_JP": {
        ("*", "Export Complete"): "エクスポート完了",
        ("*", "Export Summary"): "エクスポートサマリ",
        ("*", "Processing Time:"): "処理時間:",
        ("*", "Files Exported:"): "出力ファイル数:",
        ("*", "Total Size:"): "合計サイズ:",
        ("*", "Objects Processed:"): "処理オブジェクト数:",
        ("*", "Warnings"): "警告",
        ("*", "Errors"): "エラー",
        ("*", "Exported Files"): "出力ファイル",
        ("*", "Open Export Folder"): "出力フォルダを開く",
        ("*", "Open the folder containing exported files"): "エクスポートされたファイルのフォルダを開く",
        ("*", "Folder not found"): "フォルダが見つかりません",
    },
}


classes = [
    MIZORE_OT_open_export_folder,
    MIZORE_OT_export_result_dialog,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.translations.register(__name__, translations_dict)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.app.translations.unregister(__name__)
