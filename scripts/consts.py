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


DONT_EXPORT_GROUP_NAME = "DontExport"  # エクスポートから除外するオブジェクトのグループ名
ALWAYS_EXPORT_GROUP_NAME = "AlwaysExport"  # 非表示状態であっても常にエクスポートさせるオブジェクトのグループ名

EXPORT_TEMP_SUFFIX = ".#MizoreCEx#"  # エクスポート処理時、一時的にオブジェクト名に付加する接尾辞
MAX_NAME_LENGTH = 63  # オブジェクト名などの最大文字数（Blender側の上限）
ACTUAL_MAX_NAME_LENGTH = MAX_NAME_LENGTH - len(EXPORT_TEMP_SUFFIX)  # オブジェクトなどの名前として実際に使用可能な最大文字数

DESC = ".desc"
