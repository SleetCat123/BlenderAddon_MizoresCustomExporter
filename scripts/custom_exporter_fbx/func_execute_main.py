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

import os
import bpy
from .. import consts
from ..funcs.utils import func_object_utils, func_collection_utils, func_custom_props_utils
from ..funcs import func_addon_link, func_name_utils
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix
from io_scene_fbx import export_fbx_bin
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData


def execute_main(operator, context):
    mode_temp = None
    if bpy.context.object is not None:
        # 開始時のモードを記憶しオブジェクトモードに
        mode_temp = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')

    # 現在の選択状況を記憶
    active_temp = func_object_utils.get_active_object()
    selected_temp = bpy.context.selected_objects

    # 常時エクスポートするオブジェクトを表示
    hide_temp_always_export = {}
    layer_col_always_export = func_collection_utils.find_layer_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
    if layer_col_always_export:
        # layer_col_always_export.exclude = False
        # コレクションを表示
        layer_col_always_export.hide_viewport = False
        # オブジェクトの表示状態を記憶してから表示
        collection = func_collection_utils.find_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
        always_export_objects = (
            set(collection.objects) |
            set(func_custom_props_utils.get_objects_prop_is_true(prop_name=consts.ALWAYS_EXPORT_GROUP_NAME))
        )
        for obj in always_export_objects:
            hide_temp_always_export[obj] = obj.hide_get()
            obj.hide_set(False)

    if not operator.use_selection:
        # Selected Objectsにチェックがついていないなら全オブジェクトを選択
        func_object_utils.select_all_objects()

    if operator.use_selection and operator.use_selection_children_objects:
        current_selected = bpy.context.selected_objects
        for obj in current_selected:
            func_object_utils.set_active_object(obj)
            if bpy.context.object.mode != 'OBJECT':
                # Armatureをアクティブにしたとき勝手にPoseモードになる場合があるためここで確実にObjectモードにする
                bpy.ops.object.mode_set(mode='OBJECT')
            func_object_utils.select_children_recursive()

    if operator.use_active_collection:
        active_layer_collection = bpy.context.view_layer.active_layer_collection
        print("Active Collection: " + active_layer_collection.name)
        active_collection = active_layer_collection.collection
        func_collection_utils.select_collection_only(
            collection=active_collection,
            include_children_objects=operator.use_active_collection_children_objects,
            include_children_collections=operator.use_active_collection_children_collections,
            set_visible=False
        )

    # エクスポート除外コレクションを取得
    ignore_collection = func_collection_utils.find_collection(consts.DONT_EXPORT_GROUP_NAME)
    if ignore_collection:
        # 処理から除外するオブジェクトの選択を外す
        func_collection_utils.deselect_collection(collection=ignore_collection)
    func_custom_props_utils.select_if_prop_is_true(prop_name=consts.DONT_EXPORT_GROUP_NAME, select=False)

    # AlwaysResetのシェイプキーをリセットする
    temp_shapekeys = {}
    for obj in bpy.data.objects:
        if not func_custom_props_utils.prop_is_true(obj, consts.ALWAYS_RESET_SHAPEKEY_GROUP_NAME):
            continue
        if not obj.data or not hasattr(obj.data, 'shape_keys') or not hasattr(obj.data.shape_keys, 'key_blocks'):
            continue
        print("AlwaysReset ShapeKey: " + obj.name)
        temp_shapekeys[obj] = {
            "show_only_shape_key": obj.show_only_shape_key,
            "values": [shape_key.value for shape_key in obj.data.shape_keys.key_blocks]
        }
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0

    # 選択中オブジェクトを取得
    targets_source = bpy.context.selected_objects
    targets_source.sort(key=lambda x: x.name)
    targets_source_mode = [''] * len(targets_source)
    # PoseモードのオブジェクトをOBJECTモードにする
    # （Poseモードになっているアーマチュアが複製されないっぽいので）
    for i in range(len(targets_source)):
        o = targets_source[i]
        if o.mode == 'POSE':
            targets_source_mode[i] = o.mode
            func_object_utils.set_active_object(o)
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            targets_source_mode[i] = ''

    # オブジェクト名に接尾辞を付ける
    # （名前の末尾が xxx.001 のように数字になっている場合にオブジェクトを複製すると名前がxxx.002 のようにカウントアップされてしまい、オブジェクト名の復元時に問題が起きるのでその対策）
    for obj in targets_source:
        func_name_utils.add_suffix(obj)

    # オブジェクトを複製
    targets_dup = func_object_utils.duplicate_object()
    targets_dup.sort(key=lambda x: x.name)

    # 複製したオブジェクトの名前から接尾辞を削除
    for obj in targets_dup:
        func_name_utils.remove_suffix(obj)

    # Debug
    print("Source: [")
    for o in targets_source:
        print(o.name)
    print("]")
    print("Duplicate: [")
    for o in targets_dup:
        print(o.name)
    print("]")

    # Armatureのポーズをリセットする
    for obj in targets_dup:
        if obj.type != 'ARMATURE':
            continue
        if not func_custom_props_utils.prop_is_true(obj, consts.RESET_POSE_GROUP_NAME):
            continue
        print("Reset Pose: " + obj.name)
        for pose_bone in obj.pose.bones:
            pose_bone.matrix_basis = Matrix()

    # シェイプキーをリセットする
    for obj in targets_dup:
        if not func_custom_props_utils.prop_is_true(obj, consts.RESET_SHAPEKEY_GROUP_NAME):
            continue
        if not obj.data or not hasattr(obj.data, 'shape_keys') or not hasattr(obj.data.shape_keys, 'key_blocks'):
            continue
        print("Reset ShapeKey: " + obj.name)
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0

    # ↓ AutoMergeアドオン連携
    if operator.enable_auto_merge:
        try:
            if ignore_collection:
                ignore_collection_name = ignore_collection.name
            else:
                ignore_collection_name = ""
            # オブジェクトを結合
            b = bpy.ops.object.apply_modifier_and_merge_grouped_exporter_addon(
                enable_apply_modifiers_with_shapekeys=operator.enable_apply_modifiers_with_shapekeys,
                ignore_collection_name=ignore_collection_name,
                ignore_prop_name=consts.DONT_EXPORT_GROUP_NAME
            )
            # 結合処理失敗
            if 'FINISHED' not in b:
                # 複製されたオブジェクトを削除
                func_object_utils.remove_objects(targets_dup)
                return {'FAILED'}
        except AttributeError as e:
            t = "!!! Failed to load AutoMerge !!!"
            print(t)
            print(str(e))
    # ↑ AutoMergeアドオン連携

    print("xxxxxx Export Targets xxxxxx\n" + '\n'.join(
        [obj.name for obj in bpy.context.selected_objects]) + "\nxxxxxxxxxxxxxxx")

    # ShapeKeysUtil連携
    if func_addon_link.shapekey_util_is_found():
        if operator.enable_apply_modifiers_with_shapekeys and operator.use_mesh_modifiers:
            active = func_object_utils.get_active_object()
            selected_objects = bpy.context.selected_objects
            targets = [d for d in selected_objects if d.type == 'MESH']
            for obj in targets:
                func_object_utils.set_active_object(obj)
                bpy.ops.object.shapekeys_util_apply_mod_for_exporter_addon()
            # 選択オブジェクトを復元
            for obj in selected_objects:
                obj.select_set(True)
            func_object_utils.set_active_object(active)
        if operator.enable_separate_lr_shapekey:
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH' and obj.data.shape_keys is not None and len(
                        obj.data.shape_keys.key_blocks) != 0:
                    func_object_utils.set_active_object(obj)
                    bpy.ops.object.shapekeys_util_separate_lr_shapekey_for_exporter()
    else:
        t = "!!! Failed to load ShapeKeysUtil !!! - apply_modifiers_with_shapekeys"
        print(t)
        operator.report({'ERROR'}, t)

    # region # Export based on io_scene_fbx
    if not operator.filepath:
        raise Exception("filepath not set")

    global_matrix = (axis_conversion(to_forward=operator.axis_forward,
                                     to_up=operator.axis_up,
                                     ).to_4x4()
                     if operator.use_space_transform else Matrix())

    keywords = operator.as_keywords(ignore=("check_existing",
                                        "filter_glob",
                                        "ui_tab",
                                        ))

    keywords["global_matrix"] = global_matrix

    # use_selectionなどに該当する処理をこの関数内で行っており追加で何かをする必要はないため、エクスポート関数の処理を固定化しておく
    keywords["use_selection"] = True
    keywords["use_active_collection"] = False
    keywords["batch_mode"] = 'OFF'
    #

    # BatchMode用処理
    # TODO: このへんの挙動を調べる
    if operator.batch_mode == 'COLLECTION' or operator.batch_mode == 'SCENE_COLLECTION' or operator.batch_mode == 'ACTIVE_SCENE_COLLECTION':
        ignore_collections_name = [consts.ALWAYS_EXPORT_GROUP_NAME, consts.DONT_EXPORT_GROUP_NAME]
        if func_addon_link.auto_merge_is_found():
            automerge_collection_name = bpy.types.WindowManager.mizore_automerge_collection_name
            print(f"AutoMerge Collection Name: {automerge_collection_name}")
            ignore_collections_name.append(automerge_collection_name)

            dont_merge_to_parent_c_name = bpy.types.WindowManager.mizore_automerge_dont_merge_to_parent_collection_name
            print(f"Don'tMergeToParent Collection Name: {dont_merge_to_parent_c_name}")
            ignore_collections_name.append(dont_merge_to_parent_c_name)

        if operator.only_root_collection:
            # Scene Collection直下だけを対象とする
            target_collections = bpy.context.scene.collection.children
        else:
            # [0]はシーンコレクションなのでスキップ
            target_collections = func_collection_utils.get_all_collections()[1:]

        targets = bpy.context.selected_objects
        for collection in target_collections:
            if any(collection.name in n for n in ignore_collections_name):
                continue
            objects = func_collection_utils.get_collection_objects(collection=collection,
                                                                   include_children_collections=operator.only_root_collection)
            objects = objects & set(targets)
            if not objects:
                continue
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(objects, True)
            # パス設定
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                file=operator.filepath,
                batch=collection.name
            )
            keywords["filepath"] = path
            print("export: " + path)
            export_fbx_bin.save(operator, context, **keywords)
        # Scene Collection書き出し
        if operator.batch_mode == 'SCENE_COLLECTION' or operator.batch_mode == 'ACTIVE_SCENE_COLLECTION':
            # パス設定
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                file=operator.filepath,
                batch=f"{bpy.context.scene.name}_Scene_Collection"
            )
            keywords["filepath"] = path
            print("export: " + path)
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(targets, True)
            export_fbx_bin.save(operator, context, **keywords)
    elif operator.batch_mode == 'OFF' or operator.batch_mode == 'SCENE':
        path = operator.filepath
        if operator.batch_mode == 'SCENE':
            # ファイル名を変換
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                file=operator.filepath,
                batch=bpy.context.scene.name
            )
            keywords["filepath"] = path
        print("export: " + path)
        export_fbx_bin.save(operator, context, **keywords)
    else:
        operator.report({'ERROR'}, str(operator.batch_mode) + " は未定義です。")
    # endregion

    # 複製されたオブジェクトを削除
    func_object_utils.remove_objects(targets_dup)

    # 複製前オブジェクト名から接尾辞を削除
    for obj in targets_source:
        func_name_utils.remove_suffix(obj)

    # AlwaysResetのシェイプキーを復元する
    for obj, data in temp_shapekeys.items():
        obj.show_only_shape_key = data["show_only_shape_key"]
        values = data["values"]
        for i, shape_key in enumerate(obj.data.shape_keys.key_blocks):
            shape_key.value = values[i]

    # AlwaysExportを非表示
    if layer_col_always_export:
        # layer_col_always_export.exclude = True
        layer_col_always_export.hide_viewport = True
        # オブジェクトの表示状態を復元
        for obj, value in hide_temp_always_export.items():
            obj.hide_set(value)

    # 選択状況を処理前の状態に復元
    func_object_utils.deselect_all_objects()
    func_object_utils.select_objects(selected_temp, True)
    # set_active_object(active_temp)

    # オブジェクトのモードを復元
    for i in range(len(targets_source)):
        m = targets_source_mode[i]
        if m:
            func_object_utils.set_active_object(targets_source[i])
            bpy.ops.object.mode_set(mode=m)
    func_object_utils.set_active_object(active_temp)

    if mode_temp is not None:
        # 開始時のモードを復元
        bpy.ops.object.mode_set(mode=mode_temp)

    return {'FINISHED'}
