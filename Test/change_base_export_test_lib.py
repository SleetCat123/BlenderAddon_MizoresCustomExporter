import importlib
import hashlib
import math
import os
import sys
import traceback

import bmesh
import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTER_ADDON_DIR = os.path.dirname(SCRIPT_DIR)
ADDONS_DIR = os.path.dirname(EXPORTER_ADDON_DIR)


def _build_output_dir():
    main_module = sys.modules.get("__main__")
    main_file = os.path.abspath(getattr(main_module, "__file__", "unknown_main"))
    main_hash = hashlib.sha1(main_file.encode("utf-8")).hexdigest()[:8]
    return os.path.join(
        SCRIPT_DIR,
        "output_change_base_export",
        f"pid_{os.getpid()}_{main_hash}",
    )


OUTPUT_DIR = _build_output_dir()

EXPORTER_MODULE = "BlenderAddon-MizoresCustomExporter"
AUTOMERGE_MODULE = "BlenderAddon-AutoMerge"
SHAPEKEYS_UTIL_MODULE = "BlenderAddon_ShapeKeysUtil"
FBX_MODULE = "io_scene_fbx"


if ADDONS_DIR not in sys.path:
    sys.path.insert(0, ADDONS_DIR)


def log(message):
    print(f"[change-base-export-test] {message}")


def get_active_object():
    obj = getattr(bpy.context, "active_object", None)
    if obj is not None:
        return obj
    obj = getattr(bpy.context, "object", None)
    if obj is not None:
        return obj
    view_layer = getattr(bpy.context, "view_layer", None)
    if view_layer is not None:
        return view_layer.objects.active
    return None


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def ensure_addon_enabled(module_name):
    if module_name in bpy.context.preferences.addons:
        return
    log(f"Enabling addon: {module_name}")
    result = bpy.ops.preferences.addon_enable(module=module_name)
    if 'FINISHED' not in result:
        raise RuntimeError(f"Failed to enable addon: {module_name} ({result})")


def ensure_required_addons():
    ensure_addon_enabled(SHAPEKEYS_UTIL_MODULE)
    ensure_addon_enabled(AUTOMERGE_MODULE)
    ensure_addon_enabled(EXPORTER_MODULE)
    ensure_addon_enabled(FBX_MODULE)


def load_required_modules():
    ensure_required_addons()
    modules = {
        "change_base_settings": importlib.import_module(
            f"{AUTOMERGE_MODULE}.scripts.change_base_settings"
        ),
        "func_apply_as_shapekey": importlib.import_module(
            f"{SHAPEKEYS_UTIL_MODULE}.scripts.funcs.func_apply_as_shapekey"
        ),
        "func_execute_main": importlib.import_module(
            f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.func_execute_main"
        ),
    }
    return modules


def reset_scene():
    log("Resetting scene to factory empty state")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_required_addons()


def deselect_all():
    for obj in bpy.context.selected_objects:
        obj.select_set(False)


def select_objects(objects, active=None):
    deselect_all()
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active or (objects[0] if objects else None)


def set_parent_keep_transform(child, parent):
    matrix_world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = matrix_world


def get_mesh_vertex_coords(obj):
    return [tuple(vertex.co) for vertex in obj.data.vertices]


def get_shape_key_coords(obj, shape_key_name):
    shape_keys = obj.data.shape_keys
    if shape_keys is None or shape_key_name not in shape_keys.key_blocks:
        raise AssertionError(
            f"Shape key '{shape_key_name}' not found on '{obj.name}'. "
            f"Available: {[] if shape_keys is None else list(shape_keys.key_blocks.keys())}"
        )
    return [tuple(point.co) for point in shape_keys.key_blocks[shape_key_name].data]


def get_delta_lengths(coords_a, coords_b):
    if len(coords_a) != len(coords_b):
        raise AssertionError(
            f"Cannot compute delta lengths for different vertex counts: "
            f"{len(coords_a)} vs {len(coords_b)}"
        )

    result = []
    for co_a, co_b in zip(coords_a, coords_b):
        dx = co_a[0] - co_b[0]
        dy = co_a[1] - co_b[1]
        dz = co_a[2] - co_b[2]
        result.append(math.sqrt((dx * dx) + (dy * dy) + (dz * dz)))
    return result


def get_delta_length_signature(coords_a, coords_b, digits=6):
    delta_lengths = get_delta_lengths(coords_a, coords_b)
    rounded = [f"{value:.{digits}f}" for value in sorted(delta_lengths)]
    return hashlib.sha1("\n".join(rounded).encode("utf-8")).hexdigest()


def assert_coords_close(actual, expected, label, tolerance=1e-6):
    if len(actual) != len(expected):
        raise AssertionError(
            f"{label}: vertex count mismatch. actual={len(actual)} expected={len(expected)}"
        )

    for index, (actual_co, expected_co) in enumerate(zip(actual, expected)):
        for axis, actual_value, expected_value in zip("xyz", actual_co, expected_co):
            if math.fabs(actual_value - expected_value) > tolerance:
                raise AssertionError(
                    f"{label}: vertex {index} axis {axis} mismatch. "
                    f"actual={actual_value} expected={expected_value}"
                )


def assert_float_lists_close(actual, expected, label, tolerance=1e-6):
    if len(actual) != len(expected):
        raise AssertionError(
            f"{label}: length mismatch. actual={len(actual)} expected={len(expected)}"
        )

    for index, (actual_value, expected_value) in enumerate(zip(actual, expected)):
        if math.fabs(actual_value - expected_value) > tolerance:
            raise AssertionError(
                f"{label}: index {index} mismatch. "
                f"actual={actual_value} expected={expected_value}"
            )


def assert_float_multiset_close(actual, expected, label, tolerance=1e-6):
    assert_float_lists_close(
        sorted(actual),
        sorted(expected),
        label,
        tolerance=tolerance,
    )


def assert_shape_key_names(obj, expected_names):
    actual_names = []
    if obj.data.shape_keys is not None:
        actual_names = [key.name for key in obj.data.shape_keys.key_blocks]
    log(
        f"Shape keys on '{obj.name}': "
        f"count={len(actual_names)} names={actual_names}"
    )
    if len(actual_names) != len(expected_names):
        raise AssertionError(
            f"Unexpected shape key count on '{obj.name}'. "
            f"actual={len(actual_names)} expected={len(expected_names)} "
            f"names={actual_names}"
        )
    if actual_names != expected_names:
        raise AssertionError(
            f"Unexpected shape key order on '{obj.name}'. actual={actual_names} expected={expected_names}"
        )


def assert_shape_key_relative_keys_valid(obj):
    if obj.data.shape_keys is None:
        return

    key_blocks = obj.data.shape_keys.key_blocks
    valid_names = [key.name for key in key_blocks]
    relative_names = {}

    for key in key_blocks:
        relative_name = None
        if key.name != "Basis":
            try:
                if key.relative_key is not None:
                    relative_name = key.relative_key.name
            except ReferenceError as exc:
                raise AssertionError(
                    f"Shape key '{key.name}' on '{obj.name}' has a broken relative_key reference"
                ) from exc

            if relative_name is None:
                raise AssertionError(
                    f"Shape key '{key.name}' on '{obj.name}' has no relative_key"
                )
            if relative_name == key.name:
                raise AssertionError(
                    f"Shape key '{key.name}' on '{obj.name}' points to itself as relative_key"
                )
            if relative_name not in valid_names:
                raise AssertionError(
                    f"Shape key '{key.name}' on '{obj.name}' points to missing relative_key "
                    f"'{relative_name}'. valid={valid_names}"
                )

        relative_names[key.name] = relative_name

    log(f"Relative keys on '{obj.name}': {relative_names}")


class ExportOperatorStub:
    def __init__(
        self,
        filepath,
        enable_auto_merge,
        enable_apply_modifiers_with_shapekeys=False,
        enable_subtract_base_shapekey=False,
    ):
        self.filepath = filepath
        self.use_selection = True
        self.use_active_collection = False
        self.global_scale = 1.0
        self.scale_value_mode = 'NORMAL'
        self.scale_pivot = 'WORLD_ORIGIN'
        self.apply_unit_scale = True
        self.apply_scale_options = 'FBX_SCALE_UNITS'
        self.use_space_transform = True
        self.bake_space_transform = True
        self.object_types = {'MESH'}
        self.use_mesh_modifiers = False
        self.use_mesh_modifiers_render = True
        self.mesh_smooth_type = 'OFF'
        self.use_subsurf = False
        self.use_mesh_edges = False
        self.use_tspace = False
        self.use_custom_props = False
        self.add_leaf_bones = False
        self.primary_bone_axis = 'Y'
        self.secondary_bone_axis = 'X'
        self.use_armature_deform_only = False
        self.armature_nodetype = 'NULL'
        self.bake_anim = False
        self.bake_anim_use_all_bones = True
        self.bake_anim_use_nla_strips = True
        self.bake_anim_use_all_actions = True
        self.bake_anim_force_startend_keying = True
        self.bake_anim_step = 1.0
        self.bake_anim_simplify_factor = 1.0
        self.path_mode = 'AUTO'
        self.embed_textures = False
        self.batch_mode = 'OFF'
        self.use_batch_own_dir = False
        self.use_metadata = True
        self.save_prefs = False
        self.save_path = False
        self.batch_filename_format_presets = 'CUSTOM'
        self.batch_filename_format = "{name}_{batch}"
        self.use_selection_children_objects = False
        self.use_active_collection_children_objects = False
        self.use_active_collection_children_collections = False
        self.use_batch_collection_children_collections = False
        self.only_root_collection = False
        self.enable_auto_merge = enable_auto_merge
        self.use_update_mesh_deform_addon = False
        self.enable_apply_modifiers_with_shapekeys = enable_apply_modifiers_with_shapekeys
        self.enable_separate_lr_shapekey = False
        self.enable_subtract_base_shapekey = enable_subtract_base_shapekey
        self.enable_reorder_shapekeys = False
        self.bake_anim_use_bone_constraint = True
        self.use_variants_merge = False
        self.enable_fix_vertex_group_collisions = False
        self.enable_limit_vertex_group_count = False
        self.limit_vertex_group_count = 4
        self.axis_forward = '-Z'
        self.axis_up = 'Y'
        self.check_existing = False
        self.filter_glob = '*.fbx'
        self.ui_tab = ""
        self.report_log = []

    def as_keywords(self, ignore=()):
        ignored = set(ignore)
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("_") or key in ignored or key == "report_log":
                continue
            if callable(value):
                continue
            result[key] = value
        return result

    def report(self, levels, message):
        normalized_levels = tuple(sorted(levels))
        self.report_log.append((normalized_levels, message))
        log(f"Operator report {normalized_levels}: {message}")


