"""DuckDB key-first materialization helpers for features export carrier cores."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass

import duckdb
import pandas as pd

from .discovery import DiscoveredSourceFrame
from .join_planner import (
    JOIN_KEY_COLUMN,
    MaterializationContractError,
    dedupe_column_name,
    ensure_unique_keys,
    normalize_join_token,
    resolve_source_key,
    with_canonical_join_key,
)


@dataclass(frozen=True)
class LayerCarrierInput:
    """Layer-level carrier attributes staged for group consolidation."""

    layer_id: str
    dataframe: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]


@dataclass(frozen=True)
class CarrierCoreResult:
    """Carrier-level key-first attribute core materialization result."""

    dataframe: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]
    source_layer_ids: tuple[str, ...]


def materialize_layer_attributes(
    *,
    layer_id: str,
    carrier_layer: str | None,
    join_contract: cabc.Mapping[str, object],
    sources: cabc.Sequence[DiscoveredSourceFrame],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Materialize one key-first per-layer attributes table from discovered sources."""

    staged_tables: list[tuple[str, pd.DataFrame, dict[str, str]]] = []

    for source in sources:
        source_key = resolve_source_key(
            source_columns=source.dataframe.columns,
            join_contract=join_contract,
            source_id=source.source_id,
            carrier_layer=carrier_layer,
        )
        if source_key is None:
            if source.required:
                raise MaterializationContractError(
                    "Unable to resolve join key for required source.",
                    details=f"layer={layer_id}; source={source.source_id}",
                )
            continue

        source_frame = with_canonical_join_key(source.dataframe, source_key=source_key)
        source_frame = ensure_unique_keys(
            source_frame,
            context_label=f"layer={layer_id};source={source.source_id}",
        )
        staged_tables.append((source.source_id, source_frame, dict(source.units_by_column)))

    if not staged_tables:
        raise MaterializationContractError(
            "No source tables were available for key-first layer materialization.",
            details=f"layer={layer_id}",
        )

    _source_id, merged, source_units = staged_tables[0]
    merged = merged.copy()
    unit_mapping: dict[str, str] = {}
    for column_name, display_unit in source_units.items():
        if column_name in merged.columns and isinstance(display_unit, str) and display_unit.strip():
            unit_mapping[column_name] = display_unit.strip()

    for source_id, source_frame, source_units in staged_tables[1:]:
        right = source_frame.copy()
        used_names = set(merged.columns) | set(right.columns)
        rename_map: dict[str, str] = {}

        for column_name in list(right.columns):
            if column_name == JOIN_KEY_COLUMN:
                continue
            if column_name not in merged.columns:
                continue
            suffix = normalize_join_token(source_id) or "source"
            renamed = dedupe_column_name(f"{column_name}__{suffix}", used_names)
            rename_map[column_name] = renamed
            used_names.add(renamed)

        if rename_map:
            right = right.rename(columns=rename_map)

        merged = _duckdb_left_join(
            left_df=merged,
            right_df=right,
            left_key=JOIN_KEY_COLUMN,
            right_key=JOIN_KEY_COLUMN,
        )
        merged = ensure_unique_keys(
            merged,
            context_label=f"layer={layer_id};joined_source={source_id}",
        )

        for source_column, display_unit in source_units.items():
            if not isinstance(display_unit, str) or not display_unit.strip():
                continue
            resolved_column = rename_map.get(source_column, source_column)
            if resolved_column in merged.columns:
                unit_mapping[resolved_column] = display_unit.strip()

    return merged, unit_mapping


