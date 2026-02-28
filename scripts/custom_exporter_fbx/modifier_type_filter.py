# モディファイアタイプフィルター定義とユーティリティ
#
# Blender APIからモディファイアタイプ一覧を動的に取得し、
# エクスポート時に適用するモディファイアタイプの選択UIを提供する。
# Blenderのバージョンアップで新しいモディファイアが追加されても自動対応する。

import bpy
from bpy.props import BoolProperty

PROP_PREFIX = "mod_filter_"

# 初期状態で無効（適用しない）にするモディファイアタイプ
DEFAULT_DISABLED_TYPES = {'ARMATURE', 'MULTIRES'}

# UIカテゴリ分類マッピング（表示整理用）
# ここに含まれないタイプは "Other" カテゴリに分類される
_CATEGORY_MAP = {
    "Generate": {
        'ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE', 'EDGE_SPLIT',
        'MASK', 'MIRROR', 'MULTIRES', 'REMESH', 'SCREW', 'SKIN',
        'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'VOLUME_TO_MESH', 'WELD',
        'WIREFRAME',
    },
    "Modify": {
        'DATA_TRANSFER', 'MESH_CACHE', 'MESH_SEQUENCE_CACHE', 'NORMAL_EDIT',
        'WEIGHTED_NORMAL', 'UV_PROJECT', 'UV_WARP', 'VERTEX_WEIGHT_EDIT',
        'VERTEX_WEIGHT_MIX', 'VERTEX_WEIGHT_PROXIMITY',
    },
    "Deform": {
        'ARMATURE', 'CAST', 'CORRECTIVE_SMOOTH', 'CURVE', 'DISPLACE',
        'HOOK', 'LAPLACIANDEFORM', 'LAPLACIANSMOOTH', 'LATTICE',
        'MESH_DEFORM', 'SHRINKWRAP', 'SIMPLE_DEFORM', 'SMOOTH',
        'SURFACE_DEFORM', 'WARP', 'WAVE',
    },
    "Physics": {
        'CLOTH', 'COLLISION', 'DYNAMIC_PAINT', 'EXPLODE', 'FLUID',
        'OCEAN', 'PARTICLE_INSTANCE', 'PARTICLE_SYSTEM', 'SOFT_BODY',
    },
    "Nodes": {
        'NODES',
    },
}

# Blender APIから取得した全モディファイアタイプのキャッシュ
# [(identifier, name, description), ...]
_modifier_types_cache = None


def _get_modifier_types_from_blender() -> list:
    """Blender APIからモディファイアタイプ一覧を動的に取得

    Returns:
        list of (identifier, name): Blenderが認識する全モディファイアタイプ
    """
    global _modifier_types_cache
    if _modifier_types_cache is not None:
        return _modifier_types_cache

    enum_items = bpy.types.Modifier.bl_rna.properties['type'].enum_items
    _modifier_types_cache = [
        (item.identifier, item.name)
        for item in enum_items
    ]
    return _modifier_types_cache


def _get_category(mod_type: str) -> str:
    """モディファイアタイプのUIカテゴリを取得"""
    for category, types in _CATEGORY_MAP.items():
        if mod_type in types:
            return category
    return "Other"


def get_property_name(mod_type: str) -> str:
    """モディファイアタイプIDからBoolPropertyの属性名を生成"""
    return f"{PROP_PREFIX}{mod_type.lower()}"


def get_categorized_modifier_types() -> dict:
    """カテゴリ別にグルーピングされたモディファイアタイプを返す

    Returns:
        dict: {カテゴリ名: [(identifier, display_name), ...]}
    """
    all_types = _get_modifier_types_from_blender()
    categorized = {}
    for mod_type, display_name in all_types:
        category = _get_category(mod_type)
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((mod_type, display_name))
    return categorized


def get_skip_modifier_types(operator) -> set:
    """オペレーターのBoolPropertyからスキップ対象のモディファイアタイプsetを取得"""
    skip_types = set()
    for mod_type, _name in _get_modifier_types_from_blender():
        prop_name = get_property_name(mod_type)
        # プロパティが存在しない場合（未知のモディファイアタイプ）はデフォルトで有効（適用する）
        if not getattr(operator, prop_name, True):
            skip_types.add(mod_type)
    return skip_types


def register_properties(operator_cls):
    """オペレータークラスにモディファイアタイプフィルター用のBoolPropertyを動的に登録"""
    for mod_type, display_name in _get_modifier_types_from_blender():
        prop_name = get_property_name(mod_type)
        default = mod_type not in DEFAULT_DISABLED_TYPES
        # __annotations__ に追加することでBlenderのプロパティシステムに認識させる
        operator_cls.__annotations__[prop_name] = BoolProperty(
            name=display_name,
            default=default,
        )


def unregister_properties(operator_cls):
    """オペレータークラスからモディファイアタイプフィルター用のBoolPropertyを削除"""
    for mod_type, _name in _get_modifier_types_from_blender():
        prop_name = get_property_name(mod_type)
        if prop_name in operator_cls.__annotations__:
            del operator_cls.__annotations__[prop_name]
