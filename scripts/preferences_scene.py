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
from bpy.props import StringProperty, IntProperty, CollectionProperty


class PR_IntPropertyCollection(bpy.types.PropertyGroup):
    value: IntProperty(name="", default=0)


class PR_StringPropertyCollection(bpy.types.PropertyGroup):
    value: StringProperty(name="", default="")


class PR_MizoreExporter_ScenePref(bpy.types.PropertyGroup):
    export_str_props: CollectionProperty(type=PR_StringPropertyCollection)
    export_int_props: CollectionProperty(type=PR_IntPropertyCollection)


def set_prop_col_value(prop, key, value):
    el = prop.get(key)
    if el is None:
        el = prop.add()
        el.name = key
    el.value = value


def clear_export_props():
    bpy.context.scene.mizore_exporter_prefs.export_str_props.clear()
    bpy.context.scene.mizore_exporter_prefs.export_int_props.clear()
    print("clear export props")


def remove_str_prop(key: str):
    prop = bpy.context.scene.mizore_exporter_prefs.export_str_props
    index = prop.find(key)
    if index != -1:
        print("remove prop: " + key)
        prop.remove(index)


def load_scene_prefs(operator):
    # シーンから設定を読み込み
    p_str = bpy.context.scene.mizore_exporter_prefs.export_str_props
    print("prop(str): " + str(len(p_str)))
    for i in range(len(p_str)):
        prop = p_str[i]
        key = prop.name
        value = prop.value
        print("load prop: " + key + ", " + str(value))
        operator.properties[key] = value

    p_int = bpy.context.scene.mizore_exporter_prefs.export_int_props
    print("prop(int): " + str(len(p_int)))
    for i in range(len(p_int)):
        prop = p_int[i]
        key = prop.name
        value = prop.value
        print("load prop: " + key + ", " + str(value))
        operator.properties[key] = value


def save_scene_prefs(operator, ignore_key=None):
    # シーンに設定を保存
    if ignore_key is None:
        ignore_key = []
    p_str = bpy.context.scene.mizore_exporter_prefs.export_str_props
    p_int = bpy.context.scene.mizore_exporter_prefs.export_int_props
    for key, value in operator.properties.items():
        if key in ignore_key:
            print("ignore prop: " + key)
            continue
        t = type(value)
        if t is str:
            print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
            set_prop_col_value(p_str, key, value)
        elif t is int:
            print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
            set_prop_col_value(p_int, key, value)
        else:
            print("!!! save prop failed: " + key + ", " + str(value) + ", " + str(type(value)))
    print("prop(str): " + str(len(p_str)))
    print("prop(int): " + str(len(p_int)))


classes = [
    PR_StringPropertyCollection, PR_IntPropertyCollection,
    PR_MizoreExporter_ScenePref,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mizore_exporter_prefs = bpy.props.PointerProperty(type=PR_MizoreExporter_ScenePref)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mizore_exporter_prefs
