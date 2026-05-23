import importlib
import json
import os
import sys
import traceback

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTER_ADDON_DIR = os.path.dirname(SCRIPT_DIR)
ADDONS_DIR = os.path.dirname(EXPORTER_ADDON_DIR)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_export_sets_flow")
BLEND_PATH = os.path.join(OUTPUT_DIR, "save_export_settings_gui_button.blend")
RESULT_PATH = os.path.join(OUTPUT_DIR, "save_export_settings_gui_button.json")


if ADDONS_DIR not in sys.path:
    sys.path.insert(0, ADDONS_DIR)


def write_result(payload):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)


def request_quit():
    bpy.ops.wm.quit_blender()
    return None


def ensure_addon_enabled(module_name):
    if module_name in bpy.context.preferences.addons:
        return
    result = bpy.ops.preferences.addon_enable(module=module_name)
    if 'FINISHED' not in result:
        raise RuntimeError(f"Failed to enable addon: {module_name} ({result})")


def start():
    try:
        ensure_addon_enabled("BlenderAddon-MizoresCustomExporter")
        op_core = importlib.import_module(
            "BlenderAddon-MizoresCustomExporter.scripts.custom_exporter_fbx.op_core"
        )
        save_export_settings = importlib.import_module(
            "BlenderAddon-MizoresCustomExporter.scripts.custom_exporter_fbx.op_save_export_settings"
        )

        operator_cls = op_core.INFO_MT_file_custom_export_mizore_fbx
        original_invoke = operator_cls.invoke

        def patched_invoke(self, context, event):
            try:
                self.batch_mode = 'EXPORT_SETS'
                self.enable_auto_merge = False
                self.global_scale = 2.5
                self.limit_vertex_group_count = 8
                self.object_types = {'MESH', 'ARMATURE'}
                self.batch_filename_format = "{collection}"
                self.path_mode = 'COPY'
                self.use_selection = True
                self.mod_filter_weighted_normal = False

                save_export_settings.OBJECT_OT_mizore_save_export_settings.operator = self
                save_result = bpy.ops.object.mizore_save_export_settings()
                bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, copy=False)

                write_result({
                    "save_result": list(save_result),
                    "blend_path": BLEND_PATH,
                })
            except Exception as exc:
                write_result({
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                })
            finally:
                operator_cls.invoke = original_invoke
                bpy.app.timers.register(request_quit, first_interval=0.1)
            return {'CANCELLED'}

        operator_cls.invoke = patched_invoke
        bpy.ops.export_scene.custom_export_mizore_fbx('INVOKE_DEFAULT')
    except Exception as exc:
        write_result({
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })
        bpy.app.timers.register(request_quit, first_interval=0.1)

    return None


if __name__ == "__main__":
    bpy.app.timers.register(start, first_interval=0.1)
