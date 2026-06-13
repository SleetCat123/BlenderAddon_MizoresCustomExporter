import os
from dataclasses import dataclass

import bpy
from mathutils import Vector

from .. import consts
from ..funcs.utils import func_custom_props_utils
from ..funcs.utils import func_object_utils
from ..funcs.utils import func_temporary_duplicate_names
from .props_export_sets import get_export_set_display_name, get_export_set_raw_filename

TEMP_DUPLICATE_ID_PROP = "_mce_export_set_duplicate_id"
UNSAFE_OBJECT_REFERENCE_MODIFIER_PROPS = {
    'SURFACE_DEFORM': ("target",),
    'MESH_DEFORM': ("object",),
    'HOOK': ("object",),
}


@dataclass
class ExportSetItemRuntime:
    item: object
    source_root: object | None
    duplicate_root: object | None
    source_armatures: list
    duplicate_armatures: list


@dataclass
class ExportSetArmatureRuntime:
    item: object
    source_armature: object | None
    duplicate_armature: object | None
    is_primary_armature: bool


@dataclass
class ExportSetRuntime:
    export_set: object
    includes_armatures_in_export: bool
    source_objects: list
    staging_source_objects: list
    duplicate_objects: list
    export_objects: list
    duplicate_source_pairs: list
    item_runtimes: list
    armature_runtimes: list
    object_replace_duplicate_map: dict
    renamed_objects: list


@dataclass
class ExportSetResolvedItemContext:
    item: object
    effective_root: object | None
    effective_objects: list
    effective_additional_objects: list
    effective_armatures: list
    applied_replace_rules: list


def _iter_enabled_vertex_color_replace_rules(export_set):
    return [
        rule
        for rule in export_set.vertex_color_replace_rules
        if rule.enabled
    ]


def _iter_enabled_object_replace_rules(export_set):
    return [
        rule
        for rule in getattr(export_set, "object_replace_rules", [])
        if rule.enabled
    ]


def _iter_color_attributes(mesh, layer_name=""):
    color_attributes = getattr(mesh, "color_attributes", None)
    if color_attributes is None:
        return []

    if layer_name:
        color_attr = color_attributes.get(layer_name)
        if color_attr is None:
            return []
        if getattr(color_attr, "data_type", "") not in {'FLOAT_COLOR', 'BYTE_COLOR'}:
            return []
        return [color_attr]

    result = []
    for color_attr in color_attributes:
        if getattr(color_attr, "data_type", "") in {'FLOAT_COLOR', 'BYTE_COLOR'}:
            result.append(color_attr)
    return result


def _color_matches(color, source_color, tolerance):
    return all(
        abs(float(color[index]) - float(source_color[index])) <= tolerance
        for index in range(4)
    )


def _apply_vertex_color_replace_rules_to_mesh(mesh, rules):
    if mesh is None:
        return

    for rule in rules:
        replacement = tuple(float(channel) for channel in rule.target_color)
        tolerance = float(rule.tolerance)
        for color_attr in _iter_color_attributes(mesh, rule.layer_name):
            for color_value in color_attr.data:
                if _color_matches(color_value.color, rule.source_color, tolerance):
                    color_value.color = replacement
    mesh.update()


def apply_runtime_vertex_color_replace_rules(runtime: ExportSetRuntime):
    rules = _iter_enabled_vertex_color_replace_rules(runtime.export_set)
    if not rules:
        return

    processed_meshes = set()
    for obj in runtime.duplicate_objects:
        if not object_exists(obj) or obj.type != 'MESH' or getattr(obj, "data", None) is None:
            continue
        mesh = obj.data
        mesh_pointer = mesh.as_pointer()
        if mesh_pointer in processed_meshes:
            continue
        _apply_vertex_color_replace_rules_to_mesh(mesh, rules)
        processed_meshes.add(mesh_pointer)


def _iter_item_root_targets(item):
    root = item.root_object
    if root is None or not object_exists(root):
        return []
    stop_at_nested_armature = root.type == 'ARMATURE'
    return _resolve_root_targets(root, item.include_children, stop_at_nested_armature=stop_at_nested_armature)


def _append_unique_object_candidates(target_list: list, objects):
    for obj in objects:
        _append_unique(target_list, obj)


def _append_exportable_armature(target_list, armature_obj):
    if armature_obj is None or not object_exists(armature_obj):
        return
    if func_custom_props_utils.prop_is_true(armature_obj, consts.DONT_EXPORT_GROUP_NAME):
        return
    _append_unique(target_list, armature_obj)


def _resolve_armature_scope_targets(armature_obj):
    if armature_obj is None or not object_exists(armature_obj):
        return []
    return _resolve_root_targets(
        target=armature_obj,
        include_children=True,
        stop_at_nested_armature=True,
    )


def _is_ancestor_object(ancestor_obj, obj):
    if ancestor_obj is None or obj is None:
        return False
    parent = obj.parent
    while parent is not None:
        if parent == ancestor_obj:
            return True
        parent = parent.parent
    return False


def _resolve_item_armature_scope_targets(effective_root, armature_obj):
    if armature_obj is None or not object_exists(armature_obj):
        return []
    if effective_root is not None and object_exists(effective_root) and _is_ancestor_object(armature_obj, effective_root):
        return [armature_obj]
    return _resolve_armature_scope_targets(armature_obj)


def _resolve_item_armature_additional_objects(effective_root, armature_obj):
    scoped_targets = _resolve_item_armature_scope_targets(effective_root, armature_obj)
    result = []
    for obj in scoped_targets:
        if obj == armature_obj:
            continue
        _append_unique(result, obj)
    return result


