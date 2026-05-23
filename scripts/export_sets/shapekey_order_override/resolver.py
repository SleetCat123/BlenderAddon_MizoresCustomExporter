import importlib
from types import SimpleNamespace

from .. import func_export_sets
from . import storage


AUTOMERGE_MODULE = "BlenderAddon-AutoMerge"


def _load_automerge_module(relative_path: str):
    return importlib.import_module(f"{AUTOMERGE_MODULE}.{relative_path}")


def _storage_module():
    return _load_automerge_module("scripts.shapekey_order.storage")


def _candidate_module():
    return _load_automerge_module("scripts.shapekey_order.candidate_sources")


def _schema_module():
    return _load_automerge_module("scripts.shapekey_order.schema")


def _order_module():
    return _load_automerge_module("scripts.shapekey_order.order_resolver")


def _converter_module():
    return _load_automerge_module("scripts.shapekey_order.operation_converter")


def build_candidate_rows(obj, context=None, *, allow_write=True):
    return _candidate_module().build_candidate_rows(obj, context, allow_write=allow_write)


def build_resolved_rows(obj, ordered_names, context=None, *, allow_write=True):
    candidate_rows = build_candidate_rows(obj, context, allow_write=allow_write)
    return _order_module().resolve_rows(candidate_rows, ordered_names)


def format_rows_for_entry(rows):
    schema_module = _schema_module()
    result = []
    for row in rows:
        result.append(
            SimpleNamespace(
                final_name=row.final_name,
                kinds_label=schema_module.format_kind_label(row),
                source_objects_label=schema_module.format_source_objects_label(row),
                source_detail_label=schema_module.format_source_detail_label(row),
                match_tokens_serialized="\n".join(getattr(row, "match_tokens", [])),
                state_label=schema_module.format_state_label(row),
                is_basis=row.is_basis,
                is_resolved=row.is_resolved,
            )
        )
    return result


def _row_signature(row):
    return (
        getattr(row, "final_name", ""),
        getattr(row, "kinds_label", ""),
        getattr(row, "source_objects_label", ""),
        getattr(row, "source_detail_label", ""),
        getattr(row, "match_tokens_serialized", ""),
        getattr(row, "state_label", ""),
        bool(getattr(row, "is_basis", False)),
        bool(getattr(row, "is_resolved", True)),
    )


def get_base_ordered_names(obj, candidate_names: list[str] | None = None, candidate_rows=None):
    return _storage_module().get_ordered_names(
        obj,
        candidate_names=candidate_names,
        candidate_rows=candidate_rows,
    )


def sync_override_entry(entry, context=None):
    if entry is None or entry.target_object is None:
        return

    candidate_rows = build_candidate_rows(entry.target_object, context)
    candidate_names = [row.final_name for row in candidate_rows]
    saved_entries = storage.get_entry_saved_entries(entry)
    if not saved_entries:
        saved_entries = _storage_module().get_saved_entries(entry.target_object)
        if not saved_entries:
            saved_entries = _order_module().saved_entries_from_names(
                get_base_ordered_names(
                    entry.target_object,
                    candidate_names=candidate_names,
                    candidate_rows=candidate_rows,
                )
            )
    resolved_rows = _order_module().resolve_rows(candidate_rows, saved_entries)
    storage.set_entry_rows(entry, format_rows_for_entry(resolved_rows))


def needs_entry_sync(entry, context=None):
    if entry is None or entry.target_object is None:
        return False

    candidate_rows = build_candidate_rows(entry.target_object, context, allow_write=False)
    candidate_names = [row.final_name for row in candidate_rows]
    saved_entries = storage.get_entry_saved_entries(entry)
    if not saved_entries:
        saved_entries = _storage_module().get_saved_entries(entry.target_object)
        if not saved_entries:
            saved_entries = _order_module().saved_entries_from_names(
                get_base_ordered_names(
                    entry.target_object,
                    candidate_names=candidate_names,
                    candidate_rows=candidate_rows,
                )
            )

    resolved_rows = _order_module().resolve_rows(candidate_rows, saved_entries)
    current_signature = [_row_signature(row) for row in entry.rows]
    resolved_signature = [
        _row_signature(row)
        for row in format_rows_for_entry(resolved_rows)
    ]
    return current_signature != resolved_signature


def get_effective_ordered_names(export_set, source_obj, candidate_names: list[str] | None = None):
    candidate_rows = build_candidate_rows(source_obj)
    entry = storage.get_override_entry(export_set, source_obj)
    if entry is not None and entry.override_enabled:
        override_entries = storage.get_entry_saved_entries(entry)
        if override_entries:
            resolved_rows = _order_module().resolve_rows(candidate_rows, override_entries)
            return _order_module().ordered_names_from_rows(resolved_rows, include_unresolved=False)
    return get_base_ordered_names(
        source_obj,
        candidate_names=candidate_names,
        candidate_rows=candidate_rows,
    )


def build_operations_for_object(obj, ordered_names: list[str] | None):
    return _converter_module().build_reorder_operations(obj, ordered_names)


def build_base_reorder_targets(objects):
    result = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        candidate_rows = build_candidate_rows(obj)
        candidate_names = [row.final_name for row in candidate_rows]
        ordered_names = get_base_ordered_names(obj, candidate_names=candidate_names, candidate_rows=candidate_rows)
        operations = build_operations_for_object(obj, ordered_names)
        if operations:
            result.append((obj, operations))
    return result


def get_runtime_source_object(runtime, duplicate_obj):
    for source_obj, runtime_obj in getattr(runtime, "duplicate_source_pairs", []):
        if runtime_obj == duplicate_obj:
            return source_obj
    return None


def build_export_set_reorder_targets(export_set, runtime):
    result = []
    for obj in runtime.duplicate_objects:
        if not func_export_sets.object_exists(obj):
            continue
        if obj.type != 'MESH':
            continue
        source_obj = get_runtime_source_object(runtime, obj)
        if source_obj is None:
            continue
        candidate_rows = build_candidate_rows(source_obj)
        candidate_names = [row.final_name for row in candidate_rows]
        ordered_names = get_effective_ordered_names(
            export_set,
            source_obj,
            candidate_names=candidate_names,
        )
        operations = build_operations_for_object(obj, ordered_names)
        if operations:
            result.append((obj, operations))
    return result
