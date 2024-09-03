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
from ..funcs import func_addon_link
from . import func_export_preprocess
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix
from io_scene_fbx import export_fbx_bin
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData


def execute_main(operator, context):
    # 常時エクスポートするオブジェクトを表示
    always_export_objects = set(func_custom_props_utils.get_objects_prop_is_true(prop_name=consts.ALWAYS_EXPORT_GROUP_NAME))
    # AlwaysExportのPropをもつオブジェクトをコレクションに追加（親コレクションが非表示な場合でも表示できるように）
    layer_col_always_export = func_collection_utils.find_or_create_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
    for obj in always_export_objects:
        layer_col_always_export.objects.link(obj)
    # コレクションを表示
    layer_col_always_export.hide_viewport = False
    collection = func_collection_utils.find_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
    for obj in collection.objects:
        # オブジェクトを表示
        func_object_utils.force_unhide(obj)

    if operator.use_selection:
        # 選択中のオブジェクト以外を非表示にする
        func_object_utils.hide_unselected_objects()
    else:
        # Selected Objectsにチェックがついていないなら全オブジェクトを選択
        func_object_utils.select_all_objects()

    if operator.use_selection and operator.use_selection_children_objects:
        for obj in bpy.context.selected_objects:
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

    # region エクスポート対象でない種類のオブジェクトの選択を解除し非表示にする
    object_types = operator.object_types
    if 'EMPTY' not in object_types:
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type == 'EMPTY' :
                if 'EMPTY' not in object_types:
                    func_object_utils.select_object(obj, False)
                    obj.hide_set(True)
            elif obj.type == 'CAMERA':
                if 'CAMERA' not in object_types:
                    func_object_utils.select_object(obj, False)
                    obj.hide_set(True)
            elif obj.type == 'LIGHT':
                if 'LIGHT' not in object_types:
                    func_object_utils.select_object(obj, False)
                    obj.hide_set(True)
            elif obj.type == 'ARMATURE':
                if 'ARMATURE' not in object_types:
                    func_object_utils.select_object(obj, False)
                    obj.hide_set(True)
            elif obj.type == 'MESH':
                if 'MESH' not in object_types:
                    func_object_utils.select_object(obj, False)
                    obj.hide_set(True)
            elif obj.type in ['LATTICE', 'LIGHT_PROBE', 'SPEAKER']:
                # 常にエクスポートされない種類のオブジェクト
                func_object_utils.select_object(obj, False)
                obj.hide_set(True)
            else:
                if 'OTHER' not in object_types:
                    func_object_utils.select_object(obj, False)
                    obj.hide_set(True)
    # endregion

    # region 処理から除外するオブジェクトの選択を外し非表示にする
    dont_export_objects = func_custom_props_utils.get_objects_prop_is_true(
        prop_name=consts.DONT_EXPORT_GROUP_NAME, 
        affect_children=True
        )
    for obj in dont_export_objects:
        func_object_utils.select_object(obj, False)
        obj.hide_set(True)
    # endregion
    
    # region オブジェクトの文字数チェック
    selected_objects = bpy.context.selected_objects
    for obj in selected_objects:
        # 接尾辞をつけたときに名前の文字数が63文字（Blenderの最大文字数）を超えるオブジェクトがあるならエラー
        if consts.ACTUAL_MAX_NAME_LENGTH < len(obj.name):
            t = bpy.app.translations.pgettext("error_longname_object").format(
                str(consts.ACTUAL_MAX_NAME_LENGTH),
                obj.name,
                str(len(obj.name))
            )
            operator.report({'ERROR'}, t)
            return {'CANCELLED'}
        if obj.data and consts.ACTUAL_MAX_NAME_LENGTH < len(obj.data.name):
            t = bpy.app.translations.pgettext("error_longname_data").format(
                str(consts.ACTUAL_MAX_NAME_LENGTH),
                obj.name,
                obj.data.name,
                str(len(obj.data.name))
            )
            operator.report({'ERROR'}, t)
            return {'CANCELLED'}
    # endregion

    # region AlwaysResetのシェイプキーをリセットする
    for obj in bpy.data.objects:
        if not func_custom_props_utils.prop_is_true(obj, consts.ALWAYS_RESET_SHAPEKEY_GROUP_NAME):
            continue
        if not obj.data or not hasattr(obj.data, 'shape_keys') or not hasattr(obj.data.shape_keys, 'key_blocks'):
            continue
        print("AlwaysReset ShapeKey: " + obj.name)
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0
    # endregion

    # 選択中オブジェクトを取得
    targets_source = bpy.context.selected_objects
    targets_source.sort(key=lambda x: x.name)
    # PoseモードのオブジェクトをOBJECTモードにする
    # （Poseモードになっているアーマチュアが複製されないっぽいので）
    for i in range(len(targets_source)):
        o = targets_source[i]
        if o.mode == 'POSE':
            func_object_utils.set_active_object(o)
            bpy.ops.object.mode_set(mode='OBJECT')

    # Debug
    print("Targets: [")
    for o in targets_source:
        print(o.name)
    print("]")

    # region Preprocess
    postprocess_result = func_export_preprocess.export_preprocess(
        operator=operator,
    )
    # endregion

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

    if postprocess_result.success_shapekey_util:
        # モディファイアを適用し終わっているので標準のモディファイア適用を無効化
        keywords["use_mesh_modifiers"] = False

    # use_selectionなどに該当する処理をこの関数内で行っており追加で何かをする必要はないため、エクスポート関数の処理を固定化しておく
    keywords["use_selection"] = True
    keywords["use_active_collection"] = False
    keywords["batch_mode"] = 'OFF'
    #
    all_export_targets = bpy.context.selected_objects

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

        for collection in target_collections:
            if any(collection.name in n for n in ignore_collections_name):
                continue
            objects = func_collection_utils.get_collection_objects(collection=collection,
                                                                   include_children_collections=operator.only_root_collection)
            objects = objects & set(all_export_targets)
            # 対象オブジェクトが無い場合はスキップ
            if not objects:
                continue
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(objects, True)
            # パス設定
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=collection.name,
                use_batch_own_dir=operator.use_batch_own_dir
            )
            # ディレクトリが存在しない場合は作成
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)

            keywords["filepath"] = path
            print("export: " + path)
            export_fbx_bin.save(operator, context, **keywords)
        # Scene Collection書き出し
        if operator.batch_mode == 'SCENE_COLLECTION' or operator.batch_mode == 'ACTIVE_SCENE_COLLECTION':
            # パス設定
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=f"{bpy.context.scene.name}_Scene_Collection",
                use_batch_own_dir=operator.use_batch_own_dir
            )
            keywords["filepath"] = path
            print("export: " + path)
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(all_export_targets, True)
            export_fbx_bin.save(operator, context, **keywords)
    elif operator.batch_mode == 'OBJECTS_IN_ACTIVE_COLLECTION':
        # アクティブなコレクションに属するオブジェクト（親を持たないか、親がアクティブなコレクションに属さない）を対象とする
        active_layer_collection = bpy.context.view_layer.active_layer_collection
        active_collection = active_layer_collection.collection
        root_objects = func_collection_utils.get_root_objects(collection=active_collection)
        root_objects = set(root_objects) & set(all_export_targets)
        for root_obj in root_objects:
            children = func_object_utils.get_children_recursive(root_obj, contains_self=True)
            children = set(children) & set(all_export_targets)
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(children, True)
            # パス設定
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=root_obj.name,
                use_batch_own_dir=operator.use_batch_own_dir
            )
            keywords["filepath"] = path
            print("export: " + path)
            export_fbx_bin.save(operator, context, **keywords)
    elif operator.batch_mode == 'OFF' or operator.batch_mode == 'SCENE':
        path = operator.filepath
        if operator.batch_mode == 'SCENE':
            # ファイル名を変換
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=bpy.context.scene.name,
                use_batch_own_dir=operator.use_batch_own_dir
            )
            keywords["filepath"] = path
        print("export: " + path)
        export_fbx_bin.save(operator, context, **keywords)
    else:
        operator.report({'ERROR'}, str(operator.batch_mode) + " は未定義です。")
    # endregion