def _find_inferred_item_armatures(item):
    return _find_inferred_item_armatures_for_targets(
        item=item,
        root_object=item.root_object,
        root_targets=_iter_item_root_targets(item),
        replace_object_map={},
    )


def _get_replaced_target_object(target, replace_object_map):
    if target is None:
        return None
    return replace_object_map.get(target, target)


def _item_explicit_armature_matches_scope(explicit_armature, root_object, root_targets, replace_object_map):
    related_armatures = []
    if root_object is not None and object_exists(root_object) and root_object.type == 'ARMATURE':
        _append_exportable_armature(related_armatures, root_object)

    if root_object is not None and object_exists(root_object):
        for modifier in getattr(root_object, "modifiers", []):
            modifier_target = _get_replaced_target_object(getattr(modifier, "object", None), replace_object_map)
            if modifier.type == 'ARMATURE' and object_exists(modifier_target):
                _append_exportable_armature(related_armatures, modifier_target)

        parent = _get_replaced_target_object(root_object.parent, replace_object_map)
        if parent is not None and parent.type == 'ARMATURE' and object_exists(parent):
            _append_exportable_armature(related_armatures, parent)

    for obj in root_targets:
        if obj.type == 'ARMATURE':
            _append_exportable_armature(related_armatures, obj)

        parent = _get_replaced_target_object(obj.parent, replace_object_map)
        if parent is not None and parent.type == 'ARMATURE' and object_exists(parent):
            _append_exportable_armature(related_armatures, parent)

        for modifier in getattr(obj, "modifiers", []):
            modifier_target = _get_replaced_target_object(getattr(modifier, "object", None), replace_object_map)
            if modifier.type == 'ARMATURE' and object_exists(modifier_target):
                _append_exportable_armature(related_armatures, modifier_target)

    return explicit_armature in related_armatures


def _find_inferred_item_armatures_for_targets(item, root_object, root_targets, replace_object_map):
    explicit_armature = _get_replaced_target_object(item.armature_object, replace_object_map)
    if explicit_armature is not None and object_exists(explicit_armature):
        if not _item_explicit_armature_matches_scope(explicit_armature, root_object, root_targets, replace_object_map):
            root_name = root_object.name if root_object is not None and object_exists(root_object) else "(None)"
            raise RuntimeError(
                f"Export Set item root '{root_name}' cannot use unrelated armature '{explicit_armature.name}'."
            )
        explicit_targets = []
        _append_exportable_armature(explicit_targets, explicit_armature)
        return explicit_targets

    if not root_targets:
        return []

    if root_object is not None and object_exists(root_object) and root_object.type == 'ARMATURE':
        explicit_targets = []
        _append_exportable_armature(explicit_targets, root_object)
        return explicit_targets

    direct_modifier_targets = []
    if root_object is not None and object_exists(root_object):
        for modifier in getattr(root_object, "modifiers", []):
            modifier_target = _get_replaced_target_object(getattr(modifier, "object", None), replace_object_map)
            if modifier.type == 'ARMATURE' and object_exists(modifier_target):
                _append_exportable_armature(direct_modifier_targets, modifier_target)

    direct_parent_targets = []
    if root_object is not None and object_exists(root_object):
        parent = _get_replaced_target_object(root_object.parent, replace_object_map)
        if parent is not None and parent.type == 'ARMATURE' and object_exists(parent):
            _append_exportable_armature(direct_parent_targets, parent)

    modifier_targets = []
    parent_targets = []
    subtree_armatures = []
    for obj in root_targets:
        if obj.type == 'ARMATURE':
            _append_exportable_armature(subtree_armatures, obj)

        parent = _get_replaced_target_object(obj.parent, replace_object_map)
        if parent is not None and parent.type == 'ARMATURE' and object_exists(parent):
            _append_exportable_armature(parent_targets, parent)

        for modifier in getattr(obj, "modifiers", []):
            modifier_target = _get_replaced_target_object(getattr(modifier, "object", None), replace_object_map)
            if modifier.type == 'ARMATURE' and object_exists(modifier_target):
                _append_exportable_armature(modifier_targets, modifier_target)

    combined_targets = []
    _append_unique_object_candidates(combined_targets, modifier_targets)
    _append_unique_object_candidates(combined_targets, parent_targets)
    _append_unique_object_candidates(combined_targets, subtree_armatures)
    _append_unique_object_candidates(combined_targets, direct_modifier_targets)
    _append_unique_object_candidates(combined_targets, direct_parent_targets)
    return combined_targets


def iter_enabled_export_sets(scene: bpy.types.Scene):
    props = getattr(scene, "mizore_export_sets", None)
    if props is None:
        return []
    return [export_set for export_set in props.export_sets if export_set.enabled]


def _append_unique(objects: list, obj):
    if obj is None:
        return
    if not object_exists(obj):
        return
    if obj not in objects:
        objects.append(obj)


def _object_names(objects):
    names = []
    for obj in objects:
        if object_exists(obj):
            names.append(obj.name)
    return names


def object_exists(obj):
    if obj is None:
        return False
    try:
        return bpy.data.objects.get(obj.name) is obj
    except ReferenceError:
        return False


def _get_selected_objects():
    return [obj for obj in bpy.context.view_layer.objects if obj.select_get()]


def _normalize_duplicate_mapping(objects):
    mapping = {}
    for obj in objects:
        duplicate_id = obj.get(TEMP_DUPLICATE_ID_PROP)
        if duplicate_id:
            mapping[duplicate_id] = obj
    return mapping


