import math
import os
import importlib
import json

import bpy
from mathutils import Matrix

import change_base_export_test_lib as base_t


OUTPUT_DIR = os.path.join(base_t.SCRIPT_DIR, "output_scale_value_mode")
FBX_MODULE = "io_scene_fbx"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def remove_file_if_exists(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)


def assert_close(actual, expected, label, tolerance=1e-5):
    if math.fabs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(f"{label}: actual={actual} expected={expected}")


def assert_vector_close(actual, expected, label, tolerance=1e-5):
    if len(actual) != len(expected):
        raise AssertionError(f"{label}: length mismatch actual={len(actual)} expected={len(expected)}")
    for index, (actual_value, expected_value) in enumerate(zip(actual, expected)):
        assert_close(actual_value, expected_value, f"{label}[{index}]", tolerance=tolerance)


def _import_fbx(filepath):
    base_t.reset_scene()
    base_t.ensure_addon_enabled(FBX_MODULE)
    result = bpy.ops.import_scene.fbx(filepath=filepath)
    if 'FINISHED' not in result:
        raise AssertionError(f"FBX import failed: {result}")


def _find_mesh(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise AssertionError(f"Imported mesh not found: {name}")
    if obj.type != 'MESH':
        raise AssertionError(f"Imported object is not a mesh: {name} type={obj.type}")
    return obj


def _find_armature(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise AssertionError(f"Imported armature not found: {name}")
    if obj.type != 'ARMATURE':
        raise AssertionError(f"Imported object is not an armature: {name} type={obj.type}")
    return obj


def _build_static_scale_scene():
    base_t.reset_scene()
    ensure_output_dir()

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.0, 0.0, 0.0))
    mesh_a = base_t.get_active_object()
    mesh_a.name = "ScaleMeshA"
    mesh_a.data.name = "ScaleMeshA"
    mesh_a.scale = (1.5, 1.5, 1.5)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(3.0, 0.0, 0.0))
    mesh_b = base_t.get_active_object()
    mesh_b.name = "ScaleMeshB"
    mesh_b.data.name = "ScaleMeshB"
    mesh_b.scale = (0.75, 0.75, 0.75)

    base_t.select_objects([mesh_a, mesh_b], active=mesh_a)
    return mesh_a, mesh_b


def validate_static_scale_value_mode_export(scale_pivot, expected_locations):
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    mesh_a, mesh_b = _build_static_scale_scene()
    export_path = os.path.join(OUTPUT_DIR, f"scale_value_mode_static_{scale_pivot.lower()}.fbx")
    reference_path = os.path.join(OUTPUT_DIR, f"scale_value_mode_static_{scale_pivot.lower()}_reference.fbx")
    remove_file_if_exists(export_path)
    remove_file_if_exists(reference_path)

    original_scale_a = tuple(mesh_a.scale)
    original_scale_b = tuple(mesh_b.scale)

    if scale_pivot == 'WORLD_ORIGIN':
        _export_scale_all_reference_with_addon(
            func_execute_main,
            reference_path,
            {
                "object_types": {'MESH'},
            },
        )

    operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=export_path,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'OFF',
            "object_types": {'MESH'},
            "save_prefs": False,
            "save_path": False,
            "global_scale": 2.0,
            "scale_value_mode": 'KEEP_VALUE',
            "scale_pivot": scale_pivot,
        },
    )

    if result.errors:
        raise AssertionError(f"Export reported errors: {result.errors}")
    if operator.report_log:
        error_reports = [entry for entry in operator.report_log if 'ERROR' in entry[0]]
        if error_reports:
            raise AssertionError(f"Operator reported export errors: {error_reports}")

    restored_a = bpy.data.objects.get("ScaleMeshA")
    restored_b = bpy.data.objects.get("ScaleMeshB")
    if restored_a is None or restored_b is None:
        raise AssertionError("Original scale test meshes were not restored after export")
    assert_vector_close(tuple(restored_a.scale), original_scale_a, "restored ScaleMeshA scale")
    assert_vector_close(tuple(restored_b.scale), original_scale_b, "restored ScaleMeshB scale")

    if scale_pivot == 'WORLD_ORIGIN':
        reference_summary = _build_fbx_model_transform_summary(
            reference_path,
            {"ScaleMeshA", "ScaleMeshB"},
        )
        keep_summary = _build_fbx_model_transform_summary(
            export_path,
            {"ScaleMeshA", "ScaleMeshB"},
        )
        assert_close(
            keep_summary["unit_scale_factor"],
            reference_summary["unit_scale_factor"],
            "static world-origin unit_scale_factor",
        )
        for model_name in ("ScaleMeshA", "ScaleMeshB"):
            assert_vector_close(
                keep_summary["models"][model_name]["translation"],
                reference_summary["models"][model_name]["translation"],
                f"static world-origin translation {model_name}",
            )
            assert_vector_close(
                keep_summary["models"][model_name]["scaling"],
                reference_summary["models"][model_name]["scaling"],
                f"static world-origin scaling {model_name}",
            )
        return

    _import_fbx(export_path)
    imported_a = _find_mesh("ScaleMeshA")
    imported_b = _find_mesh("ScaleMeshB")

    assert_vector_close(tuple(imported_a.location), expected_locations["ScaleMeshA"], "ScaleMeshA location")
    assert_vector_close(tuple(imported_b.location), expected_locations["ScaleMeshB"], "ScaleMeshB location")
    assert_vector_close(tuple(imported_a.scale), original_scale_a, "ScaleMeshA imported scale")
    assert_vector_close(tuple(imported_b.scale), original_scale_b, "ScaleMeshB imported scale")
    assert_vector_close(tuple(imported_a.dimensions), (3.0, 3.0, 3.0), "ScaleMeshA dimensions")
    assert_vector_close(tuple(imported_b.dimensions), (1.5, 1.5, 1.5), "ScaleMeshB dimensions")


