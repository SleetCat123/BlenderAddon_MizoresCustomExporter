import os
import sys

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import change_base_export_test_lib as base_t


def log(message):
    print(f"[batch-mode-test] {message}")


def _create_cube(name, location, size=1.0):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = base_t.get_active_object()
    obj.name = name
    obj.data.name = f"{name}Data"
    return obj


def _create_plane(name, location, size=1.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    obj = base_t.get_active_object()
    obj.name = name
    obj.data.name = f"{name}Data"
    return obj


def _create_cone(name, location, vertices=10, radius1=0.5, depth=1.0):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, depth=depth, location=location)
    obj = base_t.get_active_object()
    obj.name = name
    obj.data.name = f"{name}Data"
    return obj


def _create_cylinder(name, location, vertices=12, radius=0.4, depth=1.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = base_t.get_active_object()
    obj.name = name
    obj.data.name = f"{name}Data"
    return obj


def _create_ico_sphere(name, location, subdivisions=1, radius=0.45):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=location)
    obj = base_t.get_active_object()
    obj.name = name
    obj.data.name = f"{name}Data"
    return obj


def _find_layer_collection(layer_collection, target_name):
    if layer_collection.collection.name == target_name:
        return layer_collection
    for child in layer_collection.children:
        found = _find_layer_collection(child, target_name)
        if found is not None:
            return found
    return None


def _set_active_collection(collection):
    layer_collection = _find_layer_collection(bpy.context.view_layer.layer_collection, collection.name)
    if layer_collection is None:
        raise AssertionError(f"Layer collection was not found: {collection.name}")
    bpy.context.view_layer.active_layer_collection = layer_collection


def _mesh_counts(*objects):
    return {obj.name: len(obj.data.vertices) for obj in objects}


def _expected_path(filename):
    return os.path.join(base_t.OUTPUT_DIR, filename)


def _assert_exported_paths(result, expected_filenames):
    actual = sorted(os.path.basename(item.filepath) for item in result.exported_files)
    expected = sorted(expected_filenames)
    if actual != expected:
        raise AssertionError(
            f"Unexpected exported files. actual={actual} expected={expected}"
        )


def _assert_exported_meshes(filepath, expected_mesh_counts, forbidden_names=None):
    imported_meshes = base_t.import_fbx(filepath)
    actual_names = sorted(imported_meshes.keys())
    expected_names = sorted(expected_mesh_counts.keys())
    if actual_names != expected_names:
        raise AssertionError(
            f"{os.path.basename(filepath)} mesh names mismatch. "
            f"actual={actual_names} expected={expected_names}"
        )

    for mesh_name, expected_count in expected_mesh_counts.items():
        actual_count = len(imported_meshes[mesh_name].data.vertices)
        if actual_count != expected_count:
            raise AssertionError(
                f"{os.path.basename(filepath)}:{mesh_name} vertex count mismatch. "
                f"actual={actual_count} expected={expected_count}"
            )

    forbidden_names = forbidden_names or []
    mixed_names = sorted(set(actual_names) & set(forbidden_names))
    if mixed_names:
        raise AssertionError(
            f"{os.path.basename(filepath)} unexpectedly contains excluded meshes: {mixed_names}"
        )


