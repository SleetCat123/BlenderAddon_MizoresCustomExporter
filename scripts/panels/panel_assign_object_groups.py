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
from ..assign_prop_panel.base_panel_assign_object_prop import OBJECT_PT_mizores_assign_group_panel


class OBJECT_PT_mizores_assign_export_targets_group_panel(OBJECT_PT_mizores_assign_group_panel):
    bl_label = "Targets (Export)" 
    required_addons = [
        "MizoresCustomExporter",
    ]
    groups = [
        "mizore_exporter_dont_export_group_name",
        "mizore_exporter_always_export_group_name",
    ]


class OBJECT_PT_mizores_assign_export_reset_group_panel(OBJECT_PT_mizores_assign_group_panel):
    bl_label = "Reset (Export)"
    required_addons = [
        "MizoresCustomExporter",
    ]
    groups = [
        "mizore_exporter_reset_pose_group_name",
        "mizore_exporter_reset_shapekey_group_name",
        "mizore_exporter_move_to_origin_group_name",
    ]


class OBJECT_PT_mizores_assign_export_reset_always_group_panel(OBJECT_PT_mizores_assign_group_panel):
    bl_label = "Reset Always (Export)"
    required_addons = [
        "MizoresCustomExporter",
    ]
    groups = [
        "mizore_exporter_always_reset_shapekey_group_name",
    ]


class OBJECT_PT_mizores_assign_export_apply_group_panel(OBJECT_PT_mizores_assign_group_panel):
    bl_label = "Apply (Export)"
    required_addons = [
        "MizoresCustomExporter",
    ]
    groups = [
        "mizore_exporter_apply_locations_group_name",
        "mizore_exporter_apply_rotations_group_name",
        "mizore_exporter_apply_scales_group_name",
    ]

class OBJECT_PT_mizores_assign_export_remove_group_panel(OBJECT_PT_mizores_assign_group_panel):
    bl_label = "Remove Groups (Export)"
    required_addons = [
        "MizoresCustomExporter",
    ]
    groups = [
        "mizore_exporter_remove_unused_groups_group_name",
        "mizore_exporter_remove_groups_not_bone_group_name",
    ]


classes = [
    OBJECT_PT_mizores_assign_export_targets_group_panel,
    OBJECT_PT_mizores_assign_export_reset_group_panel,
    OBJECT_PT_mizores_assign_export_reset_always_group_panel,
    OBJECT_PT_mizores_assign_export_apply_group_panel,
    OBJECT_PT_mizores_assign_export_remove_group_panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)


