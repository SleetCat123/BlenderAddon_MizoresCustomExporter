from dataclasses import dataclass, field

import bpy
from mathutils import Matrix

from ..funcs.utils import func_object_utils
from ..funcs.utils import func_temporary_duplicate_names


SCALE_VALUE_MODE_NORMAL = 'NORMAL'
SCALE_VALUE_MODE_KEEP = 'KEEP_VALUE'
SCALE_PIVOT_WORLD_ORIGIN = 'WORLD_ORIGIN'
SCALE_PIVOT_EACH_OBJECT_ORIGIN = 'EACH_OBJECT_ORIGIN'
TEMP_DUPLICATE_ID_PROP = "_mce_scale_value_duplicate_id"
SCALE_EPSILON = 1e-8


@dataclass
class FCurveRestoreRecord:
    fcurve: object
    keyframes: list = field(default_factory=list)
    samples: list = field(default_factory=list)


@dataclass
class ActionRestoreRecord:
    action: object
    curves: list = field(default_factory=list)


@dataclass
class TemporaryScaledExportContext:
    source_objects: list = field(default_factory=list)
    duplicate_objects: list = field(default_factory=list)
    duplicate_source_pairs: list = field(default_factory=list)
    renamed_objects: list = field(default_factory=list)
    scaled_actions: list = field(default_factory=list)
    original_selection: list = field(default_factory=list)
    original_active: object | None = None
    duplicate_active: object | None = None
    current_frame: int = 0
    current_subframe: float = 0.0
    export_frame: int = 0
    export_subframe: float = 0.0
    owns_duplicate_objects: bool = False
    owns_renamed_objects: bool = False


@dataclass
class BoneParentScaleGuard:
    duplicate_object_pointers: set = field(default_factory=set)
    original_world_matrices: dict = field(default_factory=dict)


def is_keep_scale_value_mode(operator):
    return (
        getattr(operator, "scale_value_mode", SCALE_VALUE_MODE_NORMAL) == SCALE_VALUE_MODE_KEEP
        and abs(float(getattr(operator, "global_scale", 1.0)) - 1.0) > SCALE_EPSILON
    )


def is_keep_scale_value_world_origin_mode(operator):
    return (
        is_keep_scale_value_mode(operator)
        and getattr(operator, "scale_pivot", SCALE_PIVOT_WORLD_ORIGIN) == SCALE_PIVOT_WORLD_ORIGIN
    )


def _requires_temporary_scaled_export(operator):
    return (
        is_keep_scale_value_mode(operator)
        and getattr(operator, "scale_pivot", SCALE_PIVOT_WORLD_ORIGIN) == SCALE_PIVOT_EACH_OBJECT_ORIGIN
    )


def get_export_global_scale(operator):
    if is_keep_scale_value_world_origin_mode(operator):
        return float(getattr(operator, "global_scale", 1.0))
    if _requires_temporary_scaled_export(operator):
        return 1.0
    return float(getattr(operator, "global_scale", 1.0))


def get_export_apply_scale_options(operator, current_value):
    if is_keep_scale_value_world_origin_mode(operator):
        return 'FBX_SCALE_ALL'
    if current_value is not None:
        return current_value
    return getattr(operator, "apply_scale_options", 'FBX_SCALE_UNITS')


def _resolve_export_reference_frame(operator):
    if getattr(operator, "bake_anim", False):
        return bpy.context.scene.frame_start, 0.0
    return (
        bpy.context.scene.frame_current,
        float(getattr(bpy.context.scene, "frame_subframe", 0.0)),
    )


def prepare_temporary_scaled_export(
    operator,
    existing_duplicate_source_pairs=None,
    existing_duplicate_objects=None,
):
    if not _requires_temporary_scaled_export(operator):
        return None

    selected_objects = list(bpy.context.selected_objects)
    if not selected_objects:
        return None

    context = _build_temporary_scaled_export_context(operator, selected_objects)

    try:
        _prepare_duplicate_export_targets(
            context,
            selected_objects,
            existing_duplicate_source_pairs,
            existing_duplicate_objects,
        )
        _relink_duplicate_actions_to_source_actions(context.duplicate_source_pairs)
        _apply_keep_scale_changes(context, operator)
        _restore_duplicate_active_object(context)

        return context
    except Exception:
        cleanup_temporary_scaled_export(context)
        raise