def _create_location_action(name, frame_values):
    action = bpy.data.actions.new(name=name)
    fcurve = action.fcurves.new("location", index=0)
    for frame, value in frame_values:
        fcurve.keyframe_points.insert(frame, value)
    return action


def _get_location_key_values(action_name):
    action = _find_action_by_suffix(action_name)
    for fcurve in action.fcurves:
        if fcurve.data_path == "location" and fcurve.array_index == 0:
            return [float(point.co[1]) for point in fcurve.keyframe_points]
    raise AssertionError(f"Location X fcurve not found on action: {action_name}")


def _find_action_by_suffix(action_name):
    action = bpy.data.actions.get(action_name)
    if action is not None:
        return action

    candidates = [candidate for candidate in bpy.data.actions if candidate.name.endswith(f"|{action_name}")]
    if len(candidates) == 1:
        return candidates[0]
    raise AssertionError(
        f"Action not found or ambiguous for '{action_name}'. "
        f"available={[candidate.name for candidate in bpy.data.actions]}"
    )


def _find_pose_location_fcurve(action_name, bone_name, array_index):
    action = _find_action_by_suffix(action_name)
    target_path = f'pose.bones["{bone_name}"].location'
    for fcurve in action.fcurves:
        if fcurve.data_path == target_path and fcurve.array_index == array_index:
            return fcurve
    raise AssertionError(f"Pose location fcurve not found: action={action_name} bone={bone_name} index={array_index}")


def _ensure_fbx_json(filepath):
    fbx2json = importlib.import_module("io_scene_fbx.fbx2json")
    fbx2json = importlib.reload(fbx2json)
    json_path = os.path.splitext(filepath)[0] + ".json"
    remove_file_if_exists(json_path)
    fbx2json.fbx2json(filepath)
    return json_path


def _load_fbx_json(filepath):
    json_path = _ensure_fbx_json(filepath)
    with open(json_path, "r", encoding="ascii") as handle:
        return json.load(handle)


def _get_fbx_child(elem, child_id):
    for child in elem[3]:
        if child[0] == child_id:
            return child
    return None


def _iter_fbx_elements(doc, elem_id):
    for elem in doc:
        if elem[0] == elem_id:
            yield elem
        yield from _iter_fbx_elements(elem[3], elem_id)


def _get_fbx_prop_map(elem):
    props70 = _get_fbx_child(elem, "Properties70")
    result = {}
    if props70 is None:
        return result
    for prop in props70[3]:
        if prop[0] != "P":
            continue
        values = prop[1]
        result[values[0]] = values[4:]
    return result


def _export_scale_all_reference_with_addon(func_execute_main, filepath, operator_overrides):
    operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'OFF',
            "save_prefs": False,
            "save_path": False,
            "global_scale": 2.0,
            "scale_value_mode": 'NORMAL',
            "apply_scale_options": 'FBX_SCALE_ALL',
            **operator_overrides,
        },
    )
    if result.errors:
        raise AssertionError(f"Reference export reported errors: {result.errors}")
    if operator.report_log:
        error_reports = [entry for entry in operator.report_log if 'ERROR' in entry[0]]
        if error_reports:
            raise AssertionError(f"Reference export reported operator errors: {error_reports}")


def _build_fbx_model_transform_summary(filepath, model_names):
    doc = _load_fbx_json(filepath)
    global_settings = next(_iter_fbx_elements(doc, "GlobalSettings"))
    unit_scale_factor = float(_get_fbx_prop_map(global_settings)["UnitScaleFactor"][0])
    models = {}
    for elem in _iter_fbx_elements(doc, "Model"):
        name = elem[1][1].split("::", 1)[0]
        if name not in model_names:
            continue
        prop_map = _get_fbx_prop_map(elem)
        models[name] = {
            "translation": tuple(prop_map.get("Lcl Translation", (0.0, 0.0, 0.0))),
            "scaling": tuple(prop_map.get("Lcl Scaling", (1.0, 1.0, 1.0))),
        }
    return {
        "unit_scale_factor": unit_scale_factor,
        "models": models,
    }