def create_shape_key_export_object(change_base_settings):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = get_active_object()
    obj.name = "ExportMesh"
    obj.data.name = "ExportMeshData"

    obj.shape_key_add(name="Basis")
    export_basis = obj.shape_key_add(name="ExportBasis")
    blink = obj.shape_key_add(name="Blink")

    export_basis.data[0].co.x += 1.25
    export_basis.data[1].co.y += 0.5
    blink.data[2].co.z += 0.75

    change_base_settings.set_change_base_settings(
        obj,
        [
            {
                "source_shapekey_name": "ExportBasis",
                "reverse_shapekey_name": "OriginalBasis",
            }
        ],
    )

    expected = {
        "basis": get_shape_key_coords(obj, "Basis"),
        "export_basis": get_shape_key_coords(obj, "ExportBasis"),
        "blink": get_shape_key_coords(obj, "Blink"),
        "change_base_settings": change_base_settings.get_change_base_settings(obj),
        "basis_to_export_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "ExportBasis"),
            get_shape_key_coords(obj, "Basis"),
        ),
        "blink_to_basis_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Blink"),
            get_shape_key_coords(obj, "Basis"),
        ),
    }
    log(f"Created shape key export object: {obj.name}")
    return obj, expected


def create_subtract_base_export_object():
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = get_active_object()
    obj.name = "ExportMesh"
    obj.data.name = "ExportMeshData"

    basis = obj.shape_key_add(name="Basis")
    smile = obj.shape_key_add(name="Smile")
    look_down = obj.shape_key_add(name="Look_Down@BASE:Smile")
    look_up = obj.shape_key_add(name="Look_Up@BASE:Smile")

    smile.data[0].co.x += 0.8
    smile.data[1].co.y += 0.35

    for index, point in enumerate(smile.data):
        look_down.data[index].co = (point.co.x, point.co.y, point.co.z)
        look_up.data[index].co = (point.co.x, point.co.y, point.co.z)

    look_down.data[2].co.z -= 0.6
    look_down.data[3].co.x -= 0.25
    look_up.data[2].co.z += 0.5
    look_up.data[0].co.y += 0.4

    look_down.relative_key = smile
    look_up.relative_key = smile

    expected = {
        "basis": get_shape_key_coords(obj, "Basis"),
        "smile": get_shape_key_coords(obj, "Smile"),
        "look_down_composite": get_shape_key_coords(obj, "Look_Down@BASE:Smile"),
        "look_up_composite": get_shape_key_coords(obj, "Look_Up@BASE:Smile"),
        "smile_to_basis_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Smile"),
            get_shape_key_coords(obj, "Basis"),
        ),
        "look_down_to_smile_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Look_Down@BASE:Smile"),
            get_shape_key_coords(obj, "Smile"),
        ),
        "look_up_to_smile_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Look_Up@BASE:Smile"),
            get_shape_key_coords(obj, "Smile"),
        ),
    }
    log(f"Created subtract-base export object: {obj.name}")
    return obj, expected


def create_shape_key_export_object_via_ui(change_base_settings):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = get_active_object()
    obj.name = "ExportMesh"
    obj.data.name = "ExportMeshData"

    obj.shape_key_add(name="Basis")
    export_basis = obj.shape_key_add(name="ExportBasis")
    blink = obj.shape_key_add(name="Blink")

    export_basis.data[0].co.x += 1.25
    export_basis.data[1].co.y += 0.5
    blink.data[2].co.z += 0.75

    wm = bpy.context.window_manager
    change_base_settings.ensure_ui_state_for_object(obj, wm)
    bpy.ops.object.automerge_change_base_shapekey_add()
    item = wm.automerge_change_base_shapekeys_ui[0]
    item.source_shapekey_name = "ExportBasis"
    item.reverse_shapekey_name = "OriginalBasis"

    expected = {
        "basis": get_shape_key_coords(obj, "Basis"),
        "export_basis": get_shape_key_coords(obj, "ExportBasis"),
        "blink": get_shape_key_coords(obj, "Blink"),
        "change_base_settings": change_base_settings.get_change_base_settings(obj),
        "basis_to_export_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "ExportBasis"),
            get_shape_key_coords(obj, "Basis"),
        ),
        "blink_to_basis_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Blink"),
            get_shape_key_coords(obj, "Basis"),
        ),
    }
    log(f"Created shape key export object via UI panel state: {obj.name}")
    return obj, expected


def create_shape_key_export_object_via_ui_with_standalone_target(change_base_settings):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = get_active_object()
    obj.name = "ExportMesh"
    obj.data.name = "ExportMeshData"

    obj.shape_key_add(name="Basis")
    export_basis = obj.shape_key_add(name="ExportBasis")
    blink = obj.shape_key_add(name="Blink")
    frown = obj.shape_key_add(name="Frown")

    export_basis.data[0].co.x += 1.25
    export_basis.data[1].co.y += 0.5
    blink.data[2].co.z += 0.75
    blink.data[3].co.x -= 0.35
    frown.data[0].co.y -= 0.45
    frown.data[2].co.x += 0.55

    select_objects([obj], active=obj)
    wm = bpy.context.window_manager
    change_base_settings.ensure_ui_state_for_object(obj, wm)
    bpy.ops.object.automerge_change_base_shapekey_add()
    item = wm.automerge_change_base_shapekeys_ui[0]
    item.source_shapekey_name = "ExportBasis"
    item.reverse_shapekey_name = "OriginalBasis"
    set_behavior_result = bpy.ops.object.automerge_set_change_base_target_behavior(
        item_index=0,
        target_shapekey_name="Blink",
        behavior_mode=change_base_settings.CHANGE_BASE_MODE_STANDALONE,
    )
    if 'FINISHED' not in set_behavior_result:
        raise RuntimeError(f"Failed to set standalone target behavior: {set_behavior_result}")

    expected = {
        "basis": get_shape_key_coords(obj, "Basis"),
        "export_basis": get_shape_key_coords(obj, "ExportBasis"),
        "blink": get_shape_key_coords(obj, "Blink"),
        "frown": get_shape_key_coords(obj, "Frown"),
        "change_base_settings": change_base_settings.get_change_base_settings(obj),
        "basis_to_export_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "ExportBasis"),
            get_shape_key_coords(obj, "Basis"),
        ),
        "blink_to_export_basis_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Blink"),
            get_shape_key_coords(obj, "ExportBasis"),
        ),
        "frown_to_basis_delta_lengths": get_delta_lengths(
            get_shape_key_coords(obj, "Frown"),
            get_shape_key_coords(obj, "Basis"),
        ),
    }
    log(f"Created per-shape standalone change-base object via UI panel state: {obj.name}")
    return obj, expected


def assign_merge_group(obj):
    obj["MergeGroup"] = True


