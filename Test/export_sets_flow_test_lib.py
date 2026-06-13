import importlib
import os
import sys
import traceback

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTER_ADDON_DIR = os.path.dirname(SCRIPT_DIR)
ADDONS_DIR = os.path.dirname(EXPORTER_ADDON_DIR)

EXPORTER_MODULE = "BlenderAddon-MizoresCustomExporter"
AUTOMERGE_MODULE = "BlenderAddon-AutoMerge"
SHAPEKEYS_UTIL_MODULE = "BlenderAddon_ShapeKeysUtil"
FBX_MODULE = "io_scene_fbx"

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_export_sets_flow")
STATUS_PATH = os.path.join(OUTPUT_DIR, "modal_status.txt")
BASE_EXPORT_PATH = os.path.join(OUTPUT_DIR, "_export_sets_base.fbx")
if ADDONS_DIR not in sys.path:
    sys.path.insert(0, ADDONS_DIR)


def log(message):
    print(f"[export-sets-flow-test] {message}")


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


def get_selected_objects():
    selected = getattr(bpy.context, "selected_objects", None)
    if selected is not None:
        return list(selected)
    view_layer = getattr(bpy.context, "view_layer", None)
    if view_layer is not None:
        return [obj for obj in view_layer.objects if obj.select_get()]
    return []


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def remove_file_if_exists(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)


def write_status(text):
    ensure_output_dir()
    with open(STATUS_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)


def ensure_addon_enabled(module_name):
    if module_name in bpy.context.preferences.addons:
        return
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
    return {
        "op_core": importlib.import_module(
            f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.op_core"
        ),
        "preferences_scene": importlib.import_module(
            f"{EXPORTER_MODULE}.scripts.preferences_scene"
        ),
        "op_save_export_settings": importlib.import_module(
            f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.op_save_export_settings"
        ),
        "func_export_sets": importlib.import_module(
            f"{EXPORTER_MODULE}.scripts.export_sets.func_export_sets"
        ),
        "func_execute_main": importlib.import_module(
            f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.func_execute_main"
        ),
    }


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r} actual={actual!r}")


class MockOperatorProperties(dict):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        setattr(self.owner, key, value)


class MockExportOperator:
    def __init__(self, operator_rna):
        self.bl_rna = operator_rna
        self.properties = MockOperatorProperties(self)
        self.batch_mode = 'OFF'
        self.filepath = ""


def validate_export_preferences_storage():
    modules = load_required_modules()
    preferences_scene = modules["preferences_scene"]
    operator_rna = bpy.ops.export_scene.custom_export_mizore_fbx.get_rna_type()

    preferences_scene.clear_export_props()
    preferences_scene.set_prop_col_value(
        bpy.context.scene.mizore_exporter_prefs.export_int_props,
        "batch_mode",
        1,
    )

    operator = MockExportOperator(operator_rna)
    preferences_scene.load_scene_prefs(operator)
    assert_equal(operator.batch_mode, 'SCENE', "legacy batch_mode int should load as SCENE")

    preferences_scene.clear_export_props()
    operator = MockExportOperator(operator_rna)
    operator.properties["batch_mode"] = 'EXPORT_SETS'
    operator.properties["enable_auto_merge"] = False
    operator.properties["global_scale"] = 2.5
    operator.properties["scale_value_mode"] = 'KEEP_VALUE'
    operator.properties["scale_pivot"] = 'EACH_OBJECT_ORIGIN'
    operator.properties["limit_vertex_group_count"] = 8
    operator.properties["object_types"] = {'MESH', 'ARMATURE'}
    preferences_scene.save_scene_prefs(operator, ignore_key=["filepath"])

    str_prop = bpy.context.scene.mizore_exporter_prefs.export_str_props.get("batch_mode")
    scale_value_mode_prop = bpy.context.scene.mizore_exporter_prefs.export_str_props.get("scale_value_mode")
    scale_pivot_prop = bpy.context.scene.mizore_exporter_prefs.export_str_props.get("scale_pivot")
    int_prop = bpy.context.scene.mizore_exporter_prefs.export_int_props.get("batch_mode")
    bool_prop = bpy.context.scene.mizore_exporter_prefs.export_bool_props.get("enable_auto_merge")
    float_prop = bpy.context.scene.mizore_exporter_prefs.export_float_props.get("global_scale")
    int_limit_prop = bpy.context.scene.mizore_exporter_prefs.export_int_props.get("limit_vertex_group_count")
    json_prop = bpy.context.scene.mizore_exporter_prefs.export_json_props.get("object_types")
    assert_equal(str_prop.value if str_prop else None, 'EXPORT_SETS', "batch_mode should be saved as string enum")
    assert_equal(scale_value_mode_prop.value if scale_value_mode_prop else None, 'KEEP_VALUE', "scale value mode should be saved as string enum")
    assert_equal(scale_pivot_prop.value if scale_pivot_prop else None, 'EACH_OBJECT_ORIGIN', "scale pivot should be saved as string enum")
    assert_equal(int_prop, None, "batch_mode should not remain in int props")
    assert_equal(bool_prop.value if bool_prop else None, False, "bool props should be saved")
    assert_equal(float_prop.value if float_prop else None, 2.5, "float props should be saved")
    assert_equal(int_limit_prop.value if int_limit_prop else None, 8, "int props should be saved")
    assert_equal(json_prop.value if json_prop else None, '["ARMATURE", "MESH"]', "enum-flag props should be saved")

    reloaded_operator = MockExportOperator(operator_rna)
    preferences_scene.load_scene_prefs(reloaded_operator)
    assert_equal(reloaded_operator.batch_mode, 'EXPORT_SETS', "saved batch_mode should reload")
    assert_equal(reloaded_operator.enable_auto_merge, False, "saved bool should reload")
    assert_equal(reloaded_operator.global_scale, 2.5, "saved float should reload")
    assert_equal(reloaded_operator.scale_value_mode, 'KEEP_VALUE', "saved scale value mode should reload")
    assert_equal(reloaded_operator.scale_pivot, 'EACH_OBJECT_ORIGIN', "saved scale pivot should reload")
    assert_equal(reloaded_operator.limit_vertex_group_count, 8, "saved int should reload")
    assert_equal(reloaded_operator.object_types, {'MESH', 'ARMATURE'}, "saved enum-flag should reload")


def validate_export_preferences_persist_after_mainfile_reload():
    ensure_output_dir()
    modules = load_required_modules()
    preferences_scene = modules["preferences_scene"]
    save_export_settings = modules["op_save_export_settings"]

    blend_path = os.path.join(OUTPUT_DIR, "save_export_settings_persistence.blend")
    remove_file_if_exists(blend_path)

    reset_scene()

    operator = bpy.context.window_manager.operator_properties_last("export_scene.custom_export_mizore_fbx")
    operator.batch_mode = 'EXPORT_SETS'
    operator.enable_auto_merge = False
    operator.global_scale = 2.5
    operator.scale_value_mode = 'KEEP_VALUE'
    operator.scale_pivot = 'EACH_OBJECT_ORIGIN'
    operator.limit_vertex_group_count = 8
    operator.object_types = {'MESH', 'ARMATURE'}
    operator.batch_filename_format = "{collection}"
    operator.path_mode = 'COPY'
    operator.use_selection = True
    operator.mod_filter_weighted_normal = False

    save_export_settings.OBJECT_OT_mizore_save_export_settings.operator = operator
    result = bpy.ops.object.mizore_save_export_settings()
    assert_equal(result, {'FINISHED'}, "save export settings operator should succeed")

    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=False)
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    ensure_required_addons()

    modules = load_required_modules()
    preferences_scene = modules["preferences_scene"]
    reloaded_operator = bpy.context.window_manager.operator_properties_last("export_scene.custom_export_mizore_fbx")

    # セッションに残った値で通ってしまわないよう、明示的に別値へ崩してから読み込む。
    reloaded_operator.batch_mode = 'OFF'
    reloaded_operator.enable_auto_merge = True
    reloaded_operator.global_scale = 1.0
    reloaded_operator.scale_value_mode = 'NORMAL'
    reloaded_operator.scale_pivot = 'WORLD_ORIGIN'
    reloaded_operator.limit_vertex_group_count = 4
    reloaded_operator.object_types = {'EMPTY'}
    reloaded_operator.batch_filename_format = "{scene}"
    reloaded_operator.path_mode = 'AUTO'
    reloaded_operator.use_selection = False
    reloaded_operator.mod_filter_weighted_normal = True

    preferences_scene.load_scene_prefs(reloaded_operator)

    assert_equal(reloaded_operator.batch_mode, 'EXPORT_SETS', "saved batch_mode should persist across mainfile reload")
    assert_equal(reloaded_operator.enable_auto_merge, False, "saved enable_auto_merge should persist across mainfile reload")
    assert_equal(reloaded_operator.global_scale, 2.5, "saved global_scale should persist across mainfile reload")
    assert_equal(reloaded_operator.scale_value_mode, 'KEEP_VALUE', "saved scale value mode should persist across mainfile reload")
    assert_equal(reloaded_operator.scale_pivot, 'EACH_OBJECT_ORIGIN', "saved scale pivot should persist across mainfile reload")
    assert_equal(reloaded_operator.limit_vertex_group_count, 8, "saved limit_vertex_group_count should persist across mainfile reload")
    assert_equal(reloaded_operator.object_types, {'MESH', 'ARMATURE'}, "saved object_types should persist across mainfile reload")
    assert_equal(reloaded_operator.batch_filename_format, "{collection}", "saved batch filename format should persist across mainfile reload")
    assert_equal(reloaded_operator.path_mode, 'COPY', "saved path_mode should persist across mainfile reload")
    assert_equal(reloaded_operator.use_selection, True, "saved use_selection should persist across mainfile reload")
    assert_equal(reloaded_operator.mod_filter_weighted_normal, False, "saved modifier filter should persist across mainfile reload")


