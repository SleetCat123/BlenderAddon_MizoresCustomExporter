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
from ..export_sets.shapekey_order_override import resolver as shapekey_order_override_resolver


class ExportPostprocessResult:
    success_shapekey_util: bool = False


def _phase_progress(
    start: float,
    end: float,
    current_index: int,
    total_count: int,
    *,
    at_start: bool = False,
) -> float:
    if total_count <= 0:
        return start
    completed = current_index if at_start else (current_index + 1)
    return start + (completed / total_count) * (end - start)


def _build_phase_progress(
    *,
    phase: str,
    message: str,
    start: float,
    end: float,
    current_index: int,
    total_count: int,
    object_name: str = "",
    at_start: bool = False,
) -> ProgressInfo:
    safe_total = max(total_count, 0)
    progress = _phase_progress(start, end, current_index, safe_total, at_start=at_start)
    if safe_total <= 0:
        sub_progress = 0.0
    elif at_start:
        sub_progress = current_index / safe_total
    else:
        sub_progress = (current_index + 1) / safe_total
    return ProgressInfo(
        phase=phase,
        progress=progress,
        message=message,
        object_name=object_name,
        sub_progress=sub_progress,
        total_objects=safe_total,
        current_object_index=(current_index + 1) if safe_total > 0 else 0,
    )


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
    saved_selection = list(bpy.context.selected_objects)
    saved_active = func_object_utils.get_active_object()

    if total == 0:
        print("[Preprocess] Limit Vertex Group Count: no targets")
        return

    yield ProgressInfo(
        phase="limit_vertex_groups",
        progress=0.0,
        message=T("mce_progress_limit_vertex_groups").format(current=0, total=total),
        total_objects=total,
    )

    for idx, obj in enumerate(targets):
        func_object_utils.deselect_all_objects()
        func_object_utils.select_object(obj, True)
        func_object_utils.set_active_object(obj)

        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            obj_start = time.perf_counter()
            bpy.ops.object.vertex_group_limit_total(
                group_select_mode='BONE_DEFORM',
                limit=max_groups,
            )
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
            object_name=obj.name,
            sub_progress=progress,
            total_objects=total,
            current_object_index=idx + 1,
        )

    func_object_utils.deselect_all_objects()
    func_object_utils.select_objects(saved_selection, True)
    if saved_active is not None:
        func_object_utils.set_active_object(saved_active)

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


