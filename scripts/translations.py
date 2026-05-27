import bpy

from .funcs.utils import func_package_utils

translations_dict = {
    "en_US": {
        ("*", "box_warning_slow_method_1"): "Warning: ",
        ("*", "box_warning_slow_method_2"): "If using this setting",
        ("*", "box_warning_slow_method_3"): "may take a while in progress.",

        # {0}=最大文字数
        # {1}=オブジェクト名
        # {2}=オブジェクト名の文字数
        ("*",
         "error_longname_object"): "The object name is too long so must be {0} characters or less.\n"
                                   "Name: {1}\n"
                                   "({2}characters)",
        # {0}=最大文字数
        # {1}=オブジェクト名
        # {2}=オブジェクトデータ名
        # {3}=オブジェクトデータ名の文字数
        ("*",
         "error_longname_data"): "The object data name is too long so must be {0} characters or less.\n"
                                 "Object: {1}\n"
                                 "Data Name: {2}\n"
                                 "({3}characters)",

        # Progress messages - func_execute_main
        ("*", "mce_progress_initializing"): "Initializing export",
        ("*", "mce_progress_starting_preprocess"): "Starting preprocess",
        ("*", "mce_progress_exporting_fbx"): "Exporting FBX",
        ("*", "mce_progress_export_complete"): "Export complete",

        # Progress messages - func_export_preprocess
        ("*", "mce_progress_reset_pose"): "Reset Pose",
        ("*", "mce_progress_reset_shapekey"): "Reset ShapeKey",
        ("*", "mce_progress_apply_shapekeys_before"): "Apply/Clear ShapeKeys (Before Merge)",
        ("*", "mce_progress_automerge"): "AutoMerge",
        ("*", "mce_progress_shapekeysutil"): "ShapeKeysUtil",
        ("*", "mce_progress_apply_modifiers"): "Apply Modifiers: {obj}",
        ("*", "mce_progress_separate_lr_shapekey"): "Separate LR ShapeKey",
        ("*", "mce_progress_separate_lr_shapekey_obj"): "Separate LR ShapeKey: {obj} ({current}/{total})",
        ("*", "mce_progress_subtract_base_shapekey"): "Subtract Base ShapeKey",
        ("*", "mce_progress_subtract_base_shapekey_obj"): "Subtract Base ShapeKey: {obj} ({current}/{total})",
        ("*", "mce_progress_reorder_shapekeys"): "Reorder ShapeKeys",
        ("*", "mce_progress_reorder_shapekeys_obj"): "Reorder ShapeKeys: {obj} ({current}/{total})",
        ("*", "mce_progress_transform"): "Transform",
        ("*", "mce_progress_modify"): "Modify",
        ("*", "mce_progress_limit_vertex_groups"): "Limit Vertex Groups ({current}/{total})",
        ("*", "mce_progress_limit_vertex_groups_obj"): "Limit Vertex Groups: {obj} ({current}/{total})",
        ("*", "mce_progress_apply_shapekeys_after"): "Apply/Clear ShapeKeys (After Merge)",
        ("*", "mce_progress_constraints"): "Constraints",
        ("*", "mce_progress_preprocess_complete"): "Preprocess Complete",
    },
    "ja_JP": {
        ("*", "box_warning_slow_method_1"): "注意：",
        ("*", "box_warning_slow_method_2"): "この項目を有効にすると",
        ("*", "box_warning_slow_method_3"): "処理に時間がかかる場合があります。",

        ("*", "error_longname_object"): "オブジェクト名が長すぎます。\n"
                                        "エクスポートするオブジェクトの名前は{0}文字以下である必要があります。\n"
                                        "{1}\n"
                                        "（{2}文字）",
        ("*",
         "error_longname_data"): "オブジェクトのデータ名が長すぎます。\n"
                                 "エクスポートするオブジェクトのデータの名前は{0}文字以下である必要があります。\n"
                                 "オブジェクト: {1}\n"
                                 "{2}\n"
                                 "（{3}文字）",

        # Progress messages - func_execute_main
        ("*", "mce_progress_initializing"): "エクスポート初期化中",
        ("*", "mce_progress_starting_preprocess"): "前処理開始",
        ("*", "mce_progress_exporting_fbx"): "FBXエクスポート中",
        ("*", "mce_progress_export_complete"): "エクスポート完了",

        # Progress messages - func_export_preprocess
        ("*", "mce_progress_reset_pose"): "ポーズリセット",
        ("*", "mce_progress_reset_shapekey"): "シェイプキーリセット",
        ("*", "mce_progress_apply_shapekeys_before"): "シェイプキー適用/クリア (マージ前)",
        ("*", "mce_progress_automerge"): "AutoMerge処理",
        ("*", "mce_progress_shapekeysutil"): "ShapeKeysUtil処理",
        ("*", "mce_progress_apply_modifiers"): "モディファイア適用: {obj}",
        ("*", "mce_progress_separate_lr_shapekey"): "左右シェイプキー分割",
        ("*", "mce_progress_separate_lr_shapekey_obj"): "左右シェイプキー分割: {obj} ({current}/{total})",
        ("*", "mce_progress_subtract_base_shapekey"): "基準シェイプキー差分",
        ("*", "mce_progress_subtract_base_shapekey_obj"): "基準シェイプキー差分: {obj} ({current}/{total})",
        ("*", "mce_progress_reorder_shapekeys"): "シェイプキー並び替え",
        ("*", "mce_progress_reorder_shapekeys_obj"): "シェイプキー並び替え: {obj} ({current}/{total})",
        ("*", "mce_progress_transform"): "トランスフォーム",
        ("*", "mce_progress_modify"): "修正処理",
        ("*", "mce_progress_limit_vertex_groups"): "頂点グループ数制限 ({current}/{total})",
        ("*", "mce_progress_limit_vertex_groups_obj"): "頂点グループ数制限: {obj} ({current}/{total})",
        ("*", "mce_progress_apply_shapekeys_after"): "シェイプキー適用/クリア (マージ後)",
        ("*", "mce_progress_constraints"): "コンストレイント処理",
        ("*", "mce_progress_preprocess_complete"): "前処理完了",
    },
}


def register():
    bpy.app.translations.register(func_package_utils.get_package_root(), translations_dict)


def unregister():
    bpy.app.translations.unregister(func_package_utils.get_package_root())