def validate_export_preferences_persist_on_operator_invoke():
    ensure_output_dir()
    modules = load_required_modules()
    preferences_scene = modules["preferences_scene"]
    save_export_settings = modules["op_save_export_settings"]
    op_core = modules["op_core"]

    blend_path = os.path.join(OUTPUT_DIR, "save_export_settings_invoke.blend")
    remove_file_if_exists(blend_path)

    reset_scene()

    operator = bpy.context.window_manager.operator_properties_last("export_scene.custom_export_mizore_fbx")
    operator.batch_mode = 'EXPORT_SETS'
    operator.enable_auto_merge = False
    operator.global_scale = 2.5
    operator.scale_value_mode = 'KEEP_VALUE'
    operator.scale_pivot = 'EACH_OBJECT_ORIGIN'
    operator.limit_vertex_group_count = 8
    operator.object_types = {'MESH', 'ARMATURE'}
    operator.batch_filename_format = "{collection}"
    operator.path_mode = 'COPY'
    operator.use_selection = True
    operator.mod_filter_weighted_normal = False

    save_export_settings.OBJECT_OT_mizore_save_export_settings.operator = operator
    result = bpy.ops.object.mizore_save_export_settings()
    assert_equal(result, {'FINISHED'}, "save export settings operator should succeed before invoke test")

    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=False)
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    ensure_required_addons()

    modules = load_required_modules()
    preferences_scene = modules["preferences_scene"]
    reloaded_operator = bpy.context.window_manager.operator_properties_last("export_scene.custom_export_mizore_fbx")

    reloaded_operator.batch_mode = 'OFF'
    reloaded_operator.enable_auto_merge = True
    reloaded_operator.global_scale = 1.0
    reloaded_operator.scale_value_mode = 'NORMAL'
    reloaded_operator.scale_pivot = 'WORLD_ORIGIN'
    reloaded_operator.limit_vertex_group_count = 4
    reloaded_operator.object_types = {'EMPTY'}
    reloaded_operator.batch_filename_format = "{scene}"
    reloaded_operator.path_mode = 'AUTO'
    reloaded_operator.use_selection = False
    reloaded_operator.mod_filter_weighted_normal = True

    preferences_scene.load_scene_prefs(reloaded_operator)

    assert_equal(reloaded_operator.batch_mode, 'EXPORT_SETS', "saved batch_mode should persist for invoke defaults")
    assert_equal(reloaded_operator.enable_auto_merge, False, "saved enable_auto_merge should persist for invoke defaults")
    assert_equal(reloaded_operator.global_scale, 2.5, "saved global_scale should persist for invoke defaults")
    assert_equal(reloaded_operator.scale_value_mode, 'KEEP_VALUE', "saved scale value mode should persist for invoke defaults")
    assert_equal(reloaded_operator.scale_pivot, 'EACH_OBJECT_ORIGIN', "saved scale pivot should persist for invoke defaults")
    assert_equal(reloaded_operator.limit_vertex_group_count, 8, "saved limit_vertex_group_count should persist for invoke defaults")
    assert_equal(reloaded_operator.object_types, {'MESH', 'ARMATURE'}, "saved object_types should persist for invoke defaults")
    assert_equal(reloaded_operator.batch_filename_format, "{collection}", "saved batch filename format should persist for invoke defaults")
    assert_equal(reloaded_operator.path_mode, 'COPY', "saved path_mode should persist for invoke defaults")
    assert_equal(reloaded_operator.use_selection, True, "saved use_selection should persist for invoke defaults")
    assert_equal(reloaded_operator.mod_filter_weighted_normal, False, "saved modifier filter should persist for invoke defaults")


def validate_export_set_move_operators():
    reset_scene()

    props = bpy.context.scene.mizore_export_sets

    for name in ("First", "Second", "Third"):
        export_set = props.export_sets.add()
        export_set.filename = name
    props.active_export_set_index = 1

    result = bpy.ops.scene.mizore_move_export_set(direction='UP')
    assert_equal(result, {'FINISHED'}, "move export set up should succeed")
    assert_equal([export_set.filename for export_set in props.export_sets], ["Second", "First", "Third"], "export sets should move up")
    assert_equal(props.active_export_set_index, 0, "active export set index should follow moved set")

    result = bpy.ops.scene.mizore_move_export_set(direction='DOWN')
    assert_equal(result, {'FINISHED'}, "move export set down should succeed")
    assert_equal([export_set.filename for export_set in props.export_sets], ["First", "Second", "Third"], "export sets should move down")
    assert_equal(props.active_export_set_index, 1, "active export set index should follow moved set after moving down")

    export_set = props.export_sets[props.active_export_set_index]
    for name in ("Goblin", "Sword", "Shield"):
        item = export_set.items.add()
        item.attach_to_bone = name
    export_set.active_item_index = 1

    result = bpy.ops.scene.mizore_move_export_set_item(direction='UP')
    assert_equal(result, {'FINISHED'}, "move export set item up should succeed")
    assert_equal([item.attach_to_bone for item in export_set.items], ["Sword", "Goblin", "Shield"], "export set items should move up")
    assert_equal(export_set.active_item_index, 0, "active export set item index should follow moved item")

    result = bpy.ops.scene.mizore_move_export_set_item(direction='DOWN')
    assert_equal(result, {'FINISHED'}, "move export set item down should succeed")
    assert_equal([item.attach_to_bone for item in export_set.items], ["Goblin", "Sword", "Shield"], "export set items should move down")
    assert_equal(export_set.active_item_index, 1, "active export set item index should follow moved item after moving down")


def validate_export_set_item_add_operator_does_not_copy_active_object():
    reset_scene()

    props = bpy.context.scene.mizore_export_sets
    export_set = props.export_sets.add()
    export_set.filename = "RootEdit"
    props.active_export_set_index = 0

    active_armature = _create_armature(
        "ActiveRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )
    select_objects([active_armature], active=active_armature)

    result = bpy.ops.scene.mizore_add_export_set_item()
    assert_equal(result, {'FINISHED'}, "add export set item should succeed")

    item = export_set.items[0]
    assert_equal(item.root_object, None, "new export set item should not copy the active object into root")
    assert_equal(item.armature_object, None, "new export set item should not copy the active object into armature")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_required_addons()


def deselect_all():
    for obj in get_selected_objects():
        obj.select_set(False)


def select_objects(objects, active=None):
    deselect_all()
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active or (objects[0] if objects else None)


def single_object_override(obj):
    return bpy.context.temp_override(
        active_object=obj,
        object=obj,
        selected_objects=[obj],
        selected_editable_objects=[obj],
    )


def scene_window_override(scene=None):
    window = getattr(bpy.context, "window", None)
    if window is None:
        wm = getattr(bpy.context, "window_manager", None)
        windows = getattr(wm, "windows", None)
        if windows:
            window = windows[0]
    if window is None:
        return bpy.context.temp_override()

    screen = getattr(window, "screen", None)
    area = None
    region = None
    if screen is not None:
        area = next((candidate for candidate in screen.areas if candidate.type == 'VIEW_3D'), None)
        if area is None and len(screen.areas) > 0:
            area = screen.areas[0]
    if area is not None:
        region = next((candidate for candidate in area.regions if candidate.type == 'WINDOW'), None)

    override = {
        "window": window,
        "screen": screen,
        "scene": scene or window.scene,
        "view_layer": window.view_layer,
    }
    if area is not None:
        override["area"] = area
    if region is not None:
        override["region"] = region
    return bpy.context.temp_override(**override)


def set_parent_keep_transform(child, parent):
    matrix_world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = matrix_world


def set_parent_to_bone_keep_transform(child, parent_armature, bone_name):
    matrix_world = child.matrix_world.copy()
    child.parent = parent_armature
    child.parent_type = 'BONE'
    child.parent_bone = bone_name
    child.matrix_world = matrix_world


def _create_empty(name, location):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    obj = get_active_object()
    obj.name = name
    return obj


def _rename_object_and_data(obj, name):
    obj.name = name
    if getattr(obj, "data", None) is not None:
        obj.data.name = f"{name}Data"


def _create_cube(name, location):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = get_active_object()
    _rename_object_and_data(obj, name)
    return obj


def _ensure_color_attribute(mesh, layer_name="Color"):
    color_attributes = getattr(mesh, "color_attributes", None)
    if color_attributes is None:
        raise RuntimeError(f"Mesh '{mesh.name}' does not support color attributes")

    color_attr = color_attributes.get(layer_name)
    if color_attr is None:
        color_attr = color_attributes.new(name=layer_name, type='FLOAT_COLOR', domain='CORNER')
    return color_attr


def _assign_polygon_color(obj, polygon_indices, color, layer_name="Color"):
    mesh = obj.data
    color_attr = _ensure_color_attribute(mesh, layer_name)
    color_value = tuple(float(channel) for channel in color)
    for polygon_index in polygon_indices:
        polygon = mesh.polygons[polygon_index]
        for loop_index in polygon.loop_indices:
            color_attr.data[loop_index].color = color_value


def is_fbx_leaf_bone_name(name):
    return name.endswith("_end")


def _create_cylinder(name, location, vertices=12, radius=0.2, depth=1.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = get_active_object()
    _rename_object_and_data(obj, name)
    return obj


def _create_cone(name, location, vertices=10, radius1=0.18, depth=1.1):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        depth=depth,
        location=location,
    )
    obj = get_active_object()
    _rename_object_and_data(obj, name)
    return obj


def _create_ico_sphere(name, location, subdivisions=1, radius=0.22):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=radius,
        location=location,
    )
    obj = get_active_object()
    _rename_object_and_data(obj, name)
    return obj


