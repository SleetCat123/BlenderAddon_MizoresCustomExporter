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
import re
from .utils import func_object_utils

def invert_lr(name):
    sep = "[/._-]"
    if re.search(f"(({sep}|^)l({sep}|$))|left", name, flags=re.IGNORECASE):
        name = re.sub(f'(?<={sep})l(?:(?={sep})|$)', 'r', name)
        name = re.sub(f'(?<={sep})L(?:(?={sep})|$)', 'R', name)
        name = re.sub(f'(?:(?<={sep})|^)left(?![a-z])', 'right', name)
        name = re.sub(f'(?:(?<={sep})|^)Left(?![a-z])', 'Right', name)
        name = re.sub(f'(?:(?<={sep})|^)LEFT(?![a-z])', 'RIGHT', name)
    elif re.search(f"(({sep}|^)r({sep}|$))|right", name, flags=re.IGNORECASE):
        name = re.sub(f'(?<={sep})r(?:(?={sep})|$)', 'l', name)
        name = re.sub(f'(?<={sep})R(?:(?={sep})|$)', 'L', name)
        name = re.sub(f'(?:(?<={sep})|^)right(?![a-z])', 'left', name)
        name = re.sub(f'(?:(?<={sep})|^)Right(?![a-z])', 'Left', name)
        name = re.sub(f'(?:(?<={sep})|^)RIGHT(?![a-z])', 'LEFT', name)
    return name


def remove_unused_groups(
        search_data_transfer_modifier=True,
        ):
    print("--- Remove Unused Groups ---")
    bpy.ops.object.mode_set(mode='OBJECT')
    obj = func_object_utils.get_active_object()
    print("Active Object: " + str(obj))
    if obj.type != 'MESH':
        raise Exception("This object is not a mesh")
    using_groups = []
    mirror_groups = False
    # モディファイアを検索し、使用されている頂点グループをリストに追加
    for m in obj.modifiers:
        if not mirror_groups and m.type == 'MIRROR' and m.use_mirror_vertex_groups:
            mirror_groups = True
            print("This object has Mirror Groups")
        if search_data_transfer_modifier and m.type == 'DATA_TRANSFER' and m.object and m.use_vert_data and 'VGROUP_WEIGHTS' in m.data_types_verts:
            # 頂点グループが転送されているなら、転送元オブジェクトの頂点グループもチェックする
            print("Vertex groups transferred from " + m.object.name)
            t_mirror_groups = False
            for transfer_m in m.object.modifiers:
                if not t_mirror_groups and transfer_m.type == 'MIRROR' and transfer_m.use_mirror_vertex_groups:
                    t_mirror_groups = True
                    print("This object has Mirror Groups")
            # 転送元オブジェクトの頂点グループを検索し、使用されている頂点グループをリストに追加
            for v in m.object.data.vertices:
                for g in v.groups:
                    group_name = m.object.vertex_groups[g.group].name
                    if group_name not in using_groups:
                        using_groups.append(group_name)
                        print(f"Vertex Group [{group_name}] may have been transferred from: {m.name}({m.type})")
                        if t_mirror_groups:
                            # 頂点グループ名のLRを反転させる
                            mirrored_name = invert_lr(group_name)
                            if mirrored_name not in using_groups:
                                print("Mirrored: " + mirrored_name)
                                using_groups.append(mirrored_name)
                                print(f"Vertex Group [{mirrored_name}] may have been transferred from: {m.name}({m.type})")
        if hasattr(m, 'vertex_group') and m.vertex_group:
            using_groups.append(m.vertex_group)
            print(f"Vertex Group [{m.vertex_group}] used by {m.name}({m.type})")

    # 頂点を検索し、使用されている頂点グループをリストに追加
    for v in obj.data.vertices:
        for g in v.groups:
            group_name = obj.vertex_groups[g.group].name
            if group_name not in using_groups:
                using_groups.append(group_name)
                if mirror_groups:
                    # 頂点グループ名のLRを反転させる
                    mirrored_name = invert_lr(group_name)
                    if mirrored_name not in using_groups:
                        print("Mirrored: " + mirrored_name)
                        using_groups.append(mirrored_name)

    print(using_groups)
    # 頂点グループを削除
    remove = []
    for group in obj.vertex_groups:
        if group.name not in using_groups:
            remove.append(group)
    for group in remove:
        print("Remove Group: " + group.name)
        obj.vertex_groups.remove(group)
    print( "--- Remove Unused Groups Finished ---")
        