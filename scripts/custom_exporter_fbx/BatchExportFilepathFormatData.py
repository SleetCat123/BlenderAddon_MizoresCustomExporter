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
    batch_file_formats = [
        "{name}.fbx_{batch}",
        "{name}_{batch}",
        "{batch}",
    ]
    temp_prev_batch_filename_format_presets=None
    temp_prev_batch_filename_format=None

    @staticmethod
    def init_enum_items():
        result = [('CUSTOM', "Custom", "")]
        for format in BatchExportFilepathFormatData.batch_file_formats:
            result.append((format, format + ".fbx", ""))

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
    def convert_filename_format(format_str: str, file: str, batch: str):
        if "{batch}" not in format_str:
            format_str += "_{batch}"
        file = os.path.splitext(file)[0]
        result = format_str.format(name=file, batch=batch)
        result = result.replace(' ', '_')
        if not result.endswith(".fbx"):
            result += ".fbx"
        return result