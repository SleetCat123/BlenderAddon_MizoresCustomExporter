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

import ctypes
import os
import time
from collections.abc import Generator
from typing import Optional

import bpy
from bpy_extras.io_utils import axis_conversion
from io_scene_fbx import export_fbx_bin
from mathutils import Matrix

from .. import consts
from ..export_sets import func_export_sets
from ..export_sets.shapekey_order_override import resolver as shapekey_order_override_resolver
from ..funcs import func_addon_link
from ..funcs.modal.export_result import ExportResult
from ..funcs.modal.progress_info import ProgressInfo, T
from ..funcs.utils import (
    func_collection_utils,
    func_custom_props_utils,
    func_object_utils,
)
from . import func_export_preprocess, func_export_scale_value_mode
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData


NAME_PROBE_BUFFER_SIZE = 256
NAME_FIELD_BYTE_SIZE = 64
NAME_OFFSET_CACHE = {}
EXPORT_SET_PROGRESS_START = 0.80
EXPORT_SET_PROGRESS_SPAN = 0.19


def log_export_set_stage(export_set_name: str, stage: str, detail: str = ""):
    if detail:
        print(f"[ExportSets][{stage}] {export_set_name}: {detail}")
    else:
        print(f"[ExportSets][{stage}] {export_set_name}")


def log_batch_export_stage(batch_name: str, stage: str, detail: str = ""):
    if detail:
        print(f"[BatchExport][{stage}] {batch_name}: {detail}")
    else:
        print(f"[BatchExport][{stage}] {batch_name}")


def build_export_set_progress(
    *,
    export_set_name: str,
    stage: str,
    set_index: int,
    total_sets: int,
    stage_progress: float,
    message: str,
    object_name: str = "",
) -> ProgressInfo:
    safe_total_sets = max(total_sets, 1)
    set_span = EXPORT_SET_PROGRESS_SPAN / safe_total_sets
    set_start = EXPORT_SET_PROGRESS_START + (set_span * set_index)
    progress = set_start + (set_span * max(0.0, min(1.0, stage_progress)))
    return ProgressInfo(
        phase="export_set",
        progress=progress,
        message=message,
        object_name=object_name,
        sub_progress=stage_progress,
        total_objects=safe_total_sets,
        current_object_index=set_index + 1,
    )


def build_batch_export_progress(
    *,
    batch_name: str,
    stage: str,
    item_index: int,
    total_items: int,
    stage_progress: float,
    message: str,
    object_name: str = "",
) -> ProgressInfo:
    safe_total_items = max(total_items, 1)
    item_span = EXPORT_SET_PROGRESS_SPAN / safe_total_items
    item_start = EXPORT_SET_PROGRESS_START + (item_span * item_index)
    progress = item_start + (item_span * max(0.0, min(1.0, stage_progress)))
    return ProgressInfo(
        phase="batch_export",
        progress=progress,
        message=message,
        object_name=object_name,
        sub_progress=stage_progress,
        total_objects=safe_total_items,
        current_object_index=item_index + 1,
    )


def get_reorder_target_name(reorder_target) -> str:
    if reorder_target is None:
        return ""
    if hasattr(reorder_target, "name"):
        return reorder_target.name
    if isinstance(reorder_target, tuple) and reorder_target:
        first = reorder_target[0]
        if hasattr(first, "name"):
            return first.name
    return ""


def is_object_type_enabled_for_export(object_types, obj) -> bool:
    if obj.type == 'EMPTY':
        return 'EMPTY' in object_types
    if obj.type == 'CAMERA':
        return 'CAMERA' in object_types
    if obj.type == 'LIGHT':
        return 'LIGHT' in object_types
    if obj.type == 'ARMATURE':
        return 'ARMATURE' in object_types
    if obj.type == 'MESH':
        return 'MESH' in object_types
    if obj.type in {'LATTICE', 'LIGHT_PROBE', 'SPEAKER'}:
        return False
    return 'OTHER' in object_types


def read_collection_item_name(item):
    return item.name