def _build_fbx_armature_summary(filepath):
    doc = _load_fbx_json(filepath)

    global_settings = next(_iter_fbx_elements(doc, "GlobalSettings"))
    unit_scale_factor = _get_fbx_prop_map(global_settings)["UnitScaleFactor"][0]

    model_scalings = {}
    for elem in _iter_fbx_elements(doc, "Model"):
        name = elem[1][1].split("::", 1)[0]
        prop_map = _get_fbx_prop_map(elem)
        if "Lcl Scaling" in prop_map:
            model_scalings[name] = tuple(prop_map["Lcl Scaling"])

    clusters = {}
    for elem in _iter_fbx_elements(doc, "Deformer"):
        if elem[1][2] != "Cluster":
            continue
        name = elem[1][1].split("::", 1)[0]
        child_map = {child[0]: child[1][0] for child in elem[3] if child[1]}
        clusters[name] = {
            "Transform": tuple(child_map["Transform"]),
            "TransformLink": tuple(child_map["TransformLink"]),
            "TransformAssociateModel": tuple(child_map["TransformAssociateModel"]),
        }

    return {
        "unit_scale_factor": float(unit_scale_factor),
        "model_scalings": model_scalings,
        "clusters": clusters,
    }


def _build_animation_scene():
    base_t.reset_scene()
    ensure_output_dir()

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.0, 0.0, 0.0))
    obj = base_t.get_active_object()
    obj.name = "AnimCube"
    obj.data.name = "AnimCube"
    obj.scale = (1.5, 1.5, 1.5)
    obj.animation_data_create()
    obj.animation_data.action = _create_location_action("MoveA", [(1.0, 1.0), (10.0, 2.0)])
    _create_location_action("MoveB", [(1.0, 3.0), (10.0, 5.0)])

    base_t.select_objects([obj], active=obj)
    return obj


def validate_scale_value_mode_animation_all_actions_export():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    obj = _build_animation_scene()
    export_path = os.path.join(OUTPUT_DIR, "scale_value_mode_animation_all_actions.fbx")
    reference_path = os.path.join(OUTPUT_DIR, "scale_value_mode_animation_all_actions_reference.fbx")
    remove_file_if_exists(export_path)
    remove_file_if_exists(reference_path)

    original_scale = tuple(obj.scale)
    original_move_a = _get_location_key_values("MoveA")
    original_move_b = _get_location_key_values("MoveB")

    _export_scale_all_reference_with_addon(
        func_execute_main,
        reference_path,
        {
            "object_types": {'MESH'},
            "bake_anim": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": True,
        },
    )

    operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=export_path,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'OFF',
            "object_types": {'MESH'},
            "save_prefs": False,
            "save_path": False,
            "global_scale": 2.0,
            "scale_value_mode": 'KEEP_VALUE',
            "scale_pivot": 'WORLD_ORIGIN',
            "bake_anim": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": True,
        },
    )

    if result.errors:
        raise AssertionError(f"Animated export reported errors: {result.errors}")
    if operator.report_log:
        error_reports = [entry for entry in operator.report_log if 'ERROR' in entry[0]]
        if error_reports:
            raise AssertionError(f"Animated export reported operator errors: {error_reports}")

    restored_obj = bpy.data.objects.get("AnimCube")
    if restored_obj is None:
        raise AssertionError("Original animated object was not restored after export")
    assert_vector_close(tuple(restored_obj.scale), original_scale, "AnimCube restored scale")
    assert_vector_close(_get_location_key_values("MoveA"), original_move_a, "MoveA restored keyframes")
    assert_vector_close(_get_location_key_values("MoveB"), original_move_b, "MoveB restored keyframes")

    reference_snapshot = _collect_imported_animation_snapshot(reference_path)
    keep_snapshot = _collect_imported_animation_snapshot(export_path)

    assert_vector_close(keep_snapshot["scale"], reference_snapshot["scale"], "AnimCube imported scale")
    assert_vector_close(keep_snapshot["location"], reference_snapshot["location"], "AnimCube imported location")
    assert_vector_close(keep_snapshot["dimensions"], reference_snapshot["dimensions"], "AnimCube imported dimensions")
    if keep_snapshot["action_names"] != reference_snapshot["action_names"]:
        raise AssertionError(
            f"Imported action names differ. keep={keep_snapshot['action_names']} "
            f"reference={reference_snapshot['action_names']}"
        )
    if any(name.endswith(".001") for name in keep_snapshot["action_names"]):
        raise AssertionError(f"Imported action names still contain duplicate suffixes: {keep_snapshot['action_names']}")
    assert_vector_close(keep_snapshot["move_a"], reference_snapshot["move_a"], "MoveA imported keyframes")
    assert_vector_close(keep_snapshot["move_b"], reference_snapshot["move_b"], "MoveB imported keyframes")


