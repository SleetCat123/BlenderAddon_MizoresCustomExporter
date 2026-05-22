import os
import sys

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import change_base_export_test_lib as base_t


def log(message):
    print(f"[batch-mode-original-compare] {message}")


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


def _clear_fbx_files(directory):
    if not os.path.isdir(directory):
        return
    for name in os.listdir(directory):
        if name.lower().endswith(".fbx"):
            os.remove(os.path.join(directory, name))


def _build_output_dir(label):
    path = os.path.join(base_t.OUTPUT_DIR, label)
    os.makedirs(path, exist_ok=True)
    _clear_fbx_files(path)
    return path


def _collect_mesh_manifest(output_dir, normalize_name=None):
    manifest = {}
    for name in sorted(os.listdir(output_dir)):
        if not name.lower().endswith(".fbx"):
            continue
        filepath = os.path.join(output_dir, name)
        imported_meshes = base_t.import_fbx(filepath)
        key = normalize_name(name) if normalize_name is not None else name
        manifest[key] = {
            mesh_name: len(mesh_obj.data.vertices)
            for mesh_name, mesh_obj in sorted(imported_meshes.items())
        }
    if not manifest:
        raise AssertionError(f"No FBX files were exported: {output_dir}")
    return manifest


def _assert_manifests_equal(mode_name, custom_manifest, original_manifest):
    custom_files = sorted(custom_manifest.keys())
    original_files = sorted(original_manifest.keys())
    if custom_files != original_files:
        raise AssertionError(
            f"{mode_name}: exported filenames mismatch. "
            f"custom={custom_files} original={original_files}"
        )

    for filename in custom_files:
        custom_meshes = custom_manifest[filename]
        original_meshes = original_manifest[filename]
        if custom_meshes != original_meshes:
            raise AssertionError(
                f"{mode_name}:{filename} mesh manifest mismatch. "
                f"custom={custom_meshes} original={original_meshes}"
            )


def _build_original_export_kwargs(filepath, batch_mode, *, use_selection, use_active_collection):
    return {
        "filepath": filepath,
        "check_existing": False,
        "use_selection": use_selection,
        "use_visible": False,
        "use_active_collection": use_active_collection,
        "global_scale": 1.0,
        "apply_unit_scale": True,
        "apply_scale_options": 'FBX_SCALE_UNITS',
        "use_space_transform": True,
        "bake_space_transform": True,
        "object_types": {'MESH'},
        "use_mesh_modifiers": False,
        "use_mesh_modifiers_render": True,
        "mesh_smooth_type": 'OFF',
        "colors_type": 'SRGB',
        "prioritize_active_color": False,
        "use_subsurf": False,
        "use_mesh_edges": False,
        "use_tspace": False,
        "use_triangles": False,
        "use_custom_props": False,
        "add_leaf_bones": False,
        "primary_bone_axis": 'Y',
        "secondary_bone_axis": 'X',
        "use_armature_deform_only": False,
        "armature_nodetype": 'NULL',
        "bake_anim": False,
        "bake_anim_use_all_bones": True,
        "bake_anim_use_nla_strips": True,
        "bake_anim_use_all_actions": True,
        "bake_anim_force_startend_keying": True,
        "bake_anim_step": 1.0,
        "bake_anim_simplify_factor": 1.0,
        "path_mode": 'AUTO',
        "embed_textures": False,
        "batch_mode": batch_mode,
        "use_batch_own_dir": False,
        "use_metadata": True,
        "axis_forward": '-Z',
        "axis_up": 'Y',
    }


def _normalize_original_export_name(seed_filepath, exported_name):
    seed_name = os.path.basename(seed_filepath)
    prefix = f"{seed_name}_"
    if exported_name.startswith(prefix):
        return exported_name[len(prefix):]
    return exported_name


