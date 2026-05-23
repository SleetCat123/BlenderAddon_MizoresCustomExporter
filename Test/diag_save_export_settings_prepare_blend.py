import importlib
import os
import sys

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTER_ADDON_DIR = os.path.dirname(SCRIPT_DIR)
ADDONS_DIR = os.path.dirname(EXPORTER_ADDON_DIR)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_export_sets_flow")
BLEND_PATH = os.path.join(OUTPUT_DIR, "save_export_settings_gui_invoke.blend")


if ADDONS_DIR not in sys.path:
    sys.path.insert(0, ADDONS_DIR)


def ensure_addon_enabled(module_name):
    if module_name in bpy.context.preferences.addons:
        return
    result = bpy.ops.preferences.addon_enable(module=module_name)
    if 'FINISHED' not in result:
        raise RuntimeError(f"Failed to enable addon: {module_name} ({result})")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ensure_addon_enabled("BlenderAddon-MizoresCustomExporter")
    save_export_settings = importlib.import_module(
        "BlenderAddon-MizoresCustomExporter.scripts.custom_exporter_fbx.op_save_export_settings"
    )

    operator = bpy.context.window_manager.operator_properties_last("export_scene.custom_export_mizore_fbx")
    operator.batch_mode = 'EXPORT_SETS'
    operator.enable_auto_merge = False
    operator.global_scale = 2.5
    operator.limit_vertex_group_count = 8
    operator.object_types = {'MESH', 'ARMATURE'}
    operator.batch_filename_format = "{collection}"
    operator.path_mode = 'COPY'
    operator.use_selection = True
    operator.mod_filter_weighted_normal = False

    save_export_settings.OBJECT_OT_mizore_save_export_settings.operator = operator
    result = bpy.ops.object.mizore_save_export_settings()
    if result != {'FINISHED'}:
        raise RuntimeError(f"Save Export Settings failed: {result}")

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, copy=False)
    print(f"prepared:{BLEND_PATH}")


if __name__ == "__main__":
    main()
