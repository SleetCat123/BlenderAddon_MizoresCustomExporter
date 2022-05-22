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

bl_info = {
    "name" : "MizoresCustomExporter",
    "author" : "@sleetcat123(Twitter)",
    "version" : (1,0,0),
    "blender" : (2, 80, 0),
    "location": "File > Export > Mizore's Custom Exporter",
    "description" : "Custom exporter by Mizore Nekoyanagi",
    "category" : "Import-Export"
}

DONT_EXPORT_GROUP_NAME = "DontExport" # エクスポートから除外するオブジェクトのグループ名
ALWAYS_EXPORT_GROUP_NAME = "AlwaysExport" # 非表示状態であっても常にエクスポートさせるオブジェクトのグループ名

EXPORT_TEMP_SUFFIX = ".#MizoreCEx#"

### region Translation ###
translations_dict = {
    "en_US" : {
            ("*", "box_warning_slow_method_1") : "Warning: ",
            ("*", "box_warning_slow_method_2") : "If using this setting",
            ("*", "box_warning_slow_method_3") : "may take a while in progress.",
        },
    "ja_JP" : {
            ("*", "box_warning_slow_method_1") : "注意：",
            ("*", "box_warning_slow_method_2") : "この項目を有効にすると",
            ("*", "box_warning_slow_method_3") : "処理に時間がかかる場合があります。",
        },
}
### endregion ###

### region Func ###
def select_object(obj, value=True):
    obj.select_set(value)

def select_objects(objects, value=True):
    for obj in objects:
        obj.select_set(value)

def get_active_object():
    return bpy.context.view_layer.objects.active

def set_active_object(obj):
    bpy.context.view_layer.objects.active = obj

def deselect_all_objects():
    targets = bpy.context.selected_objects
    for obj in targets:
        select_object(obj, False)
    #bpy.context.view_layer.objects.active = None

def get_children(obj):
    allobjects = bpy.data.objects
    return [child for child in allobjects if child.parent == obj]

def duplicate_selected_objects():
    dup_source = bpy.context.selected_objects
    # 対象オブジェクトを複製
    bpy.ops.object.duplicate()
    dup_result = bpy.context.selected_objects

    return (dup_source, dup_result)

def add_suffix(obj):
    if not EXPORT_TEMP_SUFFIX in obj.name:
        newname = obj.name + EXPORT_TEMP_SUFFIX
        print("Add Suffix (Object name): [" + obj.name + "] -> [" + newname + "]")
        obj.name = newname

    # インスタンス化されたメッシュがあるとインスタンスの個数分だけ関数が呼ばれるため、suffixが多重追加されないように対策しておく
    if obj.data != None and not EXPORT_TEMP_SUFFIX in obj.data.name:
        newname = obj.data.name + EXPORT_TEMP_SUFFIX
        print("Add Suffix (Data name): [" + obj.data.name + "] -> [" + newname + "]")
        obj.data.name = newname

def remove_suffix(obj):
    if EXPORT_TEMP_SUFFIX in obj.name:
        oldname =  obj.name
        newname = oldname[0:oldname.rfind(EXPORT_TEMP_SUFFIX)]
        print("Remove Suffix (Object name): [" + oldname + "] -> [" + newname + "]")
        obj.name = newname

    if obj.data != None and EXPORT_TEMP_SUFFIX in obj.data.name:
        oldname = obj.data.name
        newname = oldname[0:oldname.rfind(EXPORT_TEMP_SUFFIX)]
        print("Remove Suffix (Object name): [" + oldname + "] -> [" + newname + "]")
        obj.data.name = newname



# 現在選択中のオブジェクトのうち指定コレクションに属するものだけを選択した状態にする
def select_collection_only(collection, include_children):
    if collection == None: return
    targets = bpy.context.selected_objects
    # 対象コレクションに属するオブジェクトと選択中オブジェクトの積集合
    assigned_objs = list(set(collection.objects) & set(targets))
    result = assigned_objs
    if include_children:
        for obj in assigned_objs:
            deselect_all_objects()
            select_object(obj, True)
            set_active_object(obj)
            if bpy.context.object.mode != 'OBJECT':
                # Armatureをアクティブにしたとき勝手にPoseモードになる場合があるためここで確実にObjectモードにする
                bpy.ops.object.mode_set(mode='OBJECT')
            # オブジェクトの子も対象に含める
            bpy.ops.object.select_grouped(extend=True, type='CHILDREN_RECURSIVE')
            children = bpy.context.selected_objects;
            for child in children:
                if (obj != child) and (child in targets):
                    result.append(child)
    deselect_all_objects()
    select_objects(result, True)


