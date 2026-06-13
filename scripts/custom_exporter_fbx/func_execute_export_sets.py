import os
import time

import bpy

from .. import consts
from ..export_sets import func_export_sets
from ..export_sets.shapekey_order_override import resolver as shapekey_order_override_resolver
from ..funcs import func_addon_link
from ..funcs.modal.progress_info import ProgressInfo
from ..funcs.utils import func_custom_props_utils, func_object_utils


EXPORT_PROGRESS_START = 0.80
EXPORT_PROGRESS_SPAN = 0.19


def log_export_set_stage(export_set_name: str, stage: str, detail: str = ""):
    if detail:
        print(f"[ExportSets][{stage}] {export_set_name}: {detail}")
    else:
        print(f"[ExportSets][{stage}] {export_set_name}")


def format_elapsed_detail(elapsed_seconds: float, detail: str = "") -> str:
    elapsed_detail = f"elapsed={elapsed_seconds:.3f}s"
    if detail:
        return f"{elapsed_detail} {detail}"
    return elapsed_detail


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
    set_span = EXPORT_PROGRESS_SPAN / safe_total_sets
    set_start = EXPORT_PROGRESS_START + (set_span * set_index)
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


def prepare_export_set_preprocess_targets(export_sets, available_roots, object_types, is_object_type_enabled_for_export):
    export_set_available_roots = list(available_roots)
    export_set_item_contexts_by_ptr = {}
    preprocess_targets = []
    preprocess_target_pointers = set()
    preprocess_descendant_roots = []
    preprocess_descendant_root_pointers = set()

    for export_set in export_sets:
        item_contexts = func_export_sets.resolve_export_set_item_contexts(
            export_set=export_set,
            available_objects=available_roots,
        )
        export_set_item_contexts_by_ptr[export_set.as_pointer()] = item_contexts
        resolved_objects = func_export_sets.collect_export_set_objects_from_contexts(item_contexts)
        for item_context in item_contexts:
            effective_root = item_context.effective_root
            if effective_root is None or not func_export_sets.object_exists(effective_root):
                continue
            effective_root_pointer = effective_root.as_pointer()
            if effective_root_pointer in preprocess_descendant_root_pointers:
                continue
            preprocess_descendant_root_pointers.add(effective_root_pointer)
            preprocess_descendant_roots.append(effective_root)
        for obj in resolved_objects:
            if not func_export_sets.object_exists(obj):
                continue
            if obj.type != 'ARMATURE' and not is_object_type_enabled_for_export(object_types, obj):
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
        if preprocess_descendant_roots:
            func_object_utils.select_children_recursive(preprocess_descendant_roots)
        dont_export_objects = func_custom_props_utils.get_objects_prop_is_true(
            prop_name=consts.DONT_EXPORT_GROUP_NAME,
            affect_children=True,
            targets=list(bpy.context.selected_objects),
        )
        for obj in dont_export_objects:
            func_object_utils.select_object(obj, False)
            obj.hide_set(True)
        if active_object in preprocess_targets:
            func_object_utils.set_active_object(active_object)
        else:
            func_object_utils.set_active_object(preprocess_targets[0])
        print(
            "[ExportSets] preprocess targets=[" +
            ", ".join(obj.name for obj in preprocess_targets) +
            "]"
        )

    return export_set_available_roots, export_set_item_contexts_by_ptr


