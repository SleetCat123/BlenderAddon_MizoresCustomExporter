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


def select_object(obj, value=True):
    try:
        obj.select_set(value)
    except RuntimeError as e:
        print(e)


def select_objects(objects, value=True):
    for obj in objects:
        try:
            obj.select_set(value)
        except RuntimeError as e:
            print(e)


def get_active_object():
    return bpy.context.view_layer.objects.active


def set_active_object(obj):
    bpy.context.view_layer.objects.active = obj


def get_children_objects(obj):
    result = []
    for ob in bpy.data.objects:
        if ob.parent == obj:
            result.append(ob)
    return result


def select_children_recursive(targets=None):
    def recursive(obj):
        select_object(obj, True)
        children = get_children_objects(obj)
        for child in children:
            recursive(child)

    if targets is None:
        targets = bpy.context.selected_objects
    for obj in targets:
        recursive(obj)


def select_all_objects():
    targets = bpy.context.scene.collection.all_objects
    for obj in targets:
        select_object(obj, True)


def deselect_all_objects():
    print("deselect_all_objects")
    targets = bpy.context.scene.collection.all_objects
    for obj in targets:
        select_object(obj, False)
    # bpy.context.view_layer.objects.active = None


def remove_objects(targets=None):
    print("remove_objects")
    if targets is None:
        targets = bpy.context.selected_objects

    data_list = []
    # オブジェクトを削除
    for obj in targets:
        try:
            if obj.data and obj.data not in data_list:
                data_list.append(obj.data)
            print("remove: " + str(obj))
            bpy.data.objects.remove(obj)
        except ReferenceError:
            continue

    # オブジェクトのデータを削除
    for data in data_list:
        blocks = None
        data_type = type(data)
        if data_type == bpy.types.Mesh:
            blocks = bpy.data.meshes
        elif data_type == bpy.types.Armature:
            blocks = bpy.data.armatures
        elif data_type == bpy.types.Curve:
            blocks = bpy.data.curves
        elif data_type == bpy.types.Lattice:
            blocks = bpy.data.lattices
        elif data_type == bpy.types.Light:
            blocks = bpy.data.lights
        elif data_type == bpy.types.Camera:
            blocks = bpy.data.cameras
        elif data_type == bpy.types.MetaBall:
            blocks = bpy.data.metaballs
        elif data_type == bpy.types.GreasePencil:
            blocks = bpy.data.grease_pencils

        if blocks and data.users == 0:
            print("remove: " + str(data))
            blocks.remove(data)