def deselect_collection(collection):
    if collection == None: return
    print("Deselect Collection: " + collection.name)
    active = get_active_object()
    targets = bpy.context.selected_objects
    # 処理targetsから除外するオブジェクトの選択を外す
    # 対象コレクションに属するオブジェクトと選択中オブジェクトの積集合
    assigned_objs = list(set(collection.objects) & set(targets))
    for obj in assigned_objs:
        deselect_all_objects()
        select_object(obj, True)
        set_active_object(obj)
        if bpy.context.object.mode != 'OBJECT':
            # Armatureをアクティブにしたとき勝手にPoseモードになる場合があるためここで確実にObjectモードにする
            bpy.ops.object.mode_set(mode='OBJECT')
        # オブジェクトの子も除外対象に含める
        bpy.ops.object.select_grouped(extend=True, type='CHILDREN_RECURSIVE')
        children = bpy.context.selected_objects;
        for child in children:
            if child in targets:
                targets.remove(child)
            if child == active:
                active = None
            print("Deselect: " + child.name)
    deselect_all_objects()
    select_objects(targets, True)
    if active != None:
        set_active_object(active)

# 選択オブジェクトを指定名のグループに入れたり外したり
def assign_object_group(group_name, assign=True):
    if not group_name in bpy.data.collections:
        if assign == True:
            # コレクションが存在しなければ新規作成
            collection = bpy.data.collections.new(name=group_name)
            # bpy.context.scene.collection.children.link(collection)
        else:
            # コレクションが存在せず、割り当てがfalseなら何もせず終了
            return
    else:
        collection = bpy.data.collections[group_name]

    if not collection.name in bpy.context.scene.collection.children.keys():
        # コレクションをLinkする。
        # Unlink状態のコレクションでもPythonからは参照できてしまう場合があるようなので、確実にLink状態になるようにしておく
        bpy.context.scene.collection.children.link(collection)

    active = get_active_object()
    targets = bpy.context.selected_objects
    for obj in targets:
        if assign == True:
            set_active_object(obj)
            if not obj.name in collection.objects:
                # コレクションに追加
                collection.objects.link(obj)
        else:
            if obj.name in collection.objects:
                # コレクションから外す
                collection.objects.unlink(obj)

    if collection.objects == False:
        # コレクションが空なら削除する
        bpy.context.scene.collection.children.unlink(collection)

    # アクティブオブジェクトを元に戻す
    set_active_object(active)

def hide_collection(context, group_name, hide=True):
    if group_name in context.view_layer.layer_collection.children:
        layer_col = context.view_layer.layer_collection.children[group_name]
        layer_col.hide_viewport = hide

### endregion ###

### region ShapeKeysUtil連携 ###
def shapekey_util_is_found():
    try:
        from ShapeKeysUtil import apply_modifiers_with_shapekeys
        return True
    except ImportError:
        t="!!! Failed to load ShapeKeysUtil !!! - on shapekey_util_is_found"
        print(t)
        self.report({'ERROR'}, t)
    return False
### endregion ###

### region AutoMerge連携 ###
def auto_merge_is_found():
    try:
        from AutoMerge import apply_modifier_and_merge_children_grouped
        return True
    except ImportError:
        t = "!!! Failed to load AutoMerge !!!"
        print(t)
        self.report({'ERROR'}, t)
    return False
### endregion ###

### region AddonPreferences ###
def set_prop_col_value(prop, key, value):
    el = prop.get(key)
    if el == None:
        el = prop.add()
        el.name = key
    el.value = value

class PR_IntPropertyCollection(bpy.types.PropertyGroup):
    value: IntProperty(name="", default=0)
class PR_StringPropertyCollection(bpy.types.PropertyGroup):
    value: StringProperty(name="", default="")
class PR_MizoreExporter_ScenePref(bpy.types.PropertyGroup):
    export_str_props: CollectionProperty(type=PR_StringPropertyCollection)
    export_int_props: CollectionProperty(type=PR_IntPropertyCollection)
### endregion ###

