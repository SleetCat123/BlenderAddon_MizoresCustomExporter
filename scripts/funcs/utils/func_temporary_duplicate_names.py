import uuid

from ... import consts


def build_temporary_name(name: str, duplicate_id: str):
    suffix = consts.EXPORT_TEMP_SUFFIX + duplicate_id[:8]
    base_name = name[:max(1, consts.MAX_NAME_LENGTH - len(suffix))]
    return base_name + suffix


def set_duplicate_ids(objects, duplicate_id_prop_name: str):
    duplicate_ids = {}
    for obj in objects:
        duplicate_id = uuid.uuid4().hex
        obj[duplicate_id_prop_name] = duplicate_id
        duplicate_ids[obj.name] = duplicate_id
    return duplicate_ids


def clear_duplicate_ids(objects, duplicate_id_prop_name: str):
    for obj in objects:
        try:
            if duplicate_id_prop_name in obj:
                del obj[duplicate_id_prop_name]
        except ReferenceError:
            continue


def build_duplicate_lookup(duplicate_objects, duplicate_id_prop_name: str):
    duplicate_lookup = {}
    for obj in duplicate_objects:
        duplicate_id = obj.get(duplicate_id_prop_name)
        if duplicate_id:
            duplicate_lookup[duplicate_id] = obj
    return duplicate_lookup


def build_duplicate_source_pairs(source_objects, duplicate_objects, duplicate_id_prop_name: str):
    duplicate_lookup = build_duplicate_lookup(duplicate_objects, duplicate_id_prop_name)
    result = []
    for source_obj in source_objects:
        duplicate_id = source_obj.get(duplicate_id_prop_name)
        if not duplicate_id:
            continue
        duplicate_obj = duplicate_lookup.get(duplicate_id)
        if duplicate_obj is None:
            continue
        result.append((source_obj, duplicate_obj))
    return result


def swap_duplicate_object_and_data_names_to_source_names(
    source_objects,
    duplicate_objects,
    duplicate_id_prop_name: str,
):
    duplicate_lookup = build_duplicate_lookup(duplicate_objects, duplicate_id_prop_name)
    rename_records = []

    for source_obj in source_objects:
        duplicate_id = source_obj.get(duplicate_id_prop_name)
        if not duplicate_id:
            continue

        duplicate_obj = duplicate_lookup.get(duplicate_id)
        if duplicate_obj is None:
            continue

        source_record = {
            "source_obj": source_obj,
            "source_name": source_obj.name,
            "source_data_name": source_obj.data.name if getattr(source_obj, "data", None) is not None else None,
        }

        source_obj.name = build_temporary_name(source_obj.name, duplicate_id)
        if getattr(source_obj, "data", None) is not None and source_record["source_data_name"] is not None:
            source_obj.data.name = build_temporary_name(source_record["source_data_name"], duplicate_id)

        duplicate_obj.name = source_record["source_name"]
        if getattr(duplicate_obj, "data", None) is not None and source_record["source_data_name"] is not None:
            duplicate_obj.data.name = source_record["source_data_name"]

        rename_records.append(source_record)

    return rename_records


def restore_source_object_and_data_names(rename_records):
    for record in rename_records:
        source_obj = record["source_obj"]
        try:
            source_obj.name = record["source_name"]
            if getattr(source_obj, "data", None) is not None and record["source_data_name"] is not None:
                source_obj.data.name = record["source_data_name"]
        except ReferenceError:
            continue