def _collect_imported_animation_snapshot(filepath):
    _import_fbx(filepath)
    imported_obj = _find_mesh("AnimCube")
    return {
        "scale": tuple(imported_obj.scale),
        "location": tuple(imported_obj.location),
        "dimensions": tuple(imported_obj.dimensions),
        "action_names": sorted(action.name for action in bpy.data.actions),
        "move_a": _get_location_key_values("MoveA"),
        "move_b": _get_location_key_values("MoveB"),
    }


def _build_armature_scale_scene():
    base_t.reset_scene()
    ensure_output_dir()

    armature = base_t.create_armature_object("ScaleRig", location=(1.0, 0.0, 0.0))
    armature.scale = (1.5, 1.5, 1.5)

    base_t.select_objects([armature], active=armature)
    bpy.ops.object.mode_set(mode='EDIT')
    child_bone = armature.data.edit_bones.new("Child")
    child_bone.head = (0.0, 0.0, 1.0)
    child_bone.tail = (0.0, 0.0, 2.0)
    child_bone.parent = armature.data.edit_bones[0]
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.0, 0.0, 1.0))
    mesh = base_t.get_active_object()
    mesh.name = "ScaleRigMesh"
    mesh.data.name = "ScaleRigMesh"
    mesh.scale = (1.5, 1.5, 1.5)
    base_t.add_armature_modifier(mesh, armature)

    for bone_name in ("Bone", "Child"):
        group = mesh.vertex_groups.new(name=bone_name)
        group.add([vertex.index for vertex in mesh.data.vertices], 1.0, 'REPLACE')

    armature.animation_data_create()
    action = bpy.data.actions.new(name="RigPose")
    armature.animation_data.action = action
    fcurve = action.fcurves.new('pose.bones["Child"].location', index=0)
    fcurve.keyframe_points.insert(1.0, 0.25)
    fcurve.keyframe_points.insert(10.0, 0.75)

    base_t.select_objects([armature, mesh], active=armature)
    return armature, mesh


def _build_connected_armature_scene():
    base_t.reset_scene()
    ensure_output_dir()

    armature = base_t.create_armature_object("ConnectedRig", location=(1.0, 0.0, 0.0))
    armature.scale = (1.5, 1.5, 1.5)

    base_t.select_objects([armature], active=armature)
    bpy.ops.object.mode_set(mode='EDIT')
    root_bone = armature.data.edit_bones[0]
    root_bone.name = "Root"
    root_bone.head = (0.0, 0.0, 0.0)
    root_bone.tail = (0.0, 0.0, 1.0)

    child_bone = armature.data.edit_bones.new("ConnectedChild")
    child_bone.head = (0.0, 0.0, 1.0)
    child_bone.tail = (0.0, 0.0, 2.0)
    child_bone.parent = root_bone
    child_bone.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')

    armature.animation_data_create()
    action = bpy.data.actions.new(name="ConnectedRigPose")
    armature.animation_data.action = action
    root_pose = armature.pose.bones["Root"]
    root_pose.rotation_mode = 'XYZ'
    fcurve = action.fcurves.new('pose.bones["Root"].rotation_euler', index=1)
    fcurve.keyframe_points.insert(1.0, 0.0)
    fcurve.keyframe_points.insert(10.0, 0.5)

    base_t.select_objects([armature], active=armature)
    return armature


def _collect_armature_snapshot(filepath):
    _import_fbx(filepath)

    armature = _find_armature("ScaleRig")
    mesh = _find_mesh("ScaleRigMesh")
    snapshots = {}

    for frame in (1, 10):
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_mesh_obj = mesh.evaluated_get(depsgraph)
        eval_mesh = eval_mesh_obj.to_mesh()
        try:
            mesh_vertices = [
                tuple(eval_mesh_obj.matrix_world @ vertex.co)
                for vertex in eval_mesh.vertices[:4]
            ]
        finally:
            eval_mesh_obj.to_mesh_clear()

        pose_bone = armature.pose.bones["Child"]
        pose_world = armature.matrix_world @ pose_bone.matrix
        snapshots[str(frame)] = {
            "mesh_world_location": tuple(mesh.matrix_world.translation),
            "mesh_vertices": mesh_vertices,
            "bone_world_location": tuple(pose_world.translation),
        }

    return snapshots


