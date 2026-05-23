from . import func_execute_export_sets, func_execute_standard_batch


def run_export_jobs(
    operator,
    context,
    keywords,
    result,
    all_export_targets,
    export_set_available_roots,
    export_set_item_contexts_by_ptr,
    export_fbx_with_temporarily_safe_mesh_names,
):
    if operator.batch_mode == 'EXPORT_SETS':
        yield from func_execute_export_sets.run_export_set_jobs(
            operator,
            context,
            keywords,
            result,
            all_export_targets,
            export_set_available_roots,
            export_set_item_contexts_by_ptr,
            export_fbx_with_temporarily_safe_mesh_names,
        )
        return

    batch_jobs = func_execute_standard_batch.build_standard_batch_jobs_for_mode(
        operator,
        all_export_targets,
    )
    if batch_jobs is not None:
        yield from func_execute_standard_batch.run_standard_batch_jobs(
            operator,
            context,
            keywords,
            result,
            batch_jobs,
            export_fbx_with_temporarily_safe_mesh_names,
        )
        return

    result.add_error(f"Batch mode '{operator.batch_mode}' is not defined.")
    operator.report({'ERROR'}, str(operator.batch_mode) + " は未定義です。")
