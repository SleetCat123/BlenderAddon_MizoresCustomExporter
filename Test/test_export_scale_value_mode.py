# blender --factory-startup --background --python addons\BlenderAddon-MizoresCustomExporter\Test\test_export_scale_value_mode.py

import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import scale_value_mode_test_lib as t


def main():
    try:
        t.validate_static_scale_value_mode_export(
            scale_pivot='WORLD_ORIGIN',
            expected_locations={
                "ScaleMeshA": (2.0, 0.0, 0.0),
                "ScaleMeshB": (6.0, 0.0, 0.0),
            },
        )
        t.validate_static_scale_value_mode_export(
            scale_pivot='EACH_OBJECT_ORIGIN',
            expected_locations={
                "ScaleMeshA": (1.0, 0.0, 0.0),
                "ScaleMeshB": (3.0, 0.0, 0.0),
            },
        )
        t.validate_scale_value_mode_armature_export_matches_normal()
        t.validate_scale_value_mode_bone_parent_export_matches_normal()
        t.validate_connected_bone_each_object_origin_matches_scaled_source()
        t.validate_scale_value_mode_world_origin_matches_builtin_fbx_global_scale_reference()
        t.validate_scale_value_mode_export_sets_reuses_runtime_duplicates()
        t.validate_scale_value_mode_export_sets_merge_join_keeps_surviving_duplicates()
        t.validate_scale_value_mode_animation_all_actions_export()
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
