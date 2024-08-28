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
from .scripts.funcs.utils import func_package_utils


bl_info = {
    "name" : "MizoresCustomExporter",
    "author" : "@sleetcat123(Twitter)",
    "version" : (1,0,0),
    "blender" : (2, 80, 0),
    "location": "File > Export > Mizore's Custom Exporter",
    "description" : "Custom exporter by Mizore Nekoyanagi",
    "category" : "Import-Export"
}

if 'bpy' in locals():
    from importlib import reload
    import sys
    for k, v in list(sys.modules.items()):
        if k.startswith(func_package_utils.get_package_root()):
            reload(v)
else:
    from .scripts import (
        consts,
        preferences_scene,
        translations,
    )
    from .scripts.custom_exporter_fbx import (
        op_core,
        op_remove_saved_path,
        op_save_export_settings,
        panel_export_armature,
        panel_export_automerge,
        panel_export_bake_animation,
        panel_export_geometry,
        panel_export_include,
        panel_export_main,
        panel_export_shapekeysutil,
        panel_export_transform,
    )
    from .scripts.menu import (
        menu_object_context,
    )
    from .scripts.ops import (
        op_assign_prop,
        op_convert_collections,
        op_remove_export_prefs,
    )


classes = [
    consts,
    preferences_scene,
    translations,

    op_core,
    op_remove_saved_path,
    op_save_export_settings,
    panel_export_armature,
    panel_export_automerge,
    panel_export_bake_animation,
    panel_export_geometry,
    panel_export_include,
    panel_export_main,
    panel_export_shapekeysutil,
    panel_export_transform,

    menu_object_context,
    op_assign_prop,
    op_convert_collections,
    op_remove_export_prefs,
]


def register():
    for cls in classes:
        try:
            getattr(cls, "register", None)()
        except Exception as e:
            print(e)


def unregister():
    for cls in classes:
        try:
            getattr(cls, "unregister", None)()
        except Exception as e:
            print(e)


if __name__ == "__main__":
    register()
