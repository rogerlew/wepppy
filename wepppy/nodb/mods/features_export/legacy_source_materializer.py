"""Legacy geometry-first source materialization helpers."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .contracts import ExportWarning
from .discovery import discover_layer_sources
from .join_planner import MaterializationContractError


@dataclass(frozen=True)
class LegacyMergedSourceResult:
    """Merged legacy frame plus discovered source metadata."""

    frame: gpd.GeoDataFrame
    discovered_units: dict[str, str]
    warnings: tuple[ExportWarning, ...]


def build_legacy_merged_frame(
    *,
    wd: Path,
    layer_id: str,
    scope: str,
    catalog_layer_raw: cabc.Mapping[str, object],
    dependency_entries: cabc.Sequence[object],
    geometry_relpath: str,
    geometry_frame: gpd.GeoDataFrame,
    join_contract: cabc.Mapping[str, object],
    merge_source_dataframe: cabc.Callable[
        ...,
        tuple[gpd.GeoDataFrame, bool, dict[str, str]],
    ],
) -> LegacyMergedSourceResult:
    """Build a legacy merged GeoDataFrame with strict required-source semantics."""

    sources, warnings = discover_layer_sources(
        wd=wd,
        layer_id=layer_id,
        scope=scope,
        catalog_layer_raw=catalog_layer_raw,
        dependency_entries=dependency_entries,
        skip_vector_relpath=geometry_relpath,
    )

    merged = geometry_frame
    discovered_units: dict[str, str] = {}
    for source in sources:
        merged, joined, source_column_map = merge_source_dataframe(
            geometry_frame=merged,
            source_df=source.dataframe,
            source_id=source.source_id,
            join_contract=join_contract,
        )
        if joined:
            for source_column, display_unit in source.units_by_column.items():
                if not isinstance(display_unit, str) or not display_unit.strip():
                    continue
                resolved_column = source_column_map.get(source_column, source_column)
                if resolved_column in merged.columns:
                    discovered_units[resolved_column] = display_unit.strip()
            continue

        if source.required:
            raise MaterializationContractError(
                "Unable to resolve join key for required source.",
                details=(
                    f"layer={layer_id!r}; source_id={source.source_id!r}; "
                    "reason=required_source_join_unresolved"
                ),
            )

    return LegacyMergedSourceResult(
        frame=merged,
        discovered_units=discovered_units,
        warnings=tuple(warnings),
    )


__all__ = [
    "LegacyMergedSourceResult",
    "build_legacy_merged_frame",
]