def _assign_merge_group(obj):
    obj["MergeGroup"] = True


def _vertex_count(obj):
    return len(obj.data.vertices)


def _create_armature(name, location, bones):
    bpy.ops.object.armature_add(enter_editmode=True, location=location)
    armature_obj = get_active_object()
    _rename_object_and_data(armature_obj, name)

    with single_object_override(armature_obj):
        edit_bones = armature_obj.data.edit_bones

        first = bones[0]
        base_bone = edit_bones[0]
        base_bone.name = first["name"]
        base_bone.head = first["head"]
        base_bone.tail = first["tail"]

        for bone_spec in bones[1:]:
            bone = edit_bones.new(bone_spec["name"])
            bone.head = bone_spec["head"]
            bone.tail = bone_spec["tail"]
            if bone_spec.get("parent"):
                bone.parent = edit_bones[bone_spec["parent"]]

        bpy.ops.object.mode_set(mode='OBJECT')
    return armature_obj


def _add_full_weight_group(obj, bone_name):
    group = obj.vertex_groups.get(bone_name)
    if group is None:
        group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, 'REPLACE')


def _add_armature_modifier(obj, armature_obj, name="Armature"):
    modifier = obj.modifiers.new(name=name, type='ARMATURE')
    modifier.object = armature_obj
    return modifier


def _set_export_sets(scene, roots, armatures):
    props = scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    goblin = props.export_sets.add()
    goblin.filename = "Goblin"
    item = goblin.items.add()
    item.root_object = roots["Goblin"]
    item.include_children = True

    props.active_export_set_index = 0
    result = bpy.ops.scene.mizore_duplicate_export_set()
    assert_equal(result, {'FINISHED'}, "duplicate export set operator should succeed")
    goblin_sword = props.export_sets[props.active_export_set_index]
    assert_equal(goblin_sword.filename, "Goblin 2", "duplicated export set should get unique name")
    assert_equal(len(goblin_sword.items), 1, "duplicated export set should copy items")
    assert_equal(goblin_sword.items[0].root_object, roots["Goblin"], "duplicated export set should copy root object")
    goblin_sword.filename = "Goblin_Sword"
    goblin_sword.join_meshes_to_one = True
    goblin_sword.merge_armatures = True
    goblin_sword.target_armature = armatures["GoblinArm"]

    goblin_sword.active_item_index = 0
    result = bpy.ops.scene.mizore_duplicate_export_set_item()
    assert_equal(result, {'FINISHED'}, "duplicate export set item operator should succeed")
    assert_equal(len(goblin_sword.items), 2, "duplicated export set item should be appended")
    item = goblin_sword.items[goblin_sword.active_item_index]
    assert_equal(item.root_object, roots["Goblin"], "duplicated export set item should copy root object")
    item.root_object = roots["Sword"]

    props.active_export_set_index = 1
    result = bpy.ops.scene.mizore_duplicate_export_set()
    assert_equal(result, {'FINISHED'}, "second duplicate export set operator should succeed")
    goblin_knight = props.export_sets[props.active_export_set_index]
    assert_equal(goblin_knight.filename, "Goblin_Sword 2", "second duplicated export set should get unique name")
    assert_equal(goblin_knight.target_armature, armatures["GoblinArm"], "duplicated export set should copy target armature")
    goblin_knight.filename = "Goblin_Knight"
    goblin_knight.join_meshes_to_one = True
    goblin_knight.merge_armatures = True
    goblin_knight.target_armature = armatures["GoblinArm"]

    goblin_knight.active_item_index = 1
    result = bpy.ops.scene.mizore_duplicate_export_set_item()
    assert_equal(result, {'FINISHED'}, "second duplicate export set item operator should succeed")
    assert_equal(len(goblin_knight.items), 3, "second duplicated export set item should be appended")
    item = goblin_knight.items[goblin_knight.active_item_index]
    assert_equal(item.root_object, roots["Sword"], "second duplicated export set item should copy source item")
    item.root_object = roots["Shield"]
    item.armature_object = None