def _collect_source_armature_snapshot(armature, mesh):
    snapshots = {}

    for frame in (1, 10):
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_armature = armature.evaluated_get(depsgraph)
        eval_mesh_obj = mesh.evaluated_get(depsgraph)
        eval_mesh = eval_mesh_obj.to_mesh()
        try:
            mesh_vertices = [
                tuple(eval_mesh_obj.matrix_world @ vertex.co)
                for vertex in eval_mesh.vertices[:4]
            ]
        finally:
            eval_mesh_obj.to_mesh_clear()

        pose_bone = eval_armature.pose.bones["Child"]
        pose_world = eval_armature.matrix_world @ pose_bone.matrix
        snapshots[str(frame)] = {
            "mesh_world_location": tuple(eval_mesh_obj.matrix_world.translation),
            "mesh_vertices": mesh_vertices,
            "bone_world_location": tuple(pose_world.translation),
        }

    return snapshots


def _collect_connected_armature_snapshot(filepath):
    _import_fbx(filepath)

    armature = _find_armature("ConnectedRig")
    snapshots = {}
    for frame in (1, 10):
        bpy.context.scene.frame_set(frame)
        root_bone = armature.pose.bones["Root"]
        child_bone = armature.pose.bones["ConnectedChild"]
        snapshots[str(frame)] = {
            "object_location": tuple(armature.location),
            "object_scale": tuple(armature.scale),
            "root_head": tuple(armature.matrix_world @ root_bone.head),
            "root_tail": tuple(armature.matrix_world @ root_bone.tail),
            "child_head": tuple(armature.matrix_world @ child_bone.head),
            "child_tail": tuple(armature.matrix_world @ child_bone.tail),
        }
    return snapshots


def _collect_source_connected_armature_snapshot(armature):
    snapshots = {}
    for frame in (1, 10):
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_armature = armature.evaluated_get(depsgraph)
        root_bone = eval_armature.pose.bones["Root"]
        child_bone = eval_armature.pose.bones["ConnectedChild"]
        snapshots[str(frame)] = {
            "object_location": tuple(eval_armature.matrix_world.translation),
            "object_scale": tuple(eval_armature.scale),
            "root_head": tuple(eval_armature.matrix_world @ root_bone.head),
            "root_tail": tuple(eval_armature.matrix_world @ root_bone.tail),
            "child_head": tuple(eval_armature.matrix_world @ child_bone.head),
            "child_tail": tuple(eval_armature.matrix_world @ child_bone.tail),
        }
    return snapshots


def _build_bone_parent_scene():
    base_t.reset_scene()
    ensure_output_dir()

    armature = base_t.create_armature_object("ScaleRig", location=(1.0, 0.0, 0.0))
    armature.scale = (1.5, 1.5, 1.5)

    base_t.select_objects([armature], active=armature)
    bpy.ops.object.mode_set(mode='EDIT')
    child_bone = armature.data.edit_bones.new("Child")
    child_bone.head = (0.0, 0.0, 1.0)
    child_bone.tail = (0.0, 0.0, 2.0)
    child_bone.parent = armature.data.edit_bones[0]
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(1.0, 0.0, 2.0))
    attached = base_t.get_active_object()
    attached.name = "BoneAttached"
    attached.data.name = "BoneAttached"
    attached.scale = (1.0, 1.0, 1.0)

    matrix_world = attached.matrix_world.copy()
    attached.parent = armature
    attached.parent_type = 'BONE'
    attached.parent_bone = "Child"
    attached.matrix_parent_inverse = Matrix.Identity(4)
    attached.matrix_world = matrix_world

    armature.animation_data_create()
    action = bpy.data.actions.new(name="RigPose")
    armature.animation_data.action = action
    fcurve = action.fcurves.new('pose.bones["Child"].location', index=0)
    fcurve.keyframe_points.insert(1.0, 0.25)
    fcurve.keyframe_points.insert(10.0, 0.75)

    base_t.select_objects([armature, attached], active=armature)
    return armature, attached


def _collect_bone_parent_snapshot(filepath):
    _import_fbx(filepath)

    armature = _find_armature("ScaleRig")
    attached = _find_mesh("BoneAttached")
    snapshots = {}
    for frame in (1, 10):
        bpy.context.scene.frame_set(frame)
        pose_bone = armature.pose.bones["Child"]
        bone_world = armature.matrix_world @ pose_bone.matrix
        snapshots[str(frame)] = {
            "bone_world_location": tuple(bone_world.translation),
            "attached_world_location": tuple(attached.matrix_world.translation),
        }
    return snapshots


def _collect_source_bone_parent_snapshot(armature, attached):
    snapshots = {}
    for frame in (1, 10):
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_armature = armature.evaluated_get(depsgraph)
        eval_attached = attached.evaluated_get(depsgraph)
        pose_bone = eval_armature.pose.bones["Child"]
        bone_world = eval_armature.matrix_world @ pose_bone.matrix
        snapshots[str(frame)] = {
            "bone_world_location": tuple(bone_world.translation),
            "attached_world_location": tuple(eval_attached.matrix_world.translation),
        }
    return snapshots


