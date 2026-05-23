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


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def _add_mesh(name, location):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def main():
    try:
        t.reset_scene()
        storage = importlib.import_module(
            f"{t.EXPORTER_MODULE}.scripts.export_sets.shapekey_order_override.storage"
        )

        root_a = _add_mesh("OverrideSyncRootA", (0.0, 0.0, 0.0))
        root_b = _add_mesh("OverrideSyncRootB", (2.0, 0.0, 0.0))

        props = bpy.context.scene.mizore_export_sets
        export_set = props.export_sets.add()
        export_set.filename = "OverrideSync"
        props.active_export_set_index = 0

        item_a = export_set.items.add()
        item_a.root_object = root_a

        assert_equal(
            len(export_set.shapekey_reorder_overrides),
            1,
            "setting a root object should sync override targets outside draw",
        )
        assert_true(
            storage.needs_override_sync(export_set) is False,
            "synced override targets should not report a pending sync",
        )

        export_set.shapekey_reorder_overrides.remove(0)
        assert_true(
            storage.needs_override_sync(export_set),
            "manually desynced override targets should be detected without mutating draw state",
        )
        assert_equal(
            storage.get_active_override_entry(export_set, sync=False),
            None,
            "draw-safe active entry lookup should not recreate overrides automatically",
        )

        result = bpy.ops.scene.mizore_shapekey_override_sync_targets()
        assert_true('FINISHED' in result, "sync operator should rebuild override targets")
        assert_equal(
            len(export_set.shapekey_reorder_overrides),
            1,
            "sync operator should recreate missing override targets",
        )
        entry = storage.get_active_override_entry(export_set, sync=False)
        entry.override_enabled = True
        assert_true(
            len(entry.rows) > 0,
            "enabling override should prepare editable rows outside draw",
        )

        item_b = export_set.items.add()
        item_b.root_object = root_b
        assert_equal(
            len(export_set.shapekey_reorder_overrides),
            2,
            "adding another root object should resync override targets",
        )
        assert_true(
            storage.needs_override_sync(export_set) is False,
            "automatic sync after item update should keep override targets current",
        )

        export_set.active_item_index = len(export_set.items) - 1
        result = bpy.ops.scene.mizore_remove_export_set_item()
        assert_true('FINISHED' in result, "remove item operator should succeed")
        assert_equal(
            len(export_set.shapekey_reorder_overrides),
            1,
            "removing an export set item should clean up stale override targets",
        )
        assert_equal(
            export_set.shapekey_reorder_overrides[0].target_object.name,
            root_a.name,
            "remaining override target should stay linked to the surviving export item",
        )
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
