import json


REORDER_CUSTOM_PROP = "mizore_export_reorder_shapekeys"

VALID_REORDER_OPERATIONS = {
    'MOVE_TO_INDEX',
    'SORT_BY_NAME',
    'SWAP',
    'MOVE_BEFORE',
}


def _clear_collection(collection):
    while len(collection) > 0:
        collection.remove(len(collection) - 1)


def _load_json_list(obj, prop_name):
    raw = obj.get(prop_name, "[]")
    if not isinstance(raw, str):
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else []


def _delete_idprop_if_exists(obj, prop_name):
    if prop_name in obj:
        del obj[prop_name]


def _normalize_reorder_entry(entry):
    if not isinstance(entry, dict):
        return None

    operation_type = str(entry.get("operation_type", "SORT_BY_NAME") or "SORT_BY_NAME")
    if operation_type not in VALID_REORDER_OPERATIONS:
        operation_type = "SORT_BY_NAME"

    try:
        destination_index = int(entry.get("destination_index", 1))
    except (TypeError, ValueError):
        destination_index = 1

    return {
        "operation_type": operation_type,
        "target_shapekey_name": str(entry.get("target_shapekey_name", "") or ""),
        "destination_index": max(0, destination_index),
        "second_shapekey_name": str(entry.get("second_shapekey_name", "") or ""),
    }


def _normalized_entries(entries):
    result = []
    for entry in entries:
        normalized = _normalize_reorder_entry(entry)
        if normalized is not None:
            result.append(normalized)
    return result


def set_reorder_settings(obj, entries):
    normalized = _normalized_entries(entries)
    if normalized:
        obj[REORDER_CUSTOM_PROP] = json.dumps(normalized, ensure_ascii=False)
    else:
        _delete_idprop_if_exists(obj, REORDER_CUSTOM_PROP)


def _read_reorder_settings(obj):
    return _normalized_entries(_load_json_list(obj, REORDER_CUSTOM_PROP))


def get_reorder_settings(obj):
    return _read_reorder_settings(obj)


def is_ui_sync_in_progress(wm):
    return getattr(wm, "mizore_reorder_shapekeys_ui_syncing", False)


def _set_reorder_ui_collection(collection, entries):
    _clear_collection(collection)
    for entry in entries:
        item = collection.add()
        item.operation_type = entry["operation_type"]
        item.target_shapekey_name = entry["target_shapekey_name"]
        item.destination_index = entry["destination_index"]
        item.second_shapekey_name = entry["second_shapekey_name"]


def _clamp_ui_index(wm):
    if len(wm.mizore_reorder_shapekeys_ui) == 0:
        wm.mizore_reorder_shapekeys_ui_index = 0
    else:
        wm.mizore_reorder_shapekeys_ui_index = min(
            max(0, wm.mizore_reorder_shapekeys_ui_index),
            len(wm.mizore_reorder_shapekeys_ui) - 1,
        )


def load_ui_state_from_object(obj, wm):
    wm.mizore_reorder_shapekeys_ui_syncing = True
    try:
        _set_reorder_ui_collection(
            wm.mizore_reorder_shapekeys_ui,
            get_reorder_settings(obj),
        )
        wm.mizore_reorder_shapekeys_ui_object_name = obj.name
        _clamp_ui_index(wm)
    finally:
        wm.mizore_reorder_shapekeys_ui_syncing = False


def ensure_ui_state_for_object(obj, wm):
    object_name = getattr(wm, "mizore_reorder_shapekeys_ui_object_name", "")
    if object_name != obj.name:
        load_ui_state_from_object(obj, wm)


def save_reorder_ui_state(obj, wm):
    if is_ui_sync_in_progress(wm):
        return
    entries = [
        {
            "operation_type": item.operation_type,
            "target_shapekey_name": item.target_shapekey_name,
            "destination_index": item.destination_index,
            "second_shapekey_name": item.second_shapekey_name,
        }
        for item in wm.mizore_reorder_shapekeys_ui
    ]
    set_reorder_settings(obj, entries)
