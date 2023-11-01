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
    # try:
    bpy.context.view_layer.objects.active = obj
    # except ReferenceError:
    #    print("removed")


def get_children_objects(obj, only_current_view_layer: bool = True):
    all_objects = bpy.data.objects
    if only_current_view_layer:
        current_layer_objects_name = bpy.context.window.view_layer.objects.keys()
        return [child for child in all_objects if
                child.parent == obj and child.name in current_layer_objects_name]
    else:
        return [child for child in all_objects if child.parent == obj]


def get_children_recursive(targets, only_current_view_layer: bool = True):
    result = []

    def recursive(t):
        result.append(t)
        children = get_children_objects(t, only_current_view_layer)
        for child in children:
            recursive(child)

    if targets is bpy.types.Object:
        targets = [targets]
    for obj in targets:
        recursive(obj)
    return result


def select_children_recursive(targets=None, only_current_view_layer: bool = True):
    def recursive(t):
        select_object(t, True)
        children = get_children_objects(obj=t, only_current_view_layer=only_current_view_layer)
        for child in children:
            recursive(child)

    if targets is None:
        targets = bpy.context.selected_objects
    elif targets is bpy.types.Object:
        targets = [targets]
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


def remove_object(target: bpy.types.Object = None):
    print("remove_object")
    if target is None:
        # target = get_active_object()
        raise Exception("Remove target is empty")

    data = None
    # オブジェクトを削除
    try:
        if target.data:
            data = target.data
        print("remove: " + str(target))
        bpy.data.objects.remove(target)
    except ReferenceError:
        pass

    # オブジェクトのデータを削除
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


def remove_objects(targets=None):
    print("remove_objects")
    if targets is None:
        # targets = bpy.context.selected_objects
        raise Exception("Remove target is empty")

    for obj in targets:
        remove_object(target=obj)


def get_selected_root_objects():
    selected_objects = bpy.context.selected_objects
    not_root = []
    root_objects = []
    for obj in selected_objects:
        if obj in not_root:
            continue
        parent = obj
        while True:
            parent = parent.parent
            print(parent)
            if parent is None:
                # 親以上のオブジェクトに選択中オブジェクトが存在しなければ、そのオブジェクトはrootとなる
                root_objects.append(obj)
                break
            if parent in selected_objects:
                not_root.append(parent)
                break
    return root_objects


def duplicate_object(
        source=None,
        linked: bool = False,
        collection: bpy.types.Collection = None,
        collection_mode='SET',
):
    if source is None:
        source = bpy.context.selected_objects
    print("Duplicate Source: " + str(source))
    deselect_all_objects()
    if type(source) == bpy.types.Object:
        obj = source
        copied = obj.copy()
        if not linked and copied.data:
            copied.data = copied.data.copy()
        print(copied)
        print(copied.parent)

        # コレクションにリンク
        if collection and collection_mode == 'SET':
            collection.objects.link(copied)
        elif collection_mode == 'SCENE':
            bpy.context.scene.collection.objects.link(copied)
        else:
            # メモ：users_collectionは検索処理が重いらしいので使わずに済む場所では回避したい
            collections = obj.users_collection
            print(collections)
            for co in collections:
                co.objects.link(copied)
            if collection:
                collection.objects.link(copied)
        if collection:
            collection.objects.link(copied)

        set_active_object(copied)
        select_object(copied, True)
        return copied
    else:
        active_obj = get_active_object()
        result = []
        for obj in source:
            copied = obj.copy()
            if not linked and copied.data:
                copied.data = copied.data.copy()
            print(copied)

            # コレクションにリンク
            if collection and collection_mode == 'SET':
                collection.objects.link(copied)
            elif collection_mode == 'SCENE':
                bpy.context.scene.collection.objects.link(copied)
            else:
                # メモ：users_collectionは検索処理が重いらしいので使わずに済む場所では回避したい
                collections = obj.users_collection
                print(collections)
                for co in collections:
                    co.objects.link(copied)
                if collection:
                    collection.objects.link(copied)
            if collection:
                collection.objects.link(copied)

            if active_obj == obj:
                set_active_object(copied)
            select_object(copied, True)
            result.append(copied)
        # 親も一緒に複製されていたら親子関係を再設定する
        for i in range(len(source)):
            obj = source[i]
            if not obj.parent:
                continue
            try:
                index = source.index(obj.parent)
                copied = result[i]
                copied.parent = result[index]
            except ValueError:
                continue
        # モディファイアのオブジェクト参照を再設定:
        for i in range(len(source)):
            obj = source[i]
            if not obj.modifiers:
                continue
            for m in obj.modifiers:
                if not hasattr(m, 'object') or not m.object:
                    continue
                try:
                    index = source.index(m.object)
                    m.object = result[index]
                except ValueError:
                    continue
        print("Duplicate Result: " + str(result))
        return result


def set_object_name(obj, name):
    obj.name = name
    if obj.data:
        obj.data.name = name