def resolve_collection_item_name_offset(collection_key):
    cached_offset = NAME_OFFSET_CACHE.get(collection_key)
    if cached_offset is not None:
        return cached_offset

    probe_mesh = bpy.data.meshes.new("__mizore_export_name_probe__")
    try:
        if collection_key == "uv_layers":
            sentinel_name = "MIZORE_UV_NAME_SENTINEL_123"
            probe_item = probe_mesh.uv_layers.new(name=sentinel_name)
        elif collection_key == "color_attributes":
            sentinel_name = "MIZORE_COLOR_NAME_SENTINEL_123"
            probe_item = probe_mesh.color_attributes.new(
                name=sentinel_name,
                type='FLOAT_COLOR',
                domain='CORNER',
            )
        elif collection_key == "attributes":
            sentinel_name = "MIZORE_ATTRIBUTE_NAME_SENTINEL_123"
            probe_item = probe_mesh.attributes.new(
                name=sentinel_name,
                type='FLOAT',
                domain='POINT',
            )
        else:
            raise ValueError(f"Unsupported collection key: {collection_key}")

        sentinel_bytes = sentinel_name.encode("ascii") + b"\x00"
        probe_data = ctypes.string_at(probe_item.as_pointer(), NAME_PROBE_BUFFER_SIZE)
        offset = probe_data.find(sentinel_bytes)
        if offset < 0:
            raise RuntimeError(
                f"Failed to resolve name offset for {collection_key}: sentinel not found"
            )

        NAME_OFFSET_CACHE[collection_key] = offset
        return offset
    finally:
        try:
            if probe_mesh.users == 0:
                bpy.data.meshes.remove(probe_mesh)
        except Exception:
            pass


def save_collection_item_name_bytes(item, offset):
    return bytes(ctypes.string_at(item.as_pointer() + offset, NAME_FIELD_BYTE_SIZE))


def restore_collection_item_name_bytes(item, offset, raw_name):
    buffer = (ctypes.c_ubyte * len(raw_name)).from_address(item.as_pointer() + offset)
    for index, value in enumerate(raw_name):
        buffer[index] = value


def build_fallback_collection_name(prefix, used_names, index):
    base_name = prefix or "Item"
    candidate = base_name if base_name not in used_names else f"{base_name}.{index:03d}"
    suffix = index
    while candidate in used_names:
        suffix += 1
        candidate = f"{base_name}.{suffix:03d}"
    return candidate


def collect_unreadable_collection_items(collection, collection_key):
    unreadable_items = []
    if collection is None:
        return unreadable_items

    try:
        list(collection.keys())
        return unreadable_items
    except Exception:
        pass

    offset = resolve_collection_item_name_offset(collection_key)
    for index, item in enumerate(collection):
        try:
            read_collection_item_name(item)
        except Exception as ex:
            unreadable_items.append({
                "item": item,
                "index": index,
                "pointer": item.as_pointer(),
                "offset": offset,
                "raw_name": save_collection_item_name_bytes(item, offset),
                "error_type": type(ex).__name__,
                "error_message": str(ex),
            })

    return unreadable_items


def rename_unreadable_collection_items(
    collection,
    fallback_prefix,
    unreadable_items,
    owner_name,
    collection_label,
    renamed_item_pointers,
):
    if collection is None or not unreadable_items:
        return []

    used_names = set()
    for item in collection:
        try:
            used_names.add(read_collection_item_name(item))
        except Exception:
            continue

    renamed_items = []
    for unreadable_item in unreadable_items:
        if unreadable_item["pointer"] in renamed_item_pointers:
            continue

        safe_name = build_fallback_collection_name(
            fallback_prefix,
            used_names,
            unreadable_item["index"],
        )
        print(
            f"[MizoreExporter] Renamed unreadable {collection_label} on '{owner_name}' "
            f"(index {unreadable_item['index']}, {unreadable_item['error_type']}: "
            f"{unreadable_item['error_message']}) -> {safe_name}"
        )
        unreadable_item["item"].name = safe_name
        used_names.add(safe_name)
        renamed_item_pointers.add(unreadable_item["pointer"])
        renamed_items.append(unreadable_item)

    return renamed_items