def build_export_sets_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "Goblin.fbx"))
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "Goblin_Sword.fbx"))
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "Goblin_Knight.fbx"))

    reset_scene()

    goblin_arm = _create_armature(
        "GoblinArm",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
            {"name": "Hand.L", "head": (0.0, 0.0, 0.8), "tail": (0.45, 0.0, 1.0), "parent": "Root"},
        ],
    )

    goblin = _create_cube("Goblin", (0.0, 0.0, 0.0))
    goblin_child = _create_cylinder("GoblinHat", (0.0, 0.0, 1.1), vertices=12, radius=0.18, depth=0.7)
    set_parent_keep_transform(goblin_child, goblin)
    _add_full_weight_group(goblin, "Root")
    _add_armature_modifier(goblin, goblin_arm)
    _assign_merge_group(goblin)

    sword_arm = _create_armature(
        "SwordArm",
        location=(3.0, 0.0, 0.0),
        bones=[
            {"name": "SwordRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.9)},
        ],
    )
    set_parent_to_bone_keep_transform(sword_arm, goblin_arm, "Hand.L")

    sword = _create_cone("Sword", (3.0, 0.0, 0.0), vertices=10, radius1=0.16, depth=1.4)
    sword_child = _create_ico_sphere("SwordGem", (3.0, 0.0, 0.9), subdivisions=1, radius=0.2)
    set_parent_keep_transform(sword_child, sword)
    sword_arm_child = _create_cube("SwordCharm", (3.2, 0.0, 0.65))
    set_parent_to_bone_keep_transform(sword_arm_child, sword_arm, "SwordRoot")
    _add_full_weight_group(sword, "SwordRoot")
    _add_armature_modifier(sword, sword_arm)
    _assign_merge_group(sword)

    shield = _create_cylinder("Shield", (6.0, 0.0, 0.0), vertices=16, radius=0.5, depth=0.18)
    _assign_merge_group(shield)

    roots = {
        "Goblin": goblin,
        "Sword": sword,
        "Shield": shield,
    }
    armatures = {
        "GoblinArm": goblin_arm,
        "SwordArm": sword_arm,
    }

    expected_files = {
        "Goblin.fbx": {
            "meshes": {
                "Goblin": _vertex_count(goblin) + _vertex_count(goblin_child),
            },
            "armatures": {
                "GoblinArm": {
                    "Root": None,
                    "Hand.L": "Root",
                },
            },
        },
        "Goblin_Sword.fbx": {
            "meshes": {
                "Goblin": _vertex_count(goblin) + _vertex_count(goblin_child) + _vertex_count(sword) + _vertex_count(sword_child) + _vertex_count(sword_arm_child),
            },
            "armatures": {
                "GoblinArm": {
                    "Root": None,
                    "Hand.L": "Root",
                    "SwordRoot": "Hand.L",
                },
            },
        },
        "Goblin_Knight.fbx": {
            "meshes": {
                "Goblin": _vertex_count(goblin) + _vertex_count(goblin_child) + _vertex_count(sword) + _vertex_count(sword_child) + _vertex_count(sword_arm_child) + _vertex_count(shield),
            },
            "armatures": {
                "GoblinArm": {
                    "Root": None,
                    "Hand.L": "Root",
                    "SwordRoot": "Hand.L",
                },
            },
        },
    }

    _set_export_sets(bpy.context.scene, roots, armatures)

    select_objects([goblin, sword, shield], active=goblin)
    log(f"Scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_multi_armature_export_set_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "MultiRig.fbx"))

    reset_scene()

    rig_a = _create_armature(
        "RigA",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "RigARoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )
    rig_b = _create_armature(
        "RigB",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "RigBRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )
    rig_skip = _create_armature(
        "RigSkip",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "RigSkipRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )

    root = _create_cube("MultiRigRoot", (0.0, 0.0, 0.0))
    part_a = _create_cylinder("MultiRigPartA", (0.0, 0.0, 1.1), vertices=10, radius=0.15, depth=0.8)
    part_b = _create_cone("MultiRigPartB", (0.7, 0.0, 0.8), vertices=9, radius1=0.14, depth=0.9)
    set_parent_keep_transform(part_a, root)
    set_parent_keep_transform(part_b, root)
    set_parent_keep_transform(rig_a, root)
    set_parent_keep_transform(rig_b, root)
    set_parent_keep_transform(rig_skip, root)

    _add_full_weight_group(root, "RigARoot")
    _add_armature_modifier(root, rig_a)
    _add_full_weight_group(part_a, "RigARoot")
    _add_armature_modifier(part_a, rig_a)
    _add_full_weight_group(part_b, "RigBRoot")
    _add_armature_modifier(part_b, rig_b)

    rig_skip["DontExport"] = True

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "MultiRig"
    export_set.join_meshes_to_one = False
    export_set.merge_armatures = False
    item = export_set.items.add()
    item.root_object = root
    item.include_children = True

    expected_files = {
        "MultiRig.fbx": {
            "meshes": {
                "MultiRigRoot": _vertex_count(root),
                "MultiRigPartA": _vertex_count(part_a),
                "MultiRigPartB": _vertex_count(part_b),
            },
            "armatures": {
                "RigA": {
                    "RigARoot": None,
                },
                "RigB": {
                    "RigBRoot": None,
                },
            },
        },
    }

    select_objects([root], active=root)
    log(f"Multi armature scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_armature_root_merge_export_set_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "BodyFace.fbx"))

    reset_scene()

    body_rig = _create_armature(
        "BodyRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.9)},
            {"name": "Head", "head": (0.0, 0.0, 0.9), "tail": (0.0, 0.0, 1.4), "parent": "Root"},
        ],
    )
    face_rig = _create_armature(
        "FaceRig",
        location=(2.0, 0.0, 0.0),
        bones=[
            {"name": "FaceRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.5)},
        ],
    )
    set_parent_to_bone_keep_transform(face_rig, body_rig, "Head")

    body_mesh = _create_cube("BodyMesh", (0.0, 0.0, 0.0))
    set_parent_keep_transform(body_mesh, body_rig)
    _add_full_weight_group(body_mesh, "Root")
    _add_armature_modifier(body_mesh, body_rig)

    face_mesh = _create_cube("FaceMesh", (2.0, 0.0, 0.0))
    set_parent_keep_transform(face_mesh, face_rig)
    _add_full_weight_group(face_mesh, "FaceRoot")
    _add_armature_modifier(face_mesh, face_rig)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    export_set = props.export_sets.add()
    export_set.filename = "BodyFace"
    export_set.join_meshes_to_one = False
    export_set.merge_armatures = True
    export_set.target_armature = body_rig

    item = export_set.items.add()
    item.root_object = body_rig
    item.include_children = True

    item = export_set.items.add()
    item.root_object = face_rig
    item.include_children = True

    expected_files = {
        "BodyFace.fbx": {
            "meshes": {
                "BodyMesh": _vertex_count(body_mesh),
                "FaceMesh": _vertex_count(face_mesh),
            },
            "armatures": {
                "BodyRig": {
                    "Root": None,
                    "Head": "Root",
                    "FaceRoot": "Head",
                },
            },
        },
    }

    select_objects([body_rig, face_rig], active=body_rig)
    log(f"Armature-root merge scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_armature_merge_infer_target_export_set_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "BodyFaceInferred.fbx"))

    reset_scene()

    body_rig = _create_armature(
        "BodyRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.9)},
            {"name": "Head", "head": (0.0, 0.0, 0.9), "tail": (0.0, 0.0, 1.4), "parent": "Root"},
        ],
    )
    face_rig = _create_armature(
        "FaceRig",
        location=(2.0, 0.0, 0.0),
        bones=[
            {"name": "FaceRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.5)},
        ],
    )
    set_parent_to_bone_keep_transform(face_rig, body_rig, "Head")

    body_mesh = _create_cube("BodyMesh", (0.0, 0.0, 0.0))
    set_parent_keep_transform(body_mesh, body_rig)
    _add_full_weight_group(body_mesh, "Root")
    _add_armature_modifier(body_mesh, body_rig)

    face_mesh = _create_cube("FaceMesh", (2.0, 0.0, 0.0))
    set_parent_keep_transform(face_mesh, face_rig)
    _add_full_weight_group(face_mesh, "FaceRoot")
    _add_armature_modifier(face_mesh, face_rig)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    export_set = props.export_sets.add()
    export_set.filename = "BodyFaceInferred"
    export_set.join_meshes_to_one = False
    export_set.merge_armatures = True

    item = export_set.items.add()
    item.root_object = body_rig
    item.include_children = True

    item = export_set.items.add()
    item.root_object = face_rig
    item.include_children = True
    item.attach_to_bone = "Head"

    expected_files = {
        "BodyFaceInferred.fbx": {
            "meshes": {
                "BodyMesh": _vertex_count(body_mesh),
                "FaceMesh": _vertex_count(face_mesh),
            },
            "armatures": {
                "BodyRig": {
                    "Root": None,
                    "Head": "Root",
                    "FaceRoot": "Head",
                },
            },
        },
    }

    select_objects([body_rig, face_rig], active=body_rig)
    log(f"Armature merge infer-target scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_mesh_root_explicit_armature_merge_export_set_scene(filename="BodyFaceMeshRootExplicit", set_target=True):
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, f"{filename}.fbx"))

    reset_scene()

    body_rig = _create_armature(
        "BodyRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.9)},
            {"name": "Head", "head": (0.0, 0.0, 0.9), "tail": (0.0, 0.0, 1.4), "parent": "Root"},
        ],
    )
    face_rig = _create_armature(
        "FaceRig",
        location=(2.0, 0.0, 0.0),
        bones=[
            {"name": "FaceRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.5)},
        ],
    )
    set_parent_to_bone_keep_transform(face_rig, body_rig, "Head")

    body_mesh = _create_cube("BodyMesh", (0.0, 0.0, 0.0))
    set_parent_keep_transform(body_mesh, body_rig)
    _add_full_weight_group(body_mesh, "Root")
    _add_armature_modifier(body_mesh, body_rig)

    face_mesh = _create_cube("FaceMesh", (2.0, 0.0, 0.0))
    set_parent_keep_transform(face_mesh, face_rig)
    _add_full_weight_group(face_mesh, "FaceRoot")
    _add_armature_modifier(face_mesh, face_rig)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    export_set = props.export_sets.add()
    export_set.filename = filename
    export_set.join_meshes_to_one = False
    export_set.merge_armatures = True
    if set_target:
        export_set.target_armature = body_rig

    item = export_set.items.add()
    item.root_object = body_mesh
    item.include_children = False
    item.armature_object = body_rig

    item = export_set.items.add()
    item.root_object = face_mesh
    item.include_children = False
    item.armature_object = face_rig
    item.attach_to_bone = "Head"

    expected_files = {
        f"{filename}.fbx": {
            "meshes": {
                "BodyMesh": _vertex_count(body_mesh),
                "FaceMesh": _vertex_count(face_mesh),
            },
            "armatures": {
                "BodyRig": {
                    "Root": None,
                    "Head": "Root",
                    "FaceRoot": "Head",
                },
            },
        },
    }

    select_objects([body_mesh, face_mesh], active=body_mesh)
    log(f"Mesh-root explicit armature merge scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_shared_target_armature_multi_item_scene(filename="BodyFaceSharedTarget"):
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, f"{filename}.fbx"))

    reset_scene()

    body_rig = _create_armature(
        "BodyRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.9)},
            {"name": "Head", "head": (0.0, 0.0, 0.9), "tail": (0.0, 0.0, 1.4), "parent": "Root"},
        ],
    )
    face_rig = _create_armature(
        "FaceRig",
        location=(2.0, 0.0, 0.0),
        bones=[
            {"name": "FaceRoot", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.5)},
        ],
    )
    set_parent_to_bone_keep_transform(face_rig, body_rig, "Head")

    body_mesh = _create_cube("BodyMesh", (0.0, 0.0, 0.0))
    set_parent_keep_transform(body_mesh, body_rig)
    _add_full_weight_group(body_mesh, "Root")
    _add_armature_modifier(body_mesh, body_rig)

    accessory_mesh = _create_cube("AccessoryMesh", (0.5, 0.0, 0.8))
    set_parent_keep_transform(accessory_mesh, body_rig)
    _add_full_weight_group(accessory_mesh, "Head")
    _add_armature_modifier(accessory_mesh, body_rig)

    face_mesh = _create_cube("FaceMesh", (2.0, 0.0, 0.0))
    set_parent_keep_transform(face_mesh, face_rig)
    _add_full_weight_group(face_mesh, "FaceRoot")
    _add_armature_modifier(face_mesh, face_rig)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    export_set = props.export_sets.add()
    export_set.filename = filename
    export_set.join_meshes_to_one = False
    export_set.merge_armatures = True
    export_set.target_armature = body_rig

    item = export_set.items.add()
    item.root_object = body_mesh
    item.include_children = False
    item.armature_object = body_rig

    item = export_set.items.add()
    item.root_object = accessory_mesh
    item.include_children = False
    item.armature_object = body_rig
    item.attach_to_bone = "Head"

    item = export_set.items.add()
    item.root_object = face_mesh
    item.include_children = False
    item.armature_object = face_rig
    item.attach_to_bone = "Head"

    expected_files = {
        f"{filename}.fbx": {
            "meshes": {
                "BodyMesh": _vertex_count(body_mesh),
                "AccessoryMesh": _vertex_count(accessory_mesh),
                "FaceMesh": _vertex_count(face_mesh),
            },
            "armatures": {
                "BodyRig": {
                    "Root": None,
                    "Head": "Root",
                    "FaceRoot": "Head",
                },
            },
        },
    }

    select_objects([body_mesh, accessory_mesh, face_mesh], active=body_mesh)
    log(f"Shared-target armature scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_vertex_color_replace_export_set_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "ColorBase.fbx"))
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "ColorVariant.fbx"))

    reset_scene()

    color_body = _create_cube("ColorBody", (0.0, 0.0, 0.0))
    _assign_polygon_color(color_body, [0, 1, 2], (1.0, 0.0, 0.0, 1.0))
    _assign_polygon_color(color_body, [3, 4, 5], (0.0, 1.0, 0.0, 1.0))

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    base_set = props.export_sets.add()
    base_set.filename = "ColorBase"
    item = base_set.items.add()
    item.root_object = color_body
    item.include_children = True

    props.active_export_set_index = 0
    result = bpy.ops.scene.mizore_duplicate_export_set()
    assert_equal(result, {'FINISHED'}, "duplicate export set for color variant should succeed")
    variant_set = props.export_sets[props.active_export_set_index]
    variant_set.filename = "ColorVariant"

    result = bpy.ops.scene.mizore_add_export_set_vcol_replace_rule()
    assert_equal(result, {'FINISHED'}, "add vertex color replace rule should succeed")
    rule = variant_set.vertex_color_replace_rules[variant_set.active_vertex_color_replace_rule_index]
    rule.layer_name = "Color"
    rule.source_color = (1.0, 0.0, 0.0, 1.0)
    rule.target_color = (0.0, 0.0, 1.0, 1.0)
    rule.tolerance = 0.0001

    expected_files = {
        "ColorBase.fbx": {
            "meshes": {
                "ColorBody": _vertex_count(color_body),
            },
            "vertex_colors": {
                "ColorBody": {
                    "colors": [
                        (255, 0, 0, 255),
                        (0, 255, 0, 255),
                    ],
                },
            },
        },
        "ColorVariant.fbx": {
            "meshes": {
                "ColorBody": _vertex_count(color_body),
            },
            "vertex_colors": {
                "ColorBody": {
                    "colors": [
                        (0, 0, 255, 255),
                        (0, 255, 0, 255),
                    ],
                },
            },
        },
    }

    select_objects([color_body], active=color_body)
    log(f"Vertex color replace scene prepared. objects={[obj.name for obj in bpy.context.scene.objects]}")
    log(f"Expected export files={expected_files}")
    return expected_files


def build_export_set_scope_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "ScopedRoot.fbx"))

    reset_scene()

    shared_rig = _create_armature(
        "SharedRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )
    scoped_root = _create_cube("ScopedRoot", (0.0, 0.0, 0.0))
    scoped_child = _create_cylinder("ScopedChild", (0.0, 0.0, 1.1), vertices=12, radius=0.15, depth=0.6)
    unlisted_sibling = _create_cube("UnlistedSibling", (1.6, 0.0, 0.0))

    set_parent_keep_transform(scoped_root, shared_rig)
    set_parent_keep_transform(scoped_child, scoped_root)
    set_parent_keep_transform(unlisted_sibling, shared_rig)

    _add_full_weight_group(scoped_root, "Root")
    _add_armature_modifier(scoped_root, shared_rig)
    _add_full_weight_group(scoped_child, "Root")
    _add_armature_modifier(scoped_child, shared_rig)
    _add_full_weight_group(unlisted_sibling, "Root")
    _add_armature_modifier(unlisted_sibling, shared_rig)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "ScopedRoot"
    item = export_set.items.add()
    item.root_object = scoped_root
    item.include_children = True

    expected_files = {
        "ScopedRoot.fbx": {
            "meshes": {
                "ScopedRoot": _vertex_count(scoped_root),
                "ScopedChild": _vertex_count(scoped_child),
            },
            "armatures": {
                "SharedRig": {
                    "Root": None,
                },
            },
        },
    }

    select_objects([shared_rig, scoped_root, scoped_child, unlisted_sibling], active=scoped_root)
    return expected_files


def validate_export_set_join_uses_root_name():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    child = _create_cube("JoinChild", (0.8, 0.0, 0.0))
    root = _create_cube("JoinRoot", (0.0, 0.0, 0.0))
    set_parent_keep_transform(child, root)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    export_set = props.export_sets.add()
    export_set.filename = "JoinRootExport"
    export_set.join_meshes_to_one = True
    item = export_set.items.add()
    item.root_object = root
    item.include_children = True

    select_objects([root, child], active=root)

    runtime = func_export_sets.build_export_set_runtime(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    try:
        item_runtime = runtime.item_runtimes[0]
        duplicate_root_name = item_runtime.duplicate_root.name if item_runtime.duplicate_root else None
        assert_equal(
            duplicate_root_name,
            "JoinRoot",
            "duplicated root object should resolve even after source names are swapped",
        )

        duplicate_root = next(
            obj for obj in runtime.duplicate_objects
            if func_export_sets.object_exists(obj) and obj.type == 'MESH' and obj.name == "JoinRoot"
        )
        duplicate_child = next(
            obj for obj in runtime.duplicate_objects
            if func_export_sets.object_exists(obj) and obj.type == 'MESH' and obj.name == "JoinChild"
        )
        other_objects = [
            obj
            for obj in runtime.duplicate_objects
            if obj not in {duplicate_root, duplicate_child}
        ]
        runtime.duplicate_objects = [duplicate_child, duplicate_root, *other_objects]

        joined = func_export_sets.join_runtime_meshes(runtime)
        assert_equal(joined.name, "JoinRoot", "joined mesh should keep the root object name")
    finally:
        func_export_sets.cleanup_runtime(runtime)


def validate_export_set_scope_resolution():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    build_export_set_scope_scene()
    export_set = bpy.context.scene.mizore_export_sets.export_sets[0]

    resolved = func_export_sets.resolve_export_set_objects(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    resolved_names = sorted(obj.name for obj in resolved)
    assert_equal(
        resolved_names,
        ["ScopedChild", "ScopedRoot", "SharedRig"],
        "resolved export-set objects should not include meshes outside the item root",
    )


def validate_export_set_scope_skips_dont_export_children():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    root = _create_cube("ScopedRoot", (0.0, 0.0, 0.0))
    keep_child = _create_cube("KeepChild", (1.0, 0.0, 0.0))
    skip_child = _create_cube("SkipChild", (2.0, 0.0, 0.0))
    set_parent_keep_transform(keep_child, root)
    set_parent_keep_transform(skip_child, root)
    skip_child["DontExport"] = True

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "ScopedRoot"
    item = export_set.items.add()
    item.root_object = root
    item.include_children = True

    select_objects([root], active=root)
    resolved = func_export_sets.resolve_export_set_objects(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    resolved_names = sorted(obj.name for obj in resolved)
    assert_equal(
        resolved_names,
        ["KeepChild", "ScopedRoot"],
        "resolved export-set objects should skip DontExport children under the root",
    )


def validate_export_set_scope_skips_nested_always_export_children():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    root = _create_cube("ScopedRoot", (0.0, 0.0, 0.0))
    keep_child = _create_cube("KeepChild", (1.0, 0.0, 0.0))
    nested_export_root = _create_cube("NestedExportRoot", (2.0, 0.0, 0.0))
    set_parent_keep_transform(keep_child, root)
    set_parent_keep_transform(nested_export_root, root)
    nested_export_root["AlwaysExport"] = True

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "ScopedRoot"
    item = export_set.items.add()
    item.root_object = root
    item.include_children = True

    select_objects([root, keep_child, nested_export_root], active=root)
    resolved = func_export_sets.resolve_export_set_objects(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    resolved_names = sorted(obj.name for obj in resolved)
    assert_equal(
        resolved_names,
        ["KeepChild", "ScopedRoot"],
        "resolved export-set objects should skip nested AlwaysExport children under the root",
    )


def validate_export_set_runtime_mapping():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    build_export_sets_scene()

    export_set = bpy.context.scene.mizore_export_sets.export_sets[1]
    runtime = func_export_sets.build_export_set_runtime(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    try:
        duplicate_root_names = [
            item_runtime.duplicate_root.name if item_runtime.duplicate_root else None
            for item_runtime in runtime.item_runtimes
        ]
        assert_equal(
            duplicate_root_names,
            ["Goblin", "Sword"],
            "runtime should keep duplicated roots aligned with each export set item",
        )

        duplicate_armature_names = sorted(
            armature_runtime.duplicate_armature.name
            for armature_runtime in runtime.armature_runtimes
            if armature_runtime.duplicate_armature is not None
        )
        assert_equal(
            duplicate_armature_names,
            ["GoblinArm", "SwordArm"],
            "runtime should keep duplicated armatures aligned with each export set item",
        )

        merged_armature = func_export_sets.merge_runtime_armatures(runtime)
        assert_equal(
            merged_armature.name if merged_armature else None,
            "GoblinArm",
            "merged armature should keep the primary armature name",
        )

        joined_mesh = func_export_sets.join_runtime_meshes(runtime)
        assert_equal(
            joined_mesh.name if joined_mesh else None,
            "Goblin",
            "joined mesh should keep the first item's root name",
        )
    finally:
        func_export_sets.cleanup_runtime(runtime)


def validate_export_set_legacy_primary_armature_migration():
    load_required_modules()
    props_export_sets = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.export_sets.props_export_sets"
    )

    build_armature_root_merge_export_set_scene()

    export_set = bpy.context.scene.mizore_export_sets.export_sets[0]
    export_set.target_armature = None
    export_set.items[0]["is_primary_armature"] = True

    props_export_sets.migrate_legacy_export_set_data(bpy.context.scene)

    assert_equal(
        export_set.target_armature,
        export_set.items[0].root_object,
        "legacy primary armature should migrate to target armature",
    )
    if "is_primary_armature" in export_set.items[0].keys():
        raise AssertionError("legacy primary armature flag should be removed after migration")


def validate_duplicate_objects_preserves_export_set_references():
    load_required_modules()
    func_object_utils = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.funcs.utils.func_object_utils"
    )

    build_armature_root_merge_export_set_scene()
    export_set = bpy.context.scene.mizore_export_sets.export_sets[0]
    source_item = export_set.items[0]
    merge_item = export_set.items[1]
    override = export_set.shapekey_reorder_overrides.add()
    override.target_object = bpy.data.objects["BodyMesh"]

    source_root = source_item.root_object
    source_armature = source_item.armature_object
    merge_root = merge_item.root_object
    merge_armature = merge_item.armature_object
    target_armature = export_set.target_armature

    func_object_utils.duplicate_objects([source_root], linked=False)
    duplicates = list(bpy.context.selected_objects)
    func_object_utils.remove_objects(duplicates)

    assert_equal(source_item.root_object, source_root, "duplicate should restore item root object")
    assert_equal(source_item.armature_object, source_armature, "duplicate should restore item armature object")
    assert_equal(merge_item.root_object, merge_root, "duplicate should restore second item root object")
    assert_equal(merge_item.armature_object, merge_armature, "duplicate should restore second item armature object")
    assert_equal(export_set.target_armature, target_armature, "duplicate should restore target armature")
    assert_equal(override.target_object, bpy.data.objects["BodyMesh"], "duplicate should restore override target object")


def validate_export_set_armature_root_scope_resolution():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    build_armature_root_merge_export_set_scene()

    export_set = bpy.context.scene.mizore_export_sets.export_sets[0]
    primary_item = export_set.items[0]
    secondary_item = export_set.items[1]
    assert_equal(primary_item.armature_object, primary_item.root_object, "armature root item should sync armature to root")
    assert_equal(secondary_item.armature_object, secondary_item.root_object, "second armature root item should sync armature to root")
    export_set.items[1].enabled = False

    resolved = func_export_sets.resolve_export_set_objects(
        export_set=export_set,
        available_objects=[primary_item.root_object],
    )
    resolved_names = sorted(obj.name for obj in resolved)
    assert_equal(
        resolved_names,
        ["BodyMesh", "BodyRig"],
        "armature root item should stop before nested armature subtrees",
    )


def validate_export_set_explicit_armature_must_belong_to_item():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    root_mesh = _create_cube("ScopedMesh", (0.0, 0.0, 0.0))
    unrelated_armature = _create_armature(
        "UnrelatedRig",
        location=(2.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0

    export_set = props.export_sets.add()
    export_set.filename = "InvalidArmature"
    item = export_set.items.add()
    item.root_object = root_mesh
    item.armature_object = unrelated_armature

    select_objects([root_mesh], active=root_mesh)

    try:
        func_export_sets.build_export_set_runtime(
            export_set=export_set,
            available_objects=list(bpy.context.selected_objects),
        )
    except RuntimeError as exc:
        if "cannot use unrelated armature" not in str(exc):
            raise AssertionError(f"unexpected unrelated armature error: {exc}")
    else:
        raise AssertionError("unrelated explicit armature should raise RuntimeError")


def validate_export_set_armature_root_merge_export():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_armature_root_merge_export_set_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'EMPTY', 'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "BodyFace.fbx")],
        "armature-root merge export should produce one export-set file",
    )
    validate_exported_outputs(expected_files)


def validate_export_set_merge_infers_target_from_empty_attach_bone():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_armature_merge_infer_target_export_set_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'EMPTY', 'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "BodyFaceInferred.fbx")],
        "armature merge should infer the target from the item without attach_to_bone",
    )
    validate_exported_outputs(expected_files)


def validate_export_set_mesh_root_explicit_armature_requires_target():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    build_mesh_root_explicit_armature_merge_export_set_scene(
        filename="BodyFaceMeshRootExplicitNeedsTarget",
        set_target=False,
    )

    import change_base_export_test_lib as base_t

    try:
        base_t.export_selected_scene(
            func_execute_main_module=func_execute_main,
            filepath=BASE_EXPORT_PATH,
            enable_auto_merge=False,
            operator_overrides={
                "batch_mode": 'EXPORT_SETS',
                "object_types": {'EMPTY', 'MESH', 'ARMATURE'},
                "save_prefs": False,
                "save_path": False,
            },
        )
    except RuntimeError as exc:
        if "must set Target Armature" not in str(exc):
            raise AssertionError(f"unexpected explicit-armature target error: {exc}")
    else:
        raise AssertionError("mesh-root explicit armature items should still require Target Armature")


def validate_export_set_mesh_root_explicit_armature_merges_into_target():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_mesh_root_explicit_armature_merge_export_set_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'EMPTY', 'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "BodyFaceMeshRootExplicit.fbx")],
        "mesh-root explicit armature merge should produce one export-set file",
    )
    validate_exported_outputs(expected_files)


def validate_export_set_shared_target_armature_accepts_multiple_items():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_shared_target_armature_multi_item_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'EMPTY', 'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "BodyFaceSharedTarget.fbx")],
        "shared target armature export should produce one export-set file",
    )
    validate_exported_outputs(expected_files)



def validate_export_set_preprocess_respects_support_object_props():
    load_required_modules()
    reset_scene()

    func_execute_common = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.func_execute_common"
    )
    func_execute_export_sets = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.func_execute_export_sets"
    )
    func_export_preprocess = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.custom_exporter_fbx.func_export_preprocess"
    )
    func_export_sets = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.export_sets.func_export_sets"
    )
    consts = importlib.import_module(f"{EXPORTER_MODULE}.scripts.consts")

    support_armature = _create_armature(
        "SupportRig",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 1.0)},
        ],
    )
    support_mesh = _create_cube("SupportMesh", (0.0, 0.0, 0.5))
    _add_full_weight_group(support_mesh, "Root")
    _add_armature_modifier(support_mesh, support_armature)

    support_mesh.shape_key_add(name="Basis")
    support_key = support_mesh.shape_key_add(name="Smile")
    support_key.data[0].co.x += 0.35
    support_key.value = 1.0
    support_mesh[consts.RESET_SHAPEKEY_GROUP_NAME] = True
    support_armature[consts.RESET_POSE_GROUP_NAME] = True

    with single_object_override(support_armature):
        bpy.ops.object.mode_set(mode='POSE')
        pose_bone = support_armature.pose.bones["Root"]
        pose_bone.rotation_mode = 'XYZ'
        pose_bone.rotation_euler.z = 0.75
        bpy.ops.object.mode_set(mode='OBJECT')

    if abs(support_armature.pose.bones["Root"].rotation_euler.z) <= 1e-6:
        raise AssertionError("support armature pose setup failed before preprocess test")
    if abs(support_mesh.data.shape_keys.key_blocks["Smile"].value - 1.0) > 1e-6:
        raise AssertionError("support mesh shapekey setup failed before preprocess test")

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "SupportProps"
    item = export_set.items.add()
    item.root_object = support_mesh
    item.include_children = False
    item.armature_object = support_armature

    select_objects([support_mesh], active=support_mesh)

    import change_base_export_test_lib as base_t

    operator = base_t.ExportOperatorStub(
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
    )
    operator.batch_mode = 'EXPORT_SETS'
    operator.object_types = {'MESH'}

    selection_context = func_execute_common.prepare_export_selection_context(
        operator,
        bpy.context,
        func_export_sets.iter_enabled_export_sets,
        func_execute_export_sets.prepare_export_set_preprocess_targets,
    )

    selected_names = sorted(obj.name for obj in get_selected_objects())
    assert_equal(
        selected_names,
        ["SupportMesh", "SupportRig"],
        "export set preprocess targets should include support armatures even in mesh-only mode",
    )
    assert_equal(
        selection_context.export_set_available_roots,
        [support_mesh],
        "export set preprocess context should keep the original selected roots",
    )

    func_export_preprocess.export_preprocess(operator)

    if abs(support_mesh.data.shape_keys.key_blocks["Smile"].value) > 1e-6:
        raise AssertionError("ResetShapekeysWhenExport should reset export set mesh shapekeys")
    if abs(support_armature.pose.bones["Root"].rotation_euler.z) > 1e-6:
        raise AssertionError("Reset Pose should reset support armatures used by export set items")

