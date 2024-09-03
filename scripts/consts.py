import bpy


DONT_EXPORT_GROUP_NAME = "DontExport"  # エクスポートから除外するオブジェクトのグループ名
ALWAYS_EXPORT_GROUP_NAME = "AlwaysExport"  # 非表示状態であっても常にエクスポートさせるオブジェクトのグループ名
RESET_POSE_GROUP_NAME = "ResetPoseWhenExport"  # エクスポート時にポーズをリセットするオブジェクトのグループ名
RESET_SHAPEKEY_GROUP_NAME = "ResetShapekeysWhenExport"  # エクスポート時にシェイプキーをリセットするオブジェクトのグループ名
REMOVE_UNUSED_GROUPS_GROUP_NAME = "RemoveUnusedGroupsWhenExport"  # エクスポート時に未使用の頂点グループを削除するオブジェクトのグループ名
REMOVE_GROUPS_NOT_BONE_GROUP_NAME = "RemoveGroupsNotBoneNamesWhenExport"  # エクスポート時にボーン名以外の頂点グループを削除するオブジェクトのグループ名
MOVE_TO_ORIGIN_GROUP_NAME = "MoveToOriginWhenExport"  # エクスポート時に原点に移動するオブジェクトのグループ名
APPLY_LOCATIONS_GROUP_NAME = "ApplyLocationsWhenExport"  # エクスポート時に位置を適用するオブジェクトのグループ名
APPLY_ROTATIONS_GROUP_NAME = "ApplyRotationsWhenExport"  # エクスポート時に回転を適用するオブジェクトのグループ名
APPLY_SCALES_GROUP_NAME = "ApplyScalesWhenExport"  # エクスポート時にスケールを適用するオブジェクトのグループ名
ALWAYS_RESET_SHAPEKEY_GROUP_NAME = "AlwaysResetShapekeys"  # エクスポート時にシェイプキーをリセットするオブジェクトのグループ名（エクスポート対象外であっても常にリセット）

EXPORT_TEMP_SUFFIX = ".#MizoreCEx#"  # エクスポート処理時、一時的にオブジェクト名に付加する接尾辞
MAX_NAME_LENGTH = 63  # オブジェクト名などの最大文字数（Blender側の上限）
ACTUAL_MAX_NAME_LENGTH = MAX_NAME_LENGTH - len(EXPORT_TEMP_SUFFIX)  # オブジェクトなどの名前として実際に使用可能な最大文字数

ADDON_NAME = "MizoreCustomExporter"


def register():
    bpy.types.WindowManager.mizore_exporter_dont_export_group_name = DONT_EXPORT_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_always_export_group_name = ALWAYS_EXPORT_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_reset_pose_group_name = RESET_POSE_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_reset_shapekey_group_name = RESET_SHAPEKEY_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_remove_unused_groups_group_name = REMOVE_UNUSED_GROUPS_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_remove_groups_not_bone_group_name = REMOVE_GROUPS_NOT_BONE_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_move_to_origin_group_name = MOVE_TO_ORIGIN_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_apply_locations_group_name = APPLY_LOCATIONS_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_apply_rotations_group_name = APPLY_ROTATIONS_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_apply_scales_group_name = APPLY_SCALES_GROUP_NAME
    bpy.types.WindowManager.mizore_exporter_always_reset_shapekey_group_name = ALWAYS_RESET_SHAPEKEY_GROUP_NAME


def unregister():
    del bpy.types.WindowManager.mizore_exporter_dont_export_group_name
    del bpy.types.WindowManager.mizore_exporter_always_export_group_name
    del bpy.types.WindowManager.mizore_exporter_reset_pose_group_name
    del bpy.types.WindowManager.mizore_exporter_reset_shapekey_group_name
    del bpy.types.WindowManager.mizore_exporter_remove_unused_groups_group_name
    del bpy.types.WindowManager.mizore_exporter_remove_groups_not_bone_group_name
    del bpy.types.WindowManager.mizore_exporter_move_to_origin_group_name
    del bpy.types.WindowManager.mizore_exporter_apply_locations_group_name
    del bpy.types.WindowManager.mizore_exporter_apply_rotations_group_name
    del bpy.types.WindowManager.mizore_exporter_apply_scales_group_name
    del bpy.types.WindowManager.mizore_exporter_always_reset_shapekey_group_name
