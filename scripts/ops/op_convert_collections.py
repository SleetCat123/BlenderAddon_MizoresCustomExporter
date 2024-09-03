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
from ..funcs.utils import func_collection_utils, func_custom_props_utils, func_object_utils


class OBJECT_OT_mizore_convert_collections(bpy.types.Operator):
    bl_idname = "object.mizore_convert_collections"
    bl_label = "Convert Collections"
    bl_description = "Convert collections to CustomProperty (DontExport, AlwaysExport, MergeGroup)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wm = bpy.types.WindowManager
        collection_names = [
            consts.DONT_EXPORT_GROUP_NAME,
            consts.ALWAYS_EXPORT_GROUP_NAME,
        ]
        if hasattr(wm, "mizore_automerge_collection_name"):
            collection_names.append(wm.mizore_automerge_collection_name)

        func_object_utils.deselect_all_objects()
        for collection_name in collection_names:
            print(collection_name)
            collection = func_collection_utils.find_collection(collection_name)
            if not collection:
                continue
            objects = func_collection_utils.get_collection_objects(collection, include_children_collections=True)
            print([v.name for v in objects])
            for obj in objects:
                func_object_utils.force_unhide(obj)
                func_object_utils.select_object(obj)
            func_custom_props_utils.assign_bool_prop(
                target=objects,
                prop_name=collection_name,
                value=True,
                remove_if_false=True
            )
            # collection意外のコレクションに属していないオブジェクトはシーンコレクションに移動
            func_collection_utils.assign_object_group(collection_name, False)
            self.report({'INFO'}, f"{collection_name} converted")
        return {'FINISHED'}


translations_dict = {
    "ja_JP": {
        ("*", "Convert collections to CustomProperty (DontExport, AlwaysExport, MergeGroup)"): "コレクションをCustomPropertyに変換します。(DontExport, AlwaysExport, MergeGroup)",
    },
}


classes = [
    OBJECT_OT_mizore_convert_collections,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
