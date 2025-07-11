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
    同名の頂点グループが複数存在する異常な状態やVertex-Float AttributeとVertex Groupの名前衝突を修復します。
    各頂点のウェイトは最大値を採用してマージします。
    
    Args:
        obj: 処理対象のメッシュオブジェクト
        
    Returns:
        tuple: (修復したVertex Groupsグループ数, 削除したAttributeグループ数, VG影響頂点数, Attr影響頂点数)
    """
    if not obj or obj.type != 'MESH':
        print(f"Error: Object {obj.name if obj else 'None'} is not a mesh")
        return 0, 0, 0, 0
    
    # 元のモードを保存
    original_mode = obj.mode
    
    # オブジェクトモードに切り替え（念のため）
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # 頂点グループの重複をチェック
    vg_names = defaultdict(list)
    for vg in obj.vertex_groups:
        vg_names[vg.name].append(vg)
    
    # Vertex-Float Attributeを検出
    vertex_float_attributes = {}
    if hasattr(obj.data, 'attributes'):
        for attr in obj.data.attributes:
            if attr.domain == 'POINT' and attr.data_type == 'FLOAT':
                vertex_float_attributes[attr.name] = attr
    
    # 重複している頂点グループを検出
    collisions = {name: vgs for name, vgs in vg_names.items() if len(vgs) > 1}
    
    # AttributeとVertex Groupの名前衝突を検出
    attribute_vg_collisions = {}
    for attr_name, attr in vertex_float_attributes.items():
        if attr_name in [vg.name for vg in obj.vertex_groups]:
            attribute_vg_collisions[attr_name] = attr
    
    if not collisions and not attribute_vg_collisions:
        print(f"No Name Collisions detected in {obj.name}")
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=original_mode)
        return 0, 0, 0, 0
    
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
    
    # AttributeとVertex Groupの衝突を処理
    attr_removed_count = 0
    attr_affected_vertices = 0
    
    for attr_name, attr in attribute_vg_collisions.items():
        print(f"Fix Attribute-VertexGroup Collision in {obj.name}: {attr_name}")
        
        # 対応するVertex Groupを取得
        target_vg = None
        for vg in obj.vertex_groups:
            if vg.name == attr_name:
                target_vg = vg
                break
        
        if target_vg is None:
            continue
        
        # 各頂点について、AttributeとVertex Groupのウェイトを比較
        for vert_idx, vert in enumerate(bm.verts):
            attr_value = attr.data[vert_idx].value if vert_idx < len(attr.data) else 0.0
            vg_weight = 0.0
            
            # Vertex Groupの現在のウェイトを取得
            if target_vg.index in vert[deform_layer]:
                vg_weight = vert[deform_layer][target_vg.index]
            
            # 最大値を採用
            max_weight = max(attr_value, vg_weight)
            
            # Vertex Groupに最大値を設定
            if max_weight > 0.0:
                vert[deform_layer][target_vg.index] = max_weight
                if attr_value > 0.0 or vg_weight > 0.0:
                    attr_affected_vertices += 1
            elif target_vg.index in vert[deform_layer]:
                # ウェイトが0の場合は削除
                del vert[deform_layer][target_vg.index]
        
        attr_removed_count += 1
    
    # BMeshを更新
    bmesh.update_edit_mesh(obj.data)
    
    # オブジェクトモードに戻って頂点グループを削除
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 重複グループを削除
    for name, duplicate_vgs in collisions.items():
        remove_vgs = duplicate_vgs[1:]
        for vg in remove_vgs:
            obj.vertex_groups.remove(vg)
    
    # AttributeとVertex Groupの衝突で統合されたAttributeを削除
    for attr_name in attribute_vg_collisions.keys():
        try:
            # 名前ベースでAttributeを検索して削除
            if attr_name in obj.data.attributes:
                obj.data.attributes.remove(obj.data.attributes[attr_name])
                print(f"Removed Attribute: {attr_name}")
            else:
                print(f"Attribute {attr_name} not found for removal")
        except Exception as e:
            print(f"Failed to remove Attribute {attr_name}: {e}")
    
    # 元のモードに戻す
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=original_mode)
    
    # レポートメッセージの構築
    report_parts = []
    if fixed_count > 0:
        report_parts.append(f"{fixed_count} Vertex Groups removed")
    if attr_removed_count > 0:
        report_parts.append(f"{attr_removed_count} Attributes removed")
    
    vertex_info_parts = []
    if affected_vertices > 0:
        vertex_info_parts.append(f"{affected_vertices} vertices (VG)")
    if attr_affected_vertices > 0:
        vertex_info_parts.append(f"{attr_affected_vertices} vertices (Attr)")
    
    if report_parts:
        message = f"Name Collision fix completed for {obj.name}: {', '.join(report_parts)}"
        if vertex_info_parts:
            message += f", {', '.join(vertex_info_parts)} updated"
        print(message)
    else:
        print(f"Name Collision fix completed for {obj.name} (no processing needed)")
    
    return fixed_count, attr_removed_count, affected_vertices, attr_affected_vertices