def build_export_set_runtime_for_job(
    operator,
    result,
    export_set,
    export_set_name,
    index,
    total_sets,
    all_export_targets,
    export_set_available_roots,
    export_set_item_contexts_by_ptr,
):
    yield build_export_set_progress(
        export_set_name=export_set_name,
        stage="build_runtime",
        set_index=index,
        total_sets=total_sets,
        stage_progress=0.02,
        message=f"Export Set {index + 1}/{total_sets}: resolve targets",
    )
    log_export_set_stage(export_set_name, "build_runtime", "start")
    stage_start = time.perf_counter()
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
    elapsed = time.perf_counter() - stage_start
    if not runtime.duplicate_objects:
        warning = f"Export Set '{export_set_name}': no export targets resolved"
        log_export_set_stage(
            export_set_name,
            "build_runtime",
            format_elapsed_detail(elapsed, "duplicate_objects=0 export_targets=0"),
        )
        print(warning)
        operator.report({'WARNING'}, warning)
        result.add_warning(warning)
        return None, None

    runtime_targets = func_export_sets.get_export_objects_from_runtime(runtime)
    log_export_set_stage(
        export_set_name,
        "build_runtime",
        format_elapsed_detail(
            elapsed,
            f"duplicate_objects={len(runtime.duplicate_objects)} export_targets={len(runtime_targets)}",
        ),
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
    return runtime, runtime_targets


def transform_export_set_runtime_for_job(
    operator,
    export_set,
    export_set_name,
    index,
    total_sets,
    runtime,
    runtime_targets,
):
    log_export_set_stage(export_set_name, "retarget", "start")
    stage_start = time.perf_counter()
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
    log_export_set_stage(
        export_set_name,
        "retarget",
        format_elapsed_detail(
            time.perf_counter() - stage_start,
            f"export_targets={len(runtime_targets)}",
        ),
    )

    log_export_set_stage(export_set_name, "vertex_color", "start")
    stage_start = time.perf_counter()
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
    log_export_set_stage(
        export_set_name,
        "vertex_color",
        format_elapsed_detail(time.perf_counter() - stage_start),
    )

    if export_set.merge_armatures:
        log_export_set_stage(export_set_name, "merge_armatures", "start")
        stage_start = time.perf_counter()
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
        log_export_set_stage(
            export_set_name,
            "merge_armatures",
            format_elapsed_detail(
                time.perf_counter() - stage_start,
                f"export_targets={len(runtime_targets)}",
            ),
        )

    if export_set.join_meshes_to_one:
        log_export_set_stage(export_set_name, "join_meshes", "start")
        stage_start = time.perf_counter()
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
        log_export_set_stage(
            export_set_name,
            "join_meshes",
            format_elapsed_detail(
                time.perf_counter() - stage_start,
                f"export_targets={len(runtime_targets)}",
            ),
        )

    if operator.enable_reorder_shapekeys and func_addon_link.shapekey_util_reorder_is_available():
        objects_with_reorder = shapekey_order_override_resolver.build_export_set_reorder_targets(
            export_set,
            runtime,
        )
        reorder_target_count = len(objects_with_reorder)
        reorder_operation_count = sum(len(operations) for _, operations in objects_with_reorder)
        if objects_with_reorder:
            first_reorder_target_name = get_reorder_target_name(objects_with_reorder[0])
            log_export_set_stage(
                export_set_name,
                "reorder_shapekeys",
                f"start objects={reorder_target_count} operations={reorder_operation_count}",
            )
            stage_start = time.perf_counter()
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
            log_export_set_stage(
                export_set_name,
                "reorder_shapekeys",
                format_elapsed_detail(
                    time.perf_counter() - stage_start,
                    f"objects={reorder_target_count} operations={reorder_operation_count}",
                ),
            )
        else:
            log_export_set_stage(
                export_set_name,
                "reorder_shapekeys",
                "skip objects=0 operations=0",
            )

    return func_export_sets.get_export_objects_from_runtime(runtime)


def export_export_set_runtime_for_job(
    operator,
    context,
    keywords,
    result,
    export_set,
    export_set_name,
    index,
    total_sets,
    runtime,
    targets,
    export_fbx_with_temporarily_safe_mesh_names,
):
    if not targets:
        warning = f"Export Set '{export_set_name}': no duplicated export targets remained"
        print(warning)
        operator.report({'WARNING'}, warning)
        result.add_warning(warning)
        return

    export_path = func_export_sets.build_export_set_filepath(operator.filepath, export_set)
    log_export_set_stage(
        export_set_name,
        "export_fbx",
        f"start target_count={len(targets)} path={export_path}",
    )
    stage_start = time.perf_counter()
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
    func_object_utils.set_active_object(targets[0])

    export_dir = os.path.dirname(export_path)
    if export_dir and not os.path.exists(export_dir):
        os.makedirs(export_dir)

    print("export set: " + export_path)
    export_fbx_with_temporarily_safe_mesh_names(
        operator,
        context,
        export_path,
        keywords,
        scale_duplicate_source_pairs=runtime.duplicate_source_pairs,
        scale_duplicate_objects=targets,
    )
    result.add_exported_file(export_path)
    log_export_set_stage(
        export_set_name,
        "export_fbx",
        format_elapsed_detail(
            time.perf_counter() - stage_start,
            f"target_count={len(targets)} path={export_path}",
        ),
    )
    yield build_export_set_progress(
        export_set_name=export_set_name,
        stage="export_fbx",
        set_index=index,
        total_sets=total_sets,
        stage_progress=0.96,
        message=f"Export Set {index + 1}/{total_sets}: export complete",
        object_name=targets[0].name,
    )


def cleanup_export_set_runtime(export_set_name, runtime):
    log_export_set_stage(export_set_name, "cleanup_runtime", "start")
    stage_start = time.perf_counter()
    func_export_sets.cleanup_runtime(runtime)
    log_export_set_stage(
        export_set_name,
        "cleanup_runtime",
        format_elapsed_detail(time.perf_counter() - stage_start),
    )


def restore_saved_export_set_selection(saved_selection, saved_active):
    func_object_utils.deselect_all_objects()
    func_object_utils.select_objects(
        [obj for obj in saved_selection if func_export_sets.object_exists(obj)],
        True,
    )
    if saved_active is not None and func_export_sets.object_exists(saved_active):
        func_object_utils.set_active_object(saved_active)


def run_export_set_jobs(
    operator,
    context,
    keywords,
    result,
    all_export_targets,
    export_set_available_roots,
    export_set_item_contexts_by_ptr,
    export_fbx_with_temporarily_safe_mesh_names,
):
    export_sets = list(func_export_sets.iter_enabled_export_sets(bpy.context.scene))
    if not export_sets:
        result.add_error("Batch Mode is set to Export Sets, but no enabled export set was found.")
        operator.report({'ERROR'}, "Batch Mode is set to Export Sets, but no enabled export set was found.")
        return

    saved_selection = list(bpy.context.selected_objects)
    saved_active = func_object_utils.get_active_object()
    total_sets = len(export_sets)

    try:
        for index, export_set in enumerate(export_sets):
            export_set_name = func_export_sets.get_export_set_display_name(export_set)
            runtime, runtime_targets = yield from build_export_set_runtime_for_job(
                operator,
                result,
                export_set,
                export_set_name,
                index,
                total_sets,
                all_export_targets,
                export_set_available_roots,
                export_set_item_contexts_by_ptr,
            )
            if runtime is None:
                continue

            try:
                targets = yield from transform_export_set_runtime_for_job(
                    operator,
                    export_set,
                    export_set_name,
                    index,
                    total_sets,
                    runtime,
                    runtime_targets,
                )
                yield from export_export_set_runtime_for_job(
                    operator,
                    context,
                    keywords,
                    result,
                    export_set,
                    export_set_name,
                    index,
                    total_sets,
                    runtime,
                    targets,
                    export_fbx_with_temporarily_safe_mesh_names,
                )
            finally:
                cleanup_export_set_runtime(export_set_name, runtime)
    finally:
        restore_saved_export_set_selection(saved_selection, saved_active)
