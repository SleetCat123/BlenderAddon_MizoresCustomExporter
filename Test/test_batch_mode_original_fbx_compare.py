# blender --factory-startup --background --python addons\BlenderAddon-MizoresCustomExporter\Test\test_batch_mode_original_fbx_compare.py

import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import batch_mode_original_fbx_compare_test_lib as t


def main():
    failures = []
    for batch_mode in [
        "OFF",
        "SCENE",
        "COLLECTION",
        "SCENE_COLLECTION",
        "ACTIVE_SCENE_COLLECTION",
    ]:
        try:
            t.validate_batch_mode_matches_original_fbx(batch_mode)
        except Exception as exc:
            traceback.print_exc()
            failures.append(f"{batch_mode}: {exc}")

    if failures:
        raise AssertionError("Original FBX comparison failed:\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
