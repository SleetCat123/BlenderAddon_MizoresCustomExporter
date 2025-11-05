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
import bmesh
import bpy

from .utils import func_object_utils


def convert_uv_tiles_to_single():
    obj = func_object_utils.get_active_object()
    if obj.type != 'MESH':
        raise Exception("This object is not a mesh")
    
    temp_mode = bpy.context.mode
    if temp_mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    # UVレイヤーを取得
    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.verify()
    # UV頂点を[0,0]-[1,1]の範囲に移動
    for face in bm.faces:
        is_positive_x = None
        is_positive_y = None
        for loop in face.loops:
            loop_uv = loop[uv_layer]
            uv_x = loop_uv.uv.x - int(loop_uv.uv.x)
            uv_y = loop_uv.uv.y - int(loop_uv.uv.y)
            # 負の数の場合は1を足す
            if uv_x < 0:
                uv_x += 1
            if uv_y < 0:
                uv_y += 1

            # 0のとき、loopsの他の頂点の半数以上が0.5以上なら1.0に、そうでなければ0.0に移動する
            if uv_x == 0:
                if is_positive_x is None:
                    # 余計な計算をしないために、必要なときだけ計算する
                    is_positive_x = sum(1 for l in face.loops if l[uv_layer].uv.x >= 0.5) > len(face.loops) / 2
                if is_positive_x:
                    uv_x = 1
            if uv_y == 0:
                if is_positive_y is None:
                    # 余計な計算をしないために、必要なときだけ計算する
                    is_positive_y = sum(1 for l in face.loops if l[uv_layer].uv.y >= 0.5) > len(face.loops) / 2
                if is_positive_y:
                    uv_y = 1
            loop_uv.uv.x = uv_x
            loop_uv.uv.y = uv_y

            # count_x = sum(1 for l in face.loops if l[uv_layer].uv.x >= 0.5)
            # count_y = sum(1 for l in face.loops if l[uv_layer].uv.y >= 0.5)
            # if count_x > len(face.loops) / 2:
            #     uv_x = 1.0
            # else:
            #     uv_x = 0.0
            # if count_y > len(face.loops) / 2:
            #     uv_y = 1.0
            # else:
            #     uv_y = 0.0

    bmesh.update_edit_mesh(obj.data)
    if temp_mode != 'EDIT':
        bpy.ops.object.mode_set(mode=temp_mode)