### region Export Operator ###
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
    )# デフォルト値をFBX_SCALE_UNITSに変更

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
    ) # デフォルト値をTrueに変更

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
    ) # デフォルト値を{'ARMATURE', 'MESH'}に変更

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
    ) # デフォルト値をFalseに変更
    use_metadata: BoolProperty(
        name="Use Metadata",
        default=True,
        options={'HIDDEN'},
    )
    # endregion
    ######################################################

    save_prefs: BoolProperty(name="Save Settings", default=True)

    batch_filename_contains_extension: BoolProperty(name="Contains Extension", default=False)

    use_selection_children: BoolProperty(name="Selected Objects  (Include Children)", default=False)
    use_active_collection_children: BoolProperty(name="Active Collection (Include Children)", default=False)

    enable_auto_merge: BoolProperty(name="Enable Auto Merge", default=True)

    enable_apply_modifiers_with_shapekeys: BoolProperty(name="Apply Modifier with Shape Keys", default=True)
    enable_separate_lr_shapekey: BoolProperty(name="Separate Shape Keys LR", default=True)

    def load_scene_prefs(self):
        # シーンから設定を読み込み
        p_str = bpy.context.scene.mizore_exporter_prefs.export_str_props
        print("prop(str): " + str(len(p_str)))
        for i in range(len(p_str)):
            prop = p_str[i]
            key = prop.name
            value = prop.value
            print("load prop: " + key + ", " + str(value))
            self.properties[key] = value

        p_int = bpy.context.scene.mizore_exporter_prefs.export_int_props
        print("prop(int): " + str(len(p_int)))
        for i in range(len(p_int)):
            prop = p_int[i]
            key = prop.name
            value = prop.value
            print("load prop: " + key + ", " + str(value))
            self.properties[key] = value

    def save_scene_prefs(self):
        # シーンに設定を保存
        p_str = bpy.context.scene.mizore_exporter_prefs.export_str_props
        p_int = bpy.context.scene.mizore_exporter_prefs.export_int_props
        for key, value in self.properties.items():
            t = type(value)
            if t is str:
                print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
                set_prop_col_value(p_str, key, value)
            elif t is int:
                print("save prop: " + key + ", " + str(value) + ", " + str(type(value)))
                set_prop_col_value(p_int, key, value)
            else:
                print("!!! save prop failed: " + key + ", " + str(value) + ", " + str(type(value)))
        print("prop(str): " + str(len(p_str)))
        print("prop(int): " + str(len(p_int)))

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "save_prefs")

    def invoke(self, context, event):
        # シーンから設定を読み込み
        self.load_scene_prefs()
        return super().invoke(context, event)

    def execute(self, context):
        # # 実行前のシーンをtempディレクトリに保存
        # temp_blend_path=bpy.app.tempdir+"sc_automerge_temp.blend"
        # print("Create temp: " + temp_blend_path)
        # bpy.ops.wm.save_as_mainfile(filepath=temp_blend_path, copy=True)

        modeTemp = None
        if bpy.context.object != None:
            # 開始時のモードを記憶しオブジェクトモードに
            modeTemp = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='OBJECT')

        # 現在の選択状況を記憶
        activeTemp = get_active_object()
        selectedTemp = bpy.context.selected_objects

        # 常時エクスポートするオブジェクトを表示
        hide_temp_always_export = {}
        layer_col_always_export = None
        if ALWAYS_EXPORT_GROUP_NAME in context.view_layer.layer_collection.children:
            layer_col_always_export = context.view_layer.layer_collection.children[ALWAYS_EXPORT_GROUP_NAME]
            # layer_col_always_export.exclude = False
            # コレクションを表示
            layer_col_always_export.hide_viewport = False
            # オブジェクトの表示状態を記憶してから表示
            collection = bpy.data.collections[layer_col_always_export.name]
            for obj in collection.objects:
                hide_temp_always_export[obj] = obj.hide_get()
                obj.hide_set(False)


        if self.use_selection == False and self.use_selection_children == False:
            # Selected Objectsにチェックがついていないなら全オブジェクトを選択
            bpy.ops.object.select_all(action="SELECT")

        if self.use_selection_children:
            current_selected = bpy.context.selected_objects
            for obj in current_selected:
                set_active_object(obj)
                if bpy.context.object.mode != 'OBJECT':
                    # Armatureをアクティブにしたとき勝手にPoseモードになる場合があるためここで確実にObjectモードにする
                    bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_grouped(extend=True, type='CHILDREN_RECURSIVE')

        if self.use_active_collection or self.use_active_collection_children:
            active_layer_collection = bpy.context.view_layer.active_layer_collection
            print("Active Collection: " + active_layer_collection.name)
            active_collection = bpy.data.collections[active_layer_collection.name]
            select_collection_only(collection=active_collection, include_children=self.use_active_collection_children)

        # エクスポート除外コレクションを取得
        ignore_collection = None
        if DONT_EXPORT_GROUP_NAME in bpy.data.collections:
            ignore_collection = bpy.data.collections[DONT_EXPORT_GROUP_NAME]
            # 処理から除外するオブジェクトの選択を外す
            deselect_collection(ignore_collection)

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
                set_active_object(o)
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                targets_source_mode[i] = None

        # オブジェクト名に接尾辞を付ける
        # （名前の末尾が xxx.001 のように数字になっている場合にオブジェクトを複製すると名前がxxx.002 のようにカウントアップされてしまい、オブジェクト名の復元時に問題が起きるのでその対策）
        for obj in targets_source:
            add_suffix(obj)

        # オブジェクトを複製
        bpy.ops.object.duplicate()
        targets_dup = bpy.context.selected_objects
        targets_dup.sort(key=lambda x: x.name)

        # 複製したオブジェクトの名前から接尾辞を削除
        for obj in targets_dup:
            remove_suffix(obj)

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
                from AutoMerge import apply_modifier_and_merge_children_grouped
                result_tuple = apply_modifier_and_merge_children_grouped(
                    self, context, ignore_collection, self.enable_apply_modifiers_with_shapekeys,
                    duplicate=False, apply_parentobj_modifier=True, ignore_armature=True)

                # 結合処理失敗
                if result_tuple == False:
                    # 複製されたオブジェクトを削除
                    deselect_all_objects()
                    select_objects(targets_dup, True)
                    bpy.ops.object.delete()
                    return {'FAILED'}
            except ImportError:
                t = "!!! Failed to load AutoMerge !!!"
                print(t)
        # ↑ AutoMergeアドオン連携

        print("xxxxxx Export Targets xxxxxx\n" + '\n'.join(
            [obj.name for obj in bpy.context.selected_objects]) + "\nxxxxxxxxxxxxxxx")

        # ShapeKeysUtil連携
        if self.enable_apply_modifiers_with_shapekeys == True and self.use_mesh_modifiers:
            try:
                from ShapeKeysUtil import apply_modifiers_with_shapekeys
                active = get_active_object()
                selected_objects = bpy.context.selected_objects
                targets = [d for d in selected_objects if d.type == 'MESH']
                for obj in targets:
                    set_active_object(obj)
                    b = apply_modifiers_with_shapekeys(self, context.object, False, False)
                    if b == False: self.report({'ERROR'}, t)
                # 選択オブジェクトを復元
                for obj in selected_objects:
                    obj.select_set(True)
                set_active_object(active)
            except ImportError:
                t = "!!! Failed to load ShapeKeysUtil !!! - apply_modifiers_with_shapekeys"
                print(t)
                self.report({'ERROR'}, t)
        if self.enable_separate_lr_shapekey == True:
            try:
                from ShapeKeysUtil import separate_lr_shapekey_all
                for obj in bpy.context.selected_objects:
                    if obj.type == 'MESH' and obj.data.shape_keys != None and len(obj.data.shape_keys.key_blocks) != 0:
                        set_active_object(obj)
                        separate_lr_shapekey_all(duplicate=False, enable_sort=False, auto_detect=True)
            except ImportError:
                t = "!!! Failed to load ShapeKeysUtil !!! - separate_lr_shapekey_all"
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
        keywords["use_selection"]=True
        keywords["use_active_collection"]=False
        keywords["batch_mode"] = 'OFF'
        #

        from io_scene_fbx import export_fbx_bin
        # BatchMode用処理
        if self.batch_mode == 'SCENE':
            self.report({'ERROR'}, "未実装 WIP")
        elif self.batch_mode == 'COLLECTION':
            ignore_collections=[ALWAYS_EXPORT_GROUP_NAME]
            try:
                from AutoMerge import PARENTS_GROUP_NAME
                ignore_collections.append(PARENTS_GROUP_NAME)
            except ImportError:
                pass

            targets = bpy.context.selected_objects
            for collection in bpy.data.collections:
                if collection.name in ignore_collections:
                    continue
                deselect_all_objects()
                objects = list(set(collection.objects) & set(targets))
                select_objects(objects, True)
                if (self.batch_filename_contains_extension):
                    path = f"{self.filepath}_{collection.name}.fbx"
                else:
                    path = f"{os.path.splitext(self.filepath)[0]}_{collection.name}.fbx"
                keywords["filepath"] = path
                print("export: " + path)
                export_fbx_bin.save(self, context, **keywords)
        elif self.batch_mode == 'SCENE_COLLECTION':
            self.report({'ERROR'}, "未実装 WIP")
        elif self.batch_mode == 'ACTIVE_SCENE_COLLECTION':
            self.report({'ERROR'}, "未実装 WIP")
        else:
            export_fbx_bin.save(self, context, **keywords)
        # endregion

        # 複製されたオブジェクトを削除
        deselect_all_objects()
        for obj in targets_dup:
            try:
                obj.select_set(True)
            except ReferenceError:
                pass
        bpy.ops.object.delete()

        # 複製前オブジェクト名から接尾辞を削除
        for obj in targets_source:
            remove_suffix(obj)

        # AlwaysExportを非表示
        if layer_col_always_export:
            # layer_col_always_export.exclude = True
            layer_col_always_export.hide_viewport = True
            # オブジェクトの表示状態を復元
            for obj, value in hide_temp_always_export.items():
                obj.hide_set(value)

        # 選択状況を処理前の状態に復元
        deselect_all_objects()
        select_objects(selectedTemp, True)
        # set_active_object(activeTemp)

        # オブジェクトのモードを復元
        for i in range(len(targets_source)):
            m = targets_source_mode[i]
            if m is not None:
                set_active_object(targets_source[i])
                bpy.ops.object.mode_set(mode=m)
        set_active_object(activeTemp)

        if modeTemp != None:
            # 開始時のモードを復元
            bpy.ops.object.mode_set(mode=modeTemp)

        # シーンに設定を保存
        if self.save_prefs:
            self.save_scene_prefs()

        return {'FINISHED'}


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
        row.enabled = (operator.batch_mode != 'OFF')
        row.prop(operator, "batch_filename_contains_extension")