def _collect_duplicate_objects():
    return [
        obj
        for obj in bpy.data.objects
        if obj.get(TEMP_DUPLICATE_ID_PROP)
    ]


def _filter_out_source_objects(objects, source_objects):
    source_pointers = set()
    for obj in source_objects:
        try:
            source_pointers.add(obj.as_pointer())
        except ReferenceError:
            continue
    result = []
    for obj in objects:
        try:
            if obj.as_pointer() in source_pointers:
                continue
        except ReferenceError:
            continue
        result.append(obj)
    return result


def _get_duplicate_for_source_object(duplicate_map, source_obj):
    if source_obj is None or not object_exists(source_obj):
        return None
    duplicate_id = source_obj.get(TEMP_DUPLICATE_ID_PROP)
    if not duplicate_id:
        return None
    duplicate_obj = duplicate_map.get(duplicate_id)
    if duplicate_obj is None or not object_exists(duplicate_obj):
        return None
    return duplicate_obj


def _suspend_export_set_object_references(scene):
    if scene is None:
        return []

    props = getattr(scene, "mizore_export_sets", None)
    if props is None:
        return []

    from . import props_export_sets

    snapshots = []
    props_export_sets.suspend_export_set_item_target_sync()
    try:
        for export_set in getattr(props, "export_sets", []):
            snapshots.append((export_set, "target_armature", getattr(export_set, "target_armature", None)))
            export_set.target_armature = None

            for item in getattr(export_set, "items", []):
                snapshots.append((item, "root_object", getattr(item, "root_object", None)))
                snapshots.append((item, "armature_object", getattr(item, "armature_object", None)))
                item.root_object = None
                item.armature_object = None

            for rule in getattr(export_set, "object_replace_rules", []):
                snapshots.append((rule, "source_object", getattr(rule, "source_object", None)))
                snapshots.append((rule, "replacement_object", getattr(rule, "replacement_object", None)))
                rule.source_object = None
                rule.replacement_object = None

            for override in getattr(export_set, "shapekey_reorder_overrides", []):
                snapshots.append((override, "target_object", getattr(override, "target_object", None)))
                override.target_object = None
        return snapshots
    finally:
        props_export_sets.resume_export_set_item_target_sync()


def _restore_export_set_object_references(snapshots):
    if not snapshots:
        return

    from . import props_export_sets

    props_export_sets.suspend_export_set_item_target_sync()
    try:
        for owner, attr_name, value in reversed(snapshots):
            try:
                setattr(owner, attr_name, value)
            except Exception:
                continue
    finally:
        props_export_sets.resume_export_set_item_target_sync()


def _set_duplicate_ids(objects):
    return func_temporary_duplicate_names.set_duplicate_ids(objects, TEMP_DUPLICATE_ID_PROP)


def _swap_duplicate_names_to_source_names(source_objects, duplicate_objects):
    return func_temporary_duplicate_names.swap_duplicate_object_and_data_names_to_source_names(
        source_objects,
        duplicate_objects,
        TEMP_DUPLICATE_ID_PROP,
    )


def _restore_source_names(rename_records):
    func_temporary_duplicate_names.restore_source_object_and_data_names(rename_records)


def _clear_duplicate_ids(objects):
    func_temporary_duplicate_names.clear_duplicate_ids(objects, TEMP_DUPLICATE_ID_PROP)


def _set_active_only(obj):
    func_object_utils.deselect_all_objects()
    if obj is not None:
        func_object_utils.select_object(obj, True)
        func_object_utils.set_active_object(obj)


def _ensure_object_mode():
    active = func_object_utils.get_active_object()
    if active is not None and active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def _build_available_pointer_set(available_objects):
    if available_objects is None:
        return None

    result = set()
    for obj in available_objects:
        if not object_exists(obj):
            continue
        result.add(obj.as_pointer())
    return result


def _is_nested_export_boundary(obj):
    return (
        func_custom_props_utils.prop_is_true(obj, consts.DONT_EXPORT_GROUP_NAME)
        or func_custom_props_utils.prop_is_true(obj, consts.ALWAYS_EXPORT_GROUP_NAME)
    )


def _collect_descendants_in_export_scope(target, stop_at_nested_armature=False):
    if target is None or not object_exists(target):
        return []

    if func_custom_props_utils.prop_is_true(target, consts.DONT_EXPORT_GROUP_NAME):
        return []

    result = []

    def recursive(obj, is_root=False):
        result.append(obj)
        for child in func_object_utils.get_children_objects(obj):
            if stop_at_nested_armature and child.type == 'ARMATURE':
                continue
            if _is_nested_export_boundary(child):
                continue
            recursive(child)

    recursive(target, is_root=True)
    return result


def _iter_targets(target, include_children, stop_at_nested_armature=False):
    if target is None or not object_exists(target):
        return []

    if func_custom_props_utils.prop_is_true(target, consts.DONT_EXPORT_GROUP_NAME):
        return []

    if not include_children:
        return [target]

    return _collect_descendants_in_export_scope(
        target,
        stop_at_nested_armature=stop_at_nested_armature,
    )


def _resolve_root_targets(target, include_children, stop_at_nested_armature=False):
    if target is None or not object_exists(target):
        return []

    return _iter_targets(
        target=target,
        include_children=include_children,
        stop_at_nested_armature=stop_at_nested_armature,
    )


