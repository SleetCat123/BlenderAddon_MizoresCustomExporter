from dataclasses import dataclass
import time

import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix

from .. import consts
from ..funcs.modal.progress_info import ProgressInfo
from ..funcs.utils import (
    func_collection_utils,
    func_custom_props_utils,
    func_object_utils,
)
from . import func_export_preprocess


@dataclass
class ExportSelectionContext:
    object_types: object
    export_set_available_roots: object = None
    export_set_item_contexts_by_ptr: object = None


@dataclass
class PreparedExportExecutionContext:
    cancelled_result: object = None
    keywords: object = None
    all_export_targets: object = None


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


def ensure_always_export_objects_visible():
    always_export_objects = set(
        func_custom_props_utils.get_objects_prop_is_true(
            prop_name=consts.ALWAYS_EXPORT_GROUP_NAME
        )
    )
    layer_collection = func_collection_utils.find_or_create_collection(
        consts.ALWAYS_EXPORT_GROUP_NAME
    )
    for obj in always_export_objects:
        layer_collection.objects.link(obj)

    layer_collection.hide_viewport = False
    collection = func_collection_utils.find_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
    for obj in collection.objects:
        func_object_utils.force_unhide(obj)


def prepare_initial_selected_objects(operator):
    if operator.use_selection:
        func_object_utils.hide_unselected_objects()
    else:
        func_object_utils.select_all_objects()

    for obj in bpy.context.selected_objects:
        func_object_utils.set_active_object(obj)
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        func_object_utils.select_children_recursive()


def apply_active_collection_scope_if_needed(operator):
    active_collection_scope_mode = operator.batch_mode == 'COLLECTIONS_IN_ACTIVE_COLLECTION'
    use_active_collection_filter = operator.use_active_collection and operator.batch_mode != 'ACTIVE_SCENE_COLLECTION'
    if not (use_active_collection_filter or active_collection_scope_mode):
        return

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


def prepare_export_selection_context(
    operator,
    context,
    iter_enabled_export_sets,
    prepare_export_set_preprocess_targets,
):
    ensure_always_export_objects_visible()
    prepare_initial_selected_objects(operator)
    apply_active_collection_scope_if_needed(operator)

    object_types = operator.object_types
    filter_selected_objects_by_export_types(object_types)
    exclude_dont_export_objects()

    export_set_available_roots = None
    export_set_item_contexts_by_ptr = None

    if operator.batch_mode == 'EXPORT_SETS':
        export_sets = list(iter_enabled_export_sets(context.scene))
        if export_sets:
            export_set_available_roots, export_set_item_contexts_by_ptr = prepare_export_set_preprocess_targets(
                export_sets,
                list(context.selected_objects),
                object_types,
                is_object_type_enabled_for_export,
            )

    return ExportSelectionContext(
        object_types=object_types,
        export_set_available_roots=export_set_available_roots,
        export_set_item_contexts_by_ptr=export_set_item_contexts_by_ptr,
    )


def filter_selected_objects_by_export_types(object_types):
    if 'EMPTY' in object_types:
        return

    selected_objects = bpy.context.selected_objects
    for obj in selected_objects:
        if is_object_type_enabled_for_export(object_types, obj):
            continue
        func_object_utils.select_object(obj, False)
        obj.hide_set(True)


def exclude_dont_export_objects():
    dont_export_objects = func_custom_props_utils.get_objects_prop_is_true(
        prop_name=consts.DONT_EXPORT_GROUP_NAME,
        affect_children=True
    )
    for obj in dont_export_objects:
        func_object_utils.select_object(obj, False)
        obj.hide_set(True)


def validate_selected_object_name_lengths(operator):
    selected_objects = bpy.context.selected_objects
    for obj in selected_objects:
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
    return None


def reset_always_reset_shapekeys():
    for obj in bpy.data.objects:
        if not func_custom_props_utils.prop_is_true(obj, consts.ALWAYS_RESET_SHAPEKEY_GROUP_NAME):
            continue
        if not obj.data or not hasattr(obj.data, 'shape_keys') or not hasattr(obj.data.shape_keys, 'key_blocks'):
            continue
        print("AlwaysReset ShapeKey: " + obj.name)
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0


def normalize_export_target_modes():
    targets_source = bpy.context.selected_objects
    targets_source.sort(key=lambda x: x.name)
    for obj in targets_source:
        if obj.mode == 'POSE':
            func_object_utils.set_active_object(obj)
            bpy.ops.object.mode_set(mode='OBJECT')
    return targets_source


def log_selected_export_targets(targets_source):
    print("Targets: [")
    for obj in targets_source:
        print(obj.name)
    print("]")


def run_export_preprocess(operator):
    preprocess_gen = func_export_preprocess.export_preprocess_iter(operator=operator)
    postprocess_result = None
    try:
        while True:
            sub_progress = next(preprocess_gen)
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
    return postprocess_result


def prepare_export_execution_context_iter(
    operator,
    context,
    preprocess_message,
    export_message,
):
    validation_result = validate_selected_object_name_lengths(operator)
    if validation_result is not None:
        return PreparedExportExecutionContext(cancelled_result=validation_result)

    reset_always_reset_shapekeys()
    targets_source = normalize_export_target_modes()
    log_selected_export_targets(targets_source)

    yield ProgressInfo(
        phase="preprocess",
        progress=0.1,
        message=preprocess_message,
    )

    postprocess_result = yield from run_export_preprocess(operator)

    yield ProgressInfo(
        phase="export",
        progress=0.8,
        message=export_message,
    )

    if not operator.filepath:
        raise Exception("filepath not set")

    return PreparedExportExecutionContext(
        keywords=prepare_export_keywords(operator, postprocess_result),
        all_export_targets=list(context.selected_objects),
    )


def prepare_export_keywords(operator, postprocess_result):
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
        keywords["use_mesh_modifiers"] = False

    keywords["use_selection"] = True
    keywords["use_active_collection"] = False
    keywords["batch_mode"] = 'OFF'
    return keywords


def finalize_export_result(result, start_time, all_export_targets):
    result.processed_objects_count = len(all_export_targets)
    result.elapsed_time = time.perf_counter() - start_time