def iter_apply_or_clear_shapekeys(
    *,
    phase: str,
    message: str,
    start: float,
    end: float,
) -> Generator[ProgressInfo, None, None]:
    targets = []
    for obj in bpy.context.selected_objects:
        if not hasattr(obj, 'data') or obj.data is None:
            continue
        if not hasattr(obj.data, 'shape_keys') or obj.data.shape_keys is None:
            continue
        if not hasattr(obj.data.shape_keys, 'key_blocks') or len(obj.data.shape_keys.key_blocks) == 0:
            continue

        apply_all = func_custom_props_utils.prop_is_true(obj, consts.APPLY_ALL_SHAPEKEYS_GROUP_NAME)
        clear_all = func_custom_props_utils.prop_is_true(obj, consts.CLEAR_ALL_SHAPEKEYS_GROUP_NAME)
        if not apply_all and not clear_all:
            continue
        targets.append((obj, apply_all, clear_all))

    total_targets = len(targets)
    for idx, (obj, apply_all, clear_all) in enumerate(targets):
        actions = []
        if apply_all:
            actions.append("apply")
        if clear_all:
            actions.append("clear")
        print(
            f"[Preprocess][{phase}] {idx + 1}/{total_targets} {obj.name} "
            f"actions={','.join(actions)} shapekeys={len(obj.data.shape_keys.key_blocks)}"
        )

        func_object_utils.set_active_object(obj)
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if apply_all:
            print(f"Apply All ShapeKeys: {obj.name} (ShapeKey count: {len(obj.data.shape_keys.key_blocks)})")
            try:
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                print(f"  -> Successfully applied all shapekeys for {obj.name}")
            except Exception as e:
                print(f"  -> Failed to apply shapekeys for {obj.name}: {e}")
                traceback.print_exc()

        if clear_all:
            remaining_keys = 0 if obj.data.shape_keys is None else len(obj.data.shape_keys.key_blocks)
            print(f"Clear All ShapeKeys: {obj.name} (ShapeKey count: {remaining_keys})")
            try:
                bpy.ops.object.shape_key_remove(all=True, apply_mix=False)
                print(f"  -> Successfully cleared all shapekeys for {obj.name}")
            except Exception as e:
                print(f"  -> Failed to clear shapekeys for {obj.name}: {e}")
                traceback.print_exc()

        yield _build_phase_progress(
            phase=phase,
            message=message,
            start=start,
            end=end,
            current_index=idx,
            total_count=total_targets,
            object_name=obj.name,
        )


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

    # モディファイアタイプフィルターからスキップ対象を取得
    from . import modifier_type_filter
    skip_modifier_types = modifier_type_filter.get_skip_modifier_types(operator)
    print(f"[Preprocess] skip_modifier_types: {skip_modifier_types}")

    yield ProgressInfo(
        phase="reset_pose",
        progress=0.0,
        message=T("mce_progress_reset_pose")
    )

    # Armatureのポーズをリセットする
    print("--- Reset Pose ---")
    selected_objects = bpy.context.selected_objects
    reset_pose_targets = [
        obj for obj in selected_objects
        if obj.type == 'ARMATURE'
        and func_custom_props_utils.prop_is_true(obj, consts.RESET_POSE_GROUP_NAME)
    ]
    total_reset_pose = len(reset_pose_targets)
    for idx, obj in enumerate(reset_pose_targets):
        print(f"[Preprocess][reset_pose] {idx + 1}/{total_reset_pose} {obj.name}")
        print("Reset Pose: " + obj.name)
        for pose_bone in obj.pose.bones:
            pose_bone.matrix_basis = Matrix()
        yield _build_phase_progress(
            phase="reset_pose",
            message=T("mce_progress_reset_pose"),
            start=0.0,
            end=0.05,
            current_index=idx,
            total_count=total_reset_pose,
            object_name=obj.name,
        )
    print(f"[Preprocess] Reset Pose: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="reset_shapekey",
        progress=0.05,
        message=T("mce_progress_reset_shapekey")
    )

    # シェイプキーをリセットする
    print("--- Reset ShapeKey ---")
    reset_shapekey_targets = [
        obj for obj in selected_objects
        if func_custom_props_utils.prop_is_true(obj, consts.RESET_SHAPEKEY_GROUP_NAME)
        and obj.data
        and hasattr(obj.data, 'shape_keys')
        and hasattr(obj.data.shape_keys, 'key_blocks')
    ]
    total_reset_shapekey = len(reset_shapekey_targets)
    for idx, obj in enumerate(reset_shapekey_targets):
        print(
            f"[Preprocess][reset_shapekey] {idx + 1}/{total_reset_shapekey} "
            f"{obj.name} keys={len(obj.data.shape_keys.key_blocks)}"
        )
        print("Reset ShapeKey: " + obj.name)
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0
        yield _build_phase_progress(
            phase="reset_shapekey",
            message=T("mce_progress_reset_shapekey"),
            start=0.05,
            end=0.1,
            current_index=idx,
            total_count=total_reset_shapekey,
            object_name=obj.name,
        )
    print(f"[Preprocess] Reset ShapeKey: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="apply_shapekeys_before",
        progress=0.1,
        message=T("mce_progress_apply_shapekeys_before")
    )

    # マージ前にシェイプキーを適用/削除して、後続のシェイプキー関連処理をスキップ可能にする
    print("--- Apply/Clear ShapeKeys (Before Merge) ---")
    for progress in iter_apply_or_clear_shapekeys(
        phase="apply_shapekeys_before",
        message=T("mce_progress_apply_shapekeys_before"),
        start=0.1,
        end=0.15,
    ):
        yield progress
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
            if not func_addon_link.auto_merge_iter_is_available():
                raise AttributeError("AutoMerge iter API not available")
            merge_gen = bpy.types.WindowManager.automerge_get_merge_iter(
                operator=operator,
                use_shapekeys_util=operator.enable_apply_modifiers_with_shapekeys,
                use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon,
                remove_non_render_mod=operator.use_mesh_modifiers_render,
                skip_modifier_types=skip_modifier_types
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
                        use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon,
                        skip_modifier_types=skip_modifier_types
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
                        use_update_mesh_deform_addon=operator.use_update_mesh_deform_addon,
                        skip_modifier_types_str=','.join(skip_modifier_types))

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
                yield _build_phase_progress(
                    phase="separate_lr",
                    message=T("mce_progress_separate_lr_shapekey_obj").format(
                        obj=obj.name,
                        current=idx + 1,
                        total=total_lr,
                    ),
                    start=0.6,
                    end=0.65,
                    current_index=idx,
                    total_count=total_lr,
                    object_name=obj.name,
                    at_start=True,
                )
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
                            object_name=sub_progress.object_name or obj.name,
                            total_objects=total_lr,
                            current_object_index=idx + 1,
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
            if not func_addon_link.shapekey_util_subtract_base_is_available():
                raise AttributeError("ShapeKeysUtil subtract-base API is not available")
            subtract_targets = [
                obj for obj in bpy.context.selected_objects
                if obj.type == 'MESH' and obj.data.shape_keys is not None and len(obj.data.shape_keys.key_blocks) != 0
            ]
            total_subtract_targets = len(subtract_targets)
            for idx, obj in enumerate(subtract_targets):
                yield _build_phase_progress(
                    phase="subtract_base",
                    message=T("mce_progress_subtract_base_shapekey_obj").format(
                        obj=obj.name,
                        current=idx + 1,
                        total=total_subtract_targets,
                    ),
                    start=0.65,
                    end=0.66,
                    current_index=idx,
                    total_count=total_subtract_targets,
                    object_name=obj.name,
                    at_start=True,
                )
                func_object_utils.set_active_object(obj)
                if obj.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                bpy.types.WindowManager.shapekeys_util_subtract_base_for_exporter(obj)

        # シェイプキー並び替え
        yield ProgressInfo(
            phase="reorder_shapekeys",
            progress=0.66,
            message=T("mce_progress_reorder_shapekeys")
        )

        if (
            operator.enable_reorder_shapekeys
            and operator.batch_mode != 'EXPORT_SETS'
            and func_addon_link.shapekey_util_reorder_is_available()
        ):
            objects_with_reorder = shapekey_order_override_resolver.build_base_reorder_targets(
                bpy.context.selected_objects
            )

            if objects_with_reorder:
                total_reorder_targets = len(objects_with_reorder)
                for idx, reorder_target in enumerate(objects_with_reorder):
                    reorder_obj = reorder_target[0]
                    yield _build_phase_progress(
                        phase="reorder_shapekeys",
                        message=T("mce_progress_reorder_shapekeys_obj").format(
                            obj=reorder_obj.name,
                            current=idx + 1,
                            total=total_reorder_targets,
                        ),
                        start=0.66,
                        end=0.67,
                        current_index=idx,
                        total_count=total_reorder_targets,
                        object_name=reorder_obj.name,
                        at_start=True,
                    )
                    reorder_gen = bpy.types.WindowManager.shapekeys_util_get_reorder_iter(
                        [reorder_target]
                    )
                    progress_range = 0.01 / max(total_reorder_targets, 1)
                    for sub_progress in reorder_gen:
                        mapped_progress = 0.66 + (idx * progress_range) + (sub_progress.progress * progress_range)
                        yield ProgressInfo(
                            phase=f"reorder_{sub_progress.phase}",
                            progress=mapped_progress,
                            message=sub_progress.message,
                            object_name=sub_progress.object_name or reorder_obj.name,
                            total_objects=total_reorder_targets,
                            current_object_index=idx + 1,
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
    transform_targets = []
    for obj in temp_selected:
        move_to_origin = func_custom_props_utils.prop_is_true(obj, consts.MOVE_TO_ORIGIN_GROUP_NAME)
        apply_location = func_custom_props_utils.prop_is_true(obj, consts.APPLY_LOCATIONS_GROUP_NAME)
        apply_rotation = func_custom_props_utils.prop_is_true(obj, consts.APPLY_ROTATIONS_GROUP_NAME)
        apply_scale = func_custom_props_utils.prop_is_true(obj, consts.APPLY_SCALES_GROUP_NAME)
        if move_to_origin or apply_location or apply_rotation or apply_scale:
            transform_targets.append((obj, move_to_origin, apply_location, apply_rotation, apply_scale))

    total_transform_targets = len(transform_targets)
    for idx, (obj, move_to_origin, apply_location, apply_rotation, apply_scale) in enumerate(transform_targets):
        print(
            f"[Preprocess][transform] {idx + 1}/{total_transform_targets} {obj.name} "
            f"move_to_origin={move_to_origin} apply_location={apply_location} "
            f"apply_rotation={apply_rotation} apply_scale={apply_scale}"
        )
        if func_custom_props_utils.prop_is_true(obj, consts.MOVE_TO_ORIGIN_GROUP_NAME):
            # オブジェクトを原点に移動する
            print("Move To Origin: " + obj.name)
            obj.location = (0, 0, 0)

        if apply_location or apply_rotation or apply_scale:
            # Transformを適用する
            print(f"Apply: {obj.name} - Location: {apply_location} / Rotation: {apply_rotation} / Scale: {apply_scale}")
            func_object_utils.deselect_all_objects()
            func_object_utils.select_object(obj)
            func_object_utils.set_active_object(obj)
            bpy.ops.object.transform_apply(location=apply_location, rotation=apply_rotation, scale=apply_scale)
        yield _build_phase_progress(
            phase="transform",
            message=T("mce_progress_transform"),
            start=0.7,
            end=0.8,
            current_index=idx,
            total_count=total_transform_targets,
            object_name=obj.name,
        )
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
        collision_targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        total_collision_targets = len(collision_targets)
        for idx, obj in enumerate(collision_targets):
            print(f"[Preprocess][modify_collision] {idx + 1}/{total_collision_targets} {obj.name}")
            func_object_utils.set_active_object(obj)
            fixed_count, attr_removed_count, affected_vertices, attr_affected_vertices = func_fix_vertex_group_collisions.fix_vertex_group_name_collisions(obj)
            if fixed_count > 0 or attr_removed_count > 0:
                report_parts = []
                if fixed_count > 0:
                    report_parts.append(f"{fixed_count} vertex group collisions")
                if attr_removed_count > 0:
                    report_parts.append(f"{attr_removed_count} attribute collisions")
                print(f"Fixed {', '.join(report_parts)} in {obj.name}")
            yield _build_phase_progress(
                phase="modify",
                message=T("mce_progress_modify"),
                start=0.80,
                end=0.83,
                current_index=idx,
                total_count=total_collision_targets,
                object_name=obj.name,
            )

    if operator.enable_limit_vertex_group_count:
        # Limit Vertex Group処理（ジェネレータで進捗表示・負荷分散）
        # 進捗範囲: 0.83 - 0.87
        limit_gen = limit_vertex_group_count_iter(
            max_groups=operator.limit_vertex_group_count
        )
        for sub_progress in limit_gen:
            mapped_progress = 0.83 + (sub_progress.progress * 0.04)
            yield ProgressInfo(
                phase=f"modify_{sub_progress.phase}",
                progress=mapped_progress,
                message=sub_progress.message,
                object_name=sub_progress.object_name,
                sub_progress=sub_progress.sub_progress,
                total_objects=sub_progress.total_objects,
                current_object_index=sub_progress.current_object_index,
            )

    # その他のModify処理（オブジェクト個別設定）
    modify_targets = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    total_modify_targets = len(modify_targets)
    for idx, obj in enumerate(modify_targets):
        remove_not_bone = func_custom_props_utils.prop_is_true(obj, consts.REMOVE_GROUPS_NOT_BONE_GROUP_NAME)
        remove_unused = func_custom_props_utils.prop_is_true(obj, consts.REMOVE_UNUSED_GROUPS_GROUP_NAME)
        convert_uv_tiles = func_custom_props_utils.prop_is_true(obj, consts.CONVERT_UV_TILES_TO_SINGLE_GROUP_NAME)
        if not remove_not_bone and not remove_unused and not convert_uv_tiles:
            continue
        print(
            f"[Preprocess][modify_object] {idx + 1}/{total_modify_targets} {obj.name} "
            f"remove_not_bone={remove_not_bone} remove_unused={remove_unused} convert_uv_tiles={convert_uv_tiles}"
        )
        if remove_not_bone:
            # ボーン名以外の頂点グループを削除
            func_object_utils.set_active_object(obj)
            func_remove_groups_not_bones.remove_groups_not_bones()
        if remove_unused:
            # 使用されていない頂点グループを削除
            func_object_utils.set_active_object(obj)
            func_remove_unused_groups.remove_unused_groups(search_data_transfer_modifier=True)
        if convert_uv_tiles:
            # UVタイルを1つにする
            func_object_utils.set_active_object(obj)
            func_convert_uv_tiles_to_single.convert_uv_tiles_to_single()
        yield _build_phase_progress(
            phase="modify",
            message=T("mce_progress_modify"),
            start=0.87,
            end=0.90,
            current_index=idx,
            total_count=total_modify_targets,
            object_name=obj.name,
        )
    print(f"[Preprocess] Modify: {time.perf_counter() - section_start:.3f}s")
    section_start = time.perf_counter()

    yield ProgressInfo(
        phase="apply_shapekeys_after",
        progress=0.9,
        message=T("mce_progress_apply_shapekeys_after")
    )

    # マージやApply Modifierで増えたシェイプキーを適用/削除する
    print("--- Apply/Clear ShapeKeys (After Merge) ---")
    for progress in iter_apply_or_clear_shapekeys(
        phase="apply_shapekeys_after",
        message=T("mce_progress_apply_shapekeys_after"),
        start=0.9,
        end=0.95,
    ):
        yield progress
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
        constraint_targets = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
        total_constraint_targets = len(constraint_targets)
        for idx, obj in enumerate(constraint_targets):
            print(f"[Preprocess][constraints] {idx + 1}/{total_constraint_targets} {obj.name}")
            for bone in obj.pose.bones:
                for c in bone.constraints:
                    c.enabled = False
            yield _build_phase_progress(
                phase="constraints",
                message=T("mce_progress_constraints"),
                start=0.95,
                end=0.99,
                current_index=idx,
                total_count=total_constraint_targets,
                object_name=obj.name,
            )
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
