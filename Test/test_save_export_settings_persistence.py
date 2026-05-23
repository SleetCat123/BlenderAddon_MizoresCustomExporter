import os
import sys
import traceback

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


def main():
    try:
        t.validate_export_preferences_storage()
        t.validate_export_preferences_persist_after_mainfile_reload()
        t.validate_export_preferences_persist_on_operator_invoke()
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
