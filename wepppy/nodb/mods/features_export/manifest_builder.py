"""Manifest metadata assembly helpers for features export materialization outputs."""

from __future__ import annotations

import collections.abc as cabc


def build_output_layer_column_metadata(
    *,
    source_layer_ids: cabc.Sequence[str],
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    description_mapping: cabc.Mapping[str, str] | None = None,
    materialization: cabc.Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build deterministic per-output metadata payload for manifest column sections."""

    normalized_columns: list[str] = []
    seen_columns: set[str] = set()
    for column in selected_columns:
        token = str(column).strip()
        if not token or token in seen_columns:
            continue
        seen_columns.add(token)
        normalized_columns.append(token)

    normalized_units: dict[str, str] = {}
    for column in normalized_columns:
        unit_value = unit_mapping.get(column)
        if isinstance(unit_value, str) and unit_value.strip():
            normalized_units[column] = unit_value.strip()

    normalized_descriptions: dict[str, str] = {}
    description_source = description_mapping or {}
    for column in normalized_columns:
        description_value = description_source.get(column)
        if isinstance(description_value, str) and description_value.strip():
            normalized_descriptions[column] = description_value.strip()

    payload: dict[str, object] = {
        "source_layer_ids": [str(layer_id).strip() for layer_id in source_layer_ids if str(layer_id).strip()],
        "selected_columns": normalized_columns,
        "unit_mapping": normalized_units,
        "description_mapping": normalized_descriptions,
    }

    if isinstance(materialization, cabc.Mapping) and materialization:
        payload["materialization"] = {
            str(key): value
            for key, value in materialization.items()
            if str(key).strip()
        }

    return payload


__all__ = ["build_output_layer_column_metadata"]
