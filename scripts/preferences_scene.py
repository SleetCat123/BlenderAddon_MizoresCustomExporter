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

import json

import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, StringProperty


class PR_IntPropertyCollection(bpy.types.PropertyGroup):
    value: IntProperty(name="", default=0)


class PR_BoolPropertyCollection(bpy.types.PropertyGroup):
    value: BoolProperty(name="", default=False)


class PR_FloatPropertyCollection(bpy.types.PropertyGroup):
    value: FloatProperty(name="", default=0.0)


class PR_StringPropertyCollection(bpy.types.PropertyGroup):
    value: StringProperty(name="", default="")


class PR_MizoreExporter_ScenePref(bpy.types.PropertyGroup):
    export_str_props: CollectionProperty(type=PR_StringPropertyCollection)
    export_int_props: CollectionProperty(type=PR_IntPropertyCollection)
    export_bool_props: CollectionProperty(type=PR_BoolPropertyCollection)
    export_float_props: CollectionProperty(type=PR_FloatPropertyCollection)
    export_json_props: CollectionProperty(type=PR_StringPropertyCollection)


LEGACY_ENUM_VALUE_MAP = {
    "batch_mode": {
        0: 'OFF',
        1: 'SCENE',
        2: 'COLLECTION',
        3: 'SCENE_COLLECTION',
        4: 'ACTIVE_SCENE_COLLECTION',
        5: 'OBJECTS_IN_ACTIVE_COLLECTION',
        6: 'EXPORT_SETS',
    },
}


def set_prop_col_value(prop, key, value):
    el = prop.get(key)
    if el is None:
        el = prop.add()
        el.name = key
    el.value = value


def operator_has_property(operator, key):
    return get_operator_property_definition(operator, key) is not None


def get_operator_properties_collection(operator):
    properties = getattr(operator, "properties", None)
    if properties is not None:
        properties_rna = getattr(properties, "bl_rna", None)
        if properties_rna is not None:
            prop_collection = getattr(properties_rna, "properties", None)
            if prop_collection is not None:
                return prop_collection

    bl_rna = getattr(operator, "bl_rna", None)
    if bl_rna is not None:
        prop_collection = getattr(bl_rna, "properties", None)
        if prop_collection is not None:
            return prop_collection

    return None


def get_operator_property_definition(operator, key):
    prop_collection = get_operator_properties_collection(operator)
    if prop_collection is None:
        return None
    try:
        return prop_collection[key]
    except KeyError:
        return None


def set_operator_property(operator, key, value):
    if not operator_has_property(operator, key):
        print("skip missing prop: " + key)
        return False
    try:
        setattr(operator, key, value)
        return True
    except (AttributeError, TypeError, ValueError) as exc:
        print(f"failed to set prop: {key} -> {value!r} ({exc})")
        return False


def normalize_loaded_property_value(operator, key, value):
    prop_def = get_operator_property_definition(operator, key)
    if prop_def is None:
        return value

    if prop_def.type == 'ENUM':
        if getattr(prop_def, "is_enum_flag", False):
            if type(value) in {list, tuple}:
                return set(value)
            return value

        if type(value) is int:
            legacy_map = LEGACY_ENUM_VALUE_MAP.get(key)
            if legacy_map and value in legacy_map:
                return legacy_map[value]

            for enum_item in prop_def.enum_items:
                if enum_item.value == value:
                    return enum_item.identifier

    return value


def clear_export_props():
    bpy.context.scene.mizore_exporter_prefs.export_str_props.clear()
    bpy.context.scene.mizore_exporter_prefs.export_int_props.clear()
    bpy.context.scene.mizore_exporter_prefs.export_bool_props.clear()
    bpy.context.scene.mizore_exporter_prefs.export_float_props.clear()
    bpy.context.scene.mizore_exporter_prefs.export_json_props.clear()
    print("clear export props")


def remove_str_prop(key: str):
    prop = bpy.context.scene.mizore_exporter_prefs.export_str_props
    index = prop.find(key)
    if index != -1:
        print("remove prop: " + key)
        prop.remove(index)


def load_scene_prefs(operator):
    # シーンから設定を読み込み
    loaded_keys = set()

    def load_prop_collection(collection, label, value_loader=None):
        print(f"prop({label}): " + str(len(collection)))
        for i in range(len(collection)):
            prop = collection[i]
            key = prop.name
            if key in loaded_keys:
                print("skip prop because already loaded: " + key)
                continue
            raw_value = prop.value
            value = value_loader(raw_value) if value_loader else raw_value
            value = normalize_loaded_property_value(operator, key, value)
            print(f"load prop({label}): " + key + ", " + str(value))
            if set_operator_property(operator, key, value):
                loaded_keys.add(key)

    scene_prefs = bpy.context.scene.mizore_exporter_prefs
    load_prop_collection(scene_prefs.export_json_props, "json", json.loads)
    load_prop_collection(scene_prefs.export_str_props, "str")
    load_prop_collection(scene_prefs.export_bool_props, "bool")
    load_prop_collection(scene_prefs.export_float_props, "float")
    load_prop_collection(scene_prefs.export_int_props, "int")


def save_scene_prefs(operator, ignore_key=None):
    # シーンに設定を保存
    if ignore_key is None:
        ignore_key = []
    scene_prefs = bpy.context.scene.mizore_exporter_prefs
    p_str = scene_prefs.export_str_props
    p_int = scene_prefs.export_int_props
    p_bool = scene_prefs.export_bool_props
    p_float = scene_prefs.export_float_props
    p_json = scene_prefs.export_json_props

    prop_collection = get_operator_properties_collection(operator)
    if prop_collection is None:
        print("skip save_scene_prefs because operator properties are unavailable")
        return

    for prop_def in prop_collection:
        key = prop_def.identifier
        if key == "rna_type" or prop_def.is_readonly:
            continue
        if key in ignore_key:
            print("ignore prop: " + key)
            continue
        try:
            value = getattr(operator, key)
        except AttributeError:
            print("skip prop without value: " + key)
            continue
        if prop_def.type == 'ENUM':
            if getattr(prop_def, "is_enum_flag", False):
                json_value = json.dumps(sorted(value))
                print("save enum-flag prop: " + key + ", " + str(json_value))
                set_prop_col_value(p_json, key, json_value)
            else:
                print("save enum prop: " + key + ", " + str(value))
                set_prop_col_value(p_str, key, value)
            continue

        t = type(value)
        if t is bool:
            print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
            set_prop_col_value(p_bool, key, value)
        elif t is str:
            print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
            set_prop_col_value(p_str, key, value)
        elif t is int:
            print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
            set_prop_col_value(p_int, key, value)
        elif t is float:
            print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
            set_prop_col_value(p_float, key, value)
        else:
            print("!!! save prop failed: " + key + ", " + str(value) + ", " + str(type(value)))
    print("prop(str): " + str(len(p_str)))
    print("prop(int): " + str(len(p_int)))
    print("prop(bool): " + str(len(p_bool)))
    print("prop(float): " + str(len(p_float)))
    print("prop(json): " + str(len(p_json)))


classes = [
    PR_StringPropertyCollection, PR_IntPropertyCollection,
    PR_BoolPropertyCollection, PR_FloatPropertyCollection,
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
