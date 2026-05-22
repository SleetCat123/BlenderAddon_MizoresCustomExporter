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

from ..export_sets.panel_export_sets import draw_export_sets_editor
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData


STANDARD_BATCH_MODES = {
    'SCENE',
    'COLLECTION',
    'SCENE_COLLECTION',
    'ACTIVE_SCENE_COLLECTION',
    'COLLECTIONS_IN_ACTIVE_COLLECTION',
    'OBJECTS_IN_ACTIVE_COLLECTION',
}


class MIZORE_FBX_PT_export_batch(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Batch"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator
        props = context.scene.mizore_export_sets
        enabled_count = sum(1 for export_set in props.export_sets if export_set.enabled)

        row = layout.row(align=True)
        row.prop(operator, "batch_mode")
        sub = row.row(align=True)
        sub.enabled = operator.batch_mode in STANDARD_BATCH_MODES
        sub.prop(operator, "use_batch_own_dir", text="", icon='NEWFOLDER')

        row = layout.row(align=True)
        row.enabled = operator.batch_mode in {
            'COLLECTION',
            'SCENE_COLLECTION',
            'ACTIVE_SCENE_COLLECTION',
            'COLLECTIONS_IN_ACTIVE_COLLECTION',
        }
        row.prop(operator, "use_batch_collection_children_collections")

        row = layout.row(align=True)
        row.enabled = operator.batch_mode in {
            'COLLECTION',
            'SCENE_COLLECTION',
            'ACTIVE_SCENE_COLLECTION',
            'COLLECTIONS_IN_ACTIVE_COLLECTION',
        }
        row.prop(operator, "only_root_collection")

        if operator.batch_mode == 'EXPORT_SETS':
            layout.separator()
            layout.label(text=f"Enabled Sets: {enabled_count}", translate=False)
            if enabled_count == 0:
                layout.label(text="No enabled export sets.", icon='ERROR')
            layout.label(text="Filenames are taken from Export Sets.", icon='INFO')
            box = layout.box()
            draw_export_sets_editor(box, context)
            return

        BatchExportFilepathFormatData.update_batch_filename_format(operator)
        use_batch = operator.batch_mode in STANDARD_BATCH_MODES

        sub = layout.column(heading="Batch Filename Format")
        sub.enabled = use_batch
        row = sub.row(align=True)
        row.prop(operator, "batch_filename_format")
        row = sub.row(align=True)
        row.prop(operator, "batch_filename_format_presets")

        if use_batch:
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
    bpy.utils.register_class(MIZORE_FBX_PT_export_batch)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_batch)