def _build_temporary_scaled_export_context(operator, selected_objects):
    export_frame, export_subframe = _resolve_export_reference_frame(operator)
    return TemporaryScaledExportContext(
        original_selection=selected_objects,
        original_active=func_object_utils.get_active_object(),
        current_frame=bpy.context.scene.frame_current,
        current_subframe=float(getattr(bpy.context.scene, "frame_subframe", 0.0)),
        export_frame=export_frame,
        export_subframe=export_subframe,
    )


def _prepare_duplicate_export_targets(
    context: TemporaryScaledExportContext,
    selected_objects,
    existing_duplicate_source_pairs,
    existing_duplicate_objects,
):
    if existing_duplicate_source_pairs is not None:
        _reuse_existing_duplicate_export_targets(
            context,
            existing_duplicate_source_pairs,
            existing_duplicate_objects,
        )
        return

    _create_temporary_duplicate_export_targets(context, selected_objects)


def _reuse_existing_duplicate_export_targets(
    context: TemporaryScaledExportContext,
    existing_duplicate_source_pairs,
    existing_duplicate_objects,
):
    context.duplicate_objects = _collect_existing_duplicate_objects(
        existing_duplicate_source_pairs,
        existing_duplicate_objects,
    )
    context.duplicate_source_pairs = _collect_surviving_duplicate_source_pairs(
        existing_duplicate_source_pairs,
        context.duplicate_objects,
    )
    context.source_objects = [source_obj for source_obj, _duplicate_obj in context.duplicate_source_pairs]


def _create_temporary_duplicate_export_targets(context: TemporaryScaledExportContext, selected_objects):
    context.source_objects = selected_objects
    context.owns_duplicate_objects = True
    context.owns_renamed_objects = True

    func_temporary_duplicate_names.set_duplicate_ids(context.source_objects, TEMP_DUPLICATE_ID_PROP)
    func_object_utils.duplicate_objects(context.source_objects, linked=False)
    context.duplicate_objects = list(bpy.context.selected_objects)
    context.duplicate_source_pairs = func_temporary_duplicate_names.build_duplicate_source_pairs(
        context.source_objects,
        context.duplicate_objects,
        TEMP_DUPLICATE_ID_PROP,
    )
    context.renamed_objects = func_temporary_duplicate_names.swap_duplicate_object_and_data_names_to_source_names(
        context.source_objects,
        context.duplicate_objects,
        TEMP_DUPLICATE_ID_PROP,
    )
    func_temporary_duplicate_names.clear_duplicate_ids(context.source_objects, TEMP_DUPLICATE_ID_PROP)
    func_temporary_duplicate_names.clear_duplicate_ids(context.duplicate_objects, TEMP_DUPLICATE_ID_PROP)


def _apply_keep_scale_changes(context: TemporaryScaledExportContext, operator):
    _refresh_scene_frame(context.export_frame, context.export_subframe)
    bone_parent_guard = _build_bone_parent_scale_guard(context.duplicate_objects)
    _apply_scale_to_duplicate_objects(context, operator, bone_parent_guard)
    _scale_source_actions_for_export(context, operator, bone_parent_guard)
    _refresh_scene_frame(context.export_frame, context.export_subframe)
    _restore_bone_parent_world_matrices(
        context.duplicate_objects,
        getattr(operator, "scale_pivot", SCALE_PIVOT_WORLD_ORIGIN),
        float(getattr(operator, "global_scale", 1.0)),
        bone_parent_guard,
    )


def _restore_duplicate_active_object(context: TemporaryScaledExportContext):
    if context.original_active is None:
        return

    context.duplicate_active = _find_duplicate_for_source_object(
        context.duplicate_source_pairs,
        context.original_active,
    )
    if context.duplicate_active is not None:
        func_object_utils.set_active_object(context.duplicate_active)