class MIZORE_FBX_PT_export_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"

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

        sublayout = layout.column(heading="Limit to")
        sublayout.enabled = (operator.batch_mode == 'OFF')
        sublayout.prop(operator, "use_selection")
        sublayout.prop(operator, "use_selection_children")
        sublayout.prop(operator, "use_active_collection")
        sublayout.prop(operator, "use_active_collection_children")

        layout.column().prop(operator, "object_types")
        layout.prop(operator, "use_custom_props")


class MIZORE_FBX_PT_export_geometry(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Geometry"
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
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "mesh_smooth_type")
        layout.prop(operator, "use_subsurf")
        layout.prop(operator, "use_mesh_modifiers")
        # sub = layout.row()
        # sub.enabled = operator.use_mesh_modifiers and False  # disabled in 2.8...
        # sub.prop(operator, "use_mesh_modifiers_render")
        layout.prop(operator, "use_mesh_edges")
        sub = layout.row()
        # ~ sub.enabled = operator.mesh_smooth_type in {'OFF'}
        sub.prop(operator, "use_tspace")


class MIZORE_FBX_PT_export_armature(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Armature"
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
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "primary_bone_axis")
        layout.prop(operator, "secondary_bone_axis")
        layout.prop(operator, "armature_nodetype")
        layout.prop(operator, "use_armature_deform_only")
        layout.prop(operator, "add_leaf_bones")


