import bpy
from mathutils import Matrix
from .. import consts
from ..funcs import func_addon_link
from ..funcs.utils import func_object_utils, func_custom_props_utils
from ..funcs import func_remove_unused_groups, func_remove_groups_not_bones

def export_preprocess(operator, ignore_collection):
        # Armatureのポーズをリセットする
    selected_objects = bpy.context.selected_objects
    for obj in selected_objects:
        if obj.type != 'ARMATURE':
            continue
        if not func_custom_props_utils.prop_is_true(obj, consts.RESET_POSE_GROUP_NAME):
            continue
        print("Reset Pose: " + obj.name)
        for pose_bone in obj.pose.bones:
            pose_bone.matrix_basis = Matrix()

    # シェイプキーをリセットする
    for obj in selected_objects:
        if not func_custom_props_utils.prop_is_true(obj, consts.RESET_SHAPEKEY_GROUP_NAME):
            continue
        if not obj.data or not hasattr(obj.data, 'shape_keys') or not hasattr(obj.data.shape_keys, 'key_blocks'):
            continue
        print("Reset ShapeKey: " + obj.name)
        obj.show_only_shape_key = False
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.value = 0.0

    # ↓ AutoMergeアドオン連携
    if operator.enable_auto_merge:
        try:
            if ignore_collection:
                ignore_collection_name = ignore_collection.name
            else:
                ignore_collection_name = ""
            # オブジェクトを結合
            b = bpy.ops.object.apply_modifier_and_merge_grouped_exporter_addon(
                enable_apply_modifiers_with_shapekeys=operator.enable_apply_modifiers_with_shapekeys,
                ignore_collection_name=ignore_collection_name,
                ignore_prop_name=consts.DONT_EXPORT_GROUP_NAME
            )
            # 結合処理失敗
            if 'FINISHED' not in b:
                # 複製されたオブジェクトを削除
                func_object_utils.remove_objects(selected_objects)
                return {'FAILED'}
        except AttributeError as e:
            t = "!!! Failed to load AutoMerge !!!"
            print(t)
            print(str(e))
    # ↑ AutoMergeアドオン連携

    print("xxxxxx Export Targets xxxxxx\n" + '\n'.join(
        [obj.name for obj in bpy.context.selected_objects]) + "\nxxxxxxxxxxxxxxx")

    # ShapeKeysUtil連携
    if func_addon_link.shapekey_util_is_found():
        if operator.enable_apply_modifiers_with_shapekeys and operator.use_mesh_modifiers:
            active = func_object_utils.get_active_object()
            selected_objects = bpy.context.selected_objects
            all_export_targets = [d for d in selected_objects if d.type == 'MESH']
            for obj in all_export_targets:
                func_object_utils.set_active_object(obj)
                bpy.ops.object.shapekeys_util_apply_mod_for_exporter_addon()
            # 選択オブジェクトを復元
            for obj in selected_objects:
                obj.select_set(True)
            func_object_utils.set_active_object(active)
        if operator.enable_separate_lr_shapekey:
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH' and obj.data.shape_keys is not None and len(
                        obj.data.shape_keys.key_blocks) != 0:
                    func_object_utils.set_active_object(obj)
                    bpy.ops.object.shapekeys_util_separate_lr_shapekey_for_exporter()
    else:
        t = "!!! Failed to load ShapeKeysUtil !!! - apply_modifiers_with_shapekeys"
        print(t)
        operator.report({'ERROR'}, t)

    # Transform操作
    temp_selected = bpy.context.selected_objects
    temp_active = func_object_utils.get_active_object()
    for obj in temp_selected:
        if func_custom_props_utils.prop_is_true(obj, consts.MOVE_TO_ORIGIN_GROUP_NAME):
            # オブジェクトを原点に移動する
            print("Move To Origin: " + obj.name)
            obj.location = (0, 0, 0)
        
        apply_location = func_custom_props_utils.prop_is_true(obj, consts.APPLY_LOCATIONS_GROUP_NAME)
        apply_rotation = func_custom_props_utils.prop_is_true(obj, consts.APPLY_ROTATIONS_GROUP_NAME)
        apply_scale = func_custom_props_utils.prop_is_true(obj, consts.APPLY_SCALES_GROUP_NAME)
        if apply_location or apply_rotation or apply_scale:
            # Transformを適用する
            print(f"Apply: {obj.name} - Location: {apply_location} / Rotation: {apply_rotation} / Scale: {apply_scale}")
            func_object_utils.deselect_all_objects()
            func_object_utils.select_object(obj)
            func_object_utils.set_active_object(obj)
            bpy.ops.object.transform_apply(location=apply_location, rotation=apply_rotation, scale=apply_scale)
    func_object_utils.select_objects(temp_selected, True)
    func_object_utils.set_active_object(temp_active)
    
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            if func_custom_props_utils.prop_is_true(obj, consts.REMOVE_GROUPS_NOT_BONE_GROUP_NAME):
                # ボーン名以外の頂点グループを削除
                func_object_utils.set_active_object(obj)
                func_remove_groups_not_bones.remove_groups_not_bones()
            if func_custom_props_utils.prop_is_true(obj, consts.REMOVE_UNUSED_GROUPS_GROUP_NAME):
                # 使用されていない頂点グループを削除
                func_object_utils.set_active_object(obj)
                func_remove_unused_groups.remove_unused_groups(search_data_transfer_modifier=True)

    # if operator.bake_anim and operator.bake_anim_use_ik_constraint == False:
    #     # IK制約を無効化
    #     for obj in bpy.context.selected_objects:
    #         if obj.type == 'ARMATURE':
    #             for bone in obj.pose.bones:
    #                 for c in bone.constraints:
    #                     if c.type == 'IK':
    #                         c.enabled = False