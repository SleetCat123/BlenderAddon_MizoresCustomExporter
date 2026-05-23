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
RESULT_PATH = os.path.join(OUTPUT_DIR, "save_export_settings_gui_invoke.json")


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
        preferences_scene = importlib.import_module(
            "BlenderAddon-MizoresCustomExporter.scripts.preferences_scene"
        )

        operator_cls = op_core.INFO_MT_file_custom_export_mizore_fbx
        original_invoke = operator_cls.invoke

        def patched_invoke(self, context, event):
            try:
                bl_rna_keys = []
                try:
                    bl_rna_keys = [prop.identifier for prop in self.bl_rna.properties][:20]
                except Exception:
                    bl_rna_keys = ["<error>"]
                properties_keys = []
                try:
                    properties_keys = [prop.identifier for prop in self.properties.bl_rna.properties][:20]
                except Exception:
                    properties_keys = ["<error>"]
                preferences_scene.load_scene_prefs(self)
                write_result({
                    "self_type": str(type(self)),
                    "has_batch_mode_attr": hasattr(self, "batch_mode"),
                    "has_properties_attr": hasattr(self, "properties"),
                    "bl_rna_keys_head": bl_rna_keys,
                    "properties_bl_rna_keys_head": properties_keys,
                    "batch_mode": self.batch_mode,
                    "enable_auto_merge": self.enable_auto_merge,
                    "global_scale": self.global_scale,
                    "limit_vertex_group_count": self.limit_vertex_group_count,
                    "object_types": sorted(self.object_types),
                    "batch_filename_format": self.batch_filename_format,
                    "path_mode": self.path_mode,
                    "use_selection": self.use_selection,
                    "mod_filter_weighted_normal": self.mod_filter_weighted_normal,
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