def create_automerge_child(root, name="MergeChild", location=(2.5, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    child = get_active_object()
    child.name = name
    child.data.name = f"{name}Data"
    set_parent_keep_transform(child, root)

    expected_vertex_count = len(root.data.vertices) + len(child.data.vertices)
    log(
        "Created AutoMerge child: "
        f"root={root.name} child={child.name} expected_vertex_count>={expected_vertex_count}"
    )
    return child, expected_vertex_count


def create_subdivided_cube_object(name, location, size=1.0, cuts=1):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = get_active_object()
    obj.name = name
    obj.data.name = f"{name}Data"

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def add_as_default_modifier(obj, factor, deform_axis='Z'):
    modifier = obj.modifiers.new(name="%AS%Default", type='SIMPLE_DEFORM')
    modifier.deform_method = 'TAPER'
    modifier.factor = factor
    modifier.deform_axis = deform_axis
    return modifier


def add_as_modifier(obj, shape_name, factor, deform_axis='Z'):
    modifier = obj.modifiers.new(name=f"%AS%{shape_name}", type='SIMPLE_DEFORM')
    modifier.deform_method = 'TAPER'
    modifier.factor = factor
    modifier.deform_axis = deform_axis
    return modifier


def add_mirror_modifier(obj, name="Mirror"):
    modifier = obj.modifiers.new(name=name, type='MIRROR')
    modifier.use_axis[0] = True
    modifier.use_axis[1] = False
    modifier.use_axis[2] = False
    modifier.merge_threshold = 0.0001
    return modifier


def add_array_modifier(obj, count=2, offset=(1.0, 0.0, 0.0), name="Array"):
    modifier = obj.modifiers.new(name=name, type='ARRAY')
    modifier.count = count
    modifier.relative_offset_displace = offset
    return modifier


def add_simple_deform_modifier(
    obj,
    factor,
    deform_axis='Z',
    deform_method='TAPER',
    name="SimpleDeform",
):
    modifier = obj.modifiers.new(name=name, type='SIMPLE_DEFORM')
    modifier.deform_method = deform_method
    modifier.factor = factor
    modifier.deform_axis = deform_axis
    return modifier


def create_lattice_object(name, location, scale=(2.0, 2.0, 2.0), deform_offset=(0.0, 0.0, 0.25)):
    bpy.ops.object.add(type='LATTICE', location=location)
    lattice = get_active_object()
    lattice.name = name
    lattice.data.name = f"{name}Data"
    lattice.scale = scale
    lattice.data.points_u = 2
    lattice.data.points_v = 2
    lattice.data.points_w = 2

    for point in lattice.data.points:
        if point.co_deform.z > 0.0:
            point.co_deform.x += deform_offset[0]
            point.co_deform.y += deform_offset[1]
            point.co_deform.z += deform_offset[2]

    return lattice


def add_lattice_modifier(obj, lattice_obj, name="Lattice"):
    modifier = obj.modifiers.new(name=name, type='LATTICE')
    modifier.object = lattice_obj
    return modifier


def add_weighted_normal_modifier(obj, name="WeightedNormal"):
    modifier = obj.modifiers.new(name=name, type='WEIGHTED_NORMAL')
    modifier.keep_sharp = False
    modifier.weight = 50
    return modifier


def add_edge_split_modifier(obj, split_angle=0.523599, name="EdgeSplit"):
    modifier = obj.modifiers.new(name=name, type='EDGE_SPLIT')
    modifier.split_angle = split_angle
    return modifier


def add_vertex_group_gradient(obj, group_name, axis='X', invert=False):
    axis_index = "XYZ".index(axis.upper())
    coords = [vertex.co[axis_index] for vertex in obj.data.vertices]
    min_co = min(coords)
    max_co = max(coords)
    span = max(max_co - min_co, 1e-6)

    group = obj.vertex_groups.get(group_name)
    if group is None:
        group = obj.vertex_groups.new(name=group_name)

    for vertex in obj.data.vertices:
        value = (vertex.co[axis_index] - min_co) / span
        if invert:
            value = 1.0 - value
        group.add([vertex.index], value, 'REPLACE')

    return group


def hide_vertices_by_axis(obj, axis='X', threshold=0.0, hide_positive=True):
    axis_index = "XYZ".index(axis.upper())
    select_objects([obj], active=obj)
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
    for vert in bm.verts:
        value = vert.co[axis_index]
        if hide_positive:
            vert.select = value > threshold
        else:
            vert.select = value < threshold
    bmesh.update_edit_mesh(obj.data)

    bpy.ops.mesh.hide(unselected=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def add_data_transfer_modifier(obj, source_obj, name="DataTransfer"):
    modifier = obj.modifiers.new(name=name, type='DATA_TRANSFER')
    modifier.object = source_obj
    modifier.use_vert_data = True
    modifier.data_types_verts = {'VGROUP_WEIGHTS'}
    modifier.vert_mapping = 'POLYINTERP_NEAREST'
    return modifier


def create_armature_object(name, location):
    bpy.ops.object.armature_add(location=location)
    armature_obj = get_active_object()
    armature_obj.name = name
    armature_obj.data.name = f"{name}Data"
    return armature_obj


def add_armature_modifier(obj, armature_obj, name="Armature"):
    modifier = obj.modifiers.new(name=name, type='ARMATURE')
    modifier.object = armature_obj
    return modifier


def setup_single_bone_armature_deform(obj, armature_obj, axis='Z', offset=0.25):
    bone_name = armature_obj.data.bones[0].name
    group = obj.vertex_groups.get(bone_name)
    if group is None:
        group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, 'REPLACE')

    pose_bone = armature_obj.pose.bones[bone_name]
    if axis == 'X':
        pose_bone.location.x += offset
    elif axis == 'Y':
        pose_bone.location.y += offset
    else:
        pose_bone.location.z += offset


def duplicate_mesh_object(obj, name):
    dup_obj = obj.copy()
    dup_obj.data = obj.data.copy()
    dup_obj.name = name
    dup_obj.data.name = f"{name}Data"
    bpy.context.collection.objects.link(dup_obj)
    return dup_obj


def ensure_scene_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def move_object_to_single_collection(obj, collection):
    if collection not in obj.users_collection:
        collection.objects.link(obj)
    for current in list(obj.users_collection):
        if current != collection:
            current.objects.unlink(obj)


def mark_dont_export(obj, exporter_consts):
    obj[exporter_consts.DONT_EXPORT_GROUP_NAME] = True


def disable_all_mirror_merge():
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for modifier in obj.modifiers:
            if modifier.type != 'MIRROR':
                continue
            if hasattr(modifier, "use_mirror_merge"):
                modifier.use_mirror_merge = False
            if hasattr(modifier, "merge_threshold"):
                modifier.merge_threshold = 0.0


def create_shared_armature_for_collection_batch(
    name,
    location,
    axis,
    offset,
    helper_collection,
    exporter_consts,
):
    armature = create_armature_object(name, location=location)
    pose_bone = armature.pose.bones[armature.data.bones[0].name]
    if axis == 'X':
        pose_bone.location.x += offset
    elif axis == 'Y':
        pose_bone.location.y += offset
    else:
        pose_bone.location.z += offset
    move_object_to_single_collection(armature, helper_collection)
    mark_dont_export(armature, exporter_consts)
    return armature


def create_transfer_source_for_collection_batch(
    base_obj,
    name,
    location,
    helper_collection,
    exporter_consts,
):
    source = duplicate_mesh_object(base_obj, name)
    source.location = location
    move_object_to_single_collection(source, helper_collection)
    mark_dont_export(source, exporter_consts)
    return source


def create_lattice_helper_for_collection_batch(
    name,
    location,
    deform_offset,
    helper_collection,
    exporter_consts,
):
    lattice = create_lattice_object(
        name=name,
        location=location,
        deform_offset=deform_offset,
    )
    move_object_to_single_collection(lattice, helper_collection)
    mark_dont_export(lattice, exporter_consts)
    return lattice


def build_expected_as_shape_keys(obj, func_apply_as_shapekey_module):
    expected_obj = duplicate_mesh_object(obj, "ExpectedShapeKeyMesh")
    select_objects([expected_obj], active=expected_obj)

    default_modifier = expected_obj.modifiers["%AS%Default"]
    func_apply_as_shapekey_module.apply_as_shapekey(default_modifier)
    eyes_up_modifier = expected_obj.modifiers["%AS%Eyes_Up"]
    func_apply_as_shapekey_module.apply_as_shapekey(eyes_up_modifier)

    expected = {
        "basis_to_default_delta_lengths": get_delta_lengths(
            get_shape_key_coords(expected_obj, "Default"),
            get_shape_key_coords(expected_obj, "Basis"),
        ),
        "eyes_up_to_basis_delta_lengths": get_delta_lengths(
            get_shape_key_coords(expected_obj, "Eyes_Up"),
            get_shape_key_coords(expected_obj, "Basis"),
        ),
    }
    assert_shape_key_relative_keys_valid(expected_obj)
    return expected_obj, expected


def create_automerge_children_with_default_change_base(change_base_settings):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    root = get_active_object()
    root.name = "MergeRoot"
    root.data.name = "MergeRootData"
    root["MergeGroup"] = True

    child_specs = [
        ("MergeChildA", (1.75, 0.0, 0.0), 0.8, "ChildAOriginalBasis"),
        ("MergeChildB", (-1.75, 0.0, 0.0), -0.6, "ChildBOriginalBasis"),
    ]
    children = []

    for child_name, location, factor, reverse_name in child_specs:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
        child = get_active_object()
        child.name = child_name
        child.data.name = f"{child_name}Data"
        add_as_default_modifier(child, factor=factor)
        change_base_settings.set_change_base_settings(
            child,
            [
                {
                    "source_shapekey_name": "Default",
                    "reverse_shapekey_name": reverse_name,
                }
            ],
        )
        set_parent_keep_transform(child, root)
        children.append(child)

    expected = {
        "reverse_names": [spec[3] for spec in child_specs],
    }
    log(
        "Created AutoMerge children with %AS%Default: "
        f"root={root.name} children={[child.name for child in children]}"
    )
    return root, children, expected


def create_automerge_as_default_with_other_modifier(
    change_base_settings,
    func_apply_as_shapekey_module,
):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = get_active_object()
    obj.name = "ExportMesh"
    obj.data.name = "ExportMeshData"
    obj["MergeGroup"] = True

    add_as_default_modifier(obj, factor=1.1, deform_axis='X')
    add_as_modifier(obj, "Eyes_Up", factor=-0.75, deform_axis='Y')

    expected_helper_obj, expected = build_expected_as_shape_keys(
        obj,
        func_apply_as_shapekey_module,
    )

    change_base_settings.set_change_base_settings(
        obj,
        [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ],
    )

    log(
        "Created AutoMerge %AS%Default + %AS%Eyes_Up object: "
        f"obj={obj.name}"
    )
    return obj, expected_helper_obj, expected


def create_automerge_parent_child_mixed_shapekey_scene(change_base_settings):
    root = create_subdivided_cube_object(
        name="MixedRoot",
        location=(0.0, 0.0, 0.0),
        size=1.6,
        cuts=1,
    )
    root["MergeGroup"] = True

    root.shape_key_add(name="Basis")
    parent_manual = root.shape_key_add(name="ParentManual")
    parent_manual.data[0].co.x += 0.55
    parent_manual.data[1].co.z += 0.25
    parent_manual.data[5].co.y -= 0.2
    add_as_modifier(root, "ParentLift", factor=0.45, deform_axis='X')

    child = create_subdivided_cube_object(
        name="MixedChild",
        location=(0.0, 0.0, 1.1),
        size=1.1,
        cuts=1,
    )
    set_parent_keep_transform(child, root)

    child.shape_key_add(name="Basis")
    child_manual = child.shape_key_add(name="ChildManual")
    child_manual.data[2].co.y += 0.45
    child_manual.data[3].co.z -= 0.3
    child_manual.data[7].co.x += 0.25
    add_as_default_modifier(child, factor=0.9, deform_axis='X')
    add_as_modifier(child, "Eyes_Up", factor=-0.7, deform_axis='Y')
    change_base_settings.set_change_base_settings(
        child,
        [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ],
    )

    expected = {
        "required_names": [
            "Basis",
            "ParentManual",
            "ParentLift",
            "ChildManual",
            "Smile",
            "Eyes_Up",
        ],
        "forbidden_names": ["Default"],
        "nonzero_names": ["ParentManual", "ParentLift", "ChildManual", "Smile", "Eyes_Up"],
    }
    log(
        "Created AutoMerge parent-child mixed shape key scene: "
        f"root={root.name} child={child.name}"
    )
    return root, child, expected


def create_automerge_modifier_stack_stress_scene(change_base_settings):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    merge_root = get_active_object()
    merge_root.name = "MergeRoot"
    merge_root.data.name = "MergeRootData"
    merge_root["MergeGroup"] = True

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.75, 0.0, 0.0))
    face_main = get_active_object()
    face_main.name = "FaceMain"
    face_main.data.name = "FaceMainData"
    set_parent_keep_transform(face_main, merge_root)

    main_lattice = create_lattice_object(
        name="FaceMainLattice",
        location=face_main.location,
        deform_offset=(0.1, 0.0, 0.35),
    )
    add_mirror_modifier(face_main, name="Mirror")
    add_array_modifier(face_main, count=2, offset=(0.8, 0.0, 0.0), name="Array")
    add_lattice_modifier(face_main, main_lattice, name="Lattice")
    add_weighted_normal_modifier(face_main, name="WeightedNormal")
    add_as_default_modifier(face_main, factor=0.85, deform_axis='X')
    add_as_modifier(face_main, "Look_Down", factor=-0.55, deform_axis='Z')
    add_as_modifier(face_main, "Look_Up", factor=0.45, deform_axis='Z')
    change_base_settings.set_change_base_settings(
        face_main,
        [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ],
    )

    bpy.ops.mesh.primitive_cube_add(size=0.8, location=(-0.75, 0.0, 0.0))
    face_eyes = get_active_object()
    face_eyes.name = "FaceEyes"
    face_eyes.data.name = "FaceEyesData"
    set_parent_keep_transform(face_eyes, merge_root)

    eyes_lattice = create_lattice_object(
        name="FaceEyesLattice",
        location=face_eyes.location,
        deform_offset=(0.0, 0.1, 0.2),
    )
    add_mirror_modifier(face_eyes, name="Mirror.001")
    add_lattice_modifier(face_eyes, eyes_lattice, name="Lattice")
    add_weighted_normal_modifier(face_eyes, name="WeightedNormal")
    add_as_modifier(face_eyes, "Eyes_Smile", factor=0.65, deform_axis='Y')

    expected = {
        "required_names": ["Basis", "Smile", "Look_Down", "Look_Up", "Eyes_Smile"],
        "forbidden_names": ["Default"],
        "nonzero_names": ["Smile", "Look_Down", "Look_Up", "Eyes_Smile"],
        "delta_signatures": {
            "Smile": "4a51c3a895db9a47ec96f52d8fdc9ccbdeef78f1",
            "Look_Down": "f88726b5ba5bf8c47f2b31236b917d0c36d9d279",
            "Look_Up": "fab8354ed67ef48e8d9052036b402104dabfa06e",
            "Eyes_Smile": "3532fc946a0cca7a05e790b945ea3966c15c372d",
        },
    }
    log(
        "Created AutoMerge modifier-stack stress scene: "
        f"root={merge_root.name} children={[face_main.name, face_eyes.name]}"
    )
    return merge_root, [face_main, face_eyes], expected


