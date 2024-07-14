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

def remove_groups_not_bones():
    print("--- Remove Groups Other Than Bone Names ---")
    bpy.ops.object.mode_set(mode='OBJECT')
    obj = func_object_utils.get_active_object()
    print("Active Object: " + str(obj))
    if obj.type != 'MESH':
        raise Exception("This object is not a mesh")
    first_armature = None
    for m in obj.modifiers:
        if not first_armature and m.type == 'ARMATURE' and m.show_viewport:
            first_armature = m.object
            print("First Armature: " + first_armature.name)

    if first_armature:
        # ボーン名として使用されている以外の頂点グループを削除
        bone_names = [b.name for b in first_armature.data.bones]
        for group in obj.vertex_groups:
            if group.name not in bone_names:
                print("Remove Group: " + group.name)
                obj.vertex_groups.remove(group)
    else:
        print("No Armature Found")
    print( "--- Remove Groups Other Than Bone Names Finished ---")
        