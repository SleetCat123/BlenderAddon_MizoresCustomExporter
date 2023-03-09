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
from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, CollectionProperty)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    orientation_helper,
    path_reference_mode,
    axis_conversion,
)
from . import consts, func_object_utils, func_name_utils, func_collection_utils, func_addon_link, preferences_scene


# エクスポート
@orientation_helper(axis_forward='-Z', axis_up='Y')
class INFO_MT_file_custom_export_mizore_fbx(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.custom_export_mizore_fbx"
    bl_label = "Mizore's Custom Exporter (.fbx)"
    bl_description = ""
    bl_options = {'UNDO', 'PRESET'}

    ######################################################
    # region From io_scene_fbx
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected and visible objects only",
        default=False,
    )
    use_active_collection: BoolProperty(
        name="Active Collection",
        description="Export only objects from the active collection (and its children)",
        default=False,
    )
    global_scale: FloatProperty(
        name="Scale",
        description="Scale all data (Some importers do not support scaled armatures!)",
        min=0.001, max=1000.0,
        soft_min=0.01, soft_max=1000.0,
        default=1.0,
    )
    apply_unit_scale: BoolProperty(
        name="Apply Unit",
        description="Take into account current Blender units settings (if unset, raw Blender Units values are used as-is)",
        default=True,
    )
    apply_scale_options: EnumProperty(
        items=(('FBX_SCALE_NONE', "All Local",
                "Apply custom scaling and units scaling to each object transformation, FBX scale remains at 1.0"),
               ('FBX_SCALE_UNITS', "FBX Units Scale",
                "Apply custom scaling to each object transformation, and units scaling to FBX scale"),
               ('FBX_SCALE_CUSTOM', "FBX Custom Scale",
                "Apply custom scaling to FBX scale, and units scaling to each object transformation"),
               ('FBX_SCALE_ALL', "FBX All",
                "Apply custom scaling and units scaling to FBX scale"),
               ),
        name="Apply Scalings",
        description="How to apply custom and units scalings in generated FBX file "
                    "(Blender uses FBX scale to detect units on import, "
                    "but many other applications do not handle the same way)",
        default='FBX_SCALE_UNITS'
    )  # デフォルト値をFBX_SCALE_UNITSに変更

    use_space_transform: BoolProperty(
        name="Use Space Transform",
        description="Apply global space transform to the object rotations. When disabled "
                    "only the axis space is written to the file and all object transforms are left as-is",
        default=True,
    )
    bake_space_transform: BoolProperty(
        name="Apply Transform",
        description="Bake space transform into object data, avoids getting unwanted rotations to objects when "
                    "target space is not aligned with Blender's space "
                    "(WARNING! experimental option, use at own risks, known broken with armatures/animations)",
        default=True,
    )  # デフォルト値をTrueに変更

    object_types: EnumProperty(
        name="Object Types",
        options={'ENUM_FLAG'},
        items=(('EMPTY', "Empty", ""),
               ('CAMERA', "Camera", ""),
               ('LIGHT', "Lamp", ""),
               ('ARMATURE', "Armature", "WARNING: not supported in dupli/group instances"),
               ('MESH', "Mesh", ""),
               ('OTHER', "Other", "Other geometry types, like curve, metaball, etc. (converted to meshes)"),
               ),
        description="Which kind of object to export",
        default={'ARMATURE', 'MESH'},
    )  # デフォルト値を{'ARMATURE', 'MESH'}に変更

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects (except Armature ones) - "
                    "WARNING: prevents exporting shape keys",
        default=True,
    )
    # use_mesh_modifiers_render: BoolProperty(
    #     name="Use Modifiers Render Setting",
    #     description="Use render settings when applying modifiers to mesh objects (DISABLED in Blender 2.8)",
    #     default=True,
    # )
    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        items=(('OFF', "Normals Only", "Export only normals instead of writing edge or face smoothing data"),
               ('FACE', "Face", "Write face smoothing"),
               ('EDGE', "Edge", "Write edge smoothing"),
               ),
        description="Export smoothing information "
                    "(prefer 'Normals Only' option if your target importer understand split normals)",
        default='OFF',
    )
    use_subsurf: BoolProperty(
        name="Export Subdivision Surface",
        description="Export the last Catmull-Rom subdivision modifier as FBX subdivision "
                    "(does not apply the modifier even if 'Apply Modifiers' is enabled)",
        default=False,
    )
    use_mesh_edges: BoolProperty(
        name="Loose Edges",
        description="Export loose edges (as two-vertices polygons)",
        default=False,
    )
    use_tspace: BoolProperty(
        name="Tangent Space",
        description="Add binormal and tangent vectors, together with normal they form the tangent space "
                    "(will only work correctly with tris/quads only meshes!)",
        default=False,
    )
    use_custom_props: BoolProperty(
        name="Custom Properties",
        description="Export custom properties",
        default=False,
    )
    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain to specify last bone length "
                    "(use this when you intend to edit the armature from exported data)",
        default=True  # False for commit!
    )
    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=(('X', "X Axis", ""),
               ('Y', "Y Axis", ""),
               ('Z', "Z Axis", ""),
               ('-X', "-X Axis", ""),
               ('-Y', "-Y Axis", ""),
               ('-Z', "-Z Axis", ""),
               ),
        default='Y',
    )
    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=(('X', "X Axis", ""),
               ('Y', "Y Axis", ""),
               ('Z', "Z Axis", ""),
               ('-X', "-X Axis", ""),
               ('-Y', "-Y Axis", ""),
               ('-Z', "-Z Axis", ""),
               ),
        default='X',
    )
    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description="Only write deforming bones (and non-deforming ones when they have deforming children)",
        default=False,
    )
    armature_nodetype: EnumProperty(
        name="Armature FBXNode Type",
        items=(('NULL', "Null", "'Null' FBX node, similar to Blender's Empty (default)"),
               ('ROOT', "Root", "'Root' FBX node, supposed to be the root of chains of bones..."),
               ('LIMBNODE', "LimbNode", "'LimbNode' FBX node, a regular joint between two bones..."),
               ),
        description="FBX type of node (object) used to represent Blender's armatures "
                    "(use Null one unless you experience issues with other app, other choices may no import back "
                    "perfectly in Blender...)",
        default='NULL',
    )
    bake_anim: BoolProperty(
        name="Baked Animation",
        description="Export baked keyframe animation",
        default=True,
    )
    bake_anim_use_all_bones: BoolProperty(
        name="Key All Bones",
        description="Force exporting at least one key of animation for all bones "
                    "(needed with some target applications, like UE4)",
        default=True,
    )
    bake_anim_use_nla_strips: BoolProperty(
        name="NLA Strips",
        description="Export each non-muted NLA strip as a separated FBX's AnimStack, if any, "
                    "instead of global scene animation",
        default=True,
    )
    bake_anim_use_all_actions: BoolProperty(
        name="All Actions",
        description="Export each action as a separated FBX's AnimStack, instead of global scene animation "
                    "(note that animated objects will get all actions compatible with them, "
                    "others will get no animation at all)",
        default=True,
    )
    bake_anim_force_startend_keying: BoolProperty(
        name="Force Start/End Keying",
        description="Always add a keyframe at start and end of actions for animated channels",
        default=True,
    )
    bake_anim_step: FloatProperty(
        name="Sampling Rate",
        description="How often to evaluate animated values (in frames)",
        min=0.01, max=100.0,
        soft_min=0.1, soft_max=10.0,
        default=1.0,
    )
    bake_anim_simplify_factor: FloatProperty(
        name="Simplify",
        description="How much to simplify baked values (0.0 to disable, the higher the more simplified)",
        min=0.0, max=100.0,  # No simplification to up to 10% of current magnitude tolerance.
        soft_min=0.0, soft_max=10.0,
        default=1.0,  # default: min slope: 0.005, max frame step: 10.
    )
    path_mode: path_reference_mode
    embed_textures: BoolProperty(
        name="Embed Textures",
        description="Embed textures in FBX binary file (only for \"Copy\" path mode!)",
        default=False,
    )
    batch_mode: EnumProperty(
        name="Batch Mode",
        items=(('OFF', "Off", "Active scene to file"),
               ('SCENE', "Scene", "Each scene as a file"),
               ('COLLECTION', "Collection",
                "Each collection (data-block ones) as a file, does not include content of children collections"),
               ('SCENE_COLLECTION', "Scene Collections",
                "Each collection (including master, non-data-block ones) of each scene as a file, "
                "including content from children collections"),
               ('ACTIVE_SCENE_COLLECTION', "Active Scene Collections",
                "Each collection (including master, non-data-block one) of the active scene as a file, "
                "including content from children collections"),
               ),
    )
    use_batch_own_dir: BoolProperty(
        name="Batch Own Dir",
        description="Create a dir for each exported file",
        default=False,
    )  # デフォルト値をFalseに変更
    use_metadata: BoolProperty(
        name="Use Metadata",
        default=True,
        options={'HIDDEN'},
    )
    # endregion
    ######################################################

    save_prefs: BoolProperty(name="Save Settings", default=True)

    batch_filename_contains_extension: BoolProperty(name="Contains Extension", default=False)

    use_selection_children_objects: BoolProperty(name="Include Children Objects", default=False)
    use_active_collection_children_objects: BoolProperty(name="Include Children Objects", default=False)
    use_active_collection_children_collections: BoolProperty(name="Include Children Collections", default=False)

    only_root_collection: BoolProperty(name="Only Root Collections", default=False)

    enable_auto_merge: BoolProperty(name="Enable Auto Merge", default=True)

    enable_apply_modifiers_with_shapekeys: BoolProperty(name="Apply Modifier with Shape Keys", default=True)
    enable_separate_lr_shapekey: BoolProperty(name="Separate Shape Keys LR", default=True)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.label(text=self.bl_label)
        layout.prop(operator, "save_prefs")

    def invoke(self, context, event):
        # シーンから設定を読み込み
        preferences_scene.load_scene_prefs(self)
        return super().invoke(context, event)

    def execute_main(self, context):
        modeTemp = None
        if bpy.context.object is not None:
            # 開始時のモードを記憶しオブジェクトモードに
            modeTemp = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='OBJECT')

        # 現在の選択状況を記憶
        activeTemp = func_object_utils.get_active_object()
        selectedTemp = bpy.context.selected_objects

        # 常時エクスポートするオブジェクトを表示
        hide_temp_always_export = {}
        layer_col_always_export = func_collection_utils.find_layer_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
        if layer_col_always_export:
            # layer_col_always_export.exclude = False
            # コレクションを表示
            layer_col_always_export.hide_viewport = False
            # オブジェクトの表示状態を記憶してから表示
            collection = func_collection_utils.find_collection(consts.ALWAYS_EXPORT_GROUP_NAME)
            for obj in collection.objects:
                hide_temp_always_export[obj] = obj.hide_get()
                obj.hide_set(False)

        if self.use_selection == False:
            # Selected Objectsにチェックがついていないなら全オブジェクトを選択
            func_object_utils.select_all_objects()

        if self.use_selection and self.use_selection_children_objects:
            current_selected = bpy.context.selected_objects
            for obj in current_selected:
                func_object_utils.set_active_object(obj)
                if bpy.context.object.mode != 'OBJECT':
                    # Armatureをアクティブにしたとき勝手にPoseモードになる場合があるためここで確実にObjectモードにする
                    bpy.ops.object.mode_set(mode='OBJECT')
                func_object_utils.select_children_recursive()

        if self.use_active_collection:
            active_layer_collection = bpy.context.view_layer.active_layer_collection
            print("Active Collection: " + active_layer_collection.name)
            active_collection = active_layer_collection.collection
            func_collection_utils.select_collection_only(
                collection=active_collection,
                include_children_objects=self.use_active_collection_children_objects,
                include_children_collections=self.use_active_collection_children_collections,
                set_visible=False
            )

        # エクスポート除外コレクションを取得
        ignore_collection = func_collection_utils.find_collection(consts.DONT_EXPORT_GROUP_NAME)
        if ignore_collection:
            # 処理から除外するオブジェクトの選択を外す
            func_collection_utils.deselect_collection(collection=ignore_collection)

        # 選択中オブジェクトを取得
        targets_source = bpy.context.selected_objects
        targets_source.sort(key=lambda x: x.name)
        targets_source_mode = [''] * len(targets_source)
        # PoseモードのオブジェクトをOBJECTモードにする
        # （Poseモードになっているアーマチュアが複製されないっぽいので）
        for i in range(len(targets_source)):
            o = targets_source[i]
            if o.mode == 'POSE':
                targets_source_mode[i] = o.mode
                func_object_utils.set_active_object(o)
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                targets_source_mode[i] = None

        # オブジェクト名に接尾辞を付ける
        # （名前の末尾が xxx.001 のように数字になっている場合にオブジェクトを複製すると名前がxxx.002 のようにカウントアップされてしまい、オブジェクト名の復元時に問題が起きるのでその対策）
        for obj in targets_source:
            func_name_utils.add_suffix(obj)

        # オブジェクトを複製
        bpy.ops.object.duplicate()
        targets_dup = bpy.context.selected_objects
        targets_dup.sort(key=lambda x: x.name)

        # 複製したオブジェクトの名前から接尾辞を削除
        for obj in targets_dup:
            func_name_utils.remove_suffix(obj)

        # Debug
        print("Source: [")
        for o in targets_source:
            print(o.name)
        print("]")
        print("Duplicate: [")
        for o in targets_dup:
            print(o.name)
        print("]")

        # ↓ AutoMergeアドオン連携
        if self.enable_auto_merge:
            try:
                # オブジェクトを結合
                bpy.types.WindowManager.mizore_automerge_temp_ignore_collection = ignore_collection
                b = bpy.ops.object.apply_modifier_and_merge_grouped_exporter_addon(
                    enable_apply_modifiers_with_shapekeys=self.enable_apply_modifiers_with_shapekeys
                )
                # 結合処理失敗
                if 'FINISHED' not in b:
                    # 複製されたオブジェクトを削除
                    func_object_utils.remove_objects(targets_dup)
                    return {'FAILED'}
            except AttributeError as e:
                t = "!!! Failed to load AutoMerge !!!"
                print(t)
                print(str(e))
        # ↑ AutoMergeアドオン連携

        print("xxxxxx Export Targets xxxxxx\n" + '\n'.join(
            [obj.name for obj in bpy.context.selected_objects]) + "\nxxxxxxxxxxxxxxx")

        # ShapeKeysUtil連携
        if func_addon_link.shapekey_util_is_found():
            if self.enable_apply_modifiers_with_shapekeys and self.use_mesh_modifiers:
                active = func_object_utils.get_active_object()
                selected_objects = bpy.context.selected_objects
                targets = [d for d in selected_objects if d.type == 'MESH']
                for obj in targets:
                    func_object_utils.set_active_object(obj)
                    bpy.ops.object.shapekeys_util_apply_mod_for_exporter_addon()
                # 選択オブジェクトを復元
                for obj in selected_objects:
                    obj.select_set(True)
                func_object_utils.set_active_object(active)
            if self.enable_separate_lr_shapekey:
                for obj in bpy.context.selected_objects:
                    if obj.type == 'MESH' and obj.data.shape_keys is not None and len(
                            obj.data.shape_keys.key_blocks) != 0:
                        func_object_utils.set_active_object(obj)
                        bpy.ops.object.shapekeys_util_separate_lr_shapekey_for_exporter()
        else:
            t = "!!! Failed to load ShapeKeysUtil !!! - apply_modifiers_with_shapekeys"
            print(t)
            self.report({'ERROR'}, t)

        # region # Export based on io_scene_fbx
        from mathutils import Matrix
        if not self.filepath:
            raise Exception("filepath not set")

        global_matrix = (axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4()
                         if self.use_space_transform else Matrix())

        keywords = self.as_keywords(ignore=("check_existing",
                                            "filter_glob",
                                            "ui_tab",
                                            ))

        keywords["global_matrix"] = global_matrix

        # use_selectionなどに該当する処理をこの関数内で行っており追加で何かをする必要はないため、エクスポート関数の処理を固定化しておく
        keywords["use_selection"] = True
        keywords["use_active_collection"] = False
        keywords["batch_mode"] = 'OFF'
        #

        from io_scene_fbx import export_fbx_bin
        # BatchMode用処理
        if self.batch_mode == 'COLLECTION' or self.batch_mode == 'SCENE_COLLECTION' or self.batch_mode == 'ACTIVE_SCENE_COLLECTION':
            ignore_collections_name = [consts.ALWAYS_EXPORT_GROUP_NAME, consts.DONT_EXPORT_GROUP_NAME]
            if func_addon_link.auto_merge_is_found():
                ignore_collections_name.append(bpy.types.WindowManager.mizore_automerge_collection_name)

            # ファイル名の途中に.fbxを入れるかどうか
            if self.batch_filename_contains_extension:
                path_format = self.filepath + "_{0}.fbx"
            else:
                path_format = os.path.splitext(self.filepath)[0] + "_{0}.fbx"
            targets = bpy.context.selected_objects
            if self.only_root_collection:
                # Scene Collection直下だけを対象とする
                target_collections = bpy.context.scene.collection.children
            else:
                # [0]はシーンコレクションなのでスキップ
                target_collections = func_collection_utils.get_all_collections()[1:]
            for collection in target_collections:
                if any(collection.name in n for n in ignore_collections_name):
                    continue
                objects = func_collection_utils.get_collection_objects(collection=collection,
                                                 include_children_collections=self.only_root_collection)
                objects = objects & set(targets)
                if not objects:
                    continue
                func_object_utils.deselect_all_objects()
                func_object_utils.select_objects(objects, True)
                # パス設定
                path = path_format.format(collection.name)
                path.replace(' ', '_')
                keywords["filepath"] = path
                print("export: " + path)
                export_fbx_bin.save(self, context, **keywords)
            # Scene Collection書き出し
            if self.batch_mode == 'SCENE_COLLECTION' or self.batch_mode == 'ACTIVE_SCENE_COLLECTION':
                # パス設定
                path = path_format.format(f"{bpy.context.scene.name}_Scene_Collection")
                path.replace(' ', '_')
                keywords["filepath"] = path
                print("export: " + path)
                func_object_utils.deselect_all_objects()
                func_object_utils.select_objects(targets, True)
                export_fbx_bin.save(self, context, **keywords)
        elif self.batch_mode == 'OFF' or self.batch_mode == 'SCENE':
            path = self.filepath
            if self.batch_mode == 'SCENE':
                # ファイル名にシーン名を追加
                if (self.batch_filename_contains_extension):
                    path = f"{self.filepath}_{bpy.context.scene.name}.fbx"
                else:
                    path = f"{os.path.splitext(self.filepath)[0]}_{bpy.context.scene.name}.fbx"
                path.replace(' ', '_')
                keywords["filepath"] = path
            print("export: " + path)
            export_fbx_bin.save(self, context, **keywords)
        else:
            self.report({'ERROR'}, str(self.batch_mode) + " は未定義です。")
        # endregion

        # 複製されたオブジェクトを削除
        func_object_utils.remove_objects(targets_dup)

        # 複製前オブジェクト名から接尾辞を削除
        for obj in targets_source:
            func_name_utils.remove_suffix(obj)

        # AlwaysExportを非表示
        if layer_col_always_export:
            # layer_col_always_export.exclude = True
            layer_col_always_export.hide_viewport = True
            # オブジェクトの表示状態を復元
            for obj, value in hide_temp_always_export.items():
                obj.hide_set(value)

        # 選択状況を処理前の状態に復元
        func_object_utils.deselect_all_objects()
        func_object_utils.select_objects(selectedTemp, True)
        # set_active_object(activeTemp)

        # オブジェクトのモードを復元
        for i in range(len(targets_source)):
            m = targets_source_mode[i]
            if m is not None:
                func_object_utils.set_active_object(targets_source[i])
                bpy.ops.object.mode_set(mode=m)
        func_object_utils.set_active_object(activeTemp)

        if modeTemp is not None:
            # 開始時のモードを復元
            bpy.ops.object.mode_set(mode=modeTemp)

        return {'FINISHED'}

    def isvalid(self):
        for obj in bpy.context.view_layer.objects:
            # 接尾辞をつけたときに名前の文字数が63文字（Blenderの最大文字数）を超えるオブジェクトがあるならエラー
            if consts.ACTUAL_MAX_NAME_LENGTH < len(obj.name):
                t = bpy.app.translations.pgettext("error_longname_object").format(
                    str(consts.ACTUAL_MAX_NAME_LENGTH),
                    obj.name,
                    str(len(obj.name))
                )
                self.report({'ERROR'}, t)
                return False
            if obj.data and consts.ACTUAL_MAX_NAME_LENGTH < len(obj.data.name):
                t = bpy.app.translations.pgettext("error_longname_data").format(
                    str(consts.ACTUAL_MAX_NAME_LENGTH),
                    obj.name,
                    obj.data.name,
                    str(len(obj.data.name))
                )
                self.report({'ERROR'}, t)
                return False
        return True

    def execute(self, context):
        # シーンに設定を保存
        if self.save_prefs:
            preferences_scene.save_scene_prefs(self)

        if self.isvalid() == False:
            return {'CANCELLED'}

        if self.batch_mode == 'COLLECTION' or self.batch_mode == 'SCENE' or self.batch_mode == 'SCENE_COLLECTION':
            temp_scene = bpy.context.window.scene
            for scene in bpy.data.scenes:
                bpy.context.window.scene = scene
                print("Scene: " + scene.name)
                self.execute_main(context)
            bpy.context.window.scene = temp_scene
            return {'FINISHED'}
        else:
            return self.execute_main(context)


# ExportメニューにOperatorを登録
def INFO_MT_file_custom_export_mizore_menu(self, context):
    self.layout.operator(INFO_MT_file_custom_export_mizore_fbx.bl_idname)


classes = [
    INFO_MT_file_custom_export_mizore_fbx,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(INFO_MT_file_custom_export_mizore_menu)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_export.remove(INFO_MT_file_custom_export_mizore_menu)