def create_automerge_crash_log_regression_scene(
    change_base_settings,
    prefix="Crash",
    root_location=(0.0, 0.0, 0.0),
):
    merge_root = create_subdivided_cube_object(
        name=f"{prefix}Root",
        location=root_location,
        size=1.8,
        cuts=1,
    )
    merge_root["MergeGroup"] = True
    merge_root.shape_key_add(name="Basis")
    root_manual = merge_root.shape_key_add(name="RootManual")
    root_manual.data[0].co.x += 0.35
    root_manual.data[3].co.z -= 0.2
    add_as_modifier(merge_root, "RootLift", factor=0.35, deform_axis='Z')

    root_x, root_y, root_z = root_location
    face_main = create_subdivided_cube_object(
        name=f"{prefix}FaceMain",
        location=(root_x + 0.85, root_y, root_z),
        size=1.2,
        cuts=1,
    )
    set_parent_keep_transform(face_main, merge_root)
    face_main.shape_key_add(name="Basis")
    main_manual = face_main.shape_key_add(name="MainManual")
    main_manual.data[1].co.y += 0.28
    main_manual.data[5].co.z += 0.22
    add_vertex_group_gradient(face_main, "TransferMainA", axis='X')
    add_vertex_group_gradient(face_main, "TransferMainB", axis='Y', invert=True)

    main_transfer_a = duplicate_mesh_object(face_main, f"{prefix}FaceMainTransferA")
    main_transfer_a.location = (root_x + 3.0, root_y, root_z)
    main_transfer_b = duplicate_mesh_object(face_main, f"{prefix}FaceMainTransferB")
    main_transfer_b.location = (root_x + 4.0, root_y, root_z)
    main_armature = create_armature_object(f"{prefix}FaceMainArmature", location=(root_x + 0.85, root_y, root_z))
    main_lattice = create_lattice_object(
        name=f"{prefix}FaceMainLattice",
        location=face_main.location,
        deform_offset=(0.1, 0.0, 0.3),
    )

    add_array_modifier(face_main, count=2, offset=(0.75, 0.0, 0.0), name="Array")
    add_simple_deform_modifier(face_main, factor=0.25, deform_axis='Y', name="SimpleDeform")
    add_lattice_modifier(face_main, main_lattice, name="Lattice")
    add_as_default_modifier(face_main, factor=0.9, deform_axis='X')
    add_mirror_modifier(face_main, name="Mirror")
    add_data_transfer_modifier(face_main, main_transfer_a, name="DataTransfer")
    add_data_transfer_modifier(face_main, main_transfer_b, name="DataTransfer.001")
    add_as_modifier(face_main, "Look_Down", factor=-0.45, deform_axis='Z')
    add_as_modifier(face_main, "Look_Up", factor=0.5, deform_axis='Z')
    add_armature_modifier(face_main, main_armature, name="Armature")
    setup_single_bone_armature_deform(face_main, main_armature, axis='Z', offset=0.22)
    change_base_settings.set_change_base_settings(
        face_main,
        [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ],
    )

    face_eyes = create_subdivided_cube_object(
        name=f"{prefix}FaceEyes",
        location=(root_x - 0.85, root_y, root_z),
        size=0.95,
        cuts=1,
    )
    set_parent_keep_transform(face_eyes, merge_root)
    face_eyes.shape_key_add(name="Basis")
    eyes_manual = face_eyes.shape_key_add(name="EyesManual")
    eyes_manual.data[2].co.x -= 0.2
    eyes_manual.data[6].co.y += 0.24
    add_vertex_group_gradient(face_eyes, "TransferEyesA", axis='X')
    add_vertex_group_gradient(face_eyes, "TransferEyesB", axis='Z')

    eyes_transfer_a = duplicate_mesh_object(face_eyes, f"{prefix}FaceEyesTransferA")
    eyes_transfer_a.location = (root_x - 3.0, root_y, root_z)
    eyes_transfer_b = duplicate_mesh_object(face_eyes, f"{prefix}FaceEyesTransferB")
    eyes_transfer_b.location = (root_x - 4.0, root_y, root_z)
    eyes_armature = create_armature_object(f"{prefix}FaceEyesArmature", location=(root_x - 0.85, root_y, root_z))
    eyes_lattice = create_lattice_object(
        name=f"{prefix}FaceEyesLattice",
        location=face_eyes.location,
        deform_offset=(0.0, 0.1, 0.2),
    )

    add_lattice_modifier(face_eyes, eyes_lattice, name="Lattice")
    add_as_modifier(face_eyes, "Eyes_Smile", factor=0.6, deform_axis='Y')
    add_mirror_modifier(face_eyes, name="Mirror")
    add_edge_split_modifier(face_eyes, name="EdgeSplit")
    add_weighted_normal_modifier(face_eyes, name="WeightedNormal")
    add_data_transfer_modifier(face_eyes, eyes_transfer_a, name="DataTransfer")
    add_data_transfer_modifier(face_eyes, eyes_transfer_b, name="DataTransfer.001")
    add_armature_modifier(face_eyes, eyes_armature, name="Armature")
    setup_single_bone_armature_deform(face_eyes, eyes_armature, axis='Y', offset=0.18)

    expected = {
        "required_names": [
            "Basis",
            "RootManual",
            "RootLift",
            "MainManual",
            "Smile",
            "Look_Down",
            "Look_Up",
            "EyesManual",
            "Eyes_Smile",
        ],
        "forbidden_names": ["Default"],
        "nonzero_names": [
            "RootManual",
            "RootLift",
            "MainManual",
            "Smile",
            "Look_Down",
            "Look_Up",
            "EyesManual",
            "Eyes_Smile",
        ],
        "delta_signatures": {
            "RootManual": "a9d3c074f768097a1b0f19dadee8ef33662f9614",
            "RootLift": "e92738dffc86d2083c647cac633bfb538f0b4ed6",
            "MainManual": "31a156d9d31d99026fd65497ec88ce32ca063d55",
            "Smile": "6aa01af501687e02add5ae58e91f73dd12df5b86",
            "Look_Down": "67addf7186e5da02764a0aa17051a6d9a770a153",
            "Look_Up": "9f91a0f98ed7398c18fe2420ef084184649148b0",
            "EyesManual": "f09f05bc65d186e5ef112daf43adfb2377f64fcf",
            "Eyes_Smile": "8b31fa77deaedfaf249af4d82787bcc414ebc9f4",
        },
        "root_name": merge_root.name,
        "face_main_name": face_main.name,
    }
    log(
        "Created AutoMerge crash-log regression scene: "
        f"root={merge_root.name} children={[face_main.name, face_eyes.name]}"
    )
    return merge_root, [face_main, face_eyes], expected


def create_automerge_crash_log_multi_root_scene(change_base_settings):
    groups = []
    for index, root_x in enumerate((0.0, 7.5, 15.0), start=1):
        root, children, expected = create_automerge_crash_log_regression_scene(
            change_base_settings,
            prefix=f"Crash{index}",
            root_location=(root_x, 0.0, 0.0),
        )
        groups.append(
            {
                "root": root,
                "children": children,
                "expected": expected,
            }
        )

    roots = [group["root"] for group in groups]
    children = [child for group in groups for child in group["children"]]
    log(f"Created AutoMerge multi-root crash regression scene: roots={[obj.name for obj in roots]}")
    return groups, roots, children


def create_collection_batch_face_group(
    change_base_settings,
    exporter_consts,
    collection,
    helper_collection,
    prefix,
    root_location,
    shared_main_armature,
    shared_eyes_armature,
):
    root_x, root_y, root_z = root_location

    merge_root = create_subdivided_cube_object(
        name=f"{prefix}Root",
        location=root_location,
        size=1.8,
        cuts=1,
    )
    merge_root["MergeGroup"] = True
    merge_root.shape_key_add(name="Basis")
    root_manual = merge_root.shape_key_add(name="RootManual")
    root_manual.data[0].co.x += 0.35
    root_manual.data[3].co.z -= 0.2
    add_as_modifier(merge_root, "RootLift", factor=0.35, deform_axis='Z')
    move_object_to_single_collection(merge_root, collection)

    face_main = create_subdivided_cube_object(
        name=f"{prefix}FaceMain",
        location=(root_x + 1.1, root_y, root_z),
        size=1.2,
        cuts=1,
    )
    set_parent_keep_transform(face_main, merge_root)
    move_object_to_single_collection(face_main, collection)
    face_main.shape_key_add(name="Basis")
    main_manual = face_main.shape_key_add(name="MainManual")
    main_manual.data[1].co.y += 0.28
    main_manual.data[5].co.z += 0.22
    add_vertex_group_gradient(face_main, "TransferMainA", axis='X')
    add_vertex_group_gradient(face_main, "TransferMainB", axis='Y', invert=True)

    main_transfer_a = create_transfer_source_for_collection_batch(
        face_main,
        f"{prefix}FaceMainTransferA",
        (root_x + 4.0, root_y - 1.6, root_z),
        helper_collection,
        exporter_consts,
    )
    main_transfer_b = create_transfer_source_for_collection_batch(
        face_main,
        f"{prefix}FaceMainTransferB",
        (root_x + 5.0, root_y - 1.6, root_z),
        helper_collection,
        exporter_consts,
    )
    main_lattice = create_lattice_helper_for_collection_batch(
        name=f"{prefix}FaceMainLattice",
        location=face_main.location,
        deform_offset=(0.1, 0.0, 0.3),
        helper_collection=helper_collection,
        exporter_consts=exporter_consts,
    )

    add_array_modifier(face_main, count=2, offset=(0.75, 0.0, 0.0), name="Array")
    add_simple_deform_modifier(face_main, factor=0.25, deform_axis='Y', name="SimpleDeform")
    add_lattice_modifier(face_main, main_lattice, name="Lattice")
    add_as_default_modifier(face_main, factor=0.9, deform_axis='X')
    add_mirror_modifier(face_main, name="Mirror")
    add_data_transfer_modifier(face_main, main_transfer_a, name="DataTransfer")
    add_data_transfer_modifier(face_main, main_transfer_b, name="DataTransfer.001")
    add_as_modifier(face_main, "Look_Down", factor=-0.45, deform_axis='Z')
    add_as_modifier(face_main, "Look_Up", factor=0.5, deform_axis='Z')
    add_armature_modifier(face_main, shared_main_armature, name="Armature")
    change_base_settings.set_change_base_settings(
        face_main,
        [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ],
    )

    face_eyes = create_subdivided_cube_object(
        name=f"{prefix}FaceEyes",
        location=(root_x - 1.1, root_y, root_z),
        size=0.95,
        cuts=1,
    )
    set_parent_keep_transform(face_eyes, merge_root)
    move_object_to_single_collection(face_eyes, collection)
    face_eyes.shape_key_add(name="Basis")
    eyes_manual = face_eyes.shape_key_add(name="EyesManual")
    eyes_manual.data[2].co.x -= 0.2
    eyes_manual.data[6].co.y += 0.24
    add_vertex_group_gradient(face_eyes, "TransferEyesA", axis='X')
    add_vertex_group_gradient(face_eyes, "TransferEyesB", axis='Z')

    eyes_transfer_a = create_transfer_source_for_collection_batch(
        face_eyes,
        f"{prefix}FaceEyesTransferA",
        (root_x - 4.0, root_y - 1.6, root_z),
        helper_collection,
        exporter_consts,
    )
    eyes_transfer_b = create_transfer_source_for_collection_batch(
        face_eyes,
        f"{prefix}FaceEyesTransferB",
        (root_x - 5.0, root_y - 1.6, root_z),
        helper_collection,
        exporter_consts,
    )
    eyes_lattice = create_lattice_helper_for_collection_batch(
        name=f"{prefix}FaceEyesLattice",
        location=face_eyes.location,
        deform_offset=(0.0, 0.1, 0.2),
        helper_collection=helper_collection,
        exporter_consts=exporter_consts,
    )

    add_lattice_modifier(face_eyes, eyes_lattice, name="Lattice")
    add_as_modifier(face_eyes, "Eyes_Smile", factor=0.6, deform_axis='Y')
    add_mirror_modifier(face_eyes, name="Mirror")
    add_edge_split_modifier(face_eyes, name="EdgeSplit")
    add_weighted_normal_modifier(face_eyes, name="WeightedNormal")
    add_data_transfer_modifier(face_eyes, eyes_transfer_a, name="DataTransfer")
    add_data_transfer_modifier(face_eyes, eyes_transfer_b, name="DataTransfer.001")
    add_armature_modifier(face_eyes, shared_eyes_armature, name="Armature")

    expected = {
        "required_names": [
            "Basis",
            "RootManual",
            "RootLift",
            "MainManual",
            "Smile",
            "Look_Down",
            "Look_Up",
            "EyesManual",
            "Eyes_Smile",
        ],
        "forbidden_names": ["Default"],
        "nonzero_names": [
            "RootManual",
            "RootLift",
            "MainManual",
            "Smile",
            "Look_Down",
            "Look_Up",
            "EyesManual",
            "Eyes_Smile",
        ],
    }
    return merge_root, face_main, face_eyes, expected