def _build_scale_value_mode_export_set(roots):
    props = bpy.context.scene.mizore_export_sets
    export_set = props.export_sets.add()
    export_set.filename = "ScaleValueModeSet"
    export_set.enabled = True
    export_set.join_meshes_to_one = False
    export_set.merge_armatures = False

    for root, include_children in roots:
        item = export_set.items.add()
        item.enabled = True
        item.root_object = root
        item.include_children = include_children

    return export_set


def _export_armature_case(
    func_execute_main,
    filepath,
    scale_value_mode,
    build_scene,
    batch_mode='OFF',
):
    roots = build_scene()
    if batch_mode == 'EXPORT_SETS':
        _build_scale_value_mode_export_set(
            roots=[
                (roots[0], True),
                (roots[1], False),
            ]
        )

    _operator, export_result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=filepath,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": batch_mode,
            "object_types": {'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
            "global_scale": 2.0,
            "scale_value_mode": scale_value_mode,
            "scale_pivot": 'WORLD_ORIGIN',
            "bake_anim": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": True,
            "add_leaf_bones": False,
        },
    )
    if export_result.errors:
        raise AssertionError(f"{scale_value_mode} armature export reported errors: {export_result.errors}")


def validate_scale_value_mode_armature_export_matches_normal():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    normal_path = os.path.join(OUTPUT_DIR, "scale_value_mode_armature_normal.fbx")
    keep_path = os.path.join(OUTPUT_DIR, "scale_value_mode_armature_keep.fbx")
    remove_file_if_exists(normal_path)
    remove_file_if_exists(keep_path)

    _export_armature_case(func_execute_main, normal_path, 'NORMAL', _build_armature_scale_scene)
    _export_armature_case(func_execute_main, keep_path, 'KEEP_VALUE', _build_armature_scale_scene)

    normal_snapshot = _collect_armature_snapshot(normal_path)
    keep_snapshot = _collect_armature_snapshot(keep_path)

    for frame in ("1", "10"):
        assert_vector_close(
            keep_snapshot[frame]["mesh_world_location"],
            normal_snapshot[frame]["mesh_world_location"],
            f"mesh world location frame {frame}",
        )
        for index, (keep_vertex, normal_vertex) in enumerate(
            zip(keep_snapshot[frame]["mesh_vertices"], normal_snapshot[frame]["mesh_vertices"])
        ):
            assert_vector_close(
                keep_vertex,
                normal_vertex,
                f"mesh vertex {index} frame {frame}",
            )
        assert_vector_close(
            keep_snapshot[frame]["bone_world_location"],
            normal_snapshot[frame]["bone_world_location"],
            f"bone world location frame {frame}",
        )


def validate_scale_value_mode_armature_export_matches_scaled_source():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    normal_path = os.path.join(OUTPUT_DIR, "scale_value_mode_armature_normal.fbx")
    keep_path = os.path.join(OUTPUT_DIR, "scale_value_mode_armature_keep.fbx")
    remove_file_if_exists(normal_path)
    remove_file_if_exists(keep_path)

    source_armature, source_mesh = _build_armature_scale_scene()
    source_snapshot = _collect_source_armature_snapshot(source_armature, source_mesh)
    expected_snapshot = {}
    for frame, snapshot in source_snapshot.items():
        expected_snapshot[frame] = {
            "mesh_world_location": tuple(value * 2.0 for value in snapshot["mesh_world_location"]),
            "mesh_vertices": [
                tuple(value * 2.0 for value in vertex)
                for vertex in snapshot["mesh_vertices"]
            ],
            "bone_world_location": tuple(value * 2.0 for value in snapshot["bone_world_location"]),
        }

    _export_armature_case(func_execute_main, normal_path, 'NORMAL', _build_armature_scale_scene)
    _export_armature_case(func_execute_main, keep_path, 'KEEP_VALUE', _build_armature_scale_scene)

    for filepath, label in ((normal_path, "NORMAL"), (keep_path, "KEEP_VALUE")):
        actual_snapshot = _collect_armature_snapshot(filepath)
        for frame in ("1", "10"):
            assert_vector_close(
                actual_snapshot[frame]["mesh_world_location"],
                expected_snapshot[frame]["mesh_world_location"],
                f"{label} source mesh world location frame {frame}",
            )
            for index, (actual_vertex, expected_vertex) in enumerate(
                zip(actual_snapshot[frame]["mesh_vertices"], expected_snapshot[frame]["mesh_vertices"])
            ):
                assert_vector_close(
                    actual_vertex,
                    expected_vertex,
                    f"{label} source mesh vertex {index} frame {frame}",
                )
            assert_vector_close(
                actual_snapshot[frame]["bone_world_location"],
                expected_snapshot[frame]["bone_world_location"],
                f"{label} source bone world location frame {frame}",
            )