def prepare_temporary_safe_name_restorations(objects):
    restorations = []
    processed_meshes = set()
    renamed_item_pointers = set()

    for obj in objects:
        if obj.type != 'MESH' or getattr(obj, "data", None) is None:
            continue

        mesh = obj.data
        mesh_key = mesh.as_pointer() if hasattr(mesh, "as_pointer") else id(mesh)
        if mesh_key in processed_meshes:
            continue
        processed_meshes.add(mesh_key)

        for collection_key, fallback_prefix, collection_label in (
            ("uv_layers", "UVMap", "UV layer"),
            ("color_attributes", "Color", "color attribute"),
            ("attributes", "Attribute", "attribute"),
        ):
            collection = getattr(mesh, collection_key, None)
            unreadable_items = collect_unreadable_collection_items(collection, collection_key)
            restorations.extend(
                rename_unreadable_collection_items(
                    collection,
                    fallback_prefix,
                    unreadable_items,
                    mesh.name,
                    collection_label,
                    renamed_item_pointers,
                )
            )

    return restorations


def restore_temporary_safe_names(restorations):
    for restoration in reversed(restorations):
        try:
            restore_collection_item_name_bytes(
                restoration["item"],
                restoration["offset"],
                restoration["raw_name"],
            )
        except Exception:
            continue


def export_fbx_with_temporarily_safe_mesh_names(
    operator,
    context,
    filepath,
    keywords,
    scale_duplicate_source_pairs=None,
    scale_duplicate_objects=None,
):
    scale_context = func_export_scale_value_mode.prepare_temporary_scaled_export(
        operator,
        existing_duplicate_source_pairs=scale_duplicate_source_pairs,
        existing_duplicate_objects=scale_duplicate_objects,
    )
    selected_objects = list(bpy.context.selected_objects)
    restorations = prepare_temporary_safe_name_restorations(selected_objects)
    try:
        keywords["filepath"] = filepath
        keywords["global_scale"] = func_export_scale_value_mode.get_export_global_scale(operator)
        keywords["apply_scale_options"] = func_export_scale_value_mode.get_export_apply_scale_options(
            operator,
            keywords.get("apply_scale_options"),
        )
        export_fbx_bin.save(operator, context, **keywords)
    finally:
        restore_temporary_safe_names(restorations)
        func_export_scale_value_mode.cleanup_temporary_scaled_export(scale_context)


