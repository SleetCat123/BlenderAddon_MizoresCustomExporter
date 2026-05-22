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
    "version" : (1,2,0),
    "blender" : (2, 80, 0),
    "location": "File > Export > Mizore's Custom Exporter",
    "description" : "Custom exporter by Mizore Nekoyanagi",
    "category" : "Import-Export"
}

if 'bpy' in locals():
    import sys
    from importlib import reload
    for k, v in list(sys.modules.items()):
        if k.startswith(func_package_utils.get_package_root()):
            reload(v)
else:
    from .scripts import (
        consts,
        export_sets,
        preferences_scene,
        shapekey_operations,
        translations,
    )
    from .scripts.assign_prop_panel import (
        register_classes,
    )
    from .scripts.custom_exporter_fbx import (
        op_core,
        op_export_result_dialog,
        op_remove_export_prefs,
        op_remove_saved_path,
        op_save_export_settings,
        panel_export_armature,
        panel_export_automerge,
        panel_export_batch,
        panel_export_bake_animation,
        panel_export_geometry,
        panel_export_include,
        panel_export_main,
        panel_export_modifier_filter,
        panel_export_modify,
        panel_export_shapekeysutil,
        panel_export_transform,
    )
    from .scripts.menu import (
        menu_object_context,
    )
    from .scripts.ops import (
        op_convert_collections,
    )
    from .scripts.panels import (
        panel_assign_object_groups,
        panel_object_list,
    )

import bpy

classes = [
    consts,
    export_sets,
    preferences_scene,
    translations,

    register_classes,
    panel_assign_object_groups,
    panel_object_list,
    shapekey_operations,

    op_core,
    op_export_result_dialog,
    op_remove_saved_path,
    op_save_export_settings,
    panel_export_armature,
    panel_export_automerge,
    panel_export_batch,
    panel_export_bake_animation,
    panel_export_geometry,
    panel_export_include,
    panel_export_main,
    panel_export_modifier_filter,
    panel_export_modify,
    panel_export_shapekeysutil,
    panel_export_transform,

    menu_object_context,
    op_convert_collections,
    op_remove_export_prefs,
]


def register():
    for cls in classes:
        try:
            register_func = getattr(cls, "register", None)
            if register_func:
                register_func()
        except Exception as e:
            print(f"Error registering {cls.__name__}: {str(e)}")
            import traceback
            traceback.print_exc()


def unregister():
    for cls in classes:
        try:
            unregister_func = getattr(cls, "unregister", None)
            if unregister_func:
                unregister_func()
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    register()
