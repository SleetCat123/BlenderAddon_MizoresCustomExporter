import os
import sys
import time
import traceback

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


START_TIME = time.time()
TIMEOUT_SECONDS = 180.0


def request_quit():
    bpy.ops.wm.quit_blender()
    return None


def patch_export_operator(expected_files):
    modules = t.load_required_modules()
    operator_cls = modules["op_core"].INFO_MT_file_custom_export_mizore_fbx
    original_complete = operator_cls._on_complete
    original_error = operator_cls._on_error
    original_cancel = operator_cls._on_cancel

    def _complete(self, context):
        try:
            original_complete(self, context)
            t.validate_exported_outputs(expected_files)
        except Exception as exc:
            traceback.print_exc()
            t.write_status(t.format_exception("error", exc) + "\n" + traceback.format_exc())
        else:
            t.write_status("complete")
        bpy.app.timers.register(request_quit, first_interval=0.1)

    def _error(self, context, error):
        try:
            original_error(self, context, error)
        finally:
            t.write_status(f"error:{error}")
            bpy.app.timers.register(request_quit, first_interval=0.1)

    def _cancel(self, context):
        try:
            original_cancel(self, context)
        finally:
            t.write_status("cancel")
            bpy.app.timers.register(request_quit, first_interval=0.1)

    operator_cls._on_complete = _complete
    operator_cls._on_error = _error
    operator_cls._on_cancel = _cancel


def start_export():
    result = bpy.ops.export_scene.custom_export_mizore_fbx(
        'EXEC_DEFAULT',
        filepath=t.BASE_EXPORT_PATH,
        use_selection=True,
        object_types={'MESH', 'ARMATURE'},
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=False,
        enable_separate_lr_shapekey=False,
        enable_subtract_base_shapekey=False,
        enable_reorder_shapekeys=False,
        use_mesh_modifiers=False,
        bake_anim=False,
        save_prefs=False,
        save_path=False,
        batch_mode='EXPORT_SETS',
    )
    print(f"start_export result: {result}")
    if 'RUNNING_MODAL' not in result:
        t.write_status(f"error:unexpected operator result {result}")
        bpy.app.timers.register(request_quit, first_interval=0.1)
    return None


def setup_and_export():
    try:
        t.validate_export_preferences_storage()
        expected_files = t.build_export_sets_scene()
        patch_export_operator(expected_files)
    except Exception as exc:
        traceback.print_exc()
        t.write_status(t.format_exception("error", exc) + "\n" + traceback.format_exc())
        bpy.app.timers.register(request_quit, first_interval=0.1)
        return None

    bpy.app.timers.register(start_export, first_interval=0.1)
    return None


def watchdog():
    if os.path.exists(t.STATUS_PATH):
        return None
    if time.time() - START_TIME > TIMEOUT_SECONDS:
        t.write_status("timeout")
        bpy.app.timers.register(request_quit, first_interval=0.1)
        return None
    return 0.25


if __name__ == "__main__":
    bpy.app.timers.register(setup_and_export, first_interval=0.1)
    bpy.app.timers.register(watchdog, first_interval=0.25)
