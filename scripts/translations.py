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
from . import func_package_utils


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