def _apply_object_replace_rules_to_targets(export_set, initial_root, initial_targets):
    current_root = initial_root if initial_root in initial_targets else None
    current_targets = list(initial_targets)
    applied_replace_rules = []

    for rule in _iter_enabled_object_replace_rules(export_set):
        source_object = rule.source_object
        replacement_object = rule.replacement_object
        if source_object is None or replacement_object is None:
            continue
        if not object_exists(source_object) or not object_exists(replacement_object):
            continue

        source_targets = _resolve_root_targets(source_object, rule.include_children)
        if not source_targets:
            continue

        current_target_set = set(current_targets)
        if not current_target_set.intersection(source_targets):
            continue

        replacement_targets = _resolve_root_targets(replacement_object, rule.include_children)
        if not replacement_targets:
            continue

        next_targets = [obj for obj in current_targets if obj not in source_targets]
        _append_unique_object_candidates(next_targets, replacement_targets)
        current_targets = next_targets
        if current_root in source_targets:
            current_root = replacement_object
        applied_replace_rules.append(rule)

    return current_root, current_targets, applied_replace_rules


def _resolve_export_set_item_contexts(export_set, available_objects=None):
    available_pointers = _build_available_pointer_set(available_objects)

    contexts = []
    for item in export_set.items:
        if not item.enabled:
            continue
        if item.root_object is None or not object_exists(item.root_object):
            continue
        if (
            available_pointers is not None
            and item.root_object.as_pointer() not in available_pointers
        ):
            continue

        stop_at_nested_armature = item.root_object.type == 'ARMATURE'
        item_targets = _resolve_root_targets(
            target=item.root_object,
            include_children=item.include_children,
            stop_at_nested_armature=stop_at_nested_armature,
        )
        effective_root, effective_targets, applied_replace_rules = _apply_object_replace_rules_to_targets(
            export_set=export_set,
            initial_root=item.root_object,
            initial_targets=item_targets,
        )
        replace_object_map = {
            rule.source_object: rule.replacement_object
            for rule in applied_replace_rules
            if rule.source_object is not None and rule.replacement_object is not None
        }
        effective_armatures = _find_inferred_item_armatures_for_targets(
            item=item,
            root_object=effective_root,
            root_targets=effective_targets,
            replace_object_map=replace_object_map,
        )
        effective_additional_objects = []
        for armature in effective_armatures:
            _append_unique_object_candidates(
                effective_additional_objects,
                _resolve_item_armature_additional_objects(effective_root, armature),
            )
        contexts.append(
            ExportSetResolvedItemContext(
                item=item,
                effective_root=effective_root,
                effective_objects=effective_targets,
                effective_additional_objects=effective_additional_objects,
                effective_armatures=effective_armatures,
                applied_replace_rules=applied_replace_rules,
            )
        )
    return contexts


def resolve_export_set_item_contexts(export_set, available_objects=None):
    return _resolve_export_set_item_contexts(export_set, available_objects=available_objects)


def collect_export_set_objects_from_contexts(item_contexts):
    objects = []
    for context in item_contexts:
        _append_unique_object_candidates(objects, context.effective_objects)
        _append_unique_object_candidates(objects, context.effective_additional_objects)
        for armature in context.effective_armatures:
            _append_unique_object_candidates(
                objects,
                _resolve_item_armature_scope_targets(context.effective_root, armature),
            )
    return objects


def resolve_export_set_objects(export_set, available_objects=None):
    item_contexts = _resolve_export_set_item_contexts(export_set, available_objects=available_objects)
    return collect_export_set_objects_from_contexts(item_contexts)


def build_export_set_filepath(base_filepath: str, export_set) -> str:
    base_dir = os.path.dirname(base_filepath)
    if not base_dir:
        base_dir = bpy.path.abspath("//")

    filename = get_export_set_raw_filename(export_set) or "ExportSet"
    if not filename.lower().endswith(".fbx"):
        filename += ".fbx"
    return os.path.join(base_dir, filename)


def _snapshot_object_visibility(objects):
    snapshots = []
    for obj in objects:
        if obj is None or not object_exists(obj):
            continue
        snapshots.append(
            (
                obj,
                bool(getattr(obj, "hide_viewport", False)),
                bool(obj.hide_get()),
            )
        )
    return snapshots


def _restore_object_visibility(snapshots):
    for obj, hide_viewport, hide_set in snapshots:
        if not object_exists(obj):
            continue
        obj.hide_viewport = hide_viewport
        obj.hide_set(hide_set)


