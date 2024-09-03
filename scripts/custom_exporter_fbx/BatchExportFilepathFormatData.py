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

import os

class BatchExportFilepathFormatData:
    batch_file_format_default = "{name}_{batch}"
    batch_file_formats = [
        "{name}.fbx_{batch}",
        batch_file_format_default,
        "{batch}",
        f"{batch_file_format_default}/{batch_file_format_default}",
        f"{batch_file_format_default}/" + "{batch}",
        "{batch}/{batch}",
    ]
    temp_prev_batch_filename_format_presets=None
    temp_prev_batch_filename_format=None

    @staticmethod
    def init_enum_items():
        result = [('CUSTOM', "Custom", "")]
        for format in BatchExportFilepathFormatData.batch_file_formats:
            result.append((format, format + ".fbx", ""))
        return result

    @staticmethod
    def update_batch_filename_format(operator):
        if BatchExportFilepathFormatData.temp_prev_batch_filename_format != operator.batch_filename_format:
            if operator.batch_filename_format in BatchExportFilepathFormatData.batch_file_formats:
                operator.batch_filename_format_presets = operator.batch_filename_format
            else:
                operator.batch_filename_format_presets = 'CUSTOM'
        if BatchExportFilepathFormatData.temp_prev_batch_filename_format_presets != operator.batch_filename_format_presets:
            if operator.batch_filename_format_presets != 'CUSTOM':
                operator.batch_filename_format = operator.batch_filename_format_presets
        BatchExportFilepathFormatData.temp_prev_batch_filename_format_presets = operator.batch_filename_format_presets
        BatchExportFilepathFormatData.temp_prev_batch_filename_format = operator.batch_filename_format

    @staticmethod
    def convert_filename_format(format_str: str, path: str, batch: str, use_batch_own_dir: bool, fullpath: bool = True):
        if "{batch}" not in format_str:
            format_str += "_{batch}"
        dir = os.path.dirname(path)
        filename = os.path.splitext(os.path.basename(path))[0]
        result = format_str.format(name=filename, batch=batch)
        result = result.replace(' ', '_')
        if use_batch_own_dir:
            subdir = os.path.basename(result)
            if subdir.endswith(".fbx"):
                subdir = subdir[:-4]
            result = os.path.join(subdir, result)
        if not result.endswith(".fbx"):
            result += ".fbx"
        if fullpath:
            result = os.path.join(dir, result)
        return result