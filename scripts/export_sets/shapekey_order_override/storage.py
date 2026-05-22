from .. import func_export_sets


def _clear_collection(collection):
    while len(collection) > 0:
        collection.remove(len(collection) - 1)


def _object_key(obj):
    if obj is None:
        return ""
    return str(getattr(obj, "name", "") or "")


def _serialize_entry(entry):
    return {
        "target_object": entry.target_object,
        "override_enabled": entry.override_enabled,
        "rows": [
            {
                "final_name": row.final_name,
                "kinds_label": row.kinds_label,
                "source_objects_label": row.source_objects_label,
                "source_detail_label": row.source_detail_label,
                "match_tokens_serialized": getattr(row, "match_tokens_serialized", ""),
                "state_label": row.state_label,
                "is_basis": row.is_basis,
                "is_resolved": row.is_resolved,
            }
            for row in entry.rows
        ],
        "active_row_index": entry.active_row_index,
    }


def _append_entry(collection, entry_data):
    new_entry = collection.add()
    new_entry.target_object = entry_data["target_object"]
    new_entry.override_enabled = entry_data["override_enabled"]
    for row_data in entry_data["rows"]:
        row = new_entry.rows.add()
        row.final_name = row_data["final_name"]
        row.kinds_label = row_data["kinds_label"]
        row.source_objects_label = row_data["source_objects_label"]
        row.source_detail_label = row_data["source_detail_label"]
        row.match_tokens_serialized = row_data.get("match_tokens_serialized", "")
        row.state_label = row_data["state_label"]
        row.is_basis = row_data["is_basis"]
        row.is_resolved = row_data["is_resolved"]
    new_entry.active_row_index = entry_data["active_row_index"]


def _sort_entries_by_target(collection):
    if len(collection) <= 1:
        return
    ordered = sorted(
        [_serialize_entry(entry) for entry in collection],
        key=lambda item: (
            item["target_object"].name.lower()
            if item["target_object"] is not None
            else ""
        ),
    )
    _clear_collection(collection)
    for entry_data in ordered:
        _append_entry(collection, entry_data)


def get_mesh_targets(export_set):
    return [
        obj for obj in func_export_sets.resolve_export_set_objects(export_set)
        if obj.type == 'MESH'
    ]


def needs_override_sync(export_set, target_objects=None):
    if target_objects is None:
        target_objects = get_mesh_targets(export_set)

    target_keys = {
        _object_key(obj)
        for obj in target_objects
        if obj is not None
    }
    existing_keys = []
    for entry in export_set.shapekey_reorder_overrides:
        entry_key = _object_key(entry.target_object)
        if not entry_key:
            return True
        existing_keys.append(entry_key)

    if len(existing_keys) != len(set(existing_keys)):
        return True
    return set(existing_keys) != target_keys


def sync_override_entries(export_set):
    target_objects = get_mesh_targets(export_set)
    target_keys = {
        _object_key(obj)
        for obj in target_objects
        if obj is not None
    }
    existing_entries = {
        _object_key(entry.target_object): entry
        for entry in export_set.shapekey_reorder_overrides
        if entry.target_object is not None and _object_key(entry.target_object)
    }

    remove_indices = [
        index for index, entry in enumerate(export_set.shapekey_reorder_overrides)
        if not _object_key(entry.target_object) or _object_key(entry.target_object) not in target_keys
    ]
    for index in reversed(remove_indices):
        export_set.shapekey_reorder_overrides.remove(index)

    for obj in target_objects:
        object_key = _object_key(obj)
        if not object_key or object_key in existing_entries:
            continue
        entry = export_set.shapekey_reorder_overrides.add()
        entry.target_object = obj

    _sort_entries_by_target(export_set.shapekey_reorder_overrides)
    if export_set.active_shapekey_reorder_override_index >= len(export_set.shapekey_reorder_overrides):
        export_set.active_shapekey_reorder_override_index = max(
            0,
            len(export_set.shapekey_reorder_overrides) - 1,
        )
    return target_objects


def ensure_override_entries(export_set):
    return sync_override_entries(export_set)


def get_active_override_entry(export_set, *, sync=True):
    if sync:
        sync_override_entries(export_set)
    if not export_set.shapekey_reorder_overrides:
        return None
    index = min(
        export_set.active_shapekey_reorder_override_index,
        len(export_set.shapekey_reorder_overrides) - 1,
    )
    return export_set.shapekey_reorder_overrides[index]


def get_override_entry(export_set, target_object, *, sync=True):
    if sync:
        sync_override_entries(export_set)
    target_key = _object_key(target_object)
    for entry in export_set.shapekey_reorder_overrides:
        if _object_key(entry.target_object) == target_key:
            return entry
    return None


def get_entry_ordered_names(entry):
    return [row.final_name for row in entry.rows if row.final_name]


def get_entry_saved_entries(entry):
    return [
        {
            "final_name": row.final_name,
            "match_tokens": [
                token
                for token in str(getattr(row, "match_tokens_serialized", "") or "").splitlines()
                if token
            ],
        }
        for row in entry.rows
        if row.final_name
    ]


def set_entry_rows(entry, rows):
    _clear_collection(entry.rows)
    for row in rows:
        item = entry.rows.add()
        item.final_name = row.final_name
        item.kinds_label = row.kinds_label
        item.source_objects_label = row.source_objects_label
        item.source_detail_label = row.source_detail_label
        item.match_tokens_serialized = getattr(row, "match_tokens_serialized", "")
        item.state_label = row.state_label
        item.is_basis = row.is_basis
        item.is_resolved = row.is_resolved
    if len(entry.rows) == 0:
        entry.active_row_index = 0
    else:
        entry.active_row_index = min(max(0, entry.active_row_index), len(entry.rows) - 1)