def validate_export_set_progress_updates_are_granular():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    build_armature_root_merge_export_set_scene()

    import change_base_export_test_lib as base_t

    operator = base_t.ExportOperatorStub(
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
    )
    operator.batch_mode = 'EXPORT_SETS'
    operator.object_types = {'EMPTY', 'MESH', 'ARMATURE'}
    operator.save_prefs = False
    operator.save_path = False

    if bpy.ops.ed.undo_push.poll():
        bpy.ops.ed.undo_push(message="Export set progress granularity test")
    else:
        raise RuntimeError("Undo push is not available in this Blender context")

    progress_snapshots = []
    try:
        generator = func_execute_main.execute_main_iter(operator, bpy.context)
        while True:
            try:
                progress = next(generator)
            except StopIteration as stop:
                result = stop.value
                break
            if progress.phase == "export_set":
                progress_snapshots.append({
                    "message": progress.message,
                    "object_name": progress.object_name,
                    "progress": progress.progress,
                })
        if result is None:
            raise AssertionError("export set progress test returned no result")
        if not result.exported_files:
            raise AssertionError("export set progress test produced no exported files")
    finally:
        if bpy.ops.ed.undo_push.poll():
            bpy.ops.ed.undo_push(message="Restore export set progress test scene")
            bpy.ops.ed.undo()

    if len(progress_snapshots) < 5:
        raise AssertionError(
            f"export set progress updates are too sparse: count={len(progress_snapshots)} snapshots={progress_snapshots}"
        )

    messages = [snapshot["message"] for snapshot in progress_snapshots]
    required_fragments = [
        "resolve targets",
        "runtime ready",
        "retarget references",
        "merge armatures",
        "export FBX",
        "export complete",
    ]
    for fragment in required_fragments:
        if not any(fragment in message for message in messages):
            raise AssertionError(
                f"missing export set progress message fragment '{fragment}'. messages={messages}"
            )