def build_export_set_runtime(export_set, available_objects=None, export_object_types=None, item_contexts=None):
    scene = getattr(export_set, "id_data", None)
    if item_contexts is None:
        item_contexts = _resolve_export_set_item_contexts(export_set, available_objects=available_objects)
    includes_armatures_in_export = export_object_types is None or 'ARMATURE' in export_object_types
    export_set_name = get_export_set_display_name(export_set)
    print(
        f"[ExportSets] runtime start export_set='{export_set_name}' "
        f"available_objects={_object_names(available_objects or [])}"
    )
    for item_context in item_contexts:
        root_name = item_context.item.root_object.name if object_exists(item_context.item.root_object) else "(None)"
        effective_root_name = item_context.effective_root.name if object_exists(item_context.effective_root) else "(None)"
        print(
            f"[ExportSets] item export_set='{export_set_name}' "
            f"root='{root_name}' effective_root='{effective_root_name}' "
            f"include_children={item_context.item.include_children} "
            f"attach_to_bone='{item_context.item.attach_to_bone}' "
            f"effective_objects={_object_names(item_context.effective_objects)} "
            f"effective_additional_objects={_object_names(item_context.effective_additional_objects)} "
            f"effective_armatures={_object_names(item_context.effective_armatures)}"
        )
    source_objects = []
    export_source_objects = []
    staging_source_objects = []
    for context in item_contexts:
        _append_unique_object_candidates(export_source_objects, context.effective_objects)
        _append_unique_object_candidates(export_source_objects, context.effective_additional_objects)
        if includes_armatures_in_export:
            _append_unique_object_candidates(export_source_objects, context.effective_armatures)
        _append_unique_object_candidates(source_objects, context.effective_objects)
        _append_unique_object_candidates(source_objects, context.effective_additional_objects)
        for armature in context.effective_armatures:
            _append_unique_object_candidates(
                source_objects,
                _resolve_item_armature_scope_targets(context.effective_root, armature),
            )
        for rule in context.applied_replace_rules:
            _append_unique(staging_source_objects, rule.source_object)
    for staging_source in staging_source_objects:
        _append_unique(source_objects, staging_source)
    print(
        f"[ExportSets] runtime sources export_set='{export_set_name}' "
        f"source_objects={_object_names(source_objects)} "
        f"staging_sources={_object_names(staging_source_objects)}"
    )
    if not source_objects:
        return ExportSetRuntime(
            export_set=export_set,
            includes_armatures_in_export=includes_armatures_in_export,
            source_objects=[],
            staging_source_objects=[],
            duplicate_objects=[],
            export_objects=[],
            duplicate_source_pairs=[],
            item_runtimes=[],
            armature_runtimes=[],
            object_replace_duplicate_map={},
            renamed_objects=[],
        )

    _set_duplicate_ids(source_objects)
    duplicate_objects = []
    rename_records = []
    visibility_snapshots = _snapshot_object_visibility(source_objects)
    target_armature = export_set.target_armature if object_exists(export_set.target_armature) else None
    export_set_reference_snapshots = []
    try:
        for source_obj in source_objects:
            if object_exists(source_obj):
                func_object_utils.force_unhide(source_obj)
        active_source = func_object_utils.get_active_object()
        if active_source not in source_objects and source_objects:
            func_object_utils.set_active_object(source_objects[0])
        export_set_reference_snapshots = _suspend_export_set_object_references(scene)
        func_object_utils.duplicate_objects(source_objects, linked=False)
        _restore_export_set_object_references(export_set_reference_snapshots)
        export_set_reference_snapshots = []
        duplicate_objects = _filter_out_source_objects(
            _collect_duplicate_objects(),
            source_objects,
        )
        duplicate_map = _normalize_duplicate_mapping(duplicate_objects)
        duplicate_source_pairs = [
            (source_obj, duplicate_obj)
            for source_obj in source_objects
            for duplicate_obj in [_get_duplicate_for_source_object(duplicate_map, source_obj)]
            if duplicate_obj is not None
        ]
        export_objects = []
        for source_obj in export_source_objects:
            duplicate_obj = _get_duplicate_for_source_object(duplicate_map, source_obj)
            if duplicate_obj is None:
                continue
            _append_unique(export_objects, duplicate_obj)
        rename_records = _swap_duplicate_names_to_source_names(source_objects, duplicate_objects)
        object_replace_duplicate_map = _build_object_replace_duplicate_map(
            item_contexts=item_contexts,
            duplicate_map=duplicate_map,
        )

        item_runtimes = []
        armature_runtimes = []
        for item_context in item_contexts:
            item = item_context.item
            source_root = item_context.effective_root if item_context.effective_root in source_objects else None
            resolved_armatures = [
                armature for armature in item_context.effective_armatures
                if armature in source_objects
            ]
            duplicate_root = _get_duplicate_for_source_object(duplicate_map, source_root)
            duplicate_armatures = [
                _get_duplicate_for_source_object(duplicate_map, source_armature)
                for source_armature in resolved_armatures
            ]
            item_runtimes.append(
                ExportSetItemRuntime(
                    item=item,
                    source_root=source_root,
                    duplicate_root=duplicate_root,
                    source_armatures=resolved_armatures,
                    duplicate_armatures=[armature for armature in duplicate_armatures if armature is not None],
                )
            )

            for source_armature, duplicate_armature in zip(resolved_armatures, duplicate_armatures):
                if duplicate_armature is None:
                    continue
                armature_runtimes.append(
                    ExportSetArmatureRuntime(
                        item=item,
                        source_armature=source_armature,
                        duplicate_armature=duplicate_armature,
                        is_primary_armature=source_armature == target_armature,
                    )
                )
        runtime = ExportSetRuntime(
            export_set=export_set,
            includes_armatures_in_export=includes_armatures_in_export,
            source_objects=source_objects,
            staging_source_objects=staging_source_objects,
            duplicate_objects=duplicate_objects,
            export_objects=export_objects,
            duplicate_source_pairs=duplicate_source_pairs,
            item_runtimes=item_runtimes,
            armature_runtimes=armature_runtimes,
            object_replace_duplicate_map=object_replace_duplicate_map,
            renamed_objects=rename_records,
        )
        _detach_mesh_parented_armatures(runtime)
        return runtime
    except Exception:
        _restore_source_names(rename_records)
        for obj in list(duplicate_objects):
            if object_exists(obj):
                func_object_utils.remove_object(obj)
        raise
    finally:
        _restore_export_set_object_references(export_set_reference_snapshots)
        _restore_object_visibility(visibility_snapshots)
        _clear_duplicate_ids(source_objects)
        if duplicate_objects:
            _clear_duplicate_ids(duplicate_objects)


