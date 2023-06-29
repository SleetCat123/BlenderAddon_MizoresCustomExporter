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


bl_info = {
    "name" : "MizoresCustomExporter",
    "author" : "@sleetcat123(Twitter)",
    "version" : (1,0,0),
    "blender" : (2, 80, 0),
    "location": "File > Export > Mizore's Custom Exporter",
    "description" : "Custom exporter by Mizore Nekoyanagi",
    "category" : "Import-Export"
}


def reload():
    import importlib
    for file in files:
        importlib.reload(file)


try:
    is_loaded
    reload()
except NameError:
    from .scripts import (
        consts,
        func_addon_link,
        func_collection_utils,
        func_name_utils,
        func_object_utils,
        func_package_utils,
        menu_object_context,
        operator_assign_collection,
        operator_remove_export_prefs,
        panel_assign_groups,
        panel_object_list,
        preferences_scene,
        translations,
    )
    from .scripts.operator_custom_exporter_fbx import (
        operator_core,
        func_execute_main,
        func_isvalid,
    )
    from .scripts.panel_export import (
        panel_export_main,
        panel_export_include,
        panel_export_transform,
        panel_export_geometry,
        panel_export_armature,
        panel_export_bake_animation,
        panel_export_automerge,
        panel_export_shapekeysutil,
    )

files = [
    consts,
    func_addon_link,
    func_collection_utils,
    func_name_utils,
    func_object_utils,
    func_package_utils,
    menu_object_context,
    operator_assign_collection,
    operator_remove_export_prefs,
    panel_assign_groups,
    panel_object_list,
    preferences_scene,
    translations,

    operator_core,
    func_execute_main,
    func_isvalid,

    panel_export_main,
    panel_export_include,
    panel_export_transform,
    panel_export_geometry,
    panel_export_armature,
    panel_export_bake_animation,
    panel_export_automerge,
    panel_export_shapekeysutil,
]

is_loaded = False


def register():
    global is_loaded
    if is_loaded:
        reload()
    for file in files:
        func = getattr(file, "register", None)
        if callable(func):
            func()
    is_loaded = True


def unregister():
    for file in files:
        func = getattr(file, "unregister", None)
        if callable(func):
            func()


if __name__ == "__main__":
    register()