def validate_scale_value_mode_bone_parent_export_matches_normal():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    normal_path = os.path.join(OUTPUT_DIR, "scale_value_mode_bone_parent_normal.fbx")
    keep_path = os.path.join(OUTPUT_DIR, "scale_value_mode_bone_parent_keep.fbx")
    remove_file_if_exists(normal_path)
    remove_file_if_exists(keep_path)

    _export_armature_case(func_execute_main, normal_path, 'NORMAL', _build_bone_parent_scene)
    _export_armature_case(func_execute_main, keep_path, 'KEEP_VALUE', _build_bone_parent_scene)

    normal_snapshot = _collect_bone_parent_snapshot(normal_path)
    keep_snapshot = _collect_bone_parent_snapshot(keep_path)

    for frame in ("1", "10"):
        assert_vector_close(
            keep_snapshot[frame]["bone_world_location"],
            normal_snapshot[frame]["bone_world_location"],
            f"bone parent bone world frame {frame}",
        )
        assert_vector_close(
            keep_snapshot[frame]["attached_world_location"],
            normal_snapshot[frame]["attached_world_location"],
            f"bone parent attached world frame {frame}",
        )


def validate_scale_value_mode_bone_parent_export_matches_scaled_source():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    normal_path = os.path.join(OUTPUT_DIR, "scale_value_mode_bone_parent_normal.fbx")
    keep_path = os.path.join(OUTPUT_DIR, "scale_value_mode_bone_parent_keep.fbx")
    remove_file_if_exists(normal_path)
    remove_file_if_exists(keep_path)

    source_armature, source_attached = _build_bone_parent_scene()
    source_snapshot = _collect_source_bone_parent_snapshot(source_armature, source_attached)
    expected_snapshot = {}
    for frame, snapshot in source_snapshot.items():
        expected_snapshot[frame] = {
            "bone_world_location": tuple(value * 2.0 for value in snapshot["bone_world_location"]),
            "attached_world_location": tuple(value * 2.0 for value in snapshot["attached_world_location"]),
        }

    _export_armature_case(func_execute_main, normal_path, 'NORMAL', _build_bone_parent_scene)
    _export_armature_case(func_execute_main, keep_path, 'KEEP_VALUE', _build_bone_parent_scene)

    for filepath, label in ((normal_path, "NORMAL"), (keep_path, "KEEP_VALUE")):
        actual_snapshot = _collect_bone_parent_snapshot(filepath)
        for frame in ("1", "10"):
            assert_vector_close(
                actual_snapshot[frame]["bone_world_location"],
                expected_snapshot[frame]["bone_world_location"],
                f"{label} source bone parent bone world frame {frame}",
            )
            assert_vector_close(
                actual_snapshot[frame]["attached_world_location"],
                expected_snapshot[frame]["attached_world_location"],
                f"{label} source bone parent attached world frame {frame}",
            )


def validate_connected_bone_each_object_origin_matches_scaled_source():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    keep_path = os.path.join(OUTPUT_DIR, "scale_value_mode_connected_each_object_keep.fbx")
    remove_file_if_exists(keep_path)

    source_armature = _build_connected_armature_scene()
    source_snapshot = _collect_source_connected_armature_snapshot(source_armature)
    armature_origin = source_snapshot["1"]["object_location"]
    expected_snapshot = {}
    for frame, snapshot in source_snapshot.items():
        expected_snapshot[frame] = {
            "object_location": snapshot["object_location"],
            "object_scale": snapshot["object_scale"],
        }
        for point_name in ("root_head", "root_tail", "child_head", "child_tail"):
            expected_snapshot[frame][point_name] = tuple(
                armature_origin[index] + (snapshot[point_name][index] - armature_origin[index]) * 2.0
                for index in range(3)
            )

    operator, export_result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=keep_path,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'OFF',
            "object_types": {'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
            "global_scale": 2.0,
            "scale_value_mode": 'KEEP_VALUE',
            "scale_pivot": 'EACH_OBJECT_ORIGIN',
            "bake_anim": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": False,
            "add_leaf_bones": False,
        },
    )
    if export_result.errors:
        raise AssertionError(f"Connected bone keep export reported errors: {export_result.errors}")
    if operator.report_log:
        error_reports = [entry for entry in operator.report_log if 'ERROR' in entry[0]]
        if error_reports:
            raise AssertionError(f"Connected bone keep export reported operator errors: {error_reports}")

    actual_snapshot = _collect_connected_armature_snapshot(keep_path)
    for frame in ("1", "10"):
        assert_vector_close(
            actual_snapshot[frame]["object_location"],
            expected_snapshot[frame]["object_location"],
            f"connected armature object location frame {frame}",
        )
        assert_vector_close(
            actual_snapshot[frame]["object_scale"],
            expected_snapshot[frame]["object_scale"],
            f"connected armature object scale frame {frame}",
        )
        for point_name in ("root_head", "root_tail", "child_head", "child_tail"):
            assert_vector_close(
                actual_snapshot[frame][point_name],
                expected_snapshot[frame][point_name],
                f"connected armature {point_name} frame {frame}",
            )