def execute_main_iter(operator, context) -> Generator[ProgressInfo, None, ExportResult]:
    """エクスポートメイン処理（ジェネレータ版）

    Args:
        operator: エクスポートオペレーター
        context: Blenderコンテキスト

    Yields:
        ProgressInfo: 進捗情報

    Returns:
        ExportResult: エクスポート結果のサマリ
    """
    # 結果収集用オブジェクト
    result = ExportResult()
    start_time = time.perf_counter()

    yield ProgressInfo(
        phase="init",
        progress=0.0,
        message=T("mce_progress_initializing")
    )
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

    for obj in bpy.context.selected_objects:
        func_object_utils.set_active_object(obj)
        if obj.mode != 'OBJECT':
            # Armatureをアクティブにしたとき勝手にPoseモードになる場合があるためここで確実にObjectモードにする
            bpy.ops.object.mode_set(mode='OBJECT')
        func_object_utils.select_children_recursive()

    active_collection_scope_mode = operator.batch_mode == 'COLLECTIONS_IN_ACTIVE_COLLECTION'
    use_active_collection_filter = operator.use_active_collection and operator.batch_mode != 'ACTIVE_SCENE_COLLECTION'
    if use_active_collection_filter or active_collection_scope_mode:
        active_layer_collection = bpy.context.view_layer.active_layer_collection
        print("Active Collection: " + active_layer_collection.name)
        active_collection = active_layer_collection.collection
        func_collection_utils.select_collection_only(
            collection=active_collection,
            include_children_objects=(
                True if active_collection_scope_mode
                else operator.use_active_collection_children_objects
            ),
            include_children_collections=(
                True if active_collection_scope_mode
                else operator.use_active_collection_children_collections
            ),
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

    export_set_available_roots = None
    export_set_item_contexts_by_ptr = None

    if operator.batch_mode == 'EXPORT_SETS':
        export_sets = list(func_export_sets.iter_enabled_export_sets(bpy.context.scene))
        if export_sets:
            selected_roots = list(bpy.context.selected_objects)
            export_set_available_roots = list(selected_roots)
            export_set_item_contexts_by_ptr = {}
            preprocess_targets = []
            preprocess_target_pointers = set()
            for export_set in export_sets:
                item_contexts = func_export_sets.resolve_export_set_item_contexts(
                    export_set=export_set,
                    available_objects=selected_roots,
                )
                export_set_item_contexts_by_ptr[export_set.as_pointer()] = item_contexts
                resolved_objects = func_export_sets.collect_export_set_objects_from_contexts(item_contexts)
                for obj in resolved_objects:
                    if not func_export_sets.object_exists(obj):
                        continue
                    if not is_object_type_enabled_for_export(object_types, obj):
                        continue
                    obj_pointer = obj.as_pointer()
                    if obj_pointer in preprocess_target_pointers:
                        continue
                    preprocess_target_pointers.add(obj_pointer)
                    preprocess_targets.append(obj)

            if preprocess_targets:
                active_object = func_object_utils.get_active_object()
                func_object_utils.deselect_all_objects()
                for obj in preprocess_targets:
                    func_object_utils.force_unhide(obj)
                func_object_utils.select_objects(preprocess_targets, True)
                if active_object in preprocess_targets:
                    func_object_utils.set_active_object(active_object)
                else:
                    func_object_utils.set_active_object(preprocess_targets[0])
                print(
                    "[ExportSets] preprocess targets=[" +
                    ", ".join(obj.name for obj in preprocess_targets) +
                    "]"
                )
    
    # region オブジェクトの文字数チェック
    selected_objects = bpy.context.selected_objects
    for obj in selected_objects:
        # 接尾辞をつけたときに名前の文字数が63文字（Blenderの最大文字数）を超えるオブジェクトがあるならエラー
        if len(obj.name) > consts.ACTUAL_MAX_NAME_LENGTH:
            t = bpy.app.translations.pgettext("error_longname_object").format(
                str(consts.ACTUAL_MAX_NAME_LENGTH),
                obj.name,
                str(len(obj.name))
            )
            operator.report({'ERROR'}, t)
            return {'CANCELLED'}
        if obj.data and len(obj.data.name) > consts.ACTUAL_MAX_NAME_LENGTH:
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

    yield ProgressInfo(
        phase="preprocess",
        progress=0.1,
        message=T("mce_progress_starting_preprocess")
    )

    # region Preprocess
    # ジェネレータ版を使用して進捗を伝播
    preprocess_gen = func_export_preprocess.export_preprocess_iter(operator=operator)
    postprocess_result = None
    try:
        while True:
            sub_progress = next(preprocess_gen)
            # サブ進捗を全体進捗にマッピング（10%〜80%の範囲）
            mapped_progress = 0.1 + (sub_progress.progress * 0.7)
            yield ProgressInfo(
                phase=sub_progress.phase,
                progress=mapped_progress,
                message=sub_progress.message,
                object_name=sub_progress.object_name,
                sub_progress=sub_progress.sub_progress,
                total_objects=sub_progress.total_objects,
                current_object_index=sub_progress.current_object_index,
            )
    except StopIteration as e:
        postprocess_result = e.value

    if postprocess_result is None:
        postprocess_result = func_export_preprocess.ExportPostprocessResult()
    # endregion

    yield ProgressInfo(
        phase="export",
        progress=0.8,
        message=T("mce_progress_exporting_fbx")
    )

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
    all_export_targets = list(bpy.context.selected_objects)

    if operator.batch_mode == 'EXPORT_SETS':
        export_sets = list(func_export_sets.iter_enabled_export_sets(bpy.context.scene))
        if not export_sets:
            result.add_error("Batch Mode is set to Export Sets, but no enabled export set was found.")
            operator.report({'ERROR'}, "Batch Mode is set to Export Sets, but no enabled export set was found.")
        else:
            saved_selection = list(bpy.context.selected_objects)
            saved_active = func_object_utils.get_active_object()

            total_sets = len(export_sets)
            for index, export_set in enumerate(export_sets):
                export_set_name = func_export_sets.get_export_set_display_name(export_set)
                yield build_export_set_progress(
                    export_set_name=export_set_name,
                    stage="build_runtime",
                    set_index=index,
                    total_sets=total_sets,
                    stage_progress=0.02,
                    message=f"Export Set {index + 1}/{total_sets}: resolve targets",
                )
                log_export_set_stage(export_set_name, "build_runtime", "start")
                runtime = func_export_sets.build_export_set_runtime(
                    export_set=export_set,
                    available_objects=export_set_available_roots if export_set_available_roots is not None else all_export_targets,
                    export_object_types=operator.object_types,
                    item_contexts=(
                        export_set_item_contexts_by_ptr.get(export_set.as_pointer())
                        if export_set_item_contexts_by_ptr is not None
                        else None
                    ),
                )
                if not runtime.duplicate_objects:
                    warning = f"Export Set '{export_set_name}': no export targets resolved"
                    print(warning)
                    operator.report({'WARNING'}, warning)
                    result.add_warning(warning)
                    continue

                try:
                    runtime_targets = func_export_sets.get_export_objects_from_runtime(runtime)
                    log_export_set_stage(
                        export_set_name,
                        "build_runtime",
                        f"resolved duplicate_objects={len(runtime.duplicate_objects)} export_targets={len(runtime_targets)}",
                    )
                    yield build_export_set_progress(
                        export_set_name=export_set_name,
                        stage="build_runtime",
                        set_index=index,
                        total_sets=total_sets,
                        stage_progress=0.10,
                        message=f"Export Set {index + 1}/{total_sets}: runtime ready",
                        object_name=runtime_targets[0].name if runtime_targets else "",
                    )

                    log_export_set_stage(export_set_name, "retarget", "start")
                    yield build_export_set_progress(
                        export_set_name=export_set_name,
                        stage="retarget",
                        set_index=index,
                        total_sets=total_sets,
                        stage_progress=0.16,
                        message=f"Export Set {index + 1}/{total_sets}: retarget references",
                        object_name=runtime_targets[0].name if runtime_targets else "",
                    )
                    func_export_sets.retarget_runtime_object_replace_references(runtime)
                    func_export_sets.validate_runtime_object_replace_references(runtime)
                    func_export_sets.remove_runtime_object_replace_staging_duplicates(runtime)
                    runtime_targets = func_export_sets.get_export_objects_from_runtime(runtime)
                    log_export_set_stage(export_set_name, "retarget", "done")

                    log_export_set_stage(export_set_name, "vertex_color", "start")
                    yield build_export_set_progress(
                        export_set_name=export_set_name,
                        stage="vertex_color",
                        set_index=index,
                        total_sets=total_sets,
                        stage_progress=0.24,
                        message=f"Export Set {index + 1}/{total_sets}: apply vertex color rules",
                        object_name=runtime_targets[0].name if runtime_targets else "",
                    )
                    func_export_sets.apply_runtime_vertex_color_replace_rules(runtime)
                    log_export_set_stage(export_set_name, "vertex_color", "done")
                    if export_set.merge_armatures:
                        log_export_set_stage(export_set_name, "merge_armatures", "start")
                        yield build_export_set_progress(
                            export_set_name=export_set_name,
                            stage="merge_armatures",
                            set_index=index,
                            total_sets=total_sets,
                            stage_progress=0.34,
                            message=f"Export Set {index + 1}/{total_sets}: merge armatures",
                            object_name=runtime_targets[0].name if runtime_targets else "",
                        )
                        func_export_sets.merge_runtime_armatures(runtime)
                        runtime_targets = func_export_sets.get_export_objects_from_runtime(runtime)
                        log_export_set_stage(export_set_name, "merge_armatures", "done")
                    if export_set.join_meshes_to_one:
                        log_export_set_stage(export_set_name, "join_meshes", "start")
                        yield build_export_set_progress(
                            export_set_name=export_set_name,
                            stage="join_meshes",
                            set_index=index,
                            total_sets=total_sets,
                            stage_progress=0.46,
                            message=f"Export Set {index + 1}/{total_sets}: join meshes",
                            object_name=runtime_targets[0].name if runtime_targets else "",
                        )
                        func_export_sets.join_runtime_meshes(runtime)
                        runtime_targets = func_export_sets.get_export_objects_from_runtime(runtime)
                        log_export_set_stage(export_set_name, "join_meshes", "done")

                    if operator.enable_reorder_shapekeys and func_addon_link.shapekey_util_reorder_is_available():
                        objects_with_reorder = shapekey_order_override_resolver.build_export_set_reorder_targets(
                            export_set,
                            runtime,
                        )
                        if objects_with_reorder:
                            first_reorder_target_name = get_reorder_target_name(objects_with_reorder[0])
                            log_export_set_stage(
                                export_set_name,
                                "reorder_shapekeys",
                                f"start objects={len(objects_with_reorder)}",
                            )
                            yield build_export_set_progress(
                                export_set_name=export_set_name,
                                stage="reorder_shapekeys",
                                set_index=index,
                                total_sets=total_sets,
                                stage_progress=0.58,
                                message=f"Export Set {index + 1}/{total_sets}: reorder shapekeys",
                                object_name=first_reorder_target_name,
                            )
                            reorder_gen = bpy.types.WindowManager.shapekeys_util_get_reorder_iter(
                                objects_with_reorder
                            )
                            for reorder_progress in reorder_gen:
                                reorder_sub_progress = getattr(reorder_progress, "progress", 0.0)
                                reorder_object_name = getattr(reorder_progress, "object_name", "") or first_reorder_target_name
                                yield build_export_set_progress(
                                    export_set_name=export_set_name,
                                    stage="reorder_shapekeys",
                                    set_index=index,
                                    total_sets=total_sets,
                                    stage_progress=0.58 + (0.20 * reorder_sub_progress),
                                    message=f"Export Set {index + 1}/{total_sets}: reorder shapekeys",
                                    object_name=reorder_object_name,
                                )
                            log_export_set_stage(export_set_name, "reorder_shapekeys", "done")

                    targets = func_export_sets.get_export_objects_from_runtime(runtime)
                    if not targets:
                        warning = f"Export Set '{export_set_name}': no duplicated export targets remained"
                        print(warning)
                        operator.report({'WARNING'}, warning)
                        result.add_warning(warning)
                        continue

                    log_export_set_stage(
                        export_set_name,
                        "export_fbx",
                        f"start target_count={len(targets)} path={func_export_sets.build_export_set_filepath(operator.filepath, export_set)}",
                    )
                    yield build_export_set_progress(
                        export_set_name=export_set_name,
                        stage="export_fbx",
                        set_index=index,
                        total_sets=total_sets,
                        stage_progress=0.86,
                        message=f"Export Set {index + 1}/{total_sets}: export FBX",
                        object_name=targets[0].name,
                    )

                    func_object_utils.deselect_all_objects()
                    func_object_utils.select_objects(targets, True)
                    if targets:
                        func_object_utils.set_active_object(targets[0])

                    path = func_export_sets.build_export_set_filepath(operator.filepath, export_set)
                    dir = os.path.dirname(path)
                    if dir and not os.path.exists(dir):
                        os.makedirs(dir)

                    print("export set: " + path)
                    export_fbx_with_temporarily_safe_mesh_names(
                        operator,
                        context,
                        path,
                        keywords,
                        scale_duplicate_source_pairs=runtime.duplicate_source_pairs,
                        scale_duplicate_objects=targets,
                    )
                    result.add_exported_file(path)
                    log_export_set_stage(export_set_name, "export_fbx", "done")
                    yield build_export_set_progress(
                        export_set_name=export_set_name,
                        stage="export_fbx",
                        set_index=index,
                        total_sets=total_sets,
                        stage_progress=0.96,
                        message=f"Export Set {index + 1}/{total_sets}: export complete",
                        object_name=targets[0].name,
                    )
                finally:
                    log_export_set_stage(export_set_name, "cleanup_runtime", "start")
                    func_export_sets.cleanup_runtime(runtime)
                    log_export_set_stage(export_set_name, "cleanup_runtime", "done")

            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(
                [obj for obj in saved_selection if func_export_sets.object_exists(obj)],
                True,
            )
            if saved_active is not None and func_export_sets.object_exists(saved_active):
                func_object_utils.set_active_object(saved_active)

        result.processed_objects_count = len(all_export_targets)
        result.elapsed_time = time.perf_counter() - start_time

        yield ProgressInfo(
            phase="complete",
            progress=1.0,
            message=T("mce_progress_export_complete")
        )

        return result

    # BatchMode用処理
    # TODO: このへんの挙動を調べる
    if (
        operator.batch_mode == 'COLLECTION'
        or operator.batch_mode == 'SCENE_COLLECTION'
        or operator.batch_mode == 'ACTIVE_SCENE_COLLECTION'
        or operator.batch_mode == 'COLLECTIONS_IN_ACTIVE_COLLECTION'
    ):
        ignore_collections_name = [consts.ALWAYS_EXPORT_GROUP_NAME, consts.DONT_EXPORT_GROUP_NAME]
        batch_jobs = []
        if func_addon_link.auto_merge_is_found():
            automerge_collection_name = bpy.types.WindowManager.mizore_automerge_collection_name
            print(f"AutoMerge Collection Name: {automerge_collection_name}")
            ignore_collections_name.append(automerge_collection_name)

            dont_merge_to_parent_c_name = bpy.types.WindowManager.mizore_automerge_dont_merge_to_parent_collection_name
            print(f"Don'tMergeToParent Collection Name: {dont_merge_to_parent_c_name}")
            ignore_collections_name.append(dont_merge_to_parent_c_name)

        if operator.batch_mode == 'COLLECTIONS_IN_ACTIVE_COLLECTION':
            active_layer_collection = bpy.context.view_layer.active_layer_collection
            active_collection = active_layer_collection.collection
            if operator.only_root_collection:
                target_collections = [active_collection]
            else:
                target_collections = func_collection_utils.recursive_get_collections(active_collection)
        else:
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
                                                                   include_children_collections=operator.use_batch_collection_children_collections)
            objects = objects & set(all_export_targets)
            # 対象オブジェクトが無い場合はスキップ
            if not objects:
                continue
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=collection.name,
                use_batch_own_dir=operator.use_batch_own_dir
            )
            batch_jobs.append((collection.name, list(objects), path))
        # Scene Collection書き出し
        if (
            operator.batch_mode == 'SCENE_COLLECTION'
            or operator.batch_mode == 'ACTIVE_SCENE_COLLECTION'
            or operator.batch_mode == 'COLLECTIONS_IN_ACTIVE_COLLECTION'
        ):
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=f"{bpy.context.scene.name}_Scene_Collection",
                use_batch_own_dir=operator.use_batch_own_dir
            )
            batch_jobs.append((f"{bpy.context.scene.name}_Scene_Collection", list(all_export_targets), path))

        total_jobs = len(batch_jobs)
        for index, (batch_name, objects, path) in enumerate(batch_jobs):
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="prepare_targets",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.10,
                message=f"Batch Export {index + 1}/{total_jobs}: prepare targets",
                object_name=batch_name,
            )
            log_batch_export_stage(batch_name, "prepare_targets", f"object_count={len(objects)}")
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(objects, True)
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="select_targets",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.35,
                message=f"Batch Export {index + 1}/{total_jobs}: targets selected",
                object_name=batch_name,
            )

            dir = os.path.dirname(path)
            if dir and not os.path.exists(dir):
                os.makedirs(dir)

            log_batch_export_stage(batch_name, "export_fbx", f"path={path}")
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="export_fbx",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.75,
                message=f"Batch Export {index + 1}/{total_jobs}: export FBX",
                object_name=batch_name,
            )
            print("export: " + path)
            export_fbx_with_temporarily_safe_mesh_names(operator, context, path, keywords)
            result.add_exported_file(path)
            log_batch_export_stage(batch_name, "export_fbx", "done")
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="export_fbx",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.96,
                message=f"Batch Export {index + 1}/{total_jobs}: export complete",
                object_name=batch_name,
            )
    elif operator.batch_mode == 'OBJECTS_IN_ACTIVE_COLLECTION':
        # アクティブなコレクションに属するオブジェクト（親を持たないか、親がアクティブなコレクションに属さない）を対象とする
        active_layer_collection = bpy.context.view_layer.active_layer_collection
        active_collection = active_layer_collection.collection
        root_objects = func_collection_utils.get_root_objects(collection=active_collection)
        root_objects = set(root_objects) & set(all_export_targets)
        batch_jobs = []
        for root_obj in root_objects:
            children = func_object_utils.get_children_recursive(root_obj, contains_self=True)
            children = set(children) & set(all_export_targets)
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=root_obj.name,
                use_batch_own_dir=operator.use_batch_own_dir
            )
            batch_jobs.append((root_obj.name, list(children), path))

        total_jobs = len(batch_jobs)
        for index, (batch_name, objects, path) in enumerate(batch_jobs):
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="prepare_targets",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.10,
                message=f"Batch Export {index + 1}/{total_jobs}: prepare targets",
                object_name=batch_name,
            )
            log_batch_export_stage(batch_name, "prepare_targets", f"object_count={len(objects)}")
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(objects, True)
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="select_targets",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.35,
                message=f"Batch Export {index + 1}/{total_jobs}: targets selected",
                object_name=batch_name,
            )
            log_batch_export_stage(batch_name, "export_fbx", f"path={path}")
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="export_fbx",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.75,
                message=f"Batch Export {index + 1}/{total_jobs}: export FBX",
                object_name=batch_name,
            )
            print("export: " + path)
            export_fbx_with_temporarily_safe_mesh_names(operator, context, path, keywords)
            result.add_exported_file(path)
            log_batch_export_stage(batch_name, "export_fbx", "done")
            yield build_batch_export_progress(
                batch_name=batch_name,
                stage="export_fbx",
                item_index=index,
                total_items=total_jobs,
                stage_progress=0.96,
                message=f"Batch Export {index + 1}/{total_jobs}: export complete",
                object_name=batch_name,
            )
    elif operator.batch_mode == 'OFF' or operator.batch_mode == 'SCENE':
        path = operator.filepath
        batch_name = bpy.context.scene.name if operator.batch_mode == 'SCENE' else os.path.basename(path)
        if operator.batch_mode == 'SCENE':
            # ファイル名を変換
            path = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch=bpy.context.scene.name,
                use_batch_own_dir=operator.use_batch_own_dir
            )
        yield build_batch_export_progress(
            batch_name=batch_name,
            stage="prepare_targets",
            item_index=0,
            total_items=1,
            stage_progress=0.10,
            message="Batch Export 1/1: prepare targets",
            object_name=batch_name,
        )
        log_batch_export_stage(batch_name, "prepare_targets", f"object_count={len(all_export_targets)}")
        yield build_batch_export_progress(
            batch_name=batch_name,
            stage="export_fbx",
            item_index=0,
            total_items=1,
            stage_progress=0.75,
            message="Batch Export 1/1: export FBX",
            object_name=batch_name,
        )
        log_batch_export_stage(batch_name, "export_fbx", f"path={path}")
        print("export: " + path)
        export_fbx_with_temporarily_safe_mesh_names(operator, context, path, keywords)
        result.add_exported_file(path)
        log_batch_export_stage(batch_name, "export_fbx", "done")
        yield build_batch_export_progress(
            batch_name=batch_name,
            stage="export_fbx",
            item_index=0,
            total_items=1,
            stage_progress=0.96,
            message="Batch Export 1/1: export complete",
            object_name=batch_name,
        )
    else:
        result.add_error(f"Batch mode '{operator.batch_mode}' is not defined.")
        operator.report({'ERROR'}, str(operator.batch_mode) + " は未定義です。")
    # endregion

    # 処理対象オブジェクト数を記録
    result.processed_objects_count = len(all_export_targets)

    # 処理時間を記録
    result.elapsed_time = time.perf_counter() - start_time

    yield ProgressInfo(
        phase="complete",
        progress=1.0,
        message=T("mce_progress_export_complete")
    )

    return result


def execute_main(operator, context) -> Optional[ExportResult]:
    """エクスポートメイン処理（同期版ラッパー）

    既存コードとの互換性のため、ジェネレータ版を消費して実行します。

    Returns:
        ExportResult: エクスポート結果のサマリ
    """
    gen = execute_main_iter(operator, context)
    result = None
    try:
        while True:
            next(gen)
    except StopIteration as e:
        result = e.value
    return result