def build_batch_mode_characterization_scene():
    base_t.ensure_output_dir()
    base_t.reset_scene()
    bpy.context.scene.name = "BatchModeScene"

    collection_a = base_t.ensure_scene_collection("BatchMode_A")
    collection_b = base_t.ensure_scene_collection("BatchMode_B")
    collection_ignored_exporter = base_t.ensure_scene_collection("DontExport")
    collection_ignored_merge = base_t.ensure_scene_collection("MergeGroup")
    collection_ignored_dont_merge = base_t.ensure_scene_collection("DontMergeToParent")
    collection_a_sub = bpy.data.collections.new("BatchMode_A_Sub")
    collection_a.children.link(collection_a_sub)
    collection_b_sub = bpy.data.collections.new("BatchMode_B_Sub")
    collection_b.children.link(collection_b_sub)

    a_root = _create_cube("BatchRootA", (0.0, 0.0, 0.0))
    a_child = _create_plane("BatchChildA", (0.0, 0.0, 1.0), size=0.8)
    a_standalone = _create_cone("BatchSoloA", (2.0, 0.0, 0.0), vertices=9, radius1=0.4, depth=0.9)
    a_sub = _create_cylinder("BatchSubA", (4.0, 0.0, 0.0), vertices=8, radius=0.35, depth=0.8)
    b_item = _create_ico_sphere("BatchRootB", (6.0, 0.0, 0.0), subdivisions=1, radius=0.45)
    b_sub = _create_plane("BatchSubB", (7.5, 0.0, 0.0), size=0.65)
    excluded_prop = _create_cube("BatchDontExport", (8.0, 0.0, 0.0), size=0.8)
    ignored_exporter = _create_plane("BatchIgnoredExporterCollection", (10.0, 0.0, 0.0), size=0.7)
    ignored_merge = _create_cone("BatchIgnoredMergeCollection", (12.0, 0.0, 0.0), vertices=8, radius1=0.35, depth=0.8)
    ignored_dont_merge = _create_cylinder("BatchIgnoredDontMergeCollection", (14.0, 0.0, 0.0), vertices=9, radius=0.3, depth=0.7)

    base_t.set_parent_keep_transform(a_child, a_root)
    excluded_prop["DontExport"] = True

    base_t.move_object_to_single_collection(a_root, collection_a)
    base_t.move_object_to_single_collection(a_child, collection_a)
    base_t.move_object_to_single_collection(a_standalone, collection_a)
    base_t.move_object_to_single_collection(a_sub, collection_a_sub)
    base_t.move_object_to_single_collection(b_item, collection_b)
    base_t.move_object_to_single_collection(b_sub, collection_b_sub)
    base_t.move_object_to_single_collection(excluded_prop, collection_a)
    base_t.move_object_to_single_collection(ignored_exporter, collection_ignored_exporter)
    base_t.move_object_to_single_collection(ignored_merge, collection_ignored_merge)
    base_t.move_object_to_single_collection(ignored_dont_merge, collection_ignored_dont_merge)

    _set_active_collection(collection_a)
    base_t.select_objects([a_root, b_item], active=a_root)

    for filename in [
        "batch_mode_off.fbx",
        "BatchModeScene.fbx",
        "BatchMode_A.fbx",
        "BatchMode_A_Sub.fbx",
        "BatchMode_B.fbx",
        "BatchMode_B_Sub.fbx",
        "BatchModeScene_Scene_Collection.fbx",
        "BatchRootA.fbx",
        "BatchSoloA.fbx",
    ]:
        base_t.remove_file_if_exists(_expected_path(filename))

    return {
        "collection_a": collection_a,
        "collection_b": collection_b,
        "collection_a_sub": collection_a_sub,
        "collection_b_sub": collection_b_sub,
        "forbidden_all": [
            excluded_prop.name,
        ],
        "forbidden_collection_jobs": [
            excluded_prop.name,
            ignored_exporter.name,
            ignored_merge.name,
            ignored_dont_merge.name,
        ],
        "forbidden_active_collection": [
            excluded_prop.name,
            ignored_exporter.name,
            ignored_merge.name,
            ignored_dont_merge.name,
            b_item.name,
            b_sub.name,
        ],
        "forbidden_off": [
            excluded_prop.name,
            ignored_exporter.name,
            ignored_merge.name,
            ignored_dont_merge.name,
            a_standalone.name,
            a_sub.name,
            b_sub.name,
        ],
        "off_meshes": _mesh_counts(a_root, b_item),
        "scene_meshes": _mesh_counts(
            a_root,
            a_child,
            a_standalone,
            a_sub,
            b_item,
            b_sub,
            ignored_exporter,
            ignored_merge,
            ignored_dont_merge,
        ),
        "collection_a_meshes": _mesh_counts(a_root, a_child, a_standalone),
        "collection_a_sub_meshes": _mesh_counts(a_sub),
        "collection_b_meshes": _mesh_counts(b_item),
        "collection_b_sub_meshes": _mesh_counts(b_sub),
        "active_scene_collection_meshes": _mesh_counts(a_root, a_child, a_standalone, a_sub),
        "objects_in_active_root_meshes": _mesh_counts(a_root, a_child),
        "objects_in_active_solo_meshes": _mesh_counts(a_standalone),
    }