def build_batch_mode_original_compare_scene():
    base_t.ensure_output_dir()
    base_t.reset_scene()
    bpy.context.scene.name = "OriginalParityScene"

    collection_a = base_t.ensure_scene_collection("Parity_A")
    collection_b = base_t.ensure_scene_collection("Parity_B")
    collection_a_sub = bpy.data.collections.new("Parity_A_Sub")
    collection_a.children.link(collection_a_sub)
    collection_b_sub = bpy.data.collections.new("Parity_B_Sub")
    collection_b.children.link(collection_b_sub)

    root_a = _create_cube("ParityRootA", (0.0, 0.0, 0.0))
    child_a = _create_plane("ParityChildA", (0.0, 0.0, 1.0), size=0.8)
    solo_a = _create_cone("ParitySoloA", (2.0, 0.0, 0.0), vertices=9, radius1=0.4, depth=0.9)
    sub_a = _create_cylinder("ParitySubA", (4.0, 0.0, 0.0), vertices=8, radius=0.35, depth=0.8)
    root_b = _create_ico_sphere("ParityRootB", (6.0, 0.0, 0.0), subdivisions=1, radius=0.45)
    sub_b = _create_plane("ParitySubB", (7.5, 0.0, 0.0), size=0.65)

    base_t.set_parent_keep_transform(child_a, root_a)

    base_t.move_object_to_single_collection(root_a, collection_a)
    base_t.move_object_to_single_collection(child_a, collection_a)
    base_t.move_object_to_single_collection(solo_a, collection_a)
    base_t.move_object_to_single_collection(sub_a, collection_a_sub)
    base_t.move_object_to_single_collection(root_b, collection_b)
    base_t.move_object_to_single_collection(sub_b, collection_b_sub)

    _set_active_collection(collection_a)
    base_t.select_objects([root_a, root_b], active=root_a)

    return {
        "active_collection": collection_a,
    }


def _export_with_custom(batch_mode, scene_info, *, include_children_collections=False):
    modules = base_t.load_required_modules()
    output_dir = _build_output_dir(f"batch_mode_custom_{batch_mode.lower()}")
    filepath = os.path.join(output_dir, "parity_seed.fbx")
    if batch_mode == 'SCENE':
        filepath = os.path.join(output_dir, "OriginalParityScene.fbx")

    operator_overrides = {
        "batch_mode": batch_mode,
        "batch_filename_format": "{batch}",
        "use_batch_own_dir": False,
        "save_prefs": False,
        "save_path": False,
        "object_types": {'MESH'},
        "use_selection": batch_mode == 'OFF',
        "use_active_collection": batch_mode == 'ACTIVE_SCENE_COLLECTION',
        "use_batch_collection_children_collections": include_children_collections,
    }
    if batch_mode == 'ACTIVE_SCENE_COLLECTION':
        operator_overrides["use_active_collection_children_objects"] = True
        operator_overrides["use_active_collection_children_collections"] = True
        _set_active_collection(scene_info["active_collection"])

    base_t.export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides=operator_overrides,
    )
    return _collect_mesh_manifest(output_dir)


def _export_with_original(batch_mode, scene_info):
    base_t.ensure_required_addons()
    output_dir = _build_output_dir(f"batch_mode_original_{batch_mode.lower()}")
    filepath = os.path.join(output_dir, "parity_seed.fbx")
    if batch_mode == 'SCENE':
        filepath = os.path.join(output_dir, "OriginalParityScene.fbx")

    if batch_mode == 'ACTIVE_SCENE_COLLECTION':
        _set_active_collection(scene_info["active_collection"])

    kwargs = _build_original_export_kwargs(
        filepath,
        batch_mode,
        use_selection=(batch_mode == 'OFF'),
        use_active_collection=(batch_mode == 'ACTIVE_SCENE_COLLECTION'),
    )
    result = bpy.ops.export_scene.fbx(**kwargs)
    if 'FINISHED' not in result:
        raise AssertionError(f"Original FBX exporter failed. batch_mode={batch_mode} result={result}")

    return _collect_mesh_manifest(
        output_dir,
        normalize_name=lambda name: _normalize_original_export_name(filepath, name),
    )


def validate_batch_mode_matches_original_fbx(batch_mode):
    if batch_mode not in {'OFF', 'SCENE', 'COLLECTION', 'SCENE_COLLECTION', 'ACTIVE_SCENE_COLLECTION'}:
        raise ValueError(f"Unsupported batch mode for original FBX comparison: {batch_mode}")

    scene_info = build_batch_mode_original_compare_scene()
    custom_manifest = _export_with_custom(
        batch_mode,
        scene_info,
        include_children_collections=(batch_mode in {'SCENE_COLLECTION', 'ACTIVE_SCENE_COLLECTION'}),
    )

    scene_info = build_batch_mode_original_compare_scene()
    original_manifest = _export_with_original(batch_mode, scene_info)

    _assert_manifests_equal(batch_mode, custom_manifest, original_manifest)
    log(f"PASS: {batch_mode} custom exporter matches original FBX exporter")
