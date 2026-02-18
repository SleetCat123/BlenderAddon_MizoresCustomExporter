import time
import traceback
from collections.abc import Generator

import bpy
from mathutils import Matrix

from .. import consts
from ..funcs import (
    func_addon_link,
    func_convert_uv_tiles_to_single,
    func_fix_vertex_group_collisions,
    func_remove_groups_not_bones,
    func_remove_unused_groups,
)
from ..funcs.modal.progress_info import ProgressInfo, T
from ..funcs.utils import func_custom_props_utils, func_object_utils


class ExportPostprocessResult:
    success_shapekey_util: bool = False


def limit_vertex_group_count_iter(
    max_groups: int
) -> Generator[ProgressInfo, None, None]:
    """頂点グループ数制限処理（ジェネレータ版）

    Args:
        max_groups: 最大頂点グループ数

    Yields:
        ProgressInfo: 進捗情報
    """
    start_time = time.perf_counter()
    print("--- Limit Vertex Group Count ---")

    # 処理対象オブジェクトを収集
    targets = [
        obj for obj in bpy.context.selected_objects
        if obj.type == 'MESH' and any(m.type == 'ARMATURE' for m in obj.modifiers)
    ]
    total = len(targets)

    if total == 0:
        print("[Preprocess] Limit Vertex Group Count: no targets")
        return

    yield ProgressInfo(
        phase="limit_vertex_groups",
        progress=0.0,
        message=T("mce_progress_limit_vertex_groups").format(current=0, total=total)
    )

    for idx, obj in enumerate(targets):
        func_object_utils.set_active_object(obj)

        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            obj_start = time.perf_counter()
            bpy.ops.smoothweights.limit_groups(maxGroups=max_groups, vertexGroups='DEFORM')
            print(f"[Preprocess] Limit vertex groups {obj.name}: {time.perf_counter() - obj_start:.3f}s")
        except Exception as e:
            print(f"Failed to limit vertex group count for {obj.name}: {e}")
            import traceback
            traceback.print_exc()

        progress = (idx + 1) / total
        yield ProgressInfo(
            phase="limit_vertex_groups",
            progress=progress,
            message=T("mce_progress_limit_vertex_groups_obj").format(obj=obj.name, current=idx + 1, total=total),
            object_name=obj.name
        )

    print(f"[Preprocess] Limit Vertex Group Count total ({total} objects): {time.perf_counter() - start_time:.3f}s")


def apply_or_clear_shapekeys():
    for obj in bpy.context.selected_objects:
        if not hasattr(obj, 'data') or obj.data is None:
            continue
        if not hasattr(obj.data, 'shape_keys') or obj.data.shape_keys is None:
            continue
        if not hasattr(obj.data.shape_keys, 'key_blocks') or len(obj.data.shape_keys.key_blocks) == 0:
            continue

        # 処理対象のオブジェクトを選択
        func_object_utils.set_active_object(obj)

        if func_custom_props_utils.prop_is_true(obj, consts.APPLY_ALL_SHAPEKEYS_GROUP_NAME):
            # シェイプキーを適用
            if obj.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            print(f"Apply All ShapeKeys: {obj.name} (ShapeKey count: {len(obj.data.shape_keys.key_blocks)})")
            try:
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                print(f"  -> Successfully applied all shapekeys for {obj.name}")
            except Exception as e:
                print(f"  -> Failed to apply shapekeys for {obj.name}: {e}")
                traceback.print_exc()

        if func_custom_props_utils.prop_is_true(obj, consts.CLEAR_ALL_SHAPEKEYS_GROUP_NAME):
            # シェイプキーを全て削除
            if obj.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            print(f"Clear All ShapeKeys: {obj.name} (ShapeKey count: {len(obj.data.shape_keys.key_blocks)})")
            try:
                bpy.ops.object.shape_key_remove(all=True, apply_mix=False)
                print(f"  -> Successfully cleared all shapekeys for {obj.name}")
            except Exception as e:
                print(f"  -> Failed to clear shapekeys for {obj.name}: {e}")
                traceback.print_exc()

