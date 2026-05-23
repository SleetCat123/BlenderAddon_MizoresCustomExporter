import os

import bpy

from .. import consts
from ..funcs import func_addon_link
from ..funcs.modal.progress_info import ProgressInfo
from ..funcs.utils import func_collection_utils, func_object_utils
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData


EXPORT_PROGRESS_START = 0.80
EXPORT_PROGRESS_SPAN = 0.19


def log_batch_export_stage(batch_name: str, stage: str, detail: str = ""):
    if detail:
        print(f"[BatchExport][{stage}] {batch_name}: {detail}")
    else:
        print(f"[BatchExport][{stage}] {batch_name}")


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
    item_span = EXPORT_PROGRESS_SPAN / safe_total_items
    item_start = EXPORT_PROGRESS_START + (item_span * item_index)
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


def collect_ignored_collection_names():
    ignored_collection_names = [
        consts.ALWAYS_EXPORT_GROUP_NAME,
        consts.DONT_EXPORT_GROUP_NAME,
    ]
    if not func_addon_link.auto_merge_is_found():
        return ignored_collection_names

    automerge_collection_name = bpy.types.WindowManager.mizore_automerge_collection_name
    print(f"AutoMerge Collection Name: {automerge_collection_name}")
    ignored_collection_names.append(automerge_collection_name)

    dont_merge_to_parent_collection_name = (
        bpy.types.WindowManager.mizore_automerge_dont_merge_to_parent_collection_name
    )
    print(f"Don'tMergeToParent Collection Name: {dont_merge_to_parent_collection_name}")
    ignored_collection_names.append(dont_merge_to_parent_collection_name)
    return ignored_collection_names


def collect_target_collections_for_batch_mode(operator):
    if operator.batch_mode == 'COLLECTIONS_IN_ACTIVE_COLLECTION':
        active_layer_collection = bpy.context.view_layer.active_layer_collection
        active_collection = active_layer_collection.collection
        if operator.only_root_collection:
            return [active_collection]
        return func_collection_utils.recursive_get_collections(active_collection)

    if operator.only_root_collection:
        return bpy.context.scene.collection.children
    return func_collection_utils.get_all_collections()[1:]


def build_collection_batch_job(operator, collection, export_targets_set):
    objects = func_collection_utils.get_collection_objects(
        collection=collection,
        include_children_collections=operator.use_batch_collection_children_collections,
    )
    objects = objects & export_targets_set
    if not objects:
        return None

    path = BatchExportFilepathFormatData.convert_filename_format(
        format_str=operator.batch_filename_format,
        path=operator.filepath,
        batch=collection.name,
        use_batch_own_dir=operator.use_batch_own_dir
    )
    return collection.name, list(objects), path


def append_scene_collection_batch_job_if_needed(operator, all_export_targets, batch_jobs):
    if operator.batch_mode not in {
        'SCENE_COLLECTION',
        'ACTIVE_SCENE_COLLECTION',
        'COLLECTIONS_IN_ACTIVE_COLLECTION',
    }:
        return

    batch_name = f"{bpy.context.scene.name}_Scene_Collection"
    path = BatchExportFilepathFormatData.convert_filename_format(
        format_str=operator.batch_filename_format,
        path=operator.filepath,
        batch=batch_name,
        use_batch_own_dir=operator.use_batch_own_dir
    )
    batch_jobs.append((batch_name, list(all_export_targets), path))


def build_collection_batch_jobs(operator, all_export_targets):
    ignored_collection_names = collect_ignored_collection_names()
    batch_jobs = []
    target_collections = collect_target_collections_for_batch_mode(operator)
    export_targets_set = set(all_export_targets)
    for collection in target_collections:
        if any(collection.name in name for name in ignored_collection_names):
            continue
        batch_job = build_collection_batch_job(
            operator,
            collection,
            export_targets_set,
        )
        if batch_job is None:
            continue
        batch_jobs.append(batch_job)

    append_scene_collection_batch_job_if_needed(operator, all_export_targets, batch_jobs)

    return batch_jobs


def build_objects_in_active_collection_batch_jobs(operator, all_export_targets):
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
    return batch_jobs


def build_single_batch_job(operator, all_export_targets):
    path = operator.filepath
    batch_name = bpy.context.scene.name if operator.batch_mode == 'SCENE' else os.path.basename(path)
    if operator.batch_mode == 'SCENE':
        path = BatchExportFilepathFormatData.convert_filename_format(
            format_str=operator.batch_filename_format,
            path=operator.filepath,
            batch=bpy.context.scene.name,
            use_batch_own_dir=operator.use_batch_own_dir
        )
    return [(batch_name, list(all_export_targets), path)]


def build_standard_batch_jobs_for_mode(operator, all_export_targets):
    if operator.batch_mode in {'COLLECTION', 'SCENE_COLLECTION', 'ACTIVE_SCENE_COLLECTION', 'COLLECTIONS_IN_ACTIVE_COLLECTION'}:
        return build_collection_batch_jobs(operator, all_export_targets)
    if operator.batch_mode == 'OBJECTS_IN_ACTIVE_COLLECTION':
        return build_objects_in_active_collection_batch_jobs(operator, all_export_targets)
    if operator.batch_mode in {'OFF', 'SCENE'}:
        return build_single_batch_job(operator, all_export_targets)
    return None


def run_standard_batch_jobs(
    operator,
    context,
    keywords,
    result,
    batch_jobs,
    export_fbx_with_temporarily_safe_mesh_names,
):
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

        export_dir = os.path.dirname(path)
        if export_dir and not os.path.exists(export_dir):
            os.makedirs(export_dir)

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