def _build_object_replace_duplicate_map(item_contexts, duplicate_map):
    result = {}
    for item_context in item_contexts:
        for rule in item_context.applied_replace_rules:
            source_object = rule.source_object
            replacement_object = rule.replacement_object
            if source_object is None or replacement_object is None:
                continue
            if not object_exists(source_object) or not object_exists(replacement_object):
                continue

            duplicate_replacement = _get_duplicate_for_source_object(duplicate_map, replacement_object)
            if duplicate_replacement is None:
                continue
            result[source_object] = duplicate_replacement

            duplicate_source = _get_duplicate_for_source_object(duplicate_map, source_object)
            if duplicate_source is not None:
                result[duplicate_source] = duplicate_replacement
    return result


def _detach_mesh_parented_armatures(runtime: ExportSetRuntime):
    for armature_runtime in runtime.armature_runtimes:
        armature_obj = armature_runtime.duplicate_armature
        if armature_obj is None or not object_exists(armature_obj):
            continue
        parent = armature_obj.parent
        if parent is None or not object_exists(parent):
            continue
        if parent.type != 'MESH':
            continue

        matrix_world = armature_obj.matrix_world.copy()
        armature_obj.parent = None
        armature_obj.parent_type = 'OBJECT'
        armature_obj.parent_bone = ""
        armature_obj.matrix_world = matrix_world


def _find_duplicate_from_source_pairs(duplicate_source_pairs, source_obj):
    for source_item, duplicate_obj in duplicate_source_pairs:
        if source_item == source_obj and object_exists(duplicate_obj):
            return duplicate_obj
    return None


def _retarget_parent_object_if_replaced(obj, object_replace_duplicate_map):
    if not object_exists(obj):
        return
    parent = obj.parent
    replacement_parent = object_replace_duplicate_map.get(parent)
    if replacement_parent is None or not object_exists(replacement_parent):
        return

    matrix_world = obj.matrix_world.copy()
    parent_type = obj.parent_type
    parent_bone = obj.parent_bone
    obj.parent = replacement_parent
    if parent_type == 'BONE' and parent_bone and replacement_parent.type == 'ARMATURE' and parent_bone in replacement_parent.data.bones:
        obj.parent_type = 'BONE'
        obj.parent_bone = parent_bone
    else:
        obj.parent_type = 'OBJECT'
        obj.parent_bone = ""
    obj.matrix_world = matrix_world


def _retarget_armature_modifier_if_replaced(obj, object_replace_duplicate_map):
    if not object_exists(obj):
        return
    for modifier in getattr(obj, "modifiers", []):
        if modifier.type != 'ARMATURE':
            continue
        target = getattr(modifier, "object", None)
        replacement_target = object_replace_duplicate_map.get(target)
        if replacement_target is None:
            continue
        if replacement_target.type != 'ARMATURE':
            raise RuntimeError(
                f"Object replacement retarget requires an armature target. "
                f"object='{obj.name}' modifier='{modifier.name}' replacement='{replacement_target.name}'"
            )
        modifier.object = replacement_target


def retarget_runtime_object_replace_references(runtime: ExportSetRuntime):
    if not runtime.object_replace_duplicate_map:
        return

    for obj in list(runtime.duplicate_objects):
        _retarget_parent_object_if_replaced(obj, runtime.object_replace_duplicate_map)
        _retarget_armature_modifier_if_replaced(obj, runtime.object_replace_duplicate_map)


def validate_runtime_object_replace_references(runtime: ExportSetRuntime):
    if not runtime.object_replace_duplicate_map:
        return

    for obj in list(runtime.duplicate_objects):
        if not object_exists(obj):
            continue
        for modifier in getattr(obj, "modifiers", []):
            prop_names = UNSAFE_OBJECT_REFERENCE_MODIFIER_PROPS.get(modifier.type)
            if not prop_names:
                continue
            for prop_name in prop_names:
                target = getattr(modifier, prop_name, None)
                if target not in runtime.object_replace_duplicate_map:
                    continue
                raise RuntimeError(
                    f"Object replacement does not support modifier reference retargeting. "
                    f"object='{obj.name}' modifier='{modifier.name}' type='{modifier.type}' "
                    f"property='{prop_name}' target='{target.name}'"
                )


def remove_runtime_object_replace_staging_duplicates(runtime: ExportSetRuntime):
    if not runtime.staging_source_objects:
        return

    for staging_source in runtime.staging_source_objects:
        staging_duplicate = _find_duplicate_from_source_pairs(runtime.duplicate_source_pairs, staging_source)
        if staging_duplicate is None:
            continue
        func_object_utils.remove_object(staging_duplicate)
        runtime.duplicate_objects = [
            obj for obj in runtime.duplicate_objects
            if obj != staging_duplicate
        ]
        runtime.export_objects = [
            obj for obj in runtime.export_objects
            if obj != staging_duplicate
        ]


def _get_armature_item_runtimes(runtime: ExportSetRuntime):
    return [
        armature_runtime
        for armature_runtime in runtime.armature_runtimes
        if object_exists(armature_runtime.duplicate_armature)
    ]


def _get_unique_armature_item_runtimes(runtime: ExportSetRuntime):
    unique_runtimes = []
    seen_source_pointers = set()
    for armature_runtime in _get_armature_item_runtimes(runtime):
        if not object_exists(armature_runtime.source_armature):
            continue
        source_pointer = armature_runtime.source_armature.as_pointer()
        if source_pointer in seen_source_pointers:
            continue
        seen_source_pointers.add(source_pointer)
        unique_runtimes.append(armature_runtime)
    return unique_runtimes


