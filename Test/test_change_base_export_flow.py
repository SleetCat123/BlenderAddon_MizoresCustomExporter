import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


from change_base_export_test_lib import run_selected_scenarios


if __name__ == "__main__":
    run_selected_scenarios("all")
