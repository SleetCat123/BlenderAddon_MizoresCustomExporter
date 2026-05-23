import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


def main():
    try:
        t.validate_export_set_object_replace_duplicate_root()
        t.validate_export_set_object_replace_armature_modifier_retarget()
        t.validate_export_set_object_replace_unsupported_modifier_detection()
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
