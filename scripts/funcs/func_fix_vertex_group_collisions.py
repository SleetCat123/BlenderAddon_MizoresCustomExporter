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

import bpy
import bmesh
from collections import defaultdict


def fix_vertex_group_name_collisions(obj):
    """
    同名の頂点グループが複数存在する異常な状態を修復します。
    各頂点のウェイトは最大値を採用してマージします。
    
    Args:
        obj: 処理対象のメッシュオブジェクト
        
    Returns:
        tuple: (修復したグループ数, 影響を受けた頂点数)
    """
    if not obj or obj.type != 'MESH':
        print(f"Error: Object {obj.name if obj else 'None'} is not a mesh")
        return 0, 0
    
    # 元のモードを保存
    original_mode = obj.mode
    
    # オブジェクトモードに切り替え（念のため）
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # 頂点グループの重複をチェック
    vg_names = defaultdict(list)
    for vg in obj.vertex_groups:
        vg_names[vg.name].append(vg)
    
    # 重複している頂点グループを検出
    collisions = {name: vgs for name, vgs in vg_names.items() if len(vgs) > 1}
    
    if not collisions:
        print(f"No Name Collisions detected in {obj.name}")
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=original_mode)
        return 0, 0
    
    # Editモードに切り替えてBMeshを使用
    bpy.ops.object.mode_set(mode='EDIT')
    
    # BMeshを作成
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.layers.deform.verify()
    deform_layer = bm.verts.layers.deform.active
    
    fixed_count = 0
    affected_vertices = 0
    
    # 各重複グループを処理
    for name, duplicate_vgs in collisions.items():
        print(f"Fix Name Collision in {obj.name}: {name} ({len(duplicate_vgs)} groups)")
        
        # 最初のグループを保持、残りを削除
        keep_vg = duplicate_vgs[0]
        remove_vgs = duplicate_vgs[1:]
        
        # 削除対象グループのインデックスを取得
        remove_indices = [vg.index for vg in remove_vgs]
        
        # 各頂点について、削除対象グループのウェイトを確認し、最大値を保持グループに設定
        for vert in bm.verts:
            max_weight = 0.0
            has_weight = False
            
            # 保持グループの現在のウェイトを取得
            if keep_vg.index in vert[deform_layer]:
                max_weight = vert[deform_layer][keep_vg.index]
                has_weight = True
            
            # 削除対象グループのウェイトをチェック
            for remove_index in remove_indices:
                if remove_index in vert[deform_layer]:
                    weight = vert[deform_layer][remove_index]
                    if weight > max_weight:
                        max_weight = weight
                    has_weight = True
                    # 削除対象グループからウェイトを削除
                    del vert[deform_layer][remove_index]
            
            # 最大ウェイトを保持グループに設定
            if has_weight:
                if max_weight > 0.0:
                    vert[deform_layer][keep_vg.index] = max_weight
                    affected_vertices += 1
                elif keep_vg.index in vert[deform_layer]:
                    # ウェイトが0の場合は削除
                    del vert[deform_layer][keep_vg.index]
        
        fixed_count += len(remove_vgs)
    
    # BMeshを更新
    bmesh.update_edit_mesh(obj.data)
    
    # オブジェクトモードに戻って頂点グループを削除
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 重複グループを削除
    for name, duplicate_vgs in collisions.items():
        remove_vgs = duplicate_vgs[1:]
        for vg in remove_vgs:
            obj.vertex_groups.remove(vg)
    
    # 元のモードに戻す
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=original_mode)
    
    print(f"Name Collision fix completed for {obj.name}: {fixed_count} groups removed, {affected_vertices} vertices updated")
    return fixed_count, affected_vertices