def create_collection_batch_standalone_shapekey_mesh(
    collection,
    helper_collection,
    exporter_consts,
    prefix,
    location,
    hide_vertices_for_lr_reveal=False,
):
    mesh = create_subdivided_cube_object(
        name=f"{prefix}Standalone",
        location=location,
        size=1.15,
        cuts=1,
    )
    move_object_to_single_collection(mesh, collection)
    mesh.shape_key_add(name="Basis")
    smile = mesh.shape_key_add(name="StandaloneSmile%LR%")
    blink = mesh.shape_key_add(name="StandaloneBlink")
    smile.data[0].co.x += 0.32
    smile.data[2].co.y -= 0.18
    blink.data[5].co.z += 0.24
    blink.data[7].co.x -= 0.15

    add_vertex_group_gradient(mesh, "StandaloneTransferA", axis='X')
    add_vertex_group_gradient(mesh, "StandaloneTransferB", axis='Y', invert=True)

    transfer_a = create_transfer_source_for_collection_batch(
        mesh,
        f"{prefix}StandaloneTransferA",
        (location[0] + 3.5, location[1] - 1.0, location[2]),
        helper_collection,
        exporter_consts,
    )
    transfer_b = create_transfer_source_for_collection_batch(
        mesh,
        f"{prefix}StandaloneTransferB",
        (location[0] + 4.5, location[1] - 1.0, location[2]),
        helper_collection,
        exporter_consts,
    )
    lattice = create_lattice_helper_for_collection_batch(
        name=f"{prefix}StandaloneLattice",
        location=mesh.location,
        deform_offset=(0.05, 0.0, 0.22),
        helper_collection=helper_collection,
        exporter_consts=exporter_consts,
    )

    add_mirror_modifier(mesh, name="Mirror")
    add_edge_split_modifier(mesh, name="EdgeSplit")
    add_weighted_normal_modifier(mesh, name="WeightedNormal")
    add_data_transfer_modifier(mesh, transfer_a, name="DataTransfer")
    add_data_transfer_modifier(mesh, transfer_b, name="DataTransfer.001")
    add_lattice_modifier(mesh, lattice, name="Lattice")

    if hide_vertices_for_lr_reveal:
        hide_vertices_by_axis(mesh, axis='X', threshold=0.0, hide_positive=True)

    expected = {
        "required_names": [
            "Basis",
            "StandaloneSmile_left",
            "StandaloneSmile_right",
            "StandaloneBlink",
        ],
        "forbidden_names": ["StandaloneSmile%LR%"],
        "nonzero_names": [
            "StandaloneSmile_left",
            "StandaloneSmile_right",
            "StandaloneBlink",
        ],
    }
    return mesh, expected


def create_collection_batch_shared_data_scene(change_base_settings):
    exporter_consts = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.consts"
    )
    helper_collection = ensure_scene_collection(exporter_consts.DONT_EXPORT_GROUP_NAME)
    shared_main_armature = create_shared_armature_for_collection_batch(
        name="SharedMainArmature",
        location=(0.0, -12.0, 0.0),
        axis='Z',
        offset=0.22,
        helper_collection=helper_collection,
        exporter_consts=exporter_consts,
    )
    shared_eyes_armature = create_shared_armature_for_collection_batch(
        name="SharedEyesArmature",
        location=(0.0, -15.0, 0.0),
        axis='Y',
        offset=0.18,
        helper_collection=helper_collection,
        exporter_consts=exporter_consts,
    )

    groups = []
    template_group_data = None
    template_standalone_data = None
    for index, (x, z) in enumerate(
        (
            (0.0, 0.0),
            (6.5, 0.0),
            (13.0, 0.0),
            (19.5, 0.0),
            (0.0, 6.5),
            (6.5, 6.5),
            (13.0, 6.5),
            (19.5, 6.5),
        ),
        start=1,
    ):
        collection = ensure_scene_collection(f"BatchFace{index:02d}")
        prefix = f"Batch{index:02d}"
        root, face_main, face_eyes, root_expected = create_collection_batch_face_group(
            change_base_settings,
            exporter_consts,
            collection,
            helper_collection,
            prefix=prefix,
            root_location=(x, 0.0, z),
            shared_main_armature=shared_main_armature,
            shared_eyes_armature=shared_eyes_armature,
        )
        standalone, standalone_expected = create_collection_batch_standalone_shapekey_mesh(
            collection=collection,
            helper_collection=helper_collection,
            exporter_consts=exporter_consts,
            prefix=prefix,
            location=(x + 2.3, 0.0, z + 2.6),
        )

        if template_group_data is None:
            template_group_data = {
                "root": root.data,
                "face_main": face_main.data,
                "face_eyes": face_eyes.data,
            }
        else:
            root.data = template_group_data["root"]
            face_main.data = template_group_data["face_main"]
            face_eyes.data = template_group_data["face_eyes"]

        if template_standalone_data is None:
            template_standalone_data = standalone.data
        else:
            standalone.data = template_standalone_data

        groups.append(
            {
                "collection_name": collection.name,
                "root_name": root.name,
                "standalone_name": standalone.name,
                "face_main_name": face_main.name,
                "root_expected": root_expected,
                "standalone_expected": standalone_expected,
            }
        )

    disable_all_mirror_merge()
    return groups


def create_collection_batch_shared_data_hidden_lr_scene(change_base_settings):
    groups = create_collection_batch_shared_data_scene(change_base_settings)
    for group in groups:
        standalone = bpy.data.objects[group["standalone_name"]]
        hide_vertices_by_axis(standalone, axis='X', threshold=0.0, hide_positive=True)
    return groups


def export_selected_scene(
    func_execute_main_module,
    filepath,
    enable_auto_merge,
    enable_apply_modifiers_with_shapekeys=False,
    enable_subtract_base_shapekey=False,
    operator_overrides=None,
):
    operator = ExportOperatorStub(
        filepath=filepath,
        enable_auto_merge=enable_auto_merge,
        enable_apply_modifiers_with_shapekeys=enable_apply_modifiers_with_shapekeys,
        enable_subtract_base_shapekey=enable_subtract_base_shapekey,
    )
    if operator_overrides:
        for key, value in operator_overrides.items():
            setattr(operator, key, value)
    log(f"Starting export: {filepath} (enable_auto_merge={enable_auto_merge})")

    if bpy.ops.ed.undo_push.poll():
        bpy.ops.ed.undo_push(message="Change base export test")
    else:
        raise RuntimeError("Undo push is not available in this Blender context")

    result = func_execute_main_module.execute_main(operator, bpy.context)
    if result is None:
        raise AssertionError("Export result is None")
    if operator.batch_mode in ('OFF', 'SCENE'):
        if not os.path.exists(filepath):
            raise AssertionError(f"Export file was not created: {filepath}")
    elif not result.exported_files:
        raise AssertionError(
            f"Batch export did not produce any files. batch_mode={operator.batch_mode}"
        )

    log(
        f"Export completed. Files={result.exported_files} "
        f"Warnings={result.warnings} Errors={result.errors}"
    )

    if bpy.ops.ed.undo_push.poll():
        bpy.ops.ed.undo_push(message="Restore test scene")
        bpy.ops.ed.undo()
    else:
        raise RuntimeError("Undo restore is not available in this Blender context")

    return operator, result


def validate_subtract_base_progress_includes_object_details():
    log("Validating subtract-base progress includes object details")
    modules = load_required_modules()
    reset_scene()

    first_obj, _ = create_subtract_base_export_object()
    first_obj.name = "ExportMesh_A"
    first_obj.data.name = "ExportMeshData_A"

    second_obj, _ = create_subtract_base_export_object()
    second_obj.location.x += 3.0
    second_obj.name = "ExportMesh_B"
    second_obj.data.name = "ExportMeshData_B"

    select_objects([first_obj, second_obj], active=first_obj)

    filepath = os.path.join(OUTPUT_DIR, "subtract_base_progress_probe.fbx")
    remove_file_if_exists(filepath)

    operator = ExportOperatorStub(
        filepath=filepath,
        enable_auto_merge=False,
        enable_subtract_base_shapekey=True,
    )

    if bpy.ops.ed.undo_push.poll():
        bpy.ops.ed.undo_push(message="Subtract base progress test")
    else:
        raise RuntimeError("Undo push is not available in this Blender context")

    subtract_progress = []
    try:
        generator = modules["func_execute_main"].execute_main_iter(operator, bpy.context)
        while True:
            try:
                progress = next(generator)
            except StopIteration as stop:
                result = stop.value
                break
            if progress.phase == "subtract_base" and progress.object_name:
                subtract_progress.append({
                    "message": progress.message,
                    "object_name": progress.object_name,
                    "current": progress.current_object_index,
                    "total": progress.total_objects,
                    "progress": progress.progress,
                })
        if result is None:
            raise AssertionError("subtract-base progress test returned no result")
        if not result.exported_files:
            raise AssertionError("subtract-base progress test produced no exported files")
    finally:
        if bpy.ops.ed.undo_push.poll():
            bpy.ops.ed.undo_push(message="Restore subtract base progress test scene")
            bpy.ops.ed.undo()

    expected_names = ["ExportMesh_A", "ExportMesh_B"]
    observed_names = [snapshot["object_name"] for snapshot in subtract_progress]
    if observed_names != expected_names:
        raise AssertionError(
            f"subtract-base progress should report each object in order. "
            f"actual={subtract_progress} expected_names={expected_names}"
        )

    expected_pairs = [(1, 2), (2, 2)]
    observed_pairs = [(snapshot["current"], snapshot["total"]) for snapshot in subtract_progress]
    if observed_pairs != expected_pairs:
        raise AssertionError(
            f"subtract-base progress should include current/total counts. "
            f"actual={subtract_progress} expected_pairs={expected_pairs}"
        )

    observed_progress = [snapshot["progress"] for snapshot in subtract_progress]
    expected_progress = [0.555, 0.5585]
    if any(abs(actual - expected) > 1e-6 for actual, expected in zip(observed_progress, expected_progress)):
        raise AssertionError(
            f"subtract-base progress should start each object at its segment boundary. "
            f"actual={subtract_progress} expected_progress={expected_progress}"
        )


