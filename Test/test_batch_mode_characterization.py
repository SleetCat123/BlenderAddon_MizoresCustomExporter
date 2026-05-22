import os
import sys
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import batch_mode_characterization_test_lib as t


def main():
    try:
        t.validate_batch_mode_off_behavior()
        t.validate_batch_mode_scene_behavior()
        t.validate_batch_mode_collection_behavior()
        t.validate_batch_mode_collection_with_child_collections_behavior()
        t.validate_batch_mode_scene_collection_behavior()
        t.validate_batch_mode_scene_collection_with_child_collections_behavior()
        t.validate_batch_mode_active_scene_collection_behavior()
        t.validate_batch_mode_active_scene_collection_with_child_collections_behavior()
        t.validate_batch_mode_collections_in_active_collection_behavior()
        t.validate_batch_mode_collections_in_active_collection_with_child_collections_behavior()
        t.validate_batch_mode_objects_in_active_collection_behavior()
    except Exception as exc:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
