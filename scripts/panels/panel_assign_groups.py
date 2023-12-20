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
            "_Export Target",
            consts.DONT_EXPORT_GROUP_NAME,
            consts.ALWAYS_EXPORT_GROUP_NAME,
            "_Reset",
            consts.RESET_POSE_GROUP_NAME,
            consts.RESET_SHAPEKEY_GROUP_NAME,
            "_Reset Always",
            consts.ALWAYS_RESET_SHAPEKEY_GROUP_NAME,
            "_Auto Merge",
            wm.mizore_automerge_collection_name,
            wm.mizore_automerge_dont_merge_to_parent_collection_name
        ]
        id = op_assign_collection.OBJECT_OT_mizore_assign_group.bl_idname
        for i, group_name in enumerate(groups):
            if group_name.startswith("_"):
                continue
            if not group_name:
                continue
            if i != 0 and groups[i - 1].startswith("_"):
                if i != 1:
                    layout.separator()
                layout.label(text=groups[i - 1][1:])
            row = layout.row(align=False)
            row.label(text=group_name)

            column = row.column(align=False)
            column.scale_x = 0.45
            op = column.operator(id, text=bpy.app.translations.pgettext(id + ".Set"))
            op.name = group_name
            op.assign = True

            column = row.column(align=False)
            column.scale_x = 0.45
            op = column.operator(id, text=bpy.app.translations.pgettext(id + ".Unset"))
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