def import_fbx(filepath):
    reset_scene()
    ensure_addon_enabled(FBX_MODULE)
    log(f"Importing FBX for verification: {filepath}")
    result = bpy.ops.import_scene.fbx(filepath=filepath)
    if 'FINISHED' not in result:
        raise RuntimeError(f"FBX import failed: {result}")
    imported_meshes = {
        obj.name: obj
        for obj in bpy.context.scene.objects
        if obj.type == 'MESH'
    }
    log(f"Imported mesh objects: {sorted(imported_meshes.keys())}")
    return imported_meshes


def assert_original_scene_restored(expected_settings):
    export_obj = bpy.data.objects.get("ExportMesh")
    if export_obj is None:
        raise AssertionError("Original ExportMesh was not restored after undo")

    assert_shape_key_names(export_obj, ["Basis", "ExportBasis", "Blink"])
    assert_shape_key_relative_keys_valid(export_obj)
    assert_coords_close(
        get_shape_key_coords(export_obj, "Basis"),
        expected_settings["basis"],
        "restored Basis",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "ExportBasis"),
        expected_settings["export_basis"],
        "restored ExportBasis",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "Blink"),
        expected_settings["blink"],
        "restored Blink",
    )

    modules = load_required_modules()
    restored_settings = modules["change_base_settings"].get_change_base_settings(export_obj)
    if restored_settings != expected_settings["change_base_settings"]:
        raise AssertionError(
            f"Restored change-base settings mismatch. "
            f"actual={restored_settings} expected={expected_settings['change_base_settings']}"
        )

    log("Original scene was restored after undo")


def assert_original_scene_restored_with_standalone_target(expected_settings):
    export_obj = bpy.data.objects.get("ExportMesh")
    if export_obj is None:
        raise AssertionError("Original ExportMesh was not restored after undo")

    assert_shape_key_names(export_obj, ["Basis", "ExportBasis", "Blink", "Frown"])
    assert_shape_key_relative_keys_valid(export_obj)
    assert_coords_close(
        get_shape_key_coords(export_obj, "Basis"),
        expected_settings["basis"],
        "restored standalone-target Basis",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "ExportBasis"),
        expected_settings["export_basis"],
        "restored standalone-target ExportBasis",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "Blink"),
        expected_settings["blink"],
        "restored standalone-target Blink",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "Frown"),
        expected_settings["frown"],
        "restored standalone-target Frown",
    )

    modules = load_required_modules()
    restored_settings = modules["change_base_settings"].get_change_base_settings(export_obj)
    if restored_settings != expected_settings["change_base_settings"]:
        raise AssertionError(
            f"Restored standalone-target settings mismatch. "
            f"actual={restored_settings} expected={expected_settings['change_base_settings']}"
        )

    log("Original standalone-target scene was restored after undo")


def assert_original_subtract_base_scene_restored(expected_settings):
    export_obj = bpy.data.objects.get("ExportMesh")
    if export_obj is None:
        raise AssertionError("Original ExportMesh was not restored after undo")

    assert_shape_key_names(
        export_obj,
        ["Basis", "Smile", "Look_Down@BASE:Smile", "Look_Up@BASE:Smile"],
    )
    assert_shape_key_relative_keys_valid(export_obj)
    assert_coords_close(
        get_shape_key_coords(export_obj, "Basis"),
        expected_settings["basis"],
        "restored subtract-base Basis",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "Smile"),
        expected_settings["smile"],
        "restored subtract-base Smile",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "Look_Down@BASE:Smile"),
        expected_settings["look_down_composite"],
        "restored subtract-base Look_Down composite",
    )
    assert_coords_close(
        get_shape_key_coords(export_obj, "Look_Up@BASE:Smile"),
        expected_settings["look_up_composite"],
        "restored subtract-base Look_Up composite",
    )

    log("Original subtract-base scene was restored after undo")


def assert_imported_change_base_result(imported_obj, expected_settings, extra_zero_vertex_count=0):
    assert_shape_key_names(imported_obj, ["Basis", "OriginalBasis", "Blink"])
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported Basis matches mesh vertices",
    )

    imported_basis = get_shape_key_coords(imported_obj, "Basis")
    imported_original_basis = get_shape_key_coords(imported_obj, "OriginalBasis")
    imported_blink = get_shape_key_coords(imported_obj, "Blink")

    imported_basis_to_original_lengths = get_delta_lengths(
        imported_basis,
        imported_original_basis,
    )
    imported_blink_to_basis_lengths = get_delta_lengths(
        imported_blink,
        imported_basis,
    )

    expected_basis_to_original_lengths = list(expected_settings["basis_to_export_delta_lengths"])
    expected_blink_to_basis_lengths = list(expected_settings["blink_to_basis_delta_lengths"])
    if extra_zero_vertex_count > 0:
        expected_basis_to_original_lengths.extend([0.0] * extra_zero_vertex_count)
        expected_blink_to_basis_lengths.extend([0.0] * extra_zero_vertex_count)

    assert_float_multiset_close(
        imported_basis_to_original_lengths,
        expected_basis_to_original_lengths,
        "imported Basis vs OriginalBasis delta lengths",
    )
    assert_float_multiset_close(
        imported_blink_to_basis_lengths,
        expected_blink_to_basis_lengths,
        "imported Blink vs Basis delta lengths",
    )

    log("Imported FBX preserved expected Basis/reverse shape key geometry")


def assert_imported_change_base_standalone_result(imported_obj, expected_settings):
    assert_shape_key_names(imported_obj, ["Basis", "OriginalBasis", "Blink", "Frown"])
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported standalone-target Basis matches mesh vertices",
    )

    imported_basis = get_shape_key_coords(imported_obj, "Basis")
    imported_original_basis = get_shape_key_coords(imported_obj, "OriginalBasis")
    imported_blink = get_shape_key_coords(imported_obj, "Blink")
    imported_frown = get_shape_key_coords(imported_obj, "Frown")

    assert_float_multiset_close(
        get_delta_lengths(imported_basis, imported_original_basis),
        expected_settings["basis_to_export_delta_lengths"],
        "imported standalone-target Basis vs OriginalBasis delta lengths",
    )
    assert_float_multiset_close(
        get_delta_lengths(imported_blink, imported_basis),
        expected_settings["blink_to_export_basis_delta_lengths"],
        "imported standalone-target Blink vs Basis delta lengths",
    )
    assert_float_multiset_close(
        get_delta_lengths(imported_frown, imported_basis),
        expected_settings["frown_to_basis_delta_lengths"],
        "imported standalone-target Frown vs Basis delta lengths",
    )

    log("Imported FBX preserved per-shape standalone and reverse-required targets")


def assert_shape_key_name_set(obj, required_names, forbidden_names=()):
    actual_names = []
    if obj.data.shape_keys is not None:
        actual_names = [key.name for key in obj.data.shape_keys.key_blocks]
    log(
        f"Shape keys on '{obj.name}': "
        f"count={len(actual_names)} names={actual_names}"
    )

    missing = [name for name in required_names if name not in actual_names]
    if missing:
        raise AssertionError(
            f"Missing shape keys on '{obj.name}': {missing}. actual={actual_names}"
        )

    unexpected = [name for name in forbidden_names if name in actual_names]
    if unexpected:
        raise AssertionError(
            f"Unexpected shape keys on '{obj.name}': {unexpected}. actual={actual_names}"
        )


def assert_shape_key_has_nonzero_delta(obj, shape_key_name, tolerance=1e-5):
    basis_coords = get_shape_key_coords(obj, "Basis")
    target_coords = get_shape_key_coords(obj, shape_key_name)
    delta_lengths = get_delta_lengths(target_coords, basis_coords)
    max_delta = max(delta_lengths) if delta_lengths else 0.0
    if max_delta <= tolerance:
        raise AssertionError(
            f"Shape key '{shape_key_name}' on '{obj.name}' has no visible delta from Basis. "
            f"max_delta={max_delta}"
        )


def assert_shape_key_delta_signature(obj, shape_key_name, expected_signature, basis_name="Basis"):
    actual_signature = get_delta_length_signature(
        get_shape_key_coords(obj, shape_key_name),
        get_shape_key_coords(obj, basis_name),
    )
    if actual_signature != expected_signature:
        raise AssertionError(
            f"Shape key '{shape_key_name}' on '{obj.name}' delta signature mismatch. "
            f"actual={actual_signature} expected={expected_signature}"
        )


def assert_imported_as_default_with_other_as_result(imported_obj, expected_settings):
    assert_shape_key_names(imported_obj, ["Basis", "Smile", "Eyes_Up"])
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported Basis matches mesh vertices",
    )

    basis_to_smile_lengths = get_delta_lengths(
        get_shape_key_coords(imported_obj, "Basis"),
        get_shape_key_coords(imported_obj, "Smile"),
    )
    eyes_up_to_basis_lengths = get_delta_lengths(
        get_shape_key_coords(imported_obj, "Eyes_Up"),
        get_shape_key_coords(imported_obj, "Basis"),
    )

    assert_float_multiset_close(
        basis_to_smile_lengths,
        expected_settings["basis_to_default_delta_lengths"],
        "imported Basis vs Smile delta lengths",
    )
    assert_float_multiset_close(
        eyes_up_to_basis_lengths,
        expected_settings["eyes_up_to_basis_delta_lengths"],
        "imported Eyes_Up vs Basis delta lengths",
    )

    log("Imported FBX preserved %AS%Default and %AS%Eyes_Up layering")


def assert_imported_parent_child_mixed_shapekey_result(imported_obj, expected):
    assert_shape_key_name_set(
        imported_obj,
        required_names=expected["required_names"],
        forbidden_names=expected["forbidden_names"],
    )
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported mixed parent-child Basis matches mesh vertices",
    )

    for shape_key_name in expected["nonzero_names"]:
        assert_shape_key_has_nonzero_delta(imported_obj, shape_key_name)

    log("Imported FBX preserved parent/child mixed regular and %AS% shape keys")


