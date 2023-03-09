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
from .. import consts


def isvalid(operator):
    for obj in bpy.context.view_layer.objects:
        # 接尾辞をつけたときに名前の文字数が63文字（Blenderの最大文字数）を超えるオブジェクトがあるならエラー
        if consts.ACTUAL_MAX_NAME_LENGTH < len(obj.name):
            t = bpy.app.translations.pgettext("error_longname_object").format(
                str(consts.ACTUAL_MAX_NAME_LENGTH),
                obj.name,
                str(len(obj.name))
            )
            operator.report({'ERROR'}, t)
            return False
        if obj.data and consts.ACTUAL_MAX_NAME_LENGTH < len(obj.data.name):
            t = bpy.app.translations.pgettext("error_longname_data").format(
                str(consts.ACTUAL_MAX_NAME_LENGTH),
                obj.name,
                obj.data.name,
                str(len(obj.data.name))
            )
            operator.report({'ERROR'}, t)
            return False
    return True