def cleanup_temporary_scaled_export(context: TemporaryScaledExportContext | None):
    if context is None:
        return

    _restore_scaled_actions(context.scaled_actions)

    if context.owns_duplicate_objects:
        for obj in list(context.duplicate_objects):
            if _object_exists(obj):
                func_object_utils.remove_object(obj)

    if context.owns_renamed_objects:
        func_temporary_duplicate_names.restore_source_object_and_data_names(context.renamed_objects)
    _refresh_scene_frame(context.current_frame, context.current_subframe)

    if context.original_selection:
        existing_selection = [obj for obj in context.original_selection if _object_exists(obj)]
        func_object_utils.deselect_all_objects()
        if existing_selection:
            func_object_utils.select_objects(existing_selection, True)
            if context.original_active is not None and _object_exists(context.original_active):
                func_object_utils.set_active_object(context.original_active)


def _relink_duplicate_actions_to_source_actions(duplicate_source_pairs):
    duplicate_actions_to_remove = []

    for source_obj, duplicate_obj in duplicate_source_pairs:
        for source_anim, duplicate_anim in _iter_relink_animation_data_pairs(source_obj, duplicate_obj):
            duplicate_actions_to_remove.extend(
                _relink_animation_data_pair(source_anim, duplicate_anim)
            )

    removed = set()
    for action in duplicate_actions_to_remove:
        if action is None:
            continue
        try:
            action_pointer = action.as_pointer()
        except ReferenceError:
            continue
        if action_pointer in removed:
            continue
        removed.add(action_pointer)
        try:
            bpy.data.actions.remove(action, do_unlink=True)
        except ReferenceError:
            continue


def _relink_animation_data_pair(source_anim, duplicate_anim):
    result = []
    if source_anim is None or duplicate_anim is None:
        return result

    source_action = getattr(source_anim, "action", None)
    duplicate_action = getattr(duplicate_anim, "action", None)
    if source_action is not None and duplicate_action is not None and source_action != duplicate_action:
        duplicate_anim.action = source_action
        result.append(duplicate_action)

    source_tracks = list(getattr(source_anim, "nla_tracks", []))
    duplicate_tracks = list(getattr(duplicate_anim, "nla_tracks", []))
    for source_track, duplicate_track in zip(source_tracks, duplicate_tracks):
        for source_strip, duplicate_strip in zip(source_track.strips, duplicate_track.strips):
            source_strip_action = getattr(source_strip, "action", None)
            duplicate_strip_action = getattr(duplicate_strip, "action", None)
            if source_strip_action is not None and duplicate_strip_action is not None and source_strip_action != duplicate_strip_action:
                duplicate_strip.action = source_strip_action
                result.append(duplicate_strip_action)

    return result


def _apply_scale_to_duplicate_objects(
    context: TemporaryScaledExportContext,
    operator,
    bone_parent_guard: BoneParentScaleGuard,
):
    factor = float(getattr(operator, "global_scale", 1.0))
    if abs(factor - 1.0) <= SCALE_EPSILON:
        return

    pivot = getattr(operator, "scale_pivot", SCALE_PIVOT_WORLD_ORIGIN)
    scale_matrix = Matrix.Scale(factor, 4)
    selected_before = list(bpy.context.selected_objects)
    active_before = func_object_utils.get_active_object()

    try:
        for duplicate_obj in context.duplicate_objects:
            if not _object_exists(duplicate_obj):
                continue
            if _should_scale_world_origin_translation(duplicate_obj, pivot, bone_parent_guard):
                _scale_object_world_origin_translation(duplicate_obj, factor)
            if _should_scale_object_data(duplicate_obj, bone_parent_guard):
                _scale_object_data(duplicate_obj, factor, scale_matrix)
    finally:
        func_object_utils.deselect_all_objects()
        if selected_before:
            func_object_utils.select_objects(selected_before, True)
        if active_before is not None and _object_exists(active_before):
            func_object_utils.set_active_object(active_before)