def validate_batch_mode_off_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()

    filepath = _expected_path("batch_mode_off.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": "OFF",
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(result, ["batch_mode_off.fbx"])
    _assert_exported_meshes(filepath, scene["off_meshes"], forbidden_names=scene["forbidden_off"])


def validate_batch_mode_scene_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()

    filepath = _expected_path("BatchModeScene.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "SCENE",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    exported_filename = "BatchModeScene.fbx"
    _assert_exported_paths(result, [exported_filename])
    _assert_exported_meshes(_expected_path(exported_filename), scene["scene_meshes"], forbidden_names=scene["forbidden_all"])


def validate_batch_mode_collection_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()

    filepath = _expected_path("collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        ["BatchMode_A.fbx", "BatchMode_A_Sub.fbx", "BatchMode_B.fbx", "BatchMode_B_Sub.fbx"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_A.fbx"),
        scene["collection_a_meshes"],
        forbidden_names=scene["forbidden_collection_jobs"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_A_Sub.fbx"),
        scene["collection_a_sub_meshes"],
        forbidden_names=scene["forbidden_collection_jobs"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_B.fbx"),
        scene["collection_b_meshes"],
        forbidden_names=scene["forbidden_collection_jobs"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_B_Sub.fbx"),
        scene["collection_b_sub_meshes"],
        forbidden_names=scene["forbidden_collection_jobs"],
    )


def validate_batch_mode_collection_with_child_collections_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()

    filepath = _expected_path("collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "use_batch_collection_children_collections": True,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        ["BatchMode_A.fbx", "BatchMode_A_Sub.fbx", "BatchMode_B.fbx", "BatchMode_B_Sub.fbx"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_A.fbx"),
        {**scene["collection_a_meshes"], **scene["collection_a_sub_meshes"]},
        forbidden_names=scene["forbidden_collection_jobs"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_B.fbx"),
        {**scene["collection_b_meshes"], **scene["collection_b_sub_meshes"]},
        forbidden_names=scene["forbidden_collection_jobs"],
    )


def validate_batch_mode_scene_collection_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()

    filepath = _expected_path("scene_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "SCENE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchMode_A.fbx",
            "BatchMode_A_Sub.fbx",
            "BatchMode_B.fbx",
            "BatchMode_B_Sub.fbx",
            "BatchModeScene_Scene_Collection.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchModeScene_Scene_Collection.fbx"),
        scene["scene_meshes"],
        forbidden_names=scene["forbidden_all"],
    )


def validate_batch_mode_scene_collection_with_child_collections_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()

    filepath = _expected_path("scene_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "SCENE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "use_batch_collection_children_collections": True,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchMode_A.fbx",
            "BatchMode_A_Sub.fbx",
            "BatchMode_B.fbx",
            "BatchMode_B_Sub.fbx",
            "BatchModeScene_Scene_Collection.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_A.fbx"),
        {**scene["collection_a_meshes"], **scene["collection_a_sub_meshes"]},
        forbidden_names=scene["forbidden_collection_jobs"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_B.fbx"),
        {**scene["collection_b_meshes"], **scene["collection_b_sub_meshes"]},
        forbidden_names=scene["forbidden_collection_jobs"],
    )


def validate_batch_mode_active_scene_collection_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()
    _set_active_collection(scene["collection_a"])

    filepath = _expected_path("active_scene_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "use_active_collection": True,
            "use_active_collection_children_objects": True,
            "use_active_collection_children_collections": True,
            "batch_mode": "ACTIVE_SCENE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchMode_A.fbx",
            "BatchMode_A_Sub.fbx",
            "BatchMode_B.fbx",
            "BatchMode_B_Sub.fbx",
            "BatchModeScene_Scene_Collection.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchModeScene_Scene_Collection.fbx"),
        scene["scene_meshes"],
        forbidden_names=scene["forbidden_all"],
    )


def validate_batch_mode_active_scene_collection_with_child_collections_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()
    _set_active_collection(scene["collection_a"])

    filepath = _expected_path("active_scene_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "use_active_collection": True,
            "use_active_collection_children_objects": True,
            "use_active_collection_children_collections": True,
            "use_batch_collection_children_collections": True,
            "batch_mode": "ACTIVE_SCENE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchMode_A.fbx",
            "BatchMode_A_Sub.fbx",
            "BatchMode_B.fbx",
            "BatchMode_B_Sub.fbx",
            "BatchModeScene_Scene_Collection.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_A.fbx"),
        {**scene["collection_a_meshes"], **scene["collection_a_sub_meshes"]},
        forbidden_names=scene["forbidden_collection_jobs"],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_B.fbx"),
        {**scene["collection_b_meshes"], **scene["collection_b_sub_meshes"]},
        forbidden_names=scene["forbidden_collection_jobs"],
    )


def validate_batch_mode_objects_in_active_collection_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()
    _set_active_collection(scene["collection_a"])

    filepath = _expected_path("objects_in_active_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "OBJECTS_IN_ACTIVE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchRootA.fbx",
            "BatchSoloA.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchRootA.fbx"),
        scene["objects_in_active_root_meshes"],
        forbidden_names=scene["forbidden_active_collection"],
    )
    _assert_exported_meshes(
        _expected_path("BatchSoloA.fbx"),
        scene["objects_in_active_solo_meshes"],
        forbidden_names=scene["forbidden_active_collection"],
    )


def validate_batch_mode_collections_in_active_collection_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()
    _set_active_collection(scene["collection_a"])

    filepath = _expected_path("collections_in_active_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "COLLECTIONS_IN_ACTIVE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchMode_A.fbx",
            "BatchMode_A_Sub.fbx",
            "BatchModeScene_Scene_Collection.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchModeScene_Scene_Collection.fbx"),
        scene["active_scene_collection_meshes"],
        forbidden_names=scene["forbidden_active_collection"],
    )


def validate_batch_mode_collections_in_active_collection_with_child_collections_behavior():
    modules = base_t.load_required_modules()
    scene = build_batch_mode_characterization_scene()
    _set_active_collection(scene["collection_a"])

    filepath = _expected_path("collections_in_active_collection_mode_placeholder.fbx")
    _operator, result = base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "use_selection": False,
            "use_batch_collection_children_collections": True,
            "batch_mode": "COLLECTIONS_IN_ACTIVE_COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "save_prefs": False,
            "save_path": False,
        },
    )

    _assert_exported_paths(
        result,
        [
            "BatchMode_A.fbx",
            "BatchMode_A_Sub.fbx",
            "BatchModeScene_Scene_Collection.fbx",
        ],
    )
    _assert_exported_meshes(
        _expected_path("BatchMode_A.fbx"),
        {**scene["collection_a_meshes"], **scene["collection_a_sub_meshes"]},
        forbidden_names=scene["forbidden_active_collection"],
    )
