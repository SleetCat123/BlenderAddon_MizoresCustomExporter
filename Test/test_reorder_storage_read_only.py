import importlib
import os
import sys
import traceback

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import export_sets_flow_test_lib as t


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r} actual={actual!r}")


def main():
    try:
        t.reset_scene()
        automerge_storage = importlib.import_module(
            f"{t.AUTOMERGE_MODULE}.scripts.shapekey_order.storage"
        )
        assert_equal(
            hasattr(bpy.types.Object, "mizore_reorder_shapekeys"),
            False,
            "legacy reorder object collection should not be registered",
        )

        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
        obj = bpy.context.object
        obj.name = "ReorderReadOnlyTarget"

        obj[automerge_storage.REORDER_CUSTOM_PROP] = "[]"
        entries = automerge_storage.get_ordered_names(obj, candidate_names=["Basis", "A"])
        assert_equal(entries, [], "empty current reorder settings should read as empty list")
        assert_equal(
            obj.get(automerge_storage.REORDER_CUSTOM_PROP),
            "[]",
            "reading reorder settings should not delete the current custom property",
        )

        ordered_names = ["Basis", "Smile", "Blink"]
        automerge_storage.set_ordered_names(obj, ordered_names)
        assert_equal(
            automerge_storage.REORDER_CUSTOM_PROP in obj,
            True,
            "saving reorder settings should write the current custom property",
        )
        assert_equal(
            automerge_storage.get_ordered_names(obj, candidate_names=["Basis", "Smile", "Blink"]),
            ordered_names,
            "saved reorder settings should be readable",
        )
        automerge_storage.set_ordered_names(obj, [])
        assert_equal(
            automerge_storage.REORDER_CUSTOM_PROP in obj,
            False,
            "saving an empty list should remove the current custom property",
        )
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
