# blender --factory-startup --background --python addons\BlenderAddon-MizoresCustomExporter\Test\test_export_unreadable_mesh_names.py

import ctypes
import os
import sys

import bpy
from bpy_extras.io_utils import axis_conversion
from io_scene_fbx import export_fbx_bin
from mathutils import Matrix


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import change_base_export_test_lib as t


def corrupt_first_name_byte(item, sentinel_bytes):
    data = ctypes.string_at(item.as_pointer(), 256)
    offset = data.find(sentinel_bytes + b"\x00")
    if offset < 0:
        raise AssertionError(f"Sentinel not found in item memory: {sentinel_bytes!r}")

    buffer = (ctypes.c_ubyte * len(sentinel_bytes)).from_address(item.as_pointer() + offset)
    buffer[0] = 0x80


def build_raw_export_keywords(operator):
    global_matrix = (
        axis_conversion(
            to_forward=operator.axis_forward,
            to_up=operator.axis_up,
        ).to_4x4()
        if operator.use_space_transform else Matrix()
    )

    keywords = operator.as_keywords(ignore=("check_existing", "filter_glob", "ui_tab"))
    keywords["global_matrix"] = global_matrix
    keywords["use_selection"] = True
    keywords["use_active_collection"] = False
    keywords["batch_mode"] = 'OFF'
    return keywords


def assert_raw_export_fails(filepath):
    operator = t.ExportOperatorStub(
        filepath=filepath,
        enable_auto_merge=False,
    )
    keywords = build_raw_export_keywords(operator)
    keywords["filepath"] = filepath

    try:
        export_fbx_bin.save(operator, bpy.context, **keywords)
    except UnicodeDecodeError:
        return

    raise AssertionError("Raw FBX export unexpectedly succeeded with unreadable mesh names")


def main():
    modules = t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    t.reset_scene()
    t.ensure_output_dir()

    export_path = os.path.join(t.OUTPUT_DIR, "unreadable_mesh_names_export.fbx")
    if os.path.exists(export_path):
        os.remove(export_path)

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, 0.0))
    obj = t.get_active_object()
    obj.name = "UnreadableMesh"
    obj.data.name = "UnreadableMeshData"

    uv = obj.data.uv_layers.new(name="UV_SENTINEL_123")
    color = obj.data.color_attributes.new(
        name="COLOR_SENTINEL_123",
        type='FLOAT_COLOR',
        domain='CORNER',
    )
    for item in color.data:
        item.color = (1.0, 0.25, 0.5, 1.0)

    corrupt_first_name_byte(uv, b"UV_SENTINEL_123")
    corrupt_first_name_byte(color, b"COLOR_SENTINEL_123")

    uv_offset = func_execute_main.resolve_collection_item_name_offset("uv_layers")
    color_offset = func_execute_main.resolve_collection_item_name_offset("color_attributes")
    uv_raw_before = func_execute_main.save_collection_item_name_bytes(uv, uv_offset)
    color_raw_before = func_execute_main.save_collection_item_name_bytes(color, color_offset)

    t.select_objects([obj], active=obj)
    assert_raw_export_fails(export_path)
    if os.path.exists(export_path):
        os.remove(export_path)

    operator, result = t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=export_path,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'OFF',
            "object_types": {'MESH'},
            "save_prefs": False,
            "save_path": False,
        },
    )

    if result.errors:
        raise AssertionError(f"Export reported errors: {result.errors}")
    if operator.report_log:
        error_reports = [entry for entry in operator.report_log if 'ERROR' in entry[0]]
        if error_reports:
            raise AssertionError(f"Operator reported export errors: {error_reports}")

    restored_obj = bpy.data.objects.get("UnreadableMesh")
    if restored_obj is None:
        raise AssertionError("Original object was not restored after export")

    restored_uv = restored_obj.data.uv_layers[0]
    restored_color = restored_obj.data.color_attributes[0]
    uv_raw_after = func_execute_main.save_collection_item_name_bytes(restored_uv, uv_offset)
    color_raw_after = func_execute_main.save_collection_item_name_bytes(restored_color, color_offset)

    if uv_raw_after != uv_raw_before:
        raise AssertionError("UV layer raw name bytes were not restored after export")
    if color_raw_after != color_raw_before:
        raise AssertionError("Color attribute raw name bytes were not restored after export")

    print("PASS: unreadable mesh names export")


if __name__ == "__main__":
    main()
