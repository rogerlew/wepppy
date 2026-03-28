"""Carrier-layer source materialization helpers."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .column_selection import resolve_selected_columns
from .contracts import ExportWarning, ResolvedExportPlan, ResolvedLayerPlan
from .discovery import discover_layer_sources
from .duckdb_materializer import materialize_layer_attributes
from .join_planner import MaterializationContractError


@dataclass(frozen=True)
class CarrierLayerCoreMaterialization:
    """Projected carrier core table plus selected-column metadata."""

    frame: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]
    warnings: tuple[ExportWarning, ...]


def materialize_carrier_layer_core(
    *,
    wd: Path,
    layer: ResolvedLayerPlan,
    catalog_layer_raw: cabc.Mapping[str, object],
    request_plan: ResolvedExportPlan,
    dependency_entries: cabc.Sequence[object],
    consolidated_join_key_column: str,
) -> CarrierLayerCoreMaterialization:
    """Build one carrier-layer core frame from discovered sources."""

    discovered_sources, discovery_warnings = discover_layer_sources(
        wd=wd,
        layer_id=layer.layer_id,
        scope=layer.scope,
        catalog_layer_raw=catalog_layer_raw,
        dependency_entries=dependency_entries,
    )
    if not discovered_sources:
        raise MaterializationContractError(
            "No source tables were available for carrier layer materialization.",
            details=f"layer={layer.layer_id!r}; output_layer_id={layer.output_layer_id!r}",
        )

    join_contract = _as_mapping(catalog_layer_raw.get("join"))
    layer_frame, discovered_units = materialize_layer_attributes(
        layer_id=layer.layer_id,
        carrier_layer=layer.carrier_layer,
        join_contract=join_contract,
        sources=discovered_sources,
    )

    selected_columns, unit_mapping = resolve_selected_columns(
        layer=layer,
        frame=layer_frame,
        catalog_layer_raw=catalog_layer_raw,
        request_plan=request_plan,
        discovered_units=discovered_units,
        consolidated_join_key_column=consolidated_join_key_column,
    )
    if consolidated_join_key_column not in layer_frame.columns:
        raise MaterializationContractError(
            "Layer materialization table is missing canonical join key.",
            details=f"layer={layer.layer_id!r}; key={consolidated_join_key_column!r}",
        )

    projected_columns: list[str] = [
        column_name
        for column_name in selected_columns
        if column_name in layer_frame.columns and column_name != consolidated_join_key_column
    ]
    projected_columns.append(consolidated_join_key_column)
    projected_frame = layer_frame[projected_columns].copy()

    return CarrierLayerCoreMaterialization(
        frame=projected_frame,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        warnings=tuple(discovery_warnings),
    )


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, cabc.Mapping):
        return {str(key): val for key, val in value.items()}
    return {}


__all__ = [
    "CarrierLayerCoreMaterialization",
    "materialize_carrier_layer_core",
]