def export_preprocess_iter(operator) -> Generator[ProgressInfo, None, ExportPostprocessResult]:
    """エクスポート前処理（ジェネレータ版）

    Args:
        operator: エクスポートオペレーター

    Yields:
        ProgressInfo: 進捗情報

    Returns:
        ExportPostprocessResult: 処理結果
    """
    result = ExportPostprocessResult()
    preprocess_start = time.perf_counter()
    section_start = preprocess_start

    print("xxxxxx Export Preprocess xxxxxx")

    yield ProgressInfo(
        phase="reset_pose",
        progress=0.0,
        message=T("mce_progress_reset_pose")
    )

    # Armatureのポーズをリセットする
    print("--- Reset Pose ---")
    selected_objects = bpy.context.selected_objects
    for obj in selected_objects:
        if obj.type != 'ARMATURE':
            continue
        if not func_custom_props_utils.prop_is_true(obj, consts.RESET_POSE_GROUP_NAME):
            continue
        print("Reset Pose: " + obj.name)
        for pose_bone in obj.pose.bones:
            pose_bone.matrix_basis = Matrix()
    print(f"[Preprocess] Reset Pose: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="reset_shapekey",
        progress=0.05,
        message=T("mce_progress_reset_shapekey")
    )

    # シェイプキーをリセットする
    print("--- Reset ShapeKey ---")
    for obj in selected_objects:
        if not func_custom_props_utils.prop_is_true(obj, consts.RESET_SHAPEKEY_GROUP_NAME):
            continue
        if not obj.data or not hasattr(obj.data, 'shape_keys') or not hasattr(obj.data.shape_keys, 'key_blocks'):
            continue
        print("Reset ShapeKey: " + obj.name)
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0
    print(f"[Preprocess] Reset ShapeKey: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="apply_shapekeys_before",
        progress=0.1,
        message=T("mce_progress_apply_shapekeys_before")
    )

    # マージ前にシェイプキーを適用/削除して、後続のシェイプキー関連処理をスキップ可能にする
    print("--- Apply/Clear ShapeKeys (Before Merge) ---")
    apply_or_clear_shapekeys()
    print(f"[Preprocess] Apply/Clear ShapeKeys: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="auto_merge",
        progress=0.15,
        message=T("mce_progress_automerge")
    )

    # ↓ AutoMergeアドオン連携
    print("--- AutoMerge ---")
    if operator.enable_auto_merge:
        try:
            # ジェネレータが利用可能ならジェネレータを使用
            # （計測はジェネレータ内部で行われる）
            if func_addon_link.auto_merge_iter_is_available():
                merge_gen = bpy.types.WindowManager.automerge_get_merge_iter(
                    operator=operator,
                    use_shapekeys_util=operator.enable_apply_modifiers_with_shapekeys,
                    use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon,
                    remove_non_render_mod=operator.use_mesh_modifiers_render,
                    use_variants_merge=operator.use_variants_merge
                )
                # サブ進捗を伝播（15%〜40%の範囲）
                for sub_progress in merge_gen:
                    mapped_progress = 0.15 + (sub_progress.progress * 0.25)
                    yield ProgressInfo(
                        phase=f"merge_{sub_progress.phase}",
                        progress=mapped_progress,
                        message=sub_progress.message,
                        object_name=sub_progress.object_name
                    )
            else:
                # 同期版オペレーターにフォールバック
                bpy.ops.object.apply_modifier_and_merge_grouped_exporter_addon(
                    use_shapekeys_util=operator.enable_apply_modifiers_with_shapekeys,
                    remove_non_render_mod=operator.use_mesh_modifiers_render,
                    use_variants_merge=operator.use_variants_merge,
                    use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon
                )
        except AttributeError:
            t = "!!! Failed to load AutoMerge !!!"
            print(t)
            operator.report({'WARNING'}, t)
            traceback.print_exc()
    print(f"[Preprocess] AutoMerge: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()
    # ↑ AutoMergeアドオン連携

    print("xxxxxx Export Targets xxxxxx\n" + '\n'.join(
        [obj.name for obj in bpy.context.selected_objects]) + "\nxxxxxxxxxxxxxxx")

    yield ProgressInfo(
        phase="shapekeys_util",
        progress=0.4,
        message=T("mce_progress_shapekeysutil")
    )

    # ShapeKeysUtil連携
    print("--- ShapeKeysUtil ---")
    shapekeys_util_start = time.perf_counter()
    if func_addon_link.shapekey_util_is_found():
        use_iter = func_addon_link.shapekey_util_iter_is_available()

        if operator.enable_apply_modifiers_with_shapekeys and operator.use_mesh_modifiers:
            active = func_object_utils.get_active_object()
            selected_objects = bpy.context.selected_objects
            all_export_targets = [d for d in selected_objects if d.type == 'MESH']
            total_targets = len(all_export_targets)

            for idx, obj in enumerate(all_export_targets):
                base_progress = 0.4 + (0.2 * idx / max(total_targets, 1))
                yield ProgressInfo(
                    phase="apply_modifiers",
                    progress=base_progress,
                    message=T("mce_progress_apply_modifiers").format(obj=obj.name),
                    object_name=obj.name
                )
                func_object_utils.set_active_object(obj)

                if use_iter:
                    # ジェネレータを使用して進捗を伝播
                    apply_gen = bpy.types.WindowManager.shapekeys_util_get_apply_modifiers_iter(
                        remove_nonrender=False,
                        use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon
                    )
                    progress_range = 0.2 / max(total_targets, 1)
                    for sub_progress in apply_gen:
                        mapped_progress = base_progress + (sub_progress.progress * progress_range)
                        yield ProgressInfo(
                            phase=f"apply_{sub_progress.phase}",
                            progress=mapped_progress,
                            message=sub_progress.message,
                            object_name=sub_progress.object_name or obj.name
                        )
                else:
                    # 同期版オペレーターにフォールバック
                    bpy.ops.object.shapekeys_util_apply_mod_for_exporter_addon(
                        use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon)

            # 選択オブジェクトを復元
            for obj in selected_objects:
                obj.select_set(True)
            func_object_utils.set_active_object(active)

        yield ProgressInfo(
            phase="separate_lr",
            progress=0.6,
            message=T("mce_progress_separate_lr_shapekey")
        )

        if operator.enable_separate_lr_shapekey:
            targets_for_lr = [
                obj for obj in bpy.context.selected_objects
                if obj.type == 'MESH' and obj.data.shape_keys is not None and len(obj.data.shape_keys.key_blocks) != 0
            ]
            total_lr = len(targets_for_lr)

            for idx, obj in enumerate(targets_for_lr):
                base_progress = 0.6 + (0.05 * idx / max(total_lr, 1))
                func_object_utils.set_active_object(obj)

                if use_iter:
                    # ジェネレータを使用
                    lr_gen = bpy.types.WindowManager.shapekeys_util_get_separate_lr_iter()
                    progress_range = 0.05 / max(total_lr, 1)
                    for sub_progress in lr_gen:
                        mapped_progress = base_progress + (sub_progress.progress * progress_range)
                        yield ProgressInfo(
                            phase=f"lr_{sub_progress.phase}",
                            progress=mapped_progress,
                            message=sub_progress.message,
                            object_name=sub_progress.object_name or obj.name
                        )
                else:
                    # 同期版オペレーターにフォールバック
                    bpy.ops.object.shapekeys_util_separate_lr_shapekey_for_exporter()

        yield ProgressInfo(
            phase="subtract_base",
            progress=0.65,
            message=T("mce_progress_subtract_base_shapekey")
        )

        if operator.enable_subtract_base_shapekey:
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH' and obj.data.shape_keys is not None and len(
                        obj.data.shape_keys.key_blocks) != 0:
                    func_object_utils.set_active_object(obj)
                    # subtract_base_shapekeyはジェネレータ化していないので同期版を使用
                    bpy.ops.object.shapekeys_util_subtract_base_shapekey_for_exporter()

        # ベースシェイプキー変更
        yield ProgressInfo(
            phase="change_base_shapekey",
            progress=0.66,
            message=T("mce_progress_change_base_shapekey")
        )

        if operator.enable_change_base_shapekey and func_addon_link.shapekey_util_change_base_is_available():
            objects_with_change_base = []
            for obj in bpy.context.selected_objects:
                if obj.type != 'MESH' or obj.data.shape_keys is None:
                    continue
                if not hasattr(obj, 'mizore_change_base_shapekeys') or len(obj.mizore_change_base_shapekeys) == 0:
                    continue
                settings = [
                    (item.source_shapekey_name, item.reverse_shapekey_name)
                    for item in obj.mizore_change_base_shapekeys
                    if item.source_shapekey_name
                ]
                if settings:
                    objects_with_change_base.append((obj, settings))

            if objects_with_change_base:
                change_base_gen = bpy.types.WindowManager.shapekeys_util_get_change_base_iter(
                    objects_with_change_base
                )
                for sub_progress in change_base_gen:
                    mapped_progress = 0.66 + (sub_progress.progress * 0.01)
                    yield ProgressInfo(
                        phase=f"change_base_{sub_progress.phase}",
                        progress=mapped_progress,
                        message=sub_progress.message,
                        object_name=sub_progress.object_name
                    )

        # シェイプキー並び替え
        yield ProgressInfo(
            phase="reorder_shapekeys",
            progress=0.68,
            message=T("mce_progress_reorder_shapekeys")
        )

        if operator.enable_reorder_shapekeys and func_addon_link.shapekey_util_reorder_is_available():
            objects_with_reorder = []
            for obj in bpy.context.selected_objects:
                if obj.type != 'MESH' or obj.data.shape_keys is None:
                    continue
                if not hasattr(obj, 'mizore_reorder_shapekeys') or len(obj.mizore_reorder_shapekeys) == 0:
                    continue
                operations = []
                for item in obj.mizore_reorder_shapekeys:
                    op = {'type': item.operation_type}
                    if item.operation_type in ('MOVE_TO_INDEX', 'SWAP', 'MOVE_BEFORE'):
                        op['target'] = item.target_shapekey_name
                    if item.operation_type == 'MOVE_TO_INDEX':
                        op['index'] = item.destination_index
                    if item.operation_type in ('SWAP', 'MOVE_BEFORE'):
                        op['second'] = item.second_shapekey_name
                    operations.append(op)
                if operations:
                    objects_with_reorder.append((obj, operations))

            if objects_with_reorder:
                reorder_gen = bpy.types.WindowManager.shapekeys_util_get_reorder_iter(
                    objects_with_reorder
                )
                for sub_progress in reorder_gen:
                    mapped_progress = 0.68 + (sub_progress.progress * 0.01)
                    yield ProgressInfo(
                        phase=f"reorder_{sub_progress.phase}",
                        progress=mapped_progress,
                        message=sub_progress.message,
                        object_name=sub_progress.object_name
                    )

        result.success_shapekey_util = True
    else:
        t = "!!! Failed to load ShapeKeysUtil !!! - apply_modifiers_with_shapekeys"
        print(t)
        operator.report({'ERROR'}, t)
    print(f"[Preprocess] ShapeKeysUtil: {time.perf_counter() - shapekeys_util_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="transform",
        progress=0.7,
        message=T("mce_progress_transform")
    )

    # Transform操作
    print("--- Transform ---")
    temp_selected = bpy.context.selected_objects
    temp_active = func_object_utils.get_active_object()
    for obj in temp_selected:
        if func_custom_props_utils.prop_is_true(obj, consts.MOVE_TO_ORIGIN_GROUP_NAME):
            # オブジェクトを原点に移動する
            print("Move To Origin: " + obj.name)
            obj.location = (0, 0, 0)

        apply_location = func_custom_props_utils.prop_is_true(obj, consts.APPLY_LOCATIONS_GROUP_NAME)
        apply_rotation = func_custom_props_utils.prop_is_true(obj, consts.APPLY_ROTATIONS_GROUP_NAME)
        apply_scale = func_custom_props_utils.prop_is_true(obj, consts.APPLY_SCALES_GROUP_NAME)
        if apply_location or apply_rotation or apply_scale:
            # Transformを適用する
            print(f"Apply: {obj.name} - Location: {apply_location} / Rotation: {apply_rotation} / Scale: {apply_scale}")
            func_object_utils.deselect_all_objects()
            func_object_utils.select_object(obj)
            func_object_utils.set_active_object(obj)
            bpy.ops.object.transform_apply(location=apply_location, rotation=apply_rotation, scale=apply_scale)
    func_object_utils.select_objects(temp_selected, True)
    func_object_utils.set_active_object(temp_active)
    print(f"[Preprocess] Transform: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="modify",
        progress=0.8,
        message=T("mce_progress_modify")
    )

    print("--- Modify ---")
    # Name Collision修復（全体設定）
    if operator.enable_fix_vertex_group_collisions:
        print("--- Fix Vertex Group Name Collisions ---")
        for obj in bpy.context.selected_objects:
            if obj.type != 'MESH':
                continue
            func_object_utils.set_active_object(obj)
            fixed_count, attr_removed_count, affected_vertices, attr_affected_vertices = func_fix_vertex_group_collisions.fix_vertex_group_name_collisions(obj)
            if fixed_count > 0 or attr_removed_count > 0:
                report_parts = []
                if fixed_count > 0:
                    report_parts.append(f"{fixed_count} vertex group collisions")
                if attr_removed_count > 0:
                    report_parts.append(f"{attr_removed_count} attribute collisions")
                print(f"Fixed {', '.join(report_parts)} in {obj.name}")

    if operator.enable_limit_vertex_group_count:
        # Limit Vertex Group処理（ジェネレータで進捗表示・負荷分散）
        # 進捗範囲: 0.80 - 0.85
        limit_gen = limit_vertex_group_count_iter(
            max_groups=operator.limit_vertex_group_count
        )
        for sub_progress in limit_gen:
            mapped_progress = 0.80 + (sub_progress.progress * 0.05)
            yield ProgressInfo(
                phase=f"modify_{sub_progress.phase}",
                progress=mapped_progress,
                message=sub_progress.message,
                object_name=sub_progress.object_name
            )

    # その他のModify処理（オブジェクト個別設定）
    for obj in bpy.context.selected_objects:
        if obj.type != 'MESH':
            continue
        if func_custom_props_utils.prop_is_true(obj, consts.REMOVE_GROUPS_NOT_BONE_GROUP_NAME):
            # ボーン名以外の頂点グループを削除
            func_object_utils.set_active_object(obj)
            func_remove_groups_not_bones.remove_groups_not_bones()
        if func_custom_props_utils.prop_is_true(obj, consts.REMOVE_UNUSED_GROUPS_GROUP_NAME):
            # 使用されていない頂点グループを削除
            func_object_utils.set_active_object(obj)
            func_remove_unused_groups.remove_unused_groups(search_data_transfer_modifier=True)
        if func_custom_props_utils.prop_is_true(obj, consts.CONVERT_UV_TILES_TO_SINGLE_GROUP_NAME):
            # UVタイルを1つにする
            func_object_utils.set_active_object(obj)
            func_convert_uv_tiles_to_single.convert_uv_tiles_to_single()
    print(f"[Preprocess] Modify: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="apply_shapekeys_after",
        progress=0.9,
        message=T("mce_progress_apply_shapekeys_after")
    )

    # マージやApply Modifierで増えたシェイプキーを適用/削除する
    print("--- Apply/Clear ShapeKeys (After Merge) ---")
    apply_or_clear_shapekeys()
    print(f"[Preprocess] Apply/Clear ShapeKeys (After): {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="constraints",
        progress=0.95,
        message=T("mce_progress_constraints")
    )

    print("--- Constraints ---")
    if operator.bake_anim and not operator.bake_anim_use_bone_constraint:
        # Constraintsを無効化
        for obj in bpy.context.selected_objects:
            if obj.type == 'ARMATURE':
                for bone in obj.pose.bones:
                    for c in bone.constraints:
                        c.enabled = False
    print(f"[Preprocess] Constraints: {time.perf_counter() - section_start:.3f}s")

    yield ProgressInfo(
        phase="complete",
        progress=1.0,
        message=T("mce_progress_preprocess_complete")
    )

    print(f"[Preprocess] total: {time.perf_counter() - preprocess_start:.3f}s")
    print("xxxxxx Export Preprocess End xxxxxx")
    return result


def export_preprocess(operator) -> ExportPostprocessResult:
    """エクスポート前処理（同期版ラッパー）

    既存コードとの互換性のため、ジェネレータ版を消費して実行します。
    """
    gen = export_preprocess_iter(operator)
    result = None
    try:
        while True:
            next(gen)
    except StopIteration as e:
        result = e.value
    return result if result is not None else ExportPostprocessResult()
