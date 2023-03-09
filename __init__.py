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

import sys
import importlib

bl_info = {
    "name" : "MizoresCustomExporter",
    "author" : "@sleetcat123(Twitter)",
    "version" : (1,0,0),
    "blender" : (2, 80, 0),
    "location": "File > Export > Mizore's Custom Exporter",
    "description" : "Custom exporter by Mizore Nekoyanagi",
    "category" : "Import-Export"
}

imports = [
    "translations",
    "preferences_scene",
    "operator_custom_exporter_fbx",
    "panel_export_main",
    "panel_export_include",
    "panel_export_transform",
    "panel_export_geometry",
    "panel_export_armature",
    "panel_export_bake_animation",
    "panel_export_automerge",
    "panel_export_shapekeysutil",
    "operator_assign_collection",
    "menu_object_context",
]


def reload_modules():
    for name in imports:
        module_full_name = f"{__package__}.scripts.{name}"
        if module_full_name in sys.modules:
            importlib.reload(sys.modules[module_full_name])
        else:
            importlib.import_module(module_full_name)


def register():
    reload_modules()
    for name in imports:
        module_full_name = f"{__package__}.scripts.{name}"
        module = sys.modules[module_full_name]
        func = getattr(module, "register", None)
        if callable(func):
            func()


def unregister():
    for name in imports:
        module_full_name = f"{__package__}.scripts.{name}"
        module = sys.modules[module_full_name]
        func = getattr(module, "unregister", None)
        if callable(func):
            func()


if __name__ == "__main__":
    register()
