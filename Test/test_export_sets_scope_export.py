import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


def main():
    try:
        t.validate_export_set_scope_resolution()
        t.validate_export_set_scope_skips_dont_export_children()
        t.validate_export_set_scope_skips_nested_always_export_children()
        t.validate_export_set_scope_export()
        t.validate_export_set_mesh_only_export()
        t.validate_export_set_multi_armature_export()
        t.validate_export_set_armature_root_scope_resolution()
        t.validate_export_set_explicit_armature_must_belong_to_item()
        t.validate_export_set_armature_root_merge_export()
        t.validate_export_set_merge_infers_target_from_empty_attach_bone()
        t.validate_export_set_mesh_root_explicit_armature_requires_target()
        t.validate_export_set_mesh_root_explicit_armature_merges_into_target()
        t.validate_export_set_shared_target_armature_accepts_multiple_items()
        t.validate_shapekey_override_preview_does_not_request_writes()
        t.validate_export_set_progress_updates_are_granular()
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
