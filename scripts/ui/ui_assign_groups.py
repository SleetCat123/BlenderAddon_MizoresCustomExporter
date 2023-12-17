import bpy
from ..ops import op_assign_collection
from .. import consts

def draw_button(layout, group_name: str, assign: bool):
    assign_collection_id = op_assign_collection.OBJECT_OT_mizore_assign_group.bl_idname
    if assign:
        label = bpy.app.translations.pgettext(assign_collection_id + ".Assign")
    else:
        label = bpy.app.translations.pgettext(assign_collection_id + ".Remove")
    label = label.format(group_name)
    
    op = layout.operator(assign_collection_id, text=label)
    op.name = group_name
    op.assign = True


def draw(layout):
    # TODO: モディファイアの"AS"追加・解除ボタン

    wm = bpy.context.window_manager
    # Assign
    layout.label(text=bpy.app.translations.pgettext("mizores_custom_exporter_group_panel_assign"))
    draw_button(layout, consts.DONT_EXPORT_GROUP_NAME, True)
    draw_button(layout, consts.ALWAYS_EXPORT_GROUP_NAME, True)
    draw_button(layout, consts.RESET_POSE_GROUP_NAME, True)
    draw_button(layout, consts.RESET_SHAPEKEY_GROUP_NAME, True)
    # AutoMerge連携
    group_name = wm.mizore_automerge_collection_name
    if group_name:
        draw_button(layout, group_name, True)
    # AutoMerge連携
    group_name = wm.mizore_automerge_dont_merge_to_parent_collection_name
    if group_name:
        draw_button(layout, group_name, True)

    # Remove
    layout.label(text=bpy.app.translations.pgettext("mizores_custom_exporter_group_panel_assign"))
    draw_button(layout, consts.DONT_EXPORT_GROUP_NAME, False)
    draw_button(layout, consts.ALWAYS_EXPORT_GROUP_NAME, False)
    draw_button(layout, consts.RESET_POSE_GROUP_NAME, False)
    draw_button(layout, consts.RESET_SHAPEKEY_GROUP_NAME, False)
    # AutoMerge連携
    group_name = wm.mizore_automerge_collection_name
    if group_name:
        draw_button(layout, group_name, False)
    # AutoMerge連携
    group_name = wm.mizore_automerge_dont_merge_to_parent_collection_name
    if group_name:
        draw_button(layout, group_name, False)
