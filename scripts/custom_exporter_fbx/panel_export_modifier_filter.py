# モディファイアタイプフィルターパネル
#
# エクスポートオペレーターのファイルブラウザに
# モディファイアタイプごとの有効/無効チェックボックスを表示する。
# Blender APIから動的に取得したモディファイアタイプ一覧を使用する。

import bpy

from . import modifier_type_filter


class MIZORE_FBX_PT_export_modifier_filter(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Modifier Type Filter"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

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

        # use_mesh_modifiers が無効なら全体をdisabledに
        col = layout.column()
        col.enabled = operator.use_mesh_modifiers

        # カテゴリ別にbox表示（Blender APIから動的に取得）
        categorized = modifier_type_filter.get_categorized_modifier_types()
        for category_name, entries in categorized.items():
            box = col.box()
            box.label(text=category_name)
            box_col = box.column(align=True)
            for mod_type, _display_name in entries:
                prop_name = modifier_type_filter.get_property_name(mod_type)
                if hasattr(operator, prop_name):
                    box_col.prop(operator, prop_name)


def register():
    bpy.utils.register_class(MIZORE_FBX_PT_export_modifier_filter)


def unregister():
    bpy.utils.unregister_class(MIZORE_FBX_PT_export_modifier_filter)