class MIZORE_FBX_PT_export_bake_animation(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Bake Animation"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator

        self.layout.prop(operator, "bake_anim", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.enabled = operator.bake_anim
        layout.prop(operator, "bake_anim_use_all_bones")
        layout.prop(operator, "bake_anim_use_nla_strips")
        layout.prop(operator, "bake_anim_use_all_actions")
        layout.prop(operator, "bake_anim_force_startend_keying")
        layout.prop(operator, "bake_anim_step")
        layout.prop(operator, "bake_anim_simplify_factor")


class MIZORE_FBX_PT_export_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

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

        layout.prop(operator, "global_scale")
        layout.prop(operator, "apply_scale_options")

        layout.prop(operator, "axis_forward")
        layout.prop(operator, "axis_up")

        layout.prop(operator, "apply_unit_scale")
        layout.prop(operator, "use_space_transform")
        row = layout.row()
        row.prop(operator, "bake_space_transform")
        row.label(text="", icon='ERROR')

class MIZORE_FBX_PT_export_automerge(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "[Addon]Auto Merge"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx" and auto_merge_is_found()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "enable_auto_merge")

class MIZORE_FBX_PT_export_shapekeysutil(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "[Addon]ShapeKey Utils"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_custom_export_mizore_fbx" and shapekey_util_is_found()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "enable_apply_modifiers_with_shapekeys")
        layout.prop(operator, "enable_separate_lr_shapekey")

        box = layout.box()
        box.label(text=bpy.app.translations.pgettext("box_warning_slow_method_1"))
        box.label(text=bpy.app.translations.pgettext("box_warning_slow_method_2"))
        box.label(text=bpy.app.translations.pgettext("box_warning_slow_method_3"))

# 選択オブジェクトをDontExportグループに入れたり外したりするクラス
class OBJECT_OT_specials_assign_dont_export_group(bpy.types.Operator):
    bl_idname = "object.assign_dont_export_group"
    bl_label = "Assign Don't-Export Group"
    bl_description = "選択中のオブジェクトを\nオブジェクトグループ“"+DONT_EXPORT_GROUP_NAME+"”に入れたり外したりします"
    bl_options = {'REGISTER', 'UNDO'}

    assign: bpy.props.BoolProperty(name="Assign", default=True)

    def execute(self, context):
        assign_object_group(group_name=DONT_EXPORT_GROUP_NAME, assign=self.assign)
        # exclude_collection(context=context, group_name=DONT_EXPORT_GROUP_NAME, exclude=True)
        hide_collection(context=context, group_name=DONT_EXPORT_GROUP_NAME, hide=True)
        return {'FINISHED'}


# 選択オブジェクトをAlwaysExportグループに入れたり外したりするクラス
class OBJECT_OT_specials_assign_always_export_group(bpy.types.Operator):
    bl_idname = "object.assign_always_export_group"
    bl_label = "Assign Always-Export Group"
    bl_description = "選択中のオブジェクトを\nオブジェクトグループ“"+ALWAYS_EXPORT_GROUP_NAME+"”に入れたり外したりします"
    bl_options = {'REGISTER', 'UNDO'}

    assign: bpy.props.BoolProperty(name="Assign", default=True)

    def execute(self, context):
        assign_object_group(group_name=ALWAYS_EXPORT_GROUP_NAME, assign=self.assign)
        # exclude_collection(context=context, group_name=ALWAYS_EXPORT_GROUP_NAME, exclude=True)
        hide_collection(context=context, group_name=ALWAYS_EXPORT_GROUP_NAME, hide=True)
        return {'FINISHED'}
### endregion ###

### region Init Menu ###
# ExportメニューにOperatorを登録
def INFO_MT_file_custom_export_mizore_menu(self, context):
    self.layout.operator(INFO_MT_file_custom_export_mizore_fbx.bl_idname)


# 右クリックメニューにOperatorを登録
def INFO_MT_object_mizores_exporter_menu(self, context):
    self.layout.menu(VIEW3D_MT_object_mizores_exporter.bl_idname)
class VIEW3D_MT_object_mizores_exporter(bpy.types.Menu):
    bl_label = "Mizore's Custom Exporter"
    bl_idname = "VIEW3D_MT_object_mizores_exporter"

    def draw(self, context):
        self.layout.operator(OBJECT_OT_specials_assign_dont_export_group.bl_idname)
        self.layout.operator(OBJECT_OT_specials_assign_always_export_group.bl_idname)
### endregion ###

### region Init ###
classes = [
    VIEW3D_MT_object_mizores_exporter,
    INFO_MT_file_custom_export_mizore_fbx,
    MIZORE_FBX_PT_export_main, MIZORE_FBX_PT_export_include, MIZORE_FBX_PT_export_transform,
    MIZORE_FBX_PT_export_geometry, MIZORE_FBX_PT_export_armature, MIZORE_FBX_PT_export_bake_animation,

    MIZORE_FBX_PT_export_automerge, MIZORE_FBX_PT_export_shapekeysutil,

    OBJECT_OT_specials_assign_dont_export_group,
    OBJECT_OT_specials_assign_always_export_group,

    PR_StringPropertyCollection, PR_IntPropertyCollection,
    PR_MizoreExporter_ScenePref,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.translations.register(__name__, translations_dict)

    bpy.types.Scene.mizore_exporter_prefs = bpy.props.PointerProperty(type=PR_MizoreExporter_ScenePref)
    bpy.types.TOPBAR_MT_file_export.append(INFO_MT_file_custom_export_mizore_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(INFO_MT_object_mizores_exporter_menu)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.app.translations.unregister(__name__)

    bpy.types.Scene.mizore_exporter_prefs = None
    bpy.types.TOPBAR_MT_file_export.remove(INFO_MT_file_custom_export_mizore_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(INFO_MT_object_mizores_exporter_menu)


if __name__ == "__main__":
    register()
### endregion ###