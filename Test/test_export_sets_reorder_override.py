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


def _create_shapekey_mesh(name, location):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.shape_key_add(from_mix=False)
    bpy.ops.object.shape_key_add(from_mix=False)
    obj.data.shape_keys.key_blocks[-1].name = "Smile"
    bpy.ops.object.shape_key_add(from_mix=False)
    obj.data.shape_keys.key_blocks[-1].name = "Blink"
    return obj


def main():
    try:
        t.reset_scene()
        func_export_sets = importlib.import_module(
            f"{t.EXPORTER_MODULE}.scripts.export_sets.func_export_sets"
        )
        override_storage = importlib.import_module(
            f"{t.EXPORTER_MODULE}.scripts.export_sets.shapekey_order_override.storage"
        )
        override_resolver = importlib.import_module(
            f"{t.EXPORTER_MODULE}.scripts.export_sets.shapekey_order_override.resolver"
        )
        automerge_storage = importlib.import_module(
            f"{t.AUTOMERGE_MODULE}.scripts.shapekey_order.storage"
        )
        import change_base_export_test_lib as base_t

        obj = _create_shapekey_mesh("ExportOverrideTarget", (0.0, 0.0, 0.0))
        automerge_storage.set_ordered_names(obj, ["Basis", "Blink", "Smile"])

        props = bpy.context.scene.mizore_export_sets
        export_set = props.export_sets.add()
        export_set.filename = "OverrideTest"
        item = export_set.items.add()
        item.root_object = obj
        item.include_children = False
        props.active_export_set_index = 0

        override_storage.ensure_override_entries(export_set)
        entry = override_storage.get_override_entry(export_set, obj)
        assert_equal(entry is not None, True, "override entry should be created for export-set mesh targets")

        candidate_names = ["Basis", "Smile", "Blink"]
        base_names = override_resolver.get_effective_ordered_names(export_set, obj, candidate_names=candidate_names)
        assert_equal(base_names, ["Basis", "Blink", "Smile"], "disabled override should inherit AutoMerge base order")

        entry.override_enabled = True
        override_rows = override_resolver.format_rows_for_entry(
            override_resolver.build_resolved_rows(obj, ["Basis", "Smile", "Blink"], bpy.context)
        )
        override_storage.set_entry_rows(entry, override_rows)
        override_names = override_resolver.get_effective_ordered_names(export_set, obj, candidate_names=candidate_names)
        assert_equal(override_names, ["Basis", "Smile", "Blink"], "enabled override should replace the inherited base order")

        obj.data.shape_keys.key_blocks["Smile"].name = "Grin"
        assert_equal(
            override_resolver.needs_entry_sync(entry, bpy.context),
            True,
            "renaming a shape key should mark the override rows as needing refresh",
        )
        result = bpy.ops.scene.mizore_shapekey_override_refresh_entry()
        assert_equal(result, {'FINISHED'}, "refresh override operator should rebuild rows after rename")
        renamed_override_names = override_resolver.get_effective_ordered_names(
            export_set,
            obj,
            candidate_names=["Basis", "Grin", "Blink"],
        )
        assert_equal(
            renamed_override_names,
            ["Basis", "Grin", "Blink"],
            "override rows should keep the saved position when a shape key is renamed",
        )

        stale_row = entry.rows.add()
        stale_row.final_name = "GhostOverride"
        stale_row.match_tokens_serialized = "ghost-override-token"
        stale_row.is_resolved = False
        entry.active_row_index = len(entry.rows) - 1
        bpy.ops.scene.mizore_shapekey_override_cleanup_saved_only()
        assert_equal(
            any(row.final_name == "GhostOverride" for row in entry.rows),
            False,
            "override cleanup should remove unresolved Saved Only rows",
        )

        runtime = func_export_sets.build_export_set_runtime(
            export_set=export_set,
            available_objects=[obj],
        )
        try:
            reorder_targets = override_resolver.build_export_set_reorder_targets(export_set, runtime)
            assert_equal(len(reorder_targets), 1, "runtime reorder target should resolve for the duplicated mesh")
            runtime_obj, operations = reorder_targets[0]
            assert_equal(runtime_obj == obj, False, "runtime reorder should target the duplicated mesh, not the source object")
            assert_equal(len(operations), 2, "ordered names should convert into explicit MOVE_TO_INDEX operations")
            assert_equal(operations[0]["target"], "Grin", "override order should keep the renamed key first after Basis")
        finally:
            func_export_sets.cleanup_runtime(runtime)

        output_dir = os.path.join(SCRIPT_DIR, "output_export_sets_flow")
        os.makedirs(output_dir, exist_ok=True)
        export_path = os.path.join(output_dir, "OverrideTest.fbx")
        if os.path.exists(export_path):
            os.remove(export_path)

        operator = base_t.ExportOperatorStub(
            filepath=os.path.join(output_dir, "_export_sets_base.fbx"),
            enable_auto_merge=False,
        )
        operator.batch_mode = 'EXPORT_SETS'
        operator.object_types = {'MESH'}
        operator.enable_reorder_shapekeys = True
        operator.use_mesh_modifiers = False
        operator.save_prefs = False
        operator.save_path = False

        t.select_objects([obj], active=obj)
        generator = t.load_required_modules()["func_execute_main"].execute_main_iter(operator, bpy.context)
        while True:
            try:
                next(generator)
            except StopIteration as stop:
                result = stop.value
                break

        assert_equal(result.error_count, 0, "export-set reorder execution should not report errors")
        assert_equal(len(result.exported_files), 1, "export-set reorder execution should export one file")
        assert_equal(os.path.exists(export_path), True, "export-set reorder execution should create the output file")
    except Exception as exc:
        traceback.print_exc()
        print(t.format_exception("error", exc))
        raise


if __name__ == "__main__":
    main()