def assert_imported_subtract_base_result(imported_obj, expected_settings):
    assert_shape_key_names(imported_obj, ["Basis", "Smile", "Look_Down", "Look_Up"])
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported subtract-base Basis matches mesh vertices",
    )

    smile_to_basis_lengths = get_delta_lengths(
        get_shape_key_coords(imported_obj, "Smile"),
        get_shape_key_coords(imported_obj, "Basis"),
    )
    look_down_to_basis_lengths = get_delta_lengths(
        get_shape_key_coords(imported_obj, "Look_Down"),
        get_shape_key_coords(imported_obj, "Basis"),
    )
    look_up_to_basis_lengths = get_delta_lengths(
        get_shape_key_coords(imported_obj, "Look_Up"),
        get_shape_key_coords(imported_obj, "Basis"),
    )

    assert_float_multiset_close(
        smile_to_basis_lengths,
        expected_settings["smile_to_basis_delta_lengths"],
        "imported Smile vs Basis delta lengths",
    )
    assert_float_multiset_close(
        look_down_to_basis_lengths,
        expected_settings["look_down_to_smile_delta_lengths"],
        "imported Look_Down vs Basis delta lengths",
    )
    assert_float_multiset_close(
        look_up_to_basis_lengths,
        expected_settings["look_up_to_smile_delta_lengths"],
        "imported Look_Up vs Basis delta lengths",
    )

    log("Imported FBX preserved subtract-base shape key geometry")


def assert_imported_automerge_modifier_stack_stress_result(imported_obj, expected):
    assert_shape_key_name_set(
        imported_obj,
        required_names=expected["required_names"],
        forbidden_names=expected["forbidden_names"],
    )
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported stress Basis matches mesh vertices",
    )

    for shape_key_name in expected.get("nonzero_names", ("Smile", "Look_Down", "Look_Up", "Eyes_Smile")):
        assert_shape_key_has_nonzero_delta(imported_obj, shape_key_name)

    for shape_key_name, expected_signature in expected.get("delta_signatures", {}).items():
        assert_shape_key_delta_signature(imported_obj, shape_key_name, expected_signature)

    log("Imported FBX preserved modifier-stack stress shape keys without Default")


def assert_imported_collection_batch_standalone_result(imported_obj, expected):
    assert_shape_key_name_set(
        imported_obj,
        required_names=expected["required_names"],
        forbidden_names=expected["forbidden_names"],
    )
    assert_shape_key_relative_keys_valid(imported_obj)
    assert_coords_close(
        get_shape_key_coords(imported_obj, "Basis"),
        get_mesh_vertex_coords(imported_obj),
        "imported collection-batch standalone Basis matches mesh vertices",
    )

    for shape_key_name in expected["nonzero_names"]:
        assert_shape_key_has_nonzero_delta(imported_obj, shape_key_name)

    log("Imported collection-batch standalone mesh kept LR-separated shape keys")


def remove_file_if_exists(filepath):
    if os.path.isfile(filepath):
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass


def get_extra_vertex_count(imported_obj, expected_settings):
    extra_vertex_count = len(imported_obj.data.vertices) - len(expected_settings["basis"])
    if extra_vertex_count < 0:
        raise AssertionError(
            f"Imported mesh has fewer vertices than expected base mesh. "
            f"actual={len(imported_obj.data.vertices)} expected_base={len(expected_settings['basis'])}"
        )
    return extra_vertex_count


def assert_imported_change_base_result_after_merge(imported_obj, expected_settings):
    extra_vertex_count = get_extra_vertex_count(imported_obj, expected_settings)
    assert_imported_change_base_result(
        imported_obj,
        expected_settings,
        extra_zero_vertex_count=extra_vertex_count,
    )