def _build_bone_parent_scale_guard(objects):
    duplicate_object_pointers = set()
    for obj in objects:
        if not _object_exists(obj):
            continue
        try:
            duplicate_object_pointers.add(obj.as_pointer())
        except ReferenceError:
            continue

    return BoneParentScaleGuard(
        duplicate_object_pointers=duplicate_object_pointers,
        original_world_matrices=_collect_bone_parent_world_matrices(
            objects,
            duplicate_object_pointers,
        ),
    )


def _collect_bone_parent_world_matrices(objects, duplicate_object_pointers):
    result = {}
    for obj in objects:
        if not _object_exists(obj):
            continue
        if not _is_in_bone_parent_subtree(obj, duplicate_object_pointers):
            continue
        try:
            result[obj.as_pointer()] = obj.matrix_world.copy()
        except ReferenceError:
            continue
    return result


def _is_in_bone_parent_subtree(obj, duplicate_object_pointers):
    current = obj
    while _object_exists(current):
        parent = getattr(current, "parent", None)
        if parent is None or not _object_exists(parent):
            return False
        try:
            parent_pointer = parent.as_pointer()
        except ReferenceError:
            return False
        if parent_pointer not in duplicate_object_pointers:
            return False
        if getattr(current, "parent_type", 'OBJECT') == 'BONE':
            return True
        current = parent
    return False


def _should_scale_world_origin_translation(obj, pivot, bone_parent_guard: BoneParentScaleGuard):
    return (
        pivot == SCALE_PIVOT_WORLD_ORIGIN
        and not _is_in_bone_parent_subtree(obj, bone_parent_guard.duplicate_object_pointers)
    )


def _restore_bone_parent_world_matrices(
    objects,
    pivot,
    factor,
    bone_parent_guard: BoneParentScaleGuard,
):
    if not bone_parent_guard.original_world_matrices:
        return

    if pivot == SCALE_PIVOT_WORLD_ORIGIN:
        world_scale_matrix = Matrix.Scale(factor, 4)
    else:
        world_scale_matrix = None

    for obj in objects:
        if not _object_exists(obj):
            continue
        if not _is_in_bone_parent_subtree(obj, bone_parent_guard.duplicate_object_pointers):
            continue
        try:
            original_world = bone_parent_guard.original_world_matrices.get(obj.as_pointer())
        except ReferenceError:
            continue
        if original_world is None:
            continue
        if world_scale_matrix is None:
            obj.matrix_world = original_world
        else:
            obj.matrix_world = world_scale_matrix @ original_world


def _should_scale_object_data(obj, bone_parent_guard: BoneParentScaleGuard):
    return not _is_in_bone_parent_subtree(obj, bone_parent_guard.duplicate_object_pointers)


def _scale_object_world_origin_translation(obj, factor: float):
    matrix_world = obj.matrix_world.copy()
    matrix_world.translation *= factor
    obj.matrix_world = matrix_world


def _scale_object_data(obj, factor: float, scale_matrix):
    if obj.type == 'ARMATURE':
        _scale_armature_edit_bones(obj, factor)
        return

    data = getattr(obj, "data", None)
    if data is None:
        return

    transform = getattr(data, "transform", None)
    if transform is None:
        return

    try:
        if obj.type == 'MESH':
            transform(scale_matrix, shape_keys=True)
            data.update()
        else:
            transform(scale_matrix)
            update = getattr(data, "update", None)
            if callable(update):
                update()
    except TypeError:
        transform(scale_matrix)
        if obj.type == 'MESH':
            _scale_mesh_shape_keys_fallback(data, factor)
            data.update()
        else:
            update = getattr(data, "update", None)
            if callable(update):
                update()


def _scale_mesh_shape_keys_fallback(mesh, factor: float):
    shape_keys = getattr(mesh, "shape_keys", None)
    if shape_keys is None:
        return

    for key_block in shape_keys.key_blocks:
        for point in key_block.data:
            point.co *= factor