def _describe_armature_runtime(armature_runtime: ExportSetArmatureRuntime) -> str:
    source_name = armature_runtime.source_armature.name if object_exists(armature_runtime.source_armature) else "(None)"
    duplicate_name = armature_runtime.duplicate_armature.name if object_exists(armature_runtime.duplicate_armature) else "(None)"
    attach_to_bone = armature_runtime.item.attach_to_bone.strip()
    if not attach_to_bone:
        attach_to_bone = "(empty)"
    return (
        f"source='{source_name}' duplicate='{duplicate_name}' "
        f"attach_to_bone='{attach_to_bone}'"
    )


def _log_armature_merge_state(runtime: ExportSetRuntime, prefix: str):
    export_set_name = get_export_set_display_name(runtime.export_set)
    target_armature = runtime.export_set.target_armature
    target_name = target_armature.name if object_exists(target_armature) else "(None)"
    armature_descriptions = [
        _describe_armature_runtime(armature_runtime)
        for armature_runtime in _get_armature_item_runtimes(runtime)
    ]
    print(
        f"[ExportSets] {prefix} export_set='{export_set_name}' "
        f"merge_armatures={runtime.export_set.merge_armatures} "
        f"target_armature='{target_name}' "
        f"armatures=[{'; '.join(armature_descriptions)}]"
    )


def _find_inferred_primary_armature_runtime(runtime: ExportSetRuntime):
    armature_runtimes = _get_unique_armature_item_runtimes(runtime)
    if len(armature_runtimes) == 1:
        return armature_runtimes[0]
    candidates = [
        armature_runtime
        for armature_runtime in armature_runtimes
        if (
            not armature_runtime.item.attach_to_bone.strip()
            and armature_runtime.item.root_object == armature_runtime.source_armature
        )
    ]
    if len(candidates) == 1:
        export_set_name = get_export_set_display_name(runtime.export_set)
        print(
            f"[ExportSets] inferred target armature from empty attach_to_bone. "
            f"export_set='{export_set_name}' target='{candidates[0].source_armature.name}'"
        )
        return candidates[0]
    return None


def validate_runtime_armature_merge(runtime: ExportSetRuntime):
    armature_runtimes = _get_armature_item_runtimes(runtime)
    unique_armature_runtimes = _get_unique_armature_item_runtimes(runtime)
    if not runtime.includes_armatures_in_export and not armature_runtimes:
        return
    target_armature = runtime.export_set.target_armature
    if target_armature is not None and object_exists(target_armature):
        matching_runtimes = [
            unique_armature_runtime
            for unique_armature_runtime in unique_armature_runtimes
            if unique_armature_runtime.source_armature == target_armature
        ]
        if not matching_runtimes:
            export_set_name = get_export_set_display_name(runtime.export_set)
            _log_armature_merge_state(runtime, "target armature was not resolved")
            raise RuntimeError(
                f"Export Set '{export_set_name}' target armature '{target_armature.name}' "
                f"was not resolved from the enabled items."
            )

    if len(unique_armature_runtimes) <= 1:
        return

    if target_armature is None or not object_exists(target_armature):
        inferred_runtime = _find_inferred_primary_armature_runtime(runtime)
        if inferred_runtime is not None:
            return
        export_set_name = get_export_set_display_name(runtime.export_set)
        _log_armature_merge_state(runtime, "missing target armature")
        raise RuntimeError(
            f"Export Set '{export_set_name}' must set Target Armature "
            f"when Merge Into One Armature is enabled with multiple armatures."
        )


def _find_primary_armature_runtime(runtime: ExportSetRuntime):
    armature_runtimes = _get_unique_armature_item_runtimes(runtime)
    if not armature_runtimes:
        return None
    target_armature = runtime.export_set.target_armature
    if target_armature is not None and object_exists(target_armature):
        for armature_runtime in armature_runtimes:
            if armature_runtime.source_armature == target_armature:
                return armature_runtime
    inferred_runtime = _find_inferred_primary_armature_runtime(runtime)
    if inferred_runtime is not None:
        return inferred_runtime
    for armature_runtime in armature_runtimes:
        if armature_runtime.is_primary_armature:
            return armature_runtime
    return armature_runtimes[0]


def _snapshot_armature_bones(source_obj):
    _ensure_object_mode()
    _set_active_only(source_obj)
    bpy.ops.object.mode_set(mode='EDIT')
    snapshots = []
    for bone in source_obj.data.edit_bones:
        snapshots.append({
            "name": bone.name,
            "parent_name": bone.parent.name if bone.parent else "",
            "head_world": tuple(source_obj.matrix_world @ bone.head),
            "tail_world": tuple(source_obj.matrix_world @ bone.tail),
            "use_connect": bone.use_connect,
            "use_local_location": bone.use_local_location,
            "use_inherit_rotation": bone.use_inherit_rotation,
            "inherit_scale": bone.inherit_scale,
            "roll": bone.roll,
        })
    bpy.ops.object.mode_set(mode='OBJECT')
    return snapshots