def run_basic_scenario():
    log("Running basic change-base export scenario")
    modules = load_required_modules()
    reset_scene()

    export_obj, expected_settings = create_shape_key_export_object_via_ui(modules["change_base_settings"])
    assign_merge_group(export_obj)
    select_objects([export_obj], active=export_obj)

    filepath = os.path.join(OUTPUT_DIR, "change_base_basic.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    assert_original_scene_restored(expected_settings)

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != ["ExportMesh"]:
        raise AssertionError(
            f"Unexpected imported meshes for basic scenario: {sorted(imported_meshes.keys())}"
        )
    assert_imported_change_base_result(imported_meshes["ExportMesh"], expected_settings)


def run_basic_standalone_target_scenario():
    log("Running per-shape standalone change-base export scenario")
    modules = load_required_modules()
    reset_scene()

    export_obj, expected_settings = create_shape_key_export_object_via_ui_with_standalone_target(
        modules["change_base_settings"]
    )
    assign_merge_group(export_obj)
    select_objects([export_obj], active=export_obj)

    filepath = os.path.join(OUTPUT_DIR, "change_base_standalone_target.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    assert_original_scene_restored_with_standalone_target(expected_settings)

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != ["ExportMesh"]:
        raise AssertionError(
            f"Unexpected imported meshes for standalone-target scenario: {sorted(imported_meshes.keys())}"
        )
    assert_imported_change_base_standalone_result(imported_meshes["ExportMesh"], expected_settings)


def run_automerge_scenario():
    log("Running AutoMerge + change-base export scenario")
    modules = load_required_modules()
    reset_scene()

    export_obj, expected_settings = create_shape_key_export_object(modules["change_base_settings"])
    assign_merge_group(export_obj)
    merge_child, expected_vertex_count = create_automerge_child(export_obj)
    select_objects([export_obj, merge_child], active=export_obj)

    filepath = os.path.join(OUTPUT_DIR, "change_base_with_automerge.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    assert_original_scene_restored(expected_settings)

    restored_root = bpy.data.objects.get("ExportMesh")
    restored_child = bpy.data.objects.get("MergeChild")
    if restored_root is None or restored_child is None:
        raise AssertionError("AutoMerge test scene hierarchy was not restored after undo")
    if not restored_root.get("MergeGroup"):
        raise AssertionError("ExportMesh lost MergeGroup flag after undo")

    imported_meshes = import_fbx(filepath)
    imported_names = sorted(imported_meshes.keys())
    if imported_names != ["ExportMesh"]:
        raise AssertionError(f"Unexpected imported meshes: {imported_names}")
    if "MergeChild" in imported_meshes:
        raise AssertionError(f"MergeChild should have been merged away, imported meshes: {imported_names}")

    merge_root_import = imported_meshes["ExportMesh"]
    if len(merge_root_import.data.vertices) < expected_vertex_count:
        raise AssertionError(
            f"ExportMesh vertex count too small after AutoMerge. "
            f"actual={len(merge_root_import.data.vertices)} expected>={expected_vertex_count}"
        )

    assert_imported_change_base_result_after_merge(imported_meshes["ExportMesh"], expected_settings)
    log("AutoMerge path processed grouped root and preserved change-base export result")


def run_automerge_children_default_scenario():
    log("Running AutoMerge child %AS%Default change-base scenario")
    modules = load_required_modules()
    reset_scene()

    merge_root, merge_children, expected = create_automerge_children_with_default_change_base(
        modules["change_base_settings"]
    )
    select_objects([merge_root, *merge_children], active=merge_root)

    filepath = os.path.join(OUTPUT_DIR, "change_base_child_defaults_with_automerge.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    restored_root = bpy.data.objects.get("MergeRoot")
    restored_child_a = bpy.data.objects.get("MergeChildA")
    restored_child_b = bpy.data.objects.get("MergeChildB")
    if restored_root is None or restored_child_a is None or restored_child_b is None:
        raise AssertionError("AutoMerge child %AS%Default test scene was not restored after undo")

    for child, reverse_name in zip((restored_child_a, restored_child_b), expected["reverse_names"]):
        restored_settings = modules["change_base_settings"].get_change_base_settings(child)
        expected_settings = [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": reverse_name,
            }
        ]
        if restored_settings != expected_settings:
            raise AssertionError(
                f"Restored child settings mismatch on '{child.name}'. "
                f"actual={restored_settings} expected={expected_settings}"
            )

    imported_meshes = import_fbx(filepath)
    imported_names = sorted(imported_meshes.keys())
    if imported_names != ["MergeRoot"]:
        raise AssertionError(
            f"Unexpected imported meshes for child %AS%Default scenario: {imported_names}"
        )

    merged_obj = imported_meshes["MergeRoot"]
    assert_shape_key_name_set(
        merged_obj,
        required_names=["Basis", *expected["reverse_names"]],
        forbidden_names=["Default"],
    )
    for reverse_name in expected["reverse_names"]:
        assert_shape_key_has_nonzero_delta(merged_obj, reverse_name)

    log("AutoMerge child %AS%Default path removed Default and kept each reverse shape key")


def run_automerge_default_with_other_as_scenario():
    log("Running AutoMerge %AS%Default + other %AS% scenario")
    modules = load_required_modules()
    reset_scene()

    export_obj, expected_helper_obj, expected = create_automerge_as_default_with_other_modifier(
        modules["change_base_settings"],
        modules["func_apply_as_shapekey"],
    )
    expected_helper_name = expected_helper_obj.name
    select_objects([export_obj], active=export_obj)

    filepath = os.path.join(OUTPUT_DIR, "change_base_default_with_other_as.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    if bpy.data.objects.get("ExportMesh") is None:
        raise AssertionError("Original ExportMesh was not restored after undo")
    if modules["change_base_settings"].get_change_base_settings(bpy.data.objects["ExportMesh"]) != [
        {
            "source_shapekey_name": "Default",
            "reverse_shapekey_name": "Smile",
        }
    ]:
        raise AssertionError("Change-base settings were not restored for %AS%Default scenario")

    if bpy.data.objects.get(expected_helper_name) is None:
        raise AssertionError("Expected helper object was not restored after undo")

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != ["ExportMesh"]:
        raise AssertionError(
            f"Unexpected imported meshes for %AS%Default scenario: {sorted(imported_meshes.keys())}"
        )
    assert_imported_as_default_with_other_as_result(imported_meshes["ExportMesh"], expected)


def run_subtract_base_scenario():
    log("Running subtract-base export scenario")
    modules = load_required_modules()
    reset_scene()

    export_obj, expected_settings = create_subtract_base_export_object()
    select_objects([export_obj], active=export_obj)

    filepath = os.path.join(OUTPUT_DIR, "subtract_base_basic.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=False,
        enable_subtract_base_shapekey=True,
    )

    assert_original_subtract_base_scene_restored(expected_settings)

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != ["ExportMesh"]:
        raise AssertionError(
            f"Unexpected imported meshes for subtract-base scenario: {sorted(imported_meshes.keys())}"
        )
    assert_imported_subtract_base_result(imported_meshes["ExportMesh"], expected_settings)


def run_automerge_parent_child_mixed_shapekey_scenario():
    log("Running AutoMerge parent-child mixed shape key scenario")
    modules = load_required_modules()
    reset_scene()

    root, child, expected = create_automerge_parent_child_mixed_shapekey_scene(
        modules["change_base_settings"]
    )
    select_objects([root, child], active=root)

    filepath = os.path.join(OUTPUT_DIR, "automerge_parent_child_mixed_shapekeys.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    restored_root = bpy.data.objects.get("MixedRoot")
    restored_child = bpy.data.objects.get("MixedChild")
    if restored_root is None or restored_child is None:
        raise AssertionError("Mixed parent-child scene was not restored after undo")

    restored_settings = modules["change_base_settings"].get_change_base_settings(restored_child)
    expected_settings = [
        {
            "source_shapekey_name": "Default",
            "reverse_shapekey_name": "Smile",
        }
    ]
    if restored_settings != expected_settings:
        raise AssertionError(
            f"Restored MixedChild settings mismatch. "
            f"actual={restored_settings} expected={expected_settings}"
        )

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != ["MixedRoot"]:
        raise AssertionError(
            f"Unexpected imported meshes for mixed parent-child scenario: {sorted(imported_meshes.keys())}"
        )
    assert_imported_parent_child_mixed_shapekey_result(imported_meshes["MixedRoot"], expected)


def run_automerge_modifier_stack_stress_scenario():
    log("Running AutoMerge modifier-stack stress scenario")
    modules = load_required_modules()
    reset_scene()

    merge_root, merge_children, expected = create_automerge_modifier_stack_stress_scene(
        modules["change_base_settings"]
    )
    select_objects([merge_root, *merge_children], active=merge_root)

    filepath = os.path.join(OUTPUT_DIR, "automerge_modifier_stack_stress.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    restored_face_main = bpy.data.objects.get("FaceMain")
    if restored_face_main is None:
        raise AssertionError("FaceMain was not restored after undo in stress scenario")
    restored_settings = modules["change_base_settings"].get_change_base_settings(restored_face_main)
    expected_settings = [
        {
            "source_shapekey_name": "Default",
            "reverse_shapekey_name": "Smile",
        }
    ]
    if restored_settings != expected_settings:
        raise AssertionError(
            f"Restored FaceMain settings mismatch. "
            f"actual={restored_settings} expected={expected_settings}"
        )

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != ["MergeRoot"]:
        raise AssertionError(
            f"Unexpected imported meshes for modifier-stack stress scenario: {sorted(imported_meshes.keys())}"
        )
    assert_imported_automerge_modifier_stack_stress_result(imported_meshes["MergeRoot"], expected)


def run_automerge_crash_log_regression_scenario():
    log("Running AutoMerge crash-log regression scenario")
    modules = load_required_modules()
    reset_scene()

    merge_root, merge_children, expected = create_automerge_crash_log_regression_scene(
        modules["change_base_settings"]
    )
    select_objects([merge_root, *merge_children], active=merge_root)

    filepath = os.path.join(OUTPUT_DIR, "automerge_crash_log_regression.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    restored_face_main = bpy.data.objects.get(expected["face_main_name"])
    if restored_face_main is None:
        raise AssertionError(f"{expected['face_main_name']} was not restored after undo in regression scenario")

    restored_settings = modules["change_base_settings"].get_change_base_settings(restored_face_main)
    expected_settings = [
        {
            "source_shapekey_name": "Default",
            "reverse_shapekey_name": "Smile",
        }
    ]
    if restored_settings != expected_settings:
        raise AssertionError(
            f"Restored CrashFaceMain settings mismatch. "
            f"actual={restored_settings} expected={expected_settings}"
        )

    imported_meshes = import_fbx(filepath)
    if sorted(imported_meshes.keys()) != [expected["root_name"]]:
        raise AssertionError(
            f"Unexpected imported meshes for crash-log regression scenario: {sorted(imported_meshes.keys())}"
    )
    assert_imported_automerge_modifier_stack_stress_result(imported_meshes[expected["root_name"]], expected)


def run_automerge_crash_log_multi_root_scenario():
    log("Running AutoMerge crash-log multi-root scenario")
    modules = load_required_modules()
    reset_scene()

    groups, roots, children = create_automerge_crash_log_multi_root_scene(
        modules["change_base_settings"]
    )
    select_objects([*roots, *children], active=roots[0])

    filepath = os.path.join(OUTPUT_DIR, "automerge_crash_log_multi_root.fbx")
    remove_file_if_exists(filepath)
    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
    )

    for group in groups:
        face_main_name = group["expected"]["face_main_name"]
        restored_face_main = bpy.data.objects.get(face_main_name)
        if restored_face_main is None:
            raise AssertionError(f"{face_main_name} was not restored after undo in multi-root scenario")

        restored_settings = modules["change_base_settings"].get_change_base_settings(restored_face_main)
        expected_settings = [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ]
        if restored_settings != expected_settings:
            raise AssertionError(
                f"Restored {face_main_name} settings mismatch. "
                f"actual={restored_settings} expected={expected_settings}"
            )

    imported_meshes = import_fbx(filepath)
    expected_root_names = sorted(group["expected"]["root_name"] for group in groups)
    imported_names = sorted(imported_meshes.keys())
    if imported_names != expected_root_names:
        raise AssertionError(
            f"Unexpected imported meshes for crash-log multi-root scenario: {imported_names}"
        )

    for group in groups:
        expected = group["expected"]
        assert_imported_automerge_modifier_stack_stress_result(
            imported_meshes[expected["root_name"]],
            expected,
        )


def run_collection_batch_shared_data_crash_scenario():
    log("Running Collection BatchExport shared-data crash scenario")
    modules = load_required_modules()
    reset_scene()

    groups = create_collection_batch_shared_data_scene(modules["change_base_settings"])
    roots = [bpy.data.objects[group["root_name"]] for group in groups]
    select_objects(roots, active=roots[0])

    filepath = os.path.join(OUTPUT_DIR, "collection_batch_shared_data_crash_regression.fbx")
    remove_file_if_exists(filepath)
    for group in groups:
        remove_file_if_exists(os.path.join(OUTPUT_DIR, f"{group['collection_name']}.fbx"))

    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
        enable_subtract_base_shapekey=True,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "enable_separate_lr_shapekey": True,
            "use_mesh_modifiers": True,
        },
    )

    for group in groups:
        restored_face_main = bpy.data.objects.get(group["face_main_name"])
        if restored_face_main is None:
            raise AssertionError(f"{group['face_main_name']} was not restored after batch export undo")

        restored_settings = modules["change_base_settings"].get_change_base_settings(restored_face_main)
        expected_settings = [
            {
                "source_shapekey_name": "Default",
                "reverse_shapekey_name": "Smile",
            }
        ]
        if restored_settings != expected_settings:
            raise AssertionError(
                f"Restored {group['face_main_name']} settings mismatch. "
                f"actual={restored_settings} expected={expected_settings}"
            )

    for group in groups:
        export_path = os.path.join(OUTPUT_DIR, f"{group['collection_name']}.fbx")
        if not os.path.exists(export_path):
            raise AssertionError(f"Batch export file was not created: {export_path}")

    for group in (groups[0], groups[-1]):
        export_path = os.path.join(OUTPUT_DIR, f"{group['collection_name']}.fbx")
        imported_meshes = import_fbx(export_path)
        imported_names = sorted(imported_meshes.keys())
        expected_names = sorted([group["root_name"], group["standalone_name"]])
        if imported_names != expected_names:
            raise AssertionError(
                f"Unexpected imported meshes for collection batch scenario. "
                f"collection={group['collection_name']} actual={imported_names} expected={expected_names}"
            )

        assert_imported_automerge_modifier_stack_stress_result(
            imported_meshes[group["root_name"]],
            group["root_expected"],
        )
        assert_imported_collection_batch_standalone_result(
            imported_meshes[group["standalone_name"]],
            group["standalone_expected"],
        )


def run_collection_batch_hidden_lr_reveal_crash_scenario():
    log("Running Collection BatchExport hidden-LR reveal crash scenario")
    modules = load_required_modules()
    reset_scene()

    groups = create_collection_batch_shared_data_hidden_lr_scene(modules["change_base_settings"])
    roots = [bpy.data.objects[group["root_name"]] for group in groups]
    select_objects(roots, active=roots[0])

    filepath = os.path.join(OUTPUT_DIR, "collection_batch_hidden_lr_reveal_crash_regression.fbx")
    remove_file_if_exists(filepath)
    for group in groups:
        remove_file_if_exists(os.path.join(OUTPUT_DIR, f"{group['collection_name']}.fbx"))

    export_selected_scene(
        modules["func_execute_main"],
        filepath=filepath,
        enable_auto_merge=True,
        enable_apply_modifiers_with_shapekeys=True,
        enable_subtract_base_shapekey=True,
        operator_overrides={
            "use_selection": False,
            "batch_mode": "COLLECTION",
            "batch_filename_format": "{batch}",
            "use_batch_own_dir": False,
            "enable_separate_lr_shapekey": True,
            "use_mesh_modifiers": True,
        },
    )

    for group in (groups[0], groups[-1]):
        export_path = os.path.join(OUTPUT_DIR, f"{group['collection_name']}.fbx")
        imported_meshes = import_fbx(export_path)
        assert_imported_collection_batch_standalone_result(
            imported_meshes[group["standalone_name"]],
            group["standalone_expected"],
        )


def run_selected_scenarios(mode):
    ensure_output_dir()

    scenarios = {
        "basic": run_basic_scenario,
        "basic_standalone_target": run_basic_standalone_target_scenario,
        "subtract_base_progress": validate_subtract_base_progress_includes_object_details,
        "automerge": run_automerge_scenario,
        "automerge_children_default": run_automerge_children_default_scenario,
        "automerge_default_with_other_as": run_automerge_default_with_other_as_scenario,
        "subtract_base": run_subtract_base_scenario,
        "automerge_parent_child_mixed_shapekey": run_automerge_parent_child_mixed_shapekey_scenario,
        "automerge_modifier_stack_stress": run_automerge_modifier_stack_stress_scenario,
        "automerge_crash_log_regression": run_automerge_crash_log_regression_scenario,
        "automerge_crash_log_multi_root": run_automerge_crash_log_multi_root_scenario,
        "collection_batch_shared_data_crash": run_collection_batch_shared_data_crash_scenario,
        "collection_batch_hidden_lr_reveal_crash": run_collection_batch_hidden_lr_reveal_crash_scenario,
    }

    if mode == "all":
        selected = [
            "basic",
            "basic_standalone_target",
            "subtract_base_progress",
            "automerge",
            "automerge_children_default",
            "automerge_default_with_other_as",
            "subtract_base",
            "automerge_modifier_stack_stress",
            "automerge_crash_log_regression",
            "collection_batch_shared_data_crash",
        ]
    else:
        if mode not in scenarios:
            raise ValueError(f"Unknown scenario mode: {mode}")
        selected = [mode]

    passed = 0
    failed = 0
    failures = []

    for scenario_name in selected:
        log("=" * 72)
        log(f"Scenario start: {scenario_name}")
        try:
            scenarios[scenario_name]()
            passed += 1
            log(f"Scenario PASS: {scenario_name}")
        except Exception as exc:
            failed += 1
            failures.append((scenario_name, exc))
            log(f"Scenario FAIL: {scenario_name}")
            traceback.print_exc()

    log("=" * 72)
    log(f"Scenario summary: passed={passed} failed={failed}")
    log(f"Output directory: {OUTPUT_DIR}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    run_selected_scenarios("all")