def validate_shapekey_override_preview_does_not_request_writes():
    load_required_modules()
    resolver = importlib.import_module(
        f"{EXPORTER_MODULE}.scripts.export_sets.shapekey_order_override.resolver"
    )

    observed_allow_write = []
    original_build_candidate_rows = resolver.build_candidate_rows
    original_order_module = resolver._order_module

    class _DummyRow:
        def __init__(self, final_name):
            self.final_name = final_name
            self.kinds_label = ""
            self.source_objects_label = ""
            self.source_detail_label = ""
            self.match_tokens_serialized = ""
            self.state_label = ""
            self.is_basis = False
            self.is_resolved = True

    class _DummyOrderModule:
        @staticmethod
        def resolve_rows(candidate_rows, ordered_names):
            return [_DummyRow(name) for name in ordered_names]

    def fake_build_candidate_rows(_obj, _context=None, *, allow_write=True):
        observed_allow_write.append(allow_write)
        return [_DummyRow("Basis")]

    resolver.build_candidate_rows = fake_build_candidate_rows
    resolver._order_module = lambda: _DummyOrderModule
    try:
        rows = resolver.build_resolved_rows(None, ["Basis"], allow_write=False)
    finally:
        resolver.build_candidate_rows = original_build_candidate_rows
        resolver._order_module = original_order_module

    assert_equal(observed_allow_write, [False], "shapekey override preview should resolve rows without write access")
    assert_equal([row.final_name for row in rows], ["Basis"], "resolved rows should preserve ordered names")


