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
RESET_POSE_GROUP_NAME = "ResetPoseWhenExport"  # エクスポート時にポーズをリセットするオブジェクトのグループ名
RESET_SHAPEKEY_GROUP_NAME = "ResetShapekeysWhenExport"  # エクスポート時にシェイプキーをリセットするオブジェクトのグループ名
MOVE_TO_ORIGIN_GROUP_NAME = "MoveToOriginWhenExport"  # エクスポート時に原点に移動するオブジェクトのグループ名
APPLY_LOCATIONS_GROUP_NAME = "ApplyLocationsWhenExport"  # エクスポート時に位置を適用するオブジェクトのグループ名
APPLY_ROTATIONS_GROUP_NAME = "ApplyRotationsWhenExport"  # エクスポート時に回転を適用するオブジェクトのグループ名
APPLY_SCALES_GROUP_NAME = "ApplyScalesWhenExport"  # エクスポート時にスケールを適用するオブジェクトのグループ名
ALWAYS_RESET_SHAPEKEY_GROUP_NAME = "AlwaysResetShapekeys"  # エクスポート時にシェイプキーをリセットするオブジェクトのグループ名（エクスポート対象外であっても常にリセット）

EXPORT_TEMP_SUFFIX = ".#MizoreCEx#"  # エクスポート処理時、一時的にオブジェクト名に付加する接尾辞
MAX_NAME_LENGTH = 63  # オブジェクト名などの最大文字数（Blender側の上限）
ACTUAL_MAX_NAME_LENGTH = MAX_NAME_LENGTH - len(EXPORT_TEMP_SUFFIX)  # オブジェクトなどの名前として実際に使用可能な最大文字数

DESC = ".desc"
