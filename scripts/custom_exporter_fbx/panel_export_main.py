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
import os
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData


class MIZORE_FBX_PT_export_main(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = ""
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        row = layout.row(align=True)
        row.prop(operator, "path_mode")
        sub = row.row(align=True)
        sub.enabled = (operator.path_mode == 'COPY')
        sub.prop(operator, "embed_textures", text="", icon='PACKAGE' if operator.embed_textures else 'UGLYPACKAGE')

        row = layout.row(align=True)
        row.prop(operator, "batch_mode")
        sub = row.row(align=True)
        sub.prop(operator, "use_batch_own_dir", text="", icon='NEWFOLDER')

        row = layout.row(align=True)
        row.enabled = (
                operator.batch_mode == 'COLLECTION' or
                operator.batch_mode == 'SCENE_COLLECTION' or
                operator.batch_mode == 'ACTIVE_SCENE_COLLECTION'
        )
        row.prop(operator, "only_root_collection")

        BatchExportFilepathFormatData.update_batch_filename_format(operator)
        use_batch = (operator.batch_mode != 'OFF')
        sub = layout.column(heading="Batch Filename Format")
        sub.enabled = use_batch
        row = sub.row(align=True)
        row.prop(operator, "batch_filename_format")
        row = sub.row(align=True)
        row.prop(operator, "batch_filename_format_presets")
        # TODO: Batch対象となるコレクションを選択できるようにしたい
        if use_batch:
            # プレビュー
            preview = BatchExportFilepathFormatData.convert_filename_format(
                format_str=bpy.path.basename(operator.batch_filename_format),
                path=operator.filepath,
                batch="BATCH",
                use_batch_own_dir=operator.use_batch_own_dir,
                fullpath=False
            )
            row = sub.row(align=True)
            row.label(text=preview)

            preview = BatchExportFilepathFormatData.convert_filename_format(
                format_str=operator.batch_filename_format,
                path=operator.filepath,
                batch="BATCH",
                use_batch_own_dir=operator.use_batch_own_dir,
                fullpath=True
            )
            row = sub.row(align=True)
            row.label(text=preview)


def register():
    bpy.utils.register_class(MIZORE_FBX_PT_export_main)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_main)
