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
    },
}


def register():
    bpy.app.translations.register(func_package_utils.get_package_root(), translations_dict)


def unregister():
    bpy.app.translations.unregister(func_package_utils.get_package_root())