def _scale_armature_edit_bones(obj, factor: float):
    func_object_utils.deselect_all_objects()
    func_object_utils.select_object(obj, True)
    func_object_utils.set_active_object(obj)
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.mode_set(mode='EDIT')
    try:
        original_vectors = {
            bone.name: (bone.tail - bone.head).copy()
            for bone in obj.data.edit_bones
        }
        for bone in sorted(obj.data.edit_bones, key=_edit_bone_depth):
            if bone.parent is not None and bone.use_connect:
                bone.tail = bone.head + (original_vectors[bone.name] * factor)
                continue
            bone.head *= factor
            bone.tail *= factor
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')


def _edit_bone_depth(bone):
    depth = 0
    current = bone.parent
    while current is not None:
        depth += 1
        current = current.parent
    return depth


def _scale_source_actions_for_export(
    context: TemporaryScaledExportContext,
    operator,
    bone_parent_guard: BoneParentScaleGuard,
):
    factor = float(getattr(operator, "global_scale", 1.0))
    if abs(factor - 1.0) <= SCALE_EPSILON:
        return

    scale_object_locations = getattr(operator, "scale_pivot", SCALE_PIVOT_WORLD_ORIGIN) == SCALE_PIVOT_WORLD_ORIGIN
    processed_actions = set()

    for source_obj, duplicate_obj in context.duplicate_source_pairs:
        should_scale_object_locations = (
            scale_object_locations
            and not _is_in_bone_parent_subtree(duplicate_obj, bone_parent_guard.duplicate_object_pointers)
        )
        _scale_bound_object_actions(
            source_obj,
            factor,
            should_scale_object_locations,
            processed_actions,
            context.scaled_actions,
        )

        if getattr(operator, "bake_anim_use_all_actions", False):
            _scale_all_compatible_actions(
                source_obj,
                factor,
                should_scale_object_locations,
                processed_actions,
                context.scaled_actions,
            )


def _scale_bound_object_actions(source_obj, factor, scale_object_locations, processed_actions, scaled_actions):
    source_anim = getattr(source_obj, "animation_data", None)
    if source_anim is None:
        return

    source_actions = []
    source_action = getattr(source_anim, "action", None)
    if source_action is not None:
        source_actions.append(source_action)

    for track in source_anim.nla_tracks:
        for strip in track.strips:
            strip_action = getattr(strip, "action", None)
            if strip_action is not None:
                source_actions.append(strip_action)

    for action in source_actions:
        _scale_action_if_needed(
            action,
            factor,
            scale_object_locations,
            processed_actions,
            scaled_actions,
        )


def _scale_all_compatible_actions(source_obj, factor, scale_object_locations, processed_actions, scaled_actions):
    path_resolve = getattr(source_obj, "path_resolve", None)
    if path_resolve is None:
        return

    for action in bpy.data.actions:
        if not _validate_action_for_object(action, path_resolve):
            continue
        _scale_action_if_needed(
            action,
            factor,
            scale_object_locations,
            processed_actions,
            scaled_actions,
        )


def _validate_action_for_object(action, path_resolve):
    for fcurve in action.fcurves:
        data_path = fcurve.data_path
        if fcurve.array_index:
            data_path = data_path + f"[{fcurve.array_index}]"
        try:
            path_resolve(data_path)
        except ValueError:
            return False
    return True


def _scale_action_if_needed(action, factor, scale_object_locations, processed_actions, scaled_actions):
    try:
        action_pointer = action.as_pointer()
    except ReferenceError:
        return

    if action_pointer in processed_actions:
        return
    processed_actions.add(action_pointer)

    restore_record = _scale_action_translation_fcurves(
        action,
        factor,
        scale_object_locations,
    )
    if restore_record is not None:
        scaled_actions.append(restore_record)


def _scale_action_translation_fcurves(action, factor, scale_object_locations):
    curve_records = []

    for fcurve in action.fcurves:
        if not _should_scale_action_fcurve(fcurve, scale_object_locations):
            continue

        record = FCurveRestoreRecord(fcurve=fcurve)
        for point in fcurve.keyframe_points:
            record.keyframes.append(
                (
                    tuple(point.co),
                    tuple(point.handle_left),
                    tuple(point.handle_right),
                )
            )
            point.co[1] *= factor
            point.handle_left[1] *= factor
            point.handle_right[1] *= factor

        for point in fcurve.sampled_points:
            record.samples.append(tuple(point.co))
            point.co[1] *= factor

        fcurve.update()
        curve_records.append(record)

    if not curve_records:
        return None

    return ActionRestoreRecord(action=action, curves=curve_records)


