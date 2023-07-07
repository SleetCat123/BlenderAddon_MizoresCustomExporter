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

from ... import consts


def add_suffix(obj):
    if consts.EXPORT_TEMP_SUFFIX not in obj.name:
        new_name = obj.name + consts.EXPORT_TEMP_SUFFIX
        print("Add Suffix (Object name): [" + obj.name + "] -> [" + new_name + "]")
        obj.name = new_name

    # インスタンス化されたメッシュがあるとインスタンスの個数分だけ関数が呼ばれるため、suffixが多重追加されないように対策しておく
    if obj.data is not None and consts.EXPORT_TEMP_SUFFIX not in obj.data.name:
        new_name = obj.data.name + consts.EXPORT_TEMP_SUFFIX
        print("Add Suffix (Data name): [" + obj.data.name + "] -> [" + new_name + "]")
        obj.data.name = new_name


def remove_suffix(obj):
    if consts.EXPORT_TEMP_SUFFIX in obj.name:
        old_name = obj.name
        new_name = old_name[0:old_name.rfind(consts.EXPORT_TEMP_SUFFIX)]
        print("Remove Suffix (Object name): [" + old_name + "] -> [" + new_name + "]")
        obj.name = new_name

    if obj.data is not None and consts.EXPORT_TEMP_SUFFIX in obj.data.name:
        old_name = obj.data.name
        new_name = old_name[0:old_name.rfind(consts.EXPORT_TEMP_SUFFIX)]
        print("Remove Suffix (Data name): [" + old_name + "] -> [" + new_name + "]")
        obj.data.name = new_name