def validate_export_set_scope_export():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_export_set_scope_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'EMPTY', 'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "ScopedRoot.fbx")],
        "export should produce only the scoped export-set file",
    )
    validate_exported_outputs(expected_files)


def validate_export_set_mesh_only_export():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_export_sets_scene()
    for expected in expected_files.values():
        expected.pop("armatures", None)

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=True,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'MESH'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [
            os.path.join(OUTPUT_DIR, "Goblin.fbx"),
            os.path.join(OUTPUT_DIR, "Goblin_Sword.fbx"),
            os.path.join(OUTPUT_DIR, "Goblin_Knight.fbx"),
        ],
        "mesh-only export should still produce the export-set files",
    )
    validate_exported_outputs(expected_files)


def validate_export_set_multi_armature_export():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_multi_armature_export_set_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'MESH', 'ARMATURE'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "MultiRig.fbx")],
        "multi-armature export should produce one export-set file",
    )
    validate_exported_outputs(expected_files)


def validate_export_set_object_replace_duplicate_root():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    source_root = _create_cube("ReplaceSourceRoot", (0.0, 0.0, 0.0))
    replacement_root = _create_cone("ReplaceTargetRoot", (2.0, 0.0, 0.0), vertices=9, radius1=0.2, depth=1.0)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "ReplaceRoot"
    item = export_set.items.add()
    item.root_object = source_root
    item.include_children = False

    rule = export_set.object_replace_rules.add()
    rule.source_object = source_root
    rule.replacement_object = replacement_root
    rule.include_children = False

    select_objects([source_root], active=source_root)

    runtime = func_export_sets.build_export_set_runtime(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    try:
        assert_equal(len(runtime.item_runtimes), 1, "object replace runtime should produce one item runtime")
        duplicate_root = runtime.item_runtimes[0].duplicate_root
        assert_equal(
            duplicate_root.name if duplicate_root else None,
            "ReplaceTargetRoot",
            "item runtime root should switch to the replacement object",
        )
    finally:
        func_export_sets.cleanup_runtime(runtime)


def validate_export_set_object_replace_armature_modifier_retarget():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    holder = _create_empty("ReplaceRigHolder", (0.0, 0.0, 0.0))
    source_armature = _create_armature(
        "ReplaceSourceArm",
        location=(0.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )
    replacement_armature = _create_armature(
        "ReplaceTargetArm",
        location=(2.0, 0.0, 0.0),
        bones=[
            {"name": "Root", "head": (0.0, 0.0, 0.0), "tail": (0.0, 0.0, 0.8)},
        ],
    )
    driven_mesh = _create_cube("ReplaceDrivenMesh", (0.5, 0.0, 0.0))
    charm = _create_cube("ReplaceCharm", (0.0, 0.0, 0.9))

    set_parent_keep_transform(source_armature, holder)
    set_parent_keep_transform(driven_mesh, holder)
    set_parent_to_bone_keep_transform(charm, source_armature, "Root")
    _add_full_weight_group(driven_mesh, "Root")
    _add_armature_modifier(driven_mesh, source_armature)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "ReplaceArmature"
    item = export_set.items.add()
    item.root_object = holder
    item.include_children = True

    rule = export_set.object_replace_rules.add()
    rule.source_object = source_armature
    rule.replacement_object = replacement_armature
    rule.include_children = False

    select_objects([holder], active=holder)

    runtime = func_export_sets.build_export_set_runtime(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    try:
        duplicate_armature_names = sorted(
            armature_runtime.duplicate_armature.name
            for armature_runtime in runtime.armature_runtimes
            if armature_runtime.duplicate_armature is not None
        )
        assert_equal(
            duplicate_armature_names,
            ["ReplaceTargetArm"],
            "armature inference should switch to the replacement armature",
        )

        func_export_sets.retarget_runtime_object_replace_references(runtime)
        func_export_sets.validate_runtime_object_replace_references(runtime)

        duplicate_driven = next(
            obj for obj in runtime.duplicate_objects
            if func_export_sets.object_exists(obj) and obj.type == 'MESH' and obj.name == "ReplaceDrivenMesh"
        )
        duplicate_charm = next(
            obj for obj in runtime.duplicate_objects
            if func_export_sets.object_exists(obj) and obj.type == 'MESH' and obj.name == "ReplaceCharm"
        )
        duplicate_target_armature = next(
            obj for obj in runtime.duplicate_objects
            if func_export_sets.object_exists(obj) and obj.type == 'ARMATURE' and obj.name == "ReplaceTargetArm"
        )

        armature_modifier = next(
            modifier for modifier in duplicate_driven.modifiers
            if modifier.type == 'ARMATURE'
        )
        assert_equal(
            armature_modifier.object,
            duplicate_target_armature,
            "armature modifier should retarget to the replacement armature duplicate",
        )
        assert_equal(
            duplicate_charm.parent,
            duplicate_target_armature,
            "bone parent should retarget to the replacement armature duplicate",
        )
        assert_equal(
            duplicate_charm.parent_bone,
            "Root",
            "bone parent name should be preserved on retarget",
        )
    finally:
        func_export_sets.cleanup_runtime(runtime)


def validate_export_set_object_replace_unsupported_modifier_detection():
    modules = load_required_modules()
    func_export_sets = modules["func_export_sets"]

    reset_scene()

    holder = _create_empty("UnsupportedReplaceHolder", (0.0, 0.0, 0.0))
    source_target = _create_cube("UnsupportedReplaceSource", (0.0, 0.0, 0.0))
    replacement_target = _create_cube("UnsupportedReplaceTarget", (2.0, 0.0, 0.0))
    deform_mesh = _create_cube("UnsupportedReplaceMesh", (0.0, 1.0, 0.0))

    set_parent_keep_transform(source_target, holder)
    set_parent_keep_transform(deform_mesh, holder)
    modifier = deform_mesh.modifiers.new(name="SurfaceDeform", type='SURFACE_DEFORM')
    modifier.target = source_target

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "UnsupportedReplace"
    item = export_set.items.add()
    item.root_object = holder
    item.include_children = True

    rule = export_set.object_replace_rules.add()
    rule.source_object = source_target
    rule.replacement_object = replacement_target
    rule.include_children = False

    select_objects([holder], active=holder)

    runtime = func_export_sets.build_export_set_runtime(
        export_set=export_set,
        available_objects=list(bpy.context.selected_objects),
    )
    try:
        func_export_sets.retarget_runtime_object_replace_references(runtime)
        try:
            func_export_sets.validate_runtime_object_replace_references(runtime)
        except RuntimeError as exc:
            message = str(exc)
            if "SURFACE_DEFORM" not in message:
                raise AssertionError(f"unsupported modifier error should mention SURFACE_DEFORM: {message}")
        else:
            raise AssertionError("unsupported object-reference modifier should raise RuntimeError")
    finally:
        func_export_sets.cleanup_runtime(runtime)


def build_object_replace_export_scene():
    ensure_output_dir()
    remove_file_if_exists(STATUS_PATH)
    remove_file_if_exists(BASE_EXPORT_PATH)
    remove_file_if_exists(os.path.join(OUTPUT_DIR, "ReplaceRuntime.fbx"))

    reset_scene()

    source_mesh = _create_cube("ReplaceExportSource", (0.0, 0.0, 0.0))
    replacement_mesh = _create_cone("ReplaceExportTarget", (2.0, 0.0, 0.0), vertices=9, radius1=0.22, depth=1.1)

    props = bpy.context.scene.mizore_export_sets
    props.export_sets.clear()
    props.active_export_set_index = 0
    export_set = props.export_sets.add()
    export_set.filename = "ReplaceRuntime"
    item = export_set.items.add()
    item.root_object = source_mesh
    item.include_children = False

    rule = export_set.object_replace_rules.add()
    rule.source_object = source_mesh
    rule.replacement_object = replacement_mesh
    rule.include_children = False

    expected_files = {
        "ReplaceRuntime.fbx": {
            "meshes": {
                "ReplaceExportTarget": _vertex_count(replacement_mesh),
            },
        },
    }

    select_objects([source_mesh], active=source_mesh)
    return expected_files


def validate_export_set_object_replace_export():
    modules = load_required_modules()
    func_execute_main = modules["func_execute_main"]

    expected_files = build_object_replace_export_scene()

    import change_base_export_test_lib as base_t

    _operator, result = base_t.export_selected_scene(
        func_execute_main_module=func_execute_main,
        filepath=BASE_EXPORT_PATH,
        enable_auto_merge=False,
        operator_overrides={
            "batch_mode": 'EXPORT_SETS',
            "object_types": {'MESH'},
            "save_prefs": False,
            "save_path": False,
        },
    )
    exported_paths = [item.filepath for item in result.exported_files]
    assert_equal(
        exported_paths,
        [os.path.join(OUTPUT_DIR, "ReplaceRuntime.fbx")],
        "object replacement export should produce the replacement export-set file",
    )
    validate_exported_outputs(expected_files)


def _create_empty_temp_scene(name):
    scene = bpy.data.scenes.new(name=name)
    for obj in list(scene.objects):
        scene.collection.objects.unlink(obj)
    return scene


def _iter_mesh_color_attributes(mesh):
    color_attributes = getattr(mesh, "color_attributes", None)
    if color_attributes is None:
        return []
    return [
        color_attr
        for color_attr in color_attributes
        if getattr(color_attr, "data_type", "") in {'FLOAT_COLOR', 'BYTE_COLOR'}
    ]


def _quantize_color(color):
    return tuple(
        int(round(max(0.0, min(1.0, float(channel))) * 255.0))
        for channel in color[:4]
    )


def _collect_unique_attribute_colors(color_attr):
    return sorted({_quantize_color(item.color) for item in color_attr.data})


def validate_exported_file(filepath, expected):
    if not os.path.exists(filepath):
        raise AssertionError(f"Exported file was not created: {filepath}")

    reset_scene()
    with scene_window_override(bpy.context.scene):
        result = bpy.ops.import_scene.fbx(filepath=filepath)
    if 'FINISHED' not in result:
        raise AssertionError(f"FBX import failed for {filepath}: {result}")

    expected_meshes = expected["meshes"]
    expected_armatures = expected.get("armatures", {})
    expected_vertex_colors = expected.get("vertex_colors", {})

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    actual_names = sorted(obj.name for obj in mesh_objects)
    expected_names = sorted(expected_meshes.keys())
    if actual_names != expected_names:
        raise AssertionError(
            f"{os.path.basename(filepath)}: unexpected mesh names. "
            f"actual={actual_names} expected={expected_names}"
        )

    for obj in mesh_objects:
        actual_count = len(obj.data.vertices)
        expected_count = expected_meshes[obj.name]
        if actual_count != expected_count:
            raise AssertionError(
                f"{os.path.basename(filepath)}:{obj.name} vertex count mismatch. "
                f"actual={actual_count} expected={expected_count}"
            )

    for obj in mesh_objects:
        if obj.name not in expected_vertex_colors:
            continue
        expected_color_info = expected_vertex_colors[obj.name]
        color_attributes = _iter_mesh_color_attributes(obj.data)
        if not color_attributes:
            raise AssertionError(
                f"{os.path.basename(filepath)}:{obj.name} has no vertex color attributes"
            )
        layer_name = expected_color_info.get("layer_name", "")
        if layer_name:
            matching_attributes = [color_attr for color_attr in color_attributes if color_attr.name == layer_name]
            if not matching_attributes:
                raise AssertionError(
                    f"{os.path.basename(filepath)}:{obj.name} is missing vertex color layer '{layer_name}'"
                )
            color_attr = matching_attributes[0]
        else:
            color_attr = color_attributes[0]

        actual_colors = _collect_unique_attribute_colors(color_attr)
        expected_colors = sorted(tuple(color) for color in expected_color_info["colors"])
        if actual_colors != expected_colors:
            raise AssertionError(
                f"{os.path.basename(filepath)}:{obj.name} vertex colors mismatch. "
                f"actual={actual_colors} expected={expected_colors}"
            )

    armature_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    actual_armature_names = sorted(obj.name for obj in armature_objects)
    expected_armature_names = sorted(expected_armatures.keys())
    if actual_armature_names != expected_armature_names:
        raise AssertionError(
            f"{os.path.basename(filepath)}: unexpected armature names. "
            f"actual={actual_armature_names} expected={expected_armature_names}"
        )

    for armature_obj in armature_objects:
        armature_name = armature_obj.name
        expected_bones = expected_armatures[armature_name]
        actual_bones = {
            bone.name: bone
            for bone in armature_obj.data.bones
            if not is_fbx_leaf_bone_name(bone.name)
        }
        actual_bone_names = sorted(actual_bones.keys())
        expected_bone_names = sorted(expected_bones.keys())
        if actual_bone_names != expected_bone_names:
            raise AssertionError(
                f"{os.path.basename(filepath)}:{armature_name} bone names mismatch. "
                f"actual={actual_bone_names} expected={expected_bone_names}"
            )
        for bone_name, expected_parent_name in expected_bones.items():
            bone = actual_bones[bone_name]
            actual_parent_name = bone.parent.name if bone.parent else None
            if actual_parent_name != expected_parent_name:
                raise AssertionError(
                    f"{os.path.basename(filepath)}:{armature_name}:{bone_name} parent mismatch. "
                    f"actual={actual_parent_name} expected={expected_parent_name}"
                )

    log(f"Validated {os.path.basename(filepath)}")


def validate_exported_outputs(expected_files):
    for filename, expected in expected_files.items():
        validate_exported_file(os.path.join(OUTPUT_DIR, filename), expected)


def format_exception(prefix, exc):
    return f"{prefix}: {type(exc).__name__}: {exc}"


def traceback_text():
    return traceback.format_exc()