def _should_scale_action_fcurve(fcurve, scale_object_locations):
    data_path = fcurve.data_path
    if data_path in {'location', 'delta_location'}:
        return scale_object_locations
    if data_path.startswith('pose.bones["') and data_path.endswith('"].location'):
        return True
    return False


def _restore_scaled_actions(action_records):
    restored_actions = set()
    for action_record in reversed(action_records):
        action = action_record.action
        try:
            action_pointer = action.as_pointer()
        except ReferenceError:
            continue
        if action_pointer in restored_actions:
            continue
        restored_actions.add(action_pointer)

        for curve_record in action_record.curves:
            fcurve = curve_record.fcurve
            try:
                for point, values in zip(fcurve.keyframe_points, curve_record.keyframes):
                    co, handle_left, handle_right = values
                    point.co = co
                    point.handle_left = handle_left
                    point.handle_right = handle_right
                for point, co in zip(fcurve.sampled_points, curve_record.samples):
                    point.co = co
                fcurve.update()
            except ReferenceError:
                continue


def _find_duplicate_for_source_object(duplicate_source_pairs, source_obj):
    for source_item, duplicate_obj in duplicate_source_pairs:
        if source_item == source_obj and _object_exists(duplicate_obj):
            return duplicate_obj
    return None


def _collect_existing_duplicate_objects(existing_duplicate_source_pairs, existing_duplicate_objects):
    duplicate_candidates = existing_duplicate_objects
    if duplicate_candidates is None:
        duplicate_candidates = [
            duplicate_obj
            for _source_obj, duplicate_obj in existing_duplicate_source_pairs
        ]

    return [
        duplicate_obj
        for duplicate_obj in duplicate_candidates
        if _object_exists(duplicate_obj)
    ]


def _collect_surviving_duplicate_source_pairs(duplicate_source_pairs, duplicate_objects):
    surviving_duplicate_pointers = _collect_object_pointers(duplicate_objects)
    result = []
    for source_obj, duplicate_obj in duplicate_source_pairs:
        if not _object_exists(source_obj):
            continue
        duplicate_pointer = _get_object_pointer(duplicate_obj)
        if duplicate_pointer is None or duplicate_pointer not in surviving_duplicate_pointers:
            continue
        result.append((source_obj, duplicate_obj))
    return result


def _iter_relink_animation_data_pairs(source_obj, duplicate_obj):
    if not _object_exists(source_obj) or not _object_exists(duplicate_obj):
        return

    source_data = _safe_getattr(source_obj, "data")
    duplicate_data = _safe_getattr(duplicate_obj, "data")
    source_shape_keys = _safe_getattr(source_data, "shape_keys")
    duplicate_shape_keys = _safe_getattr(duplicate_data, "shape_keys")

    yield (
        _safe_getattr(source_obj, "animation_data"),
        _safe_getattr(duplicate_obj, "animation_data"),
    )
    yield (
        _safe_getattr(source_data, "animation_data"),
        _safe_getattr(duplicate_data, "animation_data"),
    )
    yield (
        _safe_getattr(source_shape_keys, "animation_data"),
        _safe_getattr(duplicate_shape_keys, "animation_data"),
    )


def _collect_object_pointers(objects):
    result = set()
    for obj in objects:
        pointer = _get_object_pointer(obj)
        if pointer is not None:
            result.add(pointer)
    return result


def _get_object_pointer(obj):
    if not _object_exists(obj):
        return None
    try:
        return obj.as_pointer()
    except ReferenceError:
        return None


def _refresh_scene_frame(frame: int, subframe: float):
    bpy.context.scene.frame_set(frame, subframe=subframe)


def _safe_getattr(target, attr_name, default=None):
    if target is None:
        return default
    try:
        return getattr(target, attr_name, default)
    except ReferenceError:
        return default


def _object_exists(obj):
    try:
        obj.name
        return True
    except ReferenceError:
        return False
