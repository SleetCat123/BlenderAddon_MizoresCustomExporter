import bpy
from . import consts
from .funcs.utils import func_package_utils
from .ops.op_assign_collection import OBJECT_OT_mizore_assign_group as assign_group
from .custom_exporter_fbx.op_core import OBJECT_OT_mizore_remove_saved_path as remove_export_path
from .ops.op_remove_export_prefs import OBJECT_OT_mizore_remove_export_settings as remove_export_settings
from .ops.op_convert_collections import OBJECT_OT_mizore_convert_collections as convert_collections


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

        ("*", "export_completed"): "Export completed.",
        ("*", "export_interrupted"): "Export interrupted.",

        ("*", "custom_export_mizore_fbx.save_path.desc"):
            "Export location is stored in the blend file.\n"
            "!!! Please be careful if you plan to send blend file to others"
            f"If you want to delete the saved path, execute {remove_export_path.bl_label}.\n",
        ("*", "custom_export_mizore_fbx.save_prefs.desc"):
            "Export settings are saved in a blend file.\n"
            f"If you want to delete the saved settings, execute {remove_export_settings.bl_label}.\n",

        ("*", assign_group.bl_idname + ".Set"): "Set",
        ("*", assign_group.bl_idname + ".Unset"): "Unset",
        ("*", assign_group.bl_idname + ".Set_Menu"): "Set {}",
        ("*", assign_group.bl_idname + ".Unset_Menu"): "Unset {}",
        ("*", assign_group.bl_idname + consts.DESC): "Assign or removes the selected object(s) to or from the collection",
        ("*", remove_export_path.bl_idname + consts.DESC): "Remove export destination settings saved in this blend file",
        ("*", remove_export_settings.bl_idname + consts.DESC): "Remove export settings saved in this blend file",

        ("*", "mizores_custom_exporter_group_panel_assign"): "Add to group",
        ("*", "mizores_custom_exporter_group_panel_remove"): "Remove from group",

        ("*", convert_collections.bl_idname + consts.DESC): "Convert collections such as AutoMerge to CustomProperty (new format)",
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

        ("*", "export_completed"): "エクスポートが完了しました。",
        ("*", "export_interrupted"): "エクスポートが中断されました。",

        ("*", "custom_export_mizore_fbx.save_path.desc"):
            "fbxの書き出し場所をblendファイルに記憶します。\n"
            "!!! blendファイルを他人に送る予定がある方は注意して使用してください。"
            f"保存された設定を削除したい場合は {remove_export_path.bl_label} を実行してください。\n",

        ("*", "custom_export_mizore_fbx.save_prefs.desc"): 
            "エクスポート設定をblendファイルに保存します。"
            f"保存された設定を削除したい場合は {remove_export_settings.bl_label} を実行してください。\n",

        ("*", assign_group.bl_idname + ".Set"): "登録",
        ("*", assign_group.bl_idname + ".Unset"): "解除",
        ("*", assign_group.bl_idname + ".Set_Menu"): "Set {}",
        ("*", assign_group.bl_idname + ".Unset_Menu"): "Unset {}",
        ("*", assign_group.bl_idname + consts.DESC): "選択中のオブジェクトを\nコレクションに入れたり外したりします",
        ("*", remove_export_path.bl_idname + consts.DESC): "現在のblendファイルに保存されているエクスポート先の設定を削除します",
        ("*", remove_export_settings.bl_idname + consts.DESC): "現在のblendファイルに保存されているエクスポート設定を削除します",

        ("*", "mizores_custom_exporter_group_panel_assign"): "グループに追加",
        ("*", "mizores_custom_exporter_group_panel_remove"): "グループから削除",

        ("*", convert_collections.bl_idname + consts.DESC): "AutoMerge等のコレクションをCustomProperty（新形式）に変換します",
    },
}


def register():
    bpy.app.translations.register(func_package_utils.get_package_root(), translations_dict)


def unregister():
    bpy.app.translations.unregister(func_package_utils.get_package_root())
