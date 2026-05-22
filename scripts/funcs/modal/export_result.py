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
エクスポート結果データ構造

エクスポート完了時のサマリ情報を格納します。
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class ExportedFileInfo:
    """エクスポートされたファイルの情報"""
    filepath: str
    size_bytes: int = 0

    @property
    def filename(self) -> str:
        return os.path.basename(self.filepath)

    @property
    def size_formatted(self) -> str:
        """ファイルサイズを人間が読みやすい形式で返す"""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


@dataclass
class ExportResult:
    """エクスポート結果のサマリ情報"""
    # 処理時間（秒）
    elapsed_time: float = 0.0

    # エクスポートされたファイル一覧
    exported_files: List[ExportedFileInfo] = field(default_factory=list)

    # 処理されたオブジェクト数
    processed_objects_count: int = 0

    # 警告メッセージ一覧
    warnings: List[str] = field(default_factory=list)

    # エラーメッセージ一覧
    errors: List[str] = field(default_factory=list)

    # 処理フェーズ情報（デバッグ用）
    phases_completed: List[str] = field(default_factory=list)

    def add_exported_file(self, filepath: str):
        """エクスポートされたファイルを追加"""
        size = 0
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
        self.exported_files.append(ExportedFileInfo(filepath=filepath, size_bytes=size))

    def add_warning(self, message: str):
        """警告を追加"""
        self.warnings.append(message)

    def add_error(self, message: str):
        """エラーを追加"""
        self.errors.append(message)

    @property
    def file_count(self) -> int:
        """エクスポートされたファイル数"""
        return len(self.exported_files)

    @property
    def total_size_bytes(self) -> int:
        """合計ファイルサイズ（バイト）"""
        return sum(f.size_bytes for f in self.exported_files)

    @property
    def total_size_formatted(self) -> str:
        """合計ファイルサイズを人間が読みやすい形式で返す"""
        size = self.total_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def elapsed_time_formatted(self) -> str:
        """処理時間を人間が読みやすい形式で返す"""
        if self.elapsed_time < 1:
            return f"{self.elapsed_time * 1000:.0f} ms"
        elif self.elapsed_time < 60:
            return f"{self.elapsed_time:.1f} sec"
        else:
            minutes = int(self.elapsed_time // 60)
            seconds = self.elapsed_time % 60
            return f"{minutes} min {seconds:.0f} sec"

    @property
    def warning_count(self) -> int:
        """警告の数"""
        return len(self.warnings)

    @property
    def error_count(self) -> int:
        """エラーの数"""
        return len(self.errors)

    @property
    def has_issues(self) -> bool:
        """警告またはエラーがあるか"""
        return self.warning_count > 0 or self.error_count > 0