def _merge_bone_snapshots_into_target(target_obj, bone_snapshots, attach_to_bone=""):
    _ensure_object_mode()
    _set_active_only(target_obj)
    bpy.ops.object.mode_set(mode='EDIT')
    dest_edit_bones = target_obj.data.edit_bones

    remaining = {bone["name"]: bone for bone in bone_snapshots}
    while remaining:
        progressed = False
        for bone_name, bone in list(remaining.items()):
            parent_name = bone["parent_name"]
            if parent_name:
                if parent_name not in dest_edit_bones:
                    continue
                dest_parent_name = parent_name
            else:
                dest_parent_name = attach_to_bone or ""
                if dest_parent_name and dest_parent_name not in dest_edit_bones:
                    raise RuntimeError(
                        f"Attach bone '{dest_parent_name}' was not found on '{target_obj.name}'"
                    )

            if bone_name in dest_edit_bones:
                remaining.pop(bone_name)
                progressed = True
                continue

            new_bone = dest_edit_bones.new(bone_name)
            head_local = target_obj.matrix_world.inverted() @ Vector(bone["head_world"])
            tail_local = target_obj.matrix_world.inverted() @ Vector(bone["tail_world"])
            new_bone.head = head_local
            new_bone.tail = tail_local
            new_bone.roll = bone["roll"]
            new_bone.use_local_location = bone["use_local_location"]
            new_bone.use_inherit_rotation = bone["use_inherit_rotation"]
            new_bone.inherit_scale = bone["inherit_scale"]
            if dest_parent_name:
                new_bone.parent = dest_edit_bones[dest_parent_name]
                if bone["use_connect"] and (new_bone.head - new_bone.parent.tail).length <= 1e-5:
                    new_bone.use_connect = True
                else:
                    new_bone.use_connect = False
            remaining.pop(bone_name)
            progressed = True

        if not progressed:
            unresolved = ", ".join(sorted(remaining.keys()))
            raise RuntimeError(f"Failed to merge armature bones: {unresolved}")

    bpy.ops.object.mode_set(mode='OBJECT')


def _retarget_armature_users(runtime: ExportSetRuntime, source_obj, target_obj):
    for obj in list(runtime.duplicate_objects):
        if not object_exists(obj):
            continue
        for modifier in getattr(obj, "modifiers", []):
            if modifier.type != 'ARMATURE' or not modifier.object:
                continue
            if modifier.object == source_obj:
                modifier.object = target_obj

    for obj in list(runtime.duplicate_objects):
        if not object_exists(obj):
            continue
        if obj.parent != source_obj:
            continue
        matrix_world = obj.matrix_world.copy()
        parent_type = obj.parent_type
        parent_bone = obj.parent_bone
        obj.parent = target_obj
        if parent_type == 'BONE' and parent_bone and parent_bone in target_obj.data.bones:
            obj.parent_type = 'BONE'
            obj.parent_bone = parent_bone
        else:
            obj.parent_type = 'OBJECT'
            obj.parent_bone = ""
        obj.matrix_world = matrix_world


def _resolve_attach_to_bone(source_obj, target_obj, explicit_attach_to_bone):
    attach_to_bone = explicit_attach_to_bone.strip()
    if attach_to_bone:
        return attach_to_bone
    if source_obj.parent == target_obj and source_obj.parent_type == 'BONE' and source_obj.parent_bone:
        return source_obj.parent_bone
    return ""


def merge_runtime_armatures(runtime: ExportSetRuntime):
    validate_runtime_armature_merge(runtime)
    primary_runtime = _find_primary_armature_runtime(runtime)
    if primary_runtime is None:
        return None

    target_obj = primary_runtime.duplicate_armature
    if not object_exists(target_obj):
        return None

    for armature_runtime in runtime.armature_runtimes:
        source_obj = armature_runtime.duplicate_armature
        if source_obj is None or source_obj == target_obj or not object_exists(source_obj):
            continue

        snapshots = _snapshot_armature_bones(source_obj)
        attach_to_bone = _resolve_attach_to_bone(
            source_obj=source_obj,
            target_obj=target_obj,
            explicit_attach_to_bone=armature_runtime.item.attach_to_bone,
        )
        _merge_bone_snapshots_into_target(
            target_obj=target_obj,
            bone_snapshots=snapshots,
            attach_to_bone=attach_to_bone,
        )
        _retarget_armature_users(runtime, source_obj, target_obj)
        func_object_utils.remove_object(source_obj)

    return target_obj


def join_runtime_meshes(runtime: ExportSetRuntime):
    mesh_objects = [
        obj for obj in runtime.duplicate_objects
        if object_exists(obj) and obj.type == 'MESH'
    ]
    if not mesh_objects:
        return None
    if len(mesh_objects) == 1:
        return mesh_objects[0]

    primary_root = None
    for item_runtime in runtime.item_runtimes:
        if object_exists(item_runtime.duplicate_root) and item_runtime.duplicate_root.type == 'MESH':
            primary_root = item_runtime.duplicate_root
            break

    active_mesh = primary_root if primary_root in mesh_objects else mesh_objects[0]

    armature_targets = {
        modifier.object
        for obj in mesh_objects
        for modifier in obj.modifiers
        if modifier.type == 'ARMATURE' and modifier.object is not None
    }
    existing_targets = {
        modifier.object
        for modifier in active_mesh.modifiers
        if modifier.type == 'ARMATURE' and modifier.object is not None
    }
    for armature_obj in armature_targets:
        if armature_obj in existing_targets:
            continue
        modifier = active_mesh.modifiers.new(name="Armature", type='ARMATURE')
        modifier.object = armature_obj
        existing_targets.add(armature_obj)

    func_object_utils.deselect_all_objects()
    func_object_utils.select_objects(mesh_objects, True)
    func_object_utils.set_active_object(active_mesh)
    bpy.ops.object.join()
    return active_mesh


def get_export_objects_from_runtime(runtime: ExportSetRuntime):
    result = []
    for obj in runtime.export_objects:
        if object_exists(obj):
            _append_unique(result, obj)
    return result


def cleanup_runtime(runtime: ExportSetRuntime):
    for obj in list(runtime.duplicate_objects):
        if object_exists(obj):
            func_object_utils.remove_object(obj)
    _restore_source_names(runtime.renamed_objects)
