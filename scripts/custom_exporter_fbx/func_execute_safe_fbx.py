import ctypes

import bpy
from io_scene_fbx import export_fbx_bin

from . import func_export_scale_value_mode


NAME_PROBE_BUFFER_SIZE = 256
NAME_FIELD_BYTE_SIZE = 64
NAME_OFFSET_CACHE = {}


def read_collection_item_name(item):
    return item.name


def resolve_collection_item_name_offset(collection_key):
    cached_offset = NAME_OFFSET_CACHE.get(collection_key)
    if cached_offset is not None:
        return cached_offset

    probe_mesh = bpy.data.meshes.new("__mizore_export_name_probe__")
    try:
        if collection_key == "uv_layers":
            sentinel_name = "MIZORE_UV_NAME_SENTINEL_123"
            probe_item = probe_mesh.uv_layers.new(name=sentinel_name)
        elif collection_key == "color_attributes":
            sentinel_name = "MIZORE_COLOR_NAME_SENTINEL_123"
            probe_item = probe_mesh.color_attributes.new(
                name=sentinel_name,
                type='FLOAT_COLOR',
                domain='CORNER',
            )
        elif collection_key == "attributes":
            sentinel_name = "MIZORE_ATTRIBUTE_NAME_SENTINEL_123"
            probe_item = probe_mesh.attributes.new(
                name=sentinel_name,
                type='FLOAT',
                domain='POINT',
            )
        else:
            raise ValueError(f"Unsupported collection key: {collection_key}")

        sentinel_bytes = sentinel_name.encode("ascii") + b"\x00"
        probe_data = ctypes.string_at(probe_item.as_pointer(), NAME_PROBE_BUFFER_SIZE)
        offset = probe_data.find(sentinel_bytes)
        if offset < 0:
            raise RuntimeError(
                f"Failed to resolve name offset for {collection_key}: sentinel not found"
            )

        NAME_OFFSET_CACHE[collection_key] = offset
        return offset
    finally:
        try:
            if probe_mesh.users == 0:
                bpy.data.meshes.remove(probe_mesh)
        except Exception:
            pass


def save_collection_item_name_bytes(item, offset):
    return bytes(ctypes.string_at(item.as_pointer() + offset, NAME_FIELD_BYTE_SIZE))


def restore_collection_item_name_bytes(item, offset, raw_name):
    buffer = (ctypes.c_ubyte * len(raw_name)).from_address(item.as_pointer() + offset)
    for index, value in enumerate(raw_name):
        buffer[index] = value


def build_fallback_collection_name(prefix, used_names, index):
    base_name = prefix or "Item"
    candidate = base_name if base_name not in used_names else f"{base_name}.{index:03d}"
    suffix = index
    while candidate in used_names:
        suffix += 1
        candidate = f"{base_name}.{suffix:03d}"
    return candidate


def collect_unreadable_collection_items(collection, collection_key):
    unreadable_items = []
    if collection is None:
        return unreadable_items

    try:
        list(collection.keys())
        return unreadable_items
    except Exception:
        pass

    offset = resolve_collection_item_name_offset(collection_key)
    for index, item in enumerate(collection):
        try:
            read_collection_item_name(item)
        except Exception as ex:
            unreadable_items.append({
                "item": item,
                "index": index,
                "pointer": item.as_pointer(),
                "offset": offset,
                "raw_name": save_collection_item_name_bytes(item, offset),
                "error_type": type(ex).__name__,
                "error_message": str(ex),
            })

    return unreadable_items


def rename_unreadable_collection_items(
    collection,
    fallback_prefix,
    unreadable_items,
    owner_name,
    collection_label,
    renamed_item_pointers,
):
    if collection is None or not unreadable_items:
        return []

    used_names = set()
    for item in collection:
        try:
            used_names.add(read_collection_item_name(item))
        except Exception:
            continue

    renamed_items = []
    for unreadable_item in unreadable_items:
        if unreadable_item["pointer"] in renamed_item_pointers:
            continue

        safe_name = build_fallback_collection_name(
            fallback_prefix,
            used_names,
            unreadable_item["index"],
        )
        print(
            f"[MizoreExporter] Renamed unreadable {collection_label} on '{owner_name}' "
            f"(index {unreadable_item['index']}, {unreadable_item['error_type']}: "
            f"{unreadable_item['error_message']}) -> {safe_name}"
        )
        unreadable_item["item"].name = safe_name
        used_names.add(safe_name)
        renamed_item_pointers.add(unreadable_item["pointer"])
        renamed_items.append(unreadable_item)

    return renamed_items


def prepare_temporary_safe_name_restorations(objects):
    restorations = []
    processed_meshes = set()
    renamed_item_pointers = set()

    for obj in objects:
        if obj.type != 'MESH' or getattr(obj, "data", None) is None:
            continue

        mesh = obj.data
        mesh_key = mesh.as_pointer() if hasattr(mesh, "as_pointer") else id(mesh)
        if mesh_key in processed_meshes:
            continue
        processed_meshes.add(mesh_key)

        for collection_key, fallback_prefix, collection_label in (
            ("uv_layers", "UVMap", "UV layer"),
            ("color_attributes", "Color", "color attribute"),
            ("attributes", "Attribute", "attribute"),
        ):
            collection = getattr(mesh, collection_key, None)
            unreadable_items = collect_unreadable_collection_items(collection, collection_key)
            restorations.extend(
                rename_unreadable_collection_items(
                    collection,
                    fallback_prefix,
                    unreadable_items,
                    mesh.name,
                    collection_label,
                    renamed_item_pointers,
                )
            )

    return restorations


def restore_temporary_safe_names(restorations):
    for restoration in reversed(restorations):
        try:
            restore_collection_item_name_bytes(
                restoration["item"],
                restoration["offset"],
                restoration["raw_name"],
            )
        except Exception:
            continue


def export_fbx_with_temporarily_safe_mesh_names(
    operator,
    context,
    filepath,
    keywords,
    scale_duplicate_source_pairs=None,
    scale_duplicate_objects=None,
):
    scale_context = func_export_scale_value_mode.prepare_temporary_scaled_export(
        operator,
        existing_duplicate_source_pairs=scale_duplicate_source_pairs,
        existing_duplicate_objects=scale_duplicate_objects,
    )
    selected_objects = list(bpy.context.selected_objects)
    restorations = prepare_temporary_safe_name_restorations(selected_objects)
    try:
        keywords["filepath"] = filepath
        keywords["global_scale"] = func_export_scale_value_mode.get_export_global_scale(operator)
        keywords["apply_scale_options"] = func_export_scale_value_mode.get_export_apply_scale_options(
            operator,
            keywords.get("apply_scale_options"),
        )
        export_fbx_bin.save(operator, context, **keywords)
    finally:
        restore_temporary_safe_names(restorations)
        func_export_scale_value_mode.cleanup_temporary_scaled_export(scale_context)