def materialize_carrier_core(
    *,
    carrier_label: str,
    layer_inputs: cabc.Sequence[LayerCarrierInput],
) -> CarrierCoreResult:
    """Consolidate one carrier core table across resolved source layers."""

    if not layer_inputs:
        raise MaterializationContractError(
            "No layer inputs were supplied for carrier core materialization.",
            details=f"carrier={carrier_label}",
        )

    normalized_inputs: list[LayerCarrierInput] = []
    for layer_input in layer_inputs:
        normalized_frame = ensure_unique_keys(
            layer_input.dataframe,
            context_label=f"carrier={carrier_label};layer={layer_input.layer_id}",
        )
        normalized_inputs.append(
            LayerCarrierInput(
                layer_id=layer_input.layer_id,
                dataframe=normalized_frame,
                selected_columns=tuple(layer_input.selected_columns),
                unit_mapping=dict(layer_input.unit_mapping),
            )
        )

    key_seed = _union_key_seed([entry.dataframe for entry in normalized_inputs])

    selected_columns: list[str] = []
    unit_mapping: dict[str, str] = {}
    source_layer_ids: list[str] = []

    merged = key_seed
    for layer_input in normalized_inputs:
        source_layer_ids.append(layer_input.layer_id)
        right = layer_input.dataframe.copy()

        used_names = set(merged.columns) | set(right.columns)
        rename_map: dict[str, str] = {}
        suffix = normalize_join_token(layer_input.layer_id) or "layer"

        for column_name in list(right.columns):
            if column_name == JOIN_KEY_COLUMN:
                continue
            if column_name not in merged.columns:
                continue
            renamed = dedupe_column_name(f"{column_name}__{suffix}", used_names)
            rename_map[column_name] = renamed
            used_names.add(renamed)

        if rename_map:
            right = right.rename(columns=rename_map)

        merged = _duckdb_left_join(
            left_df=merged,
            right_df=right,
            left_key=JOIN_KEY_COLUMN,
            right_key=JOIN_KEY_COLUMN,
        )
        merged = ensure_unique_keys(
            merged,
            context_label=f"carrier={carrier_label};joined_layer={layer_input.layer_id}",
        )

        for column_name in layer_input.selected_columns:
            mapped_name = rename_map.get(column_name, column_name)
            if mapped_name in merged.columns and mapped_name not in selected_columns:
                selected_columns.append(mapped_name)

            display_unit = layer_input.unit_mapping.get(column_name)
            if isinstance(display_unit, str) and display_unit.strip() and mapped_name in merged.columns:
                unit_mapping[mapped_name] = display_unit.strip()

    return CarrierCoreResult(
        dataframe=merged,
        selected_columns=tuple(selected_columns),
        unit_mapping=unit_mapping,
        source_layer_ids=tuple(source_layer_ids),
    )


def _union_key_seed(frames: cabc.Sequence[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        raise MaterializationContractError("Unable to build key seed from empty frame sequence.")

    connection = duckdb.connect(database=":memory:")
    try:
        select_clauses: list[str] = []
        for index, frame in enumerate(frames):
            table_name = f"seed_{index}"
            connection.register(table_name, frame[[JOIN_KEY_COLUMN]].copy())
            select_clauses.append(f"SELECT {JOIN_KEY_COLUMN} FROM {table_name}")

        sql = (
            f"SELECT DISTINCT {JOIN_KEY_COLUMN} FROM ("
            + " UNION ALL ".join(select_clauses)
            + ") ORDER BY "
            + JOIN_KEY_COLUMN
        )
        seed = connection.execute(sql).df()
    finally:
        connection.close()

    return ensure_unique_keys(seed, context_label="carrier_key_seed")


def _duckdb_left_join(
    *,
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_key: str,
    right_key: str,
) -> pd.DataFrame:
    connection = duckdb.connect(database=":memory:")
    try:
        connection.register("left_table", left_df.copy())
        connection.register("right_table", right_df.copy())

        select_columns: list[str] = []
        for column_name in left_df.columns:
            select_columns.append(f'l.{_quote_ident(column_name)}')
        for column_name in right_df.columns:
            if column_name == right_key:
                continue
            select_columns.append(f'r.{_quote_ident(column_name)} AS {_quote_ident(column_name)}')

        sql = (
            f"SELECT {', '.join(select_columns)} "
            f"FROM left_table l LEFT JOIN right_table r "
            f"ON l.{_quote_ident(left_key)} = r.{_quote_ident(right_key)}"
        )
        return connection.execute(sql).df()
    finally:
        connection.close()


def _quote_ident(identifier: str) -> str:
    escaped = str(identifier).replace('"', '""')
    return f'"{escaped}"'


__all__ = [
    "CarrierCoreResult",
    "LayerCarrierInput",
    "materialize_carrier_core",
    "materialize_layer_attributes",
]
