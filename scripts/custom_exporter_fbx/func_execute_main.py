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
from collections.abc import Generator
from typing import Optional

from ..funcs.modal.export_result import ExportResult
from ..funcs.modal.progress_info import ProgressInfo, T
from . import (
    func_execute_common,
    func_execute_dispatch,
    func_execute_export_sets,
    func_execute_safe_fbx,
)


def execute_main_iter(operator, context) -> Generator[ProgressInfo, None, ExportResult]:
    """エクスポートメイン処理（ジェネレータ版）

    Args:
        operator: エクスポートオペレーター
        context: Blenderコンテキスト

    Yields:
        ProgressInfo: 進捗情報

    Returns:
        ExportResult: エクスポート結果のサマリ
    """
    # 結果収集用オブジェクト
    result = ExportResult()
    start_time = time.perf_counter()

    yield ProgressInfo(
        phase="init",
        progress=0.0,
        message=T("mce_progress_initializing")
    )
    selection_context = func_execute_common.prepare_export_selection_context(
        operator,
        context,
        func_execute_export_sets.func_export_sets.iter_enabled_export_sets,
        func_execute_export_sets.prepare_export_set_preprocess_targets,
    )
    export_set_available_roots = selection_context.export_set_available_roots
    export_set_item_contexts_by_ptr = selection_context.export_set_item_contexts_by_ptr

    execution_context = yield from func_execute_common.prepare_export_execution_context_iter(
        operator,
        context,
        T("mce_progress_starting_preprocess"),
        T("mce_progress_exporting_fbx"),
    )
    if execution_context.cancelled_result is not None:
        return execution_context.cancelled_result

    keywords = execution_context.keywords
    all_export_targets = execution_context.all_export_targets

    yield from func_execute_dispatch.run_export_jobs(
        operator,
        context,
        keywords,
        result,
        all_export_targets,
        export_set_available_roots,
        export_set_item_contexts_by_ptr,
        func_execute_safe_fbx.export_fbx_with_temporarily_safe_mesh_names,
    )

    func_execute_common.finalize_export_result(result, start_time, all_export_targets)

    yield ProgressInfo(
        phase="complete",
        progress=1.0,
        message=T("mce_progress_export_complete")
    )

    return result


def execute_main(operator, context) -> Optional[ExportResult]:
    """エクスポートメイン処理（同期版ラッパー）

    既存コードとの互換性のため、ジェネレータ版を消費して実行します。

    Returns:
        ExportResult: エクスポート結果のサマリ
    """
    gen = execute_main_iter(operator, context)
    result = None
    try:
        while True:
            next(gen)
    except StopIteration as e:
        result = e.value
    return result
