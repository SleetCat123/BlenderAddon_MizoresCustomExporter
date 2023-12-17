import bpy
from .. import consts
from ..ops import op_assign_collection


class OBJECT_PT_mizores_custom_exporter_group_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mizore"
    bl_label = "Assign Groups"

    def draw(self, context):
        # TODO: モディファイアの"AS"追加・解除ボタン
        layout = self.layout
        wm = bpy.context.window_manager
        groups = [
            consts.DONT_EXPORT_GROUP_NAME,
            consts.ALWAYS_EXPORT_GROUP_NAME,
            consts.RESET_POSE_GROUP_NAME,
            consts.RESET_SHAPEKEY_GROUP_NAME,
            wm.mizore_automerge_collection_name,
            wm.mizore_automerge_dont_merge_to_parent_collection_name
        ]
        id = op_assign_collection.OBJECT_OT_mizore_assign_group.bl_idname
        for group_name in groups:
            if not group_name:
                continue
            row = layout.row(align=False)
            row.label(text=group_name)

            op = row.operator(id, text=bpy.app.translations.pgettext(id + ".Set"))
            op.name = group_name
            op.assign = True

            op = row.operator(id, text=bpy.app.translations.pgettext(id + ".Unset"))
            op.name = group_name
            op.assign = False


classes = [
    OBJECT_PT_mizores_custom_exporter_group_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
