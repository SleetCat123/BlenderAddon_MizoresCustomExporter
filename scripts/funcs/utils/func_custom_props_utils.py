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
from . import func_object_utils


def select_if_prop_is_true(prop_name: str, select: bool = True):
    if select:
        targets = bpy.context.window.view_layer.objects
    else:
        targets = bpy.context.selected_objects
    for obj in targets:
        if prop_name in obj and obj[prop_name]:
            func_object_utils.select_object(obj, select)


def prop_is_true(obj, prop_name: str):
    return prop_name in obj and obj[prop_name]


def get_objects_prop_is_true(prop_name: str, only_current_view_layer: bool = True):
    if only_current_view_layer:
        targets = func_object_utils.get_current_view_layer_objects()
    else:
        targets = bpy.data.objects
    return [obj for obj in targets if prop_is_true(obj=obj, prop_name=prop_name)]


def assign_bool_prop(target, prop_name: str, value: bool, remove_if_false: bool):
    if isinstance(target, list):
        targets = target
    else:
        targets = [target]
    for t in targets:
        t[prop_name] = value
        if remove_if_false and not value:
            del t[prop_name]