def validate_scale_value_mode_export_sets_reuses_runtime_duplicates():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]
    func_object_utils = importlib.import_module(
        f"{base_t.EXPORTER_MODULE}.scripts.funcs.utils.func_object_utils"
    )

    call_count = {"duplicate_objects": 0}
    original_duplicate_objects = func_object_utils.duplicate_objects

    def counted_duplicate_objects(*args, **kwargs):
        call_count["duplicate_objects"] += 1
        return original_duplicate_objects(*args, **kwargs)

    filepath = os.path.join(OUTPUT_DIR, "scale_value_mode_export_sets_keep.fbx")
    remove_file_if_exists(filepath)

    try:
        func_object_utils.duplicate_objects = counted_duplicate_objects
        _export_armature_case(
            func_execute_main,
            filepath,
            'KEEP_VALUE',
            _build_armature_scale_scene,
            batch_mode='EXPORT_SETS',
        )
    finally:
        func_object_utils.duplicate_objects = original_duplicate_objects

    if call_count["duplicate_objects"] != 1:
        raise AssertionError(
            f"EXPORT_SETS keep-value export duplicated objects {call_count['duplicate_objects']} times, expected 1"
        )


def validate_scale_value_mode_export_sets_merge_join_keeps_surviving_duplicates():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]
    export_sets_flow_t = importlib.import_module("export_sets_flow_test_lib")

    expected_files = export_sets_flow_t.build_export_sets_scene()
    base_filepath = os.path.join(export_sets_flow_t.OUTPUT_DIR, "_scale_value_mode_export_sets_merge_join_base.fbx")
    remove_file_if_exists(base_filepath)
    for filename in expected_files.keys():
        remove_file_if_exists(os.path.join(export_sets_flow_t.OUTPUT_DIR, filename))

    operator, export_result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=base_filepath,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
            "global_scale": 2.0,
            "scale_value_mode": 'KEEP_VALUE',
            "scale_pivot": 'WORLD_ORIGIN',
            "bake_anim": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": True,
            "add_leaf_bones": False,
        },
    )
    if export_result.errors:
        raise AssertionError(f"KEEP_VALUE export-set merge/join export reported errors: {export_result.errors}")
    if operator.report_log:
        error_reports = [entry for entry in operator.report_log if 'ERROR' in entry[0]]
        if error_reports:
            raise AssertionError(f"Operator reported export errors: {error_reports}")


def validate_scale_value_mode_world_origin_matches_builtin_fbx_global_scale_reference():
    modules = base_t.load_required_modules()
    func_execute_main = modules["func_execute_main"]

    reference_path = os.path.join(OUTPUT_DIR, "scale_value_mode_world_origin_reference.fbx")
    keep_path = os.path.join(OUTPUT_DIR, "scale_value_mode_world_origin_keep.fbx")
    remove_file_if_exists(reference_path)
    remove_file_if_exists(keep_path)

    _build_armature_scale_scene()
    _export_scale_all_reference_with_addon(
        func_execute_main,
        reference_path,
        {
            "object_types": {'ARMATURE', 'MESH'},
            "bake_anim": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": True,
            "add_leaf_bones": False,
        },
    )

    _export_armature_case(func_execute_main, keep_path, 'KEEP_VALUE', _build_armature_scale_scene)

    reference_summary = _build_fbx_armature_summary(reference_path)
    keep_summary = _build_fbx_armature_summary(keep_path)

    assert_close(
        keep_summary["unit_scale_factor"],
        reference_summary["unit_scale_factor"],
        "world-origin keep unit_scale_factor",
    )
    for model_name in ("ScaleRig", "ScaleRigMesh"):
        assert_vector_close(
            keep_summary["model_scalings"][model_name],
            reference_summary["model_scalings"][model_name],
            f"world-origin keep model scaling {model_name}",
        )
    for cluster_name in ("Bone", "Child"):
        for matrix_name in ("Transform", "TransformLink", "TransformAssociateModel"):
            assert_vector_close(
                keep_summary["clusters"][cluster_name][matrix_name],
                reference_summary["clusters"][cluster_name][matrix_name],
                f"world-origin keep cluster {cluster_name} {matrix_name}",
            )
