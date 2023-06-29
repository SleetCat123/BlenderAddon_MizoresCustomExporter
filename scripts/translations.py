# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from . import consts, func_package_utils
from .operator_assign_collection import OBJECT_OT_specials_assign_always_export_group as assign_always_export_group
from .operator_assign_collection import OBJECT_OT_specials_assign_dont_export_group as assign_dont_export_group
from .operator_remove_export_prefs import OBJECT_OT_mizore_remove_export_path as remove_export_path
from .operator_remove_export_prefs import OBJECT_OT_mizore_remove_export_settings as remove_export_settings


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
            "!!! Please be careful if you plan to send blend file to others",
        ("*", assign_dont_export_group.bl_idname + consts.DESC):
            f"Assign or removes the selected object(s) to or from the collection \"{consts.DONT_EXPORT_GROUP_NAME}\"",
        ("*", assign_always_export_group.bl_idname + consts.DESC):
            f"Assign or removes the selected object(s) to or from the collection \"{consts.ALWAYS_EXPORT_GROUP_NAME}\"",
        ("*", remove_export_path.bl_idname + consts.DESC): "Remove export destination settings saved in this blend file",
        ("*", remove_export_settings.bl_idname + consts.DESC): "Remove export settings saved in this blend file",
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
            "!!! blendファイルを他人に送る予定がある方は注意して使用してください。",
        ("*", assign_dont_export_group.bl_idname + consts.DESC):
            "選択中のオブジェクトを\nコレクション“" + consts.DONT_EXPORT_GROUP_NAME + "”に入れたり外したりします",
        ("*", assign_always_export_group.bl_idname + consts.DESC):
            "選択中のオブジェクトを\nコレクション" + consts.ALWAYS_EXPORT_GROUP_NAME + "”に入れたり外したりします",
        ("*", remove_export_path.bl_idname + consts.DESC): "現在のblendファイルに保存されているエクスポート先の設定を削除します",
        ("*", remove_export_settings.bl_idname + consts.DESC): "現在のblendファイルに保存されているエクスポート設定を削除します",
    },
}


def register():
    bpy.app.translations.register(func_package_utils.get_package_root(), translations_dict)


def unregister():
    bpy.app.translations.unregister(func_package_utils.get_package_root())
