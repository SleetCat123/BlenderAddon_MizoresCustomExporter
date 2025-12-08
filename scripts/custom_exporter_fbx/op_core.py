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

import time
import traceback

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, orientation_helper, path_reference_mode

from .. import preferences_scene
from ..funcs.modal.modal_base import create_progress_bar
from . import func_execute_main
from .BatchExportFilepathFormatData import BatchExportFilepathFormatData
from .op_remove_saved_path import OBJECT_OT_mizore_remove_saved_path
from .op_save_export_settings import OBJECT_OT_mizore_save_export_settings


# エクスポート
@orientation_helper(axis_forward='-Z', axis_up='Y')
class INFO_MT_file_custom_export_mizore_fbx(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.custom_export_mizore_fbx"
    bl_label = "Mizore's Custom Exporter (.fbx)"
    bl_description = "Export selected objects as FBX with custom settings"
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
        items=[('FBX_SCALE_NONE', "All Local",
                "Apply custom scaling and units scaling to each object transformation, FBX scale remains at 1.0"),
               ('FBX_SCALE_UNITS', "FBX Units Scale",
                "Apply custom scaling to each object transformation, and units scaling to FBX scale"),
               ('FBX_SCALE_CUSTOM', "FBX Custom Scale",
                "Apply custom scaling to FBX scale, and units scaling to each object transformation"),
               ('FBX_SCALE_ALL', "FBX All",
                "Apply custom scaling and units scaling to FBX scale"),
               ],
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
        items=[('EMPTY', "Empty", ""),
               ('CAMERA', "Camera", ""),
               ('LIGHT', "Lamp", ""),
               ('ARMATURE', "Armature", "WARNING: not supported in dupli/group instances"),
               ('MESH', "Mesh", ""),
               ('OTHER', "Other", "Other geometry types, like curve, metaball, etc. (converted to meshes)"),
               ],
        description="Which kind of object to export",
        default={'ARMATURE', 'MESH', 'OTHER'},
    )  # デフォルト値を{'ARMATURE', 'MESH', 'OTHER'}に変更

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects (except Armature ones) - "
                    "WARNING: prevents exporting shape keys",
        default=True,
    )
    use_mesh_modifiers_render: BoolProperty(
        name="Use Modifiers Render Setting",
        description="Use render settings when applying modifiers to mesh objects",
        default=True,
    )
    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        items=[('OFF', "Normals Only", "Export only normals instead of writing edge or face smoothing data"),
               ('FACE', "Face", "Write face smoothing"),
               ('EDGE', "Edge", "Write edge smoothing"),
               ],
        description="Export smoothing information "
                    "(prefer 'Normals Only' option if your target importer understand split normals)",
        default='OFF',
    ) # デフォルト値をFACEに変更→OFFに戻した
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
        items=[('X', "X Axis", ""),
               ('Y', "Y Axis", ""),
               ('Z', "Z Axis", ""),
               ('-X', "-X Axis", ""),
               ('-Y', "-Y Axis", ""),
               ('-Z', "-Z Axis", ""),
               ],
        default='Y',
    )
    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=[('X', "X Axis", ""),
               ('Y', "Y Axis", ""),
               ('Z', "Z Axis", ""),
               ('-X', "-X Axis", ""),
               ('-Y', "-Y Axis", ""),
               ('-Z', "-Z Axis", ""),
               ],
        default='X',
    )
    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description="Only write deforming bones (and non-deforming ones when they have deforming children)",
        default=False,
    )
    armature_nodetype: EnumProperty(
        name="Armature FBXNode Type",
        items=[('NULL', "Null", "'Null' FBX node, similar to Blender's Empty (default)"),
               ('ROOT', "Root", "'Root' FBX node, supposed to be the root of chains of bones..."),
               ('LIMBNODE', "LimbNode", "'LimbNode' FBX node, a regular joint between two bones..."),
               ],
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
        items=[('OFF', "Off", "Active scene to file"),
               ('SCENE', "Scene", "Each scene as a file"),
               ('COLLECTION', "Collection",
                "Each collection (data-block ones) as a file, does not include content of children collections"),
               ('SCENE_COLLECTION', "Scene Collections",
                "Each collection (including master, non-data-block ones) of each scene as a file, "
                "including content from children collections"),
               ('ACTIVE_SCENE_COLLECTION', "Active Scene Collections",
                "Each collection (including master, non-data-block one) of the active scene as a file, "
                "including content from children collections"),

                # 追加
                ('OBJECTS_IN_ACTIVE_COLLECTION', "Objects in Active Collection", "Each object in active collection as a file"),
               ],
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

    save_prefs: BoolProperty(
        name="Save Settings",
        default=True,
        description="Export settings are saved in a blend file.\n"
            "If you want to delete the saved settings, execute \"Remove Export Settings\" in the right-click menu of the Object mode."
    )
    save_path: BoolProperty(
        name="Save Export Path",
        default=False,
        description="Export location is stored in the blend file.\n"
            "!!! Please be careful if you plan to send blend file to others"
    )

    batch_filename_format_presets: EnumProperty(
        name="",
        items=BatchExportFilepathFormatData.init_enum_items()
    )
    batch_filename_format: StringProperty(
        name="",
        default=BatchExportFilepathFormatData.batch_file_format_default,
    )

    use_selection_children_objects: BoolProperty(name="Include Children Objects", default=False)
    use_active_collection_children_objects: BoolProperty(name="Include Children Objects", default=False)
    use_active_collection_children_collections: BoolProperty(name="Include Children Collections", default=False)

    only_root_collection: BoolProperty(name="Only Root Collections", default=False)

    enable_auto_merge: BoolProperty(name="Enable Auto Merge", default=True)

    use_update_mesh_deform_addon: BoolProperty(name="Use Update Mesh Deform Addon", default=True)

    enable_apply_modifiers_with_shapekeys: BoolProperty(name="Apply Modifier with Shape Keys", default=True)
    enable_separate_lr_shapekey: BoolProperty(name="Separate Shape Keys LR", default=True)
    enable_subtract_base_shapekey: BoolProperty(name="Subtract Base Shape Keys", default=True)

    bake_anim_use_bone_constraint: BoolProperty(name="Use Bone Constraint", default=True)

    use_variants_merge: BoolProperty(name="Use Variants Merge", default=True)

    enable_fix_vertex_group_collisions: BoolProperty(
        name="Fix Vertex Group Name Collisions", 
        default=True,
        description="Fix vertex group name collisions before export (duplicate groups will be merged using max weight)"
    )

    scene = None

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        # layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.label(text=self.bl_label)

        row = layout.row(align=True)
        row.prop(operator, "save_prefs")
        OBJECT_OT_mizore_save_export_settings.operator = self
        row.operator(OBJECT_OT_mizore_save_export_settings.bl_idname)

        row = layout.row(align=True)
        row.enabled = operator.save_prefs
        row.prop(operator, "save_path")
        row.operator(OBJECT_OT_mizore_remove_saved_path.bl_idname)

    def invoke(self, context, event):
        # シーンから設定を読み込み
        preferences_scene.load_scene_prefs(self)
        self.scene = bpy.context.scene
        return super().invoke(context, event)

    # Modal処理用の設定
    _timer_interval: float = 0.001  # 1000Hz
    _batch_time_limit: float = 0.05  # 50ms per frame

    def execute(self, context):
        """Modal処理を開始"""
        # インスタンス変数の初期化
        self._timer = None
        self._generator = None
        self._is_cancelled = False
        self._last_progress = None
        self._export_error = None
        self._batch_scenes = []
        self._current_scene_index = 0
        self._temp_scene = None

        try:
            # 復元ポイントを作成
            bpy.ops.ed.undo_push(message="Before Export")

            # バッチモードでシーンごとの処理が必要な場合
            if self.batch_mode in ('COLLECTION', 'SCENE', 'SCENE_COLLECTION'):
                self._temp_scene = bpy.context.window.scene
                self._batch_scenes = list(bpy.data.scenes)
                self._current_scene_index = 0
                if self._batch_scenes:
                    bpy.context.window.scene = self._batch_scenes[0]
                    print("Scene: " + self._batch_scenes[0].name)
                    self._generator = func_execute_main.execute_main_iter(self, context)
            else:
                self._generator = func_execute_main.execute_main_iter(self, context)

            if self._generator is None:
                return {'CANCELLED'}

            # タイマーを開始
            self._timer = context.window_manager.event_timer_add(
                self._timer_interval,
                window=context.window
            )

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        except Exception as e:
            traceback.print_exc()
            self._on_error(context, e)
            return {'CANCELLED'}

    def modal(self, context, event):
        """Modalイベント処理"""
        # キャンセル判定
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._is_cancelled = True
            self._cleanup(context)
            self._on_cancel(context)
            return {'CANCELLED'}

        # タイマーイベント
        if event.type == 'TIMER':
            try:
                # バッチ処理：時間制限内で複数のyieldを処理
                start_time = time.perf_counter()

                while True:
                    try:
                        progress = next(self._generator)
                        self._last_progress = progress

                        # 時間制限チェック
                        elapsed = time.perf_counter() - start_time
                        if elapsed >= self._batch_time_limit:
                            break
                    except StopIteration:
                        # 現在のジェネレータが完了
                        # バッチモードで次のシーンがあるかチェック
                        if self._batch_scenes and self._current_scene_index < len(self._batch_scenes) - 1:
                            self._current_scene_index += 1
                            next_scene = self._batch_scenes[self._current_scene_index]
                            bpy.context.window.scene = next_scene
                            print("Scene: " + next_scene.name)
                            self._generator = func_execute_main.execute_main_iter(self, context)
                            break
                        else:
                            # 全て完了
                            if self._temp_scene:
                                bpy.context.window.scene = self._temp_scene
                            self._cleanup(context)
                            self._on_complete(context)
                            return {'FINISHED'}

                # 進捗を更新
                if self._last_progress:
                    self._update_progress(context, self._last_progress)

                return {'RUNNING_MODAL'}

            except Exception as e:
                traceback.print_exc()
                self._cleanup(context)
                self._on_error(context, e)
                return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _update_progress(self, context, progress):
        """進捗表示を更新"""
        percent = int(progress.progress * 100)
        bar = create_progress_bar(progress.progress, width=15)

        # メッセージ構築: プログレスバー + パーセント + メッセージ
        # messageフィールドを優先表示（処理内容がわかりやすい）
        parts = [f"{bar} {percent:3d}%"]

        if progress.message:
            # メッセージがある場合はそれを表示
            parts.append(progress.message)
        else:
            # メッセージがない場合はフェーズとオブジェクト名を表示
            if progress.phase:
                phase_short = progress.phase[:12]
                parts.append(f"[{phase_short}]")
            if progress.object_name:
                parts.append(progress.object_name)

        display_message = " ".join(parts)
        context.workspace.status_text_set(display_message)

    def _cleanup(self, context):
        """クリーンアップ処理"""
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        context.workspace.status_text_set(None)
        self._generator = None

    def _on_complete(self, context):
        """処理完了時のコールバック"""
        # 実行前の状態に戻す
        bpy.ops.ed.undo_push(message="Restore point 1")
        bpy.ops.ed.undo()
        # シーンに設定を保存
        if self.save_prefs:
            ignore_key = ["reset_path"]
            if not self.save_path:
                ignore_key.append("filepath")
            preferences_scene.clear_export_props()
            preferences_scene.save_scene_prefs(operator=self, ignore_key=ignore_key)
        bpy.ops.ed.undo_push(message="Restore point")

        log = bpy.app.translations.pgettext("export_completed")
        print(log)
        self.report({'INFO'}, log)

    def _on_cancel(self, context):
        """キャンセル時のコールバック"""
        # 実行前の状態に戻す
        if bpy.ops.ed.undo.poll():
            bpy.ops.ed.undo()
        self.report({'WARNING'}, "Export cancelled")

    def _on_error(self, context, error):
        """エラー時のコールバック"""
        # 実行前の状態に戻す
        if bpy.ops.ed.undo.poll():
            bpy.ops.ed.undo()
        log = bpy.app.translations.pgettext("export_interrupted") + "\n\n" + str(error)
        self.report({'ERROR'}, log)


# ExportメニューにOperatorを登録
def INFO_MT_file_custom_export_mizore_menu(self, context):
    self.layout.operator(INFO_MT_file_custom_export_mizore_fbx.bl_idname)


translations_dict = {
    "en_US": {
        ("*", "export_completed"): "Export completed.",
        ("*", "export_interrupted"): "Export interrupted.",
    },
    "ja_JP": {
        ("*", "export_completed"): "エクスポートが完了しました。",
        ("*", "export_interrupted"): "エクスポートが中断されました。",

        ("*", "Save Settings"): "設定を保存",
        ("*", "Save Export Path"): "出力パスを保存",

        ("*", "Export location is stored in the blend file.\n"
            "!!! Please be careful if you plan to send blend file to others"):
            "fbxの書き出し場所をblendファイルに記憶します。\n"
            "!!! blendファイルを他人に送る予定がある場合は注意して使用してください。",

        ("*", "Export settings are saved in a blend file.\n"
            "If you want to delete the saved settings, execute \"Remove Export Settings\" in the right-click menu of the Object mode."): 
            "エクスポート設定をblendファイルに保存します。"
            "保存された設定を削除したい場合は、オブジェクトモードの右クリックメニューから\"Remove Export Settings\"を実行してください。",

        ("*", "Export selected objects as FBX with custom settings"): "カスタム設定でFBXファイルとしてオブジェクトをエクスポート",
    },
}


classes = [
    INFO_MT_file_custom_export_mizore_fbx,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(INFO_MT_file_custom_export_mizore_menu)
    bpy.app.translations.register(__name__, translations_dict)



def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_export.remove(INFO_MT_file_custom_export_mizore_menu)
    bpy.app.translations.unregister(__name__)

