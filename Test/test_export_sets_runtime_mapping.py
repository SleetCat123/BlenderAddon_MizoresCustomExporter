import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


def main():
    try:
        t.validate_export_set_legacy_primary_armature_migration()
        t.validate_duplicate_objects_preserves_export_set_references()
        t.validate_export_set_runtime_mapping()
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
