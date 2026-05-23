import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


def main():
    try:
        t.validate_export_set_move_operators()
        t.validate_export_set_item_add_operator_does_not_copy_active_object()
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
