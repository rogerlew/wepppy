"""Canonical carrier-geometry loading and one-time attachment helpers."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from wepppy.runtime_paths.materialize import materialize_path_if_archive

from .join_planner import (
    JOIN_KEY_COLUMN,
    MaterializationContractError,
    canonical_join_value,
    ensure_unique_keys,
    resolve_geometry_key,
)


@dataclass(frozen=True)
class CanonicalGeometryCarrier:
    """Canonicalized one-row-per-key carrier geometry table."""

    carrier_layer: str | None
    geometry_relpath: str
    key_column: str
    dataframe: gpd.GeoDataFrame


def build_canonical_geometry_carrier(
    *,
    wd: Path,
    carrier_layer: str | None,
    geometry_relpaths: cabc.Sequence[str],
    candidate_key_tokens: cabc.Sequence[str],
) -> CanonicalGeometryCarrier:
    """Load, key-resolve, and canonicalize one carrier geometry table."""

    relpaths = sorted({str(relpath).strip() for relpath in geometry_relpaths if str(relpath).strip()})
    if not relpaths:
        raise MaterializationContractError(
            "Unable to resolve geometry dependency for carrier materialization.",
            details=f"carrier={carrier_layer}",
        )
    if len(relpaths) > 1:
        raise MaterializationContractError(
            "Carrier materialization resolved multiple geometry sources.",
            details=f"carrier={carrier_layer}; geometry_relpaths={relpaths}",
        )

    geometry_relpath = relpaths[0]
    frame = _load_vector_dataframe(wd, geometry_relpath)

    key_column = resolve_geometry_key(
        geometry_columns=frame.columns,
        carrier_layer=carrier_layer,
        candidate_tokens=candidate_key_tokens,
    )
    if key_column is None:
        raise MaterializationContractError(
            "Unable to resolve canonical geometry key for carrier.",
            details=(
                f"carrier={carrier_layer}; geometry_relpath={geometry_relpath!r}; "
                f"candidate_keys={list(candidate_key_tokens)!r}"
            ),
        )

    working = frame.copy()
    geometry_name = working.geometry.name
    working[JOIN_KEY_COLUMN] = working[key_column].map(canonical_join_value)
    working = working.loc[working[JOIN_KEY_COLUMN].notna()].reset_index(drop=True)
    if working.empty:
        raise MaterializationContractError(
            "Carrier geometry source has no usable key rows.",
            details=f"carrier={carrier_layer}; key_column={key_column!r}",
        )

    duplicate_mask = working.duplicated(subset=[JOIN_KEY_COLUMN], keep=False)
    if duplicate_mask.any():
        duplicates = working.loc[duplicate_mask]
        non_geometry_columns = [
            column
            for column in working.columns
            if column not in {JOIN_KEY_COLUMN, geometry_name}
        ]
        conflicting_keys: list[str] = []
        for key_value, group in duplicates.groupby(JOIN_KEY_COLUMN, dropna=False, sort=False):
            if group.empty:
                continue
            for column_name in non_geometry_columns:
                if group[column_name].nunique(dropna=False) > 1:
                    conflicting_keys.append(str(key_value))
                    break

        if conflicting_keys:
            preview = ", ".join(sorted(set(conflicting_keys))[:8])
            raise MaterializationContractError(
                "Carrier geometry contains conflicting duplicate key attributes.",
                details=(
                    f"carrier={carrier_layer}; key_column={key_column!r}; "
                    f"conflicting_keys={preview}"
                ),
            )

        # Deterministic canonicalization for repeated keys: first attrs + dissolved geometry.
        attribute_columns = [
            column
            for column in working.columns
            if column not in {geometry_name}
        ]
        attrs = (
            working[attribute_columns]
            .drop_duplicates(subset=[JOIN_KEY_COLUMN], keep="first")
            .reset_index(drop=True)
        )
        dissolved = (
            working[[JOIN_KEY_COLUMN, geometry_name]]
            .dissolve(by=JOIN_KEY_COLUMN, as_index=False)
            .reset_index(drop=True)
        )
        working = attrs.merge(dissolved, on=JOIN_KEY_COLUMN, how="left")
        working = gpd.GeoDataFrame(working, geometry=geometry_name, crs=frame.crs)

    # Ensure key uniqueness after canonicalization.
    key_only = ensure_unique_keys(
        pd.DataFrame(working.drop(columns=[geometry_name])),
        context_label=f"carrier_geometry={carrier_layer}",
    )
    geometry_lookup = working.set_index(JOIN_KEY_COLUMN)[geometry_name]
    key_only[geometry_name] = key_only[JOIN_KEY_COLUMN].map(geometry_lookup)
    canonical_frame = gpd.GeoDataFrame(key_only, geometry=geometry_name, crs=frame.crs)

    return CanonicalGeometryCarrier(
        carrier_layer=carrier_layer,
        geometry_relpath=geometry_relpath,
        key_column=key_column,
        dataframe=canonical_frame,
    )


def attach_geometry_once(
    *,
    core_table: pd.DataFrame,
    geometry_carrier: CanonicalGeometryCarrier,
    allow_non_unique_keys: bool = False,
) -> gpd.GeoDataFrame:
    """Attach canonical carrier geometry once to one key-first attribute core table."""

    if JOIN_KEY_COLUMN not in core_table.columns:
        raise MaterializationContractError(
            "Carrier core table is missing canonical join key.",
            details=f"carrier={geometry_carrier.carrier_layer}",
        )

    if allow_non_unique_keys:
        core_unique = core_table.copy()
        core_unique = core_unique.loc[core_unique[JOIN_KEY_COLUMN].notna()].reset_index(drop=True)
        if core_unique.empty:
            raise MaterializationContractError(
                "Carrier core table has no usable join keys.",
                details=f"carrier={geometry_carrier.carrier_layer}",
            )
    else:
        core_unique = ensure_unique_keys(
            core_table,
            context_label=f"carrier_core={geometry_carrier.carrier_layer}",
        )
    geometry_frame = geometry_carrier.dataframe
    geometry_name = geometry_frame.geometry.name

    geometry_non_geom = pd.DataFrame(geometry_frame.drop(columns=[geometry_name]))
    duplicate_columns = [column for column in geometry_non_geom.columns if column != JOIN_KEY_COLUMN and column in core_unique.columns]
    if allow_non_unique_keys:
        core_for_join = core_unique.drop(columns=duplicate_columns, errors="ignore")
        merged = geometry_non_geom.merge(core_for_join, on=JOIN_KEY_COLUMN, how="left")
    else:
        if duplicate_columns:
            geometry_non_geom = geometry_non_geom.drop(columns=duplicate_columns, errors="ignore")
        merged = core_unique.merge(geometry_non_geom, on=JOIN_KEY_COLUMN, how="left")
    geometry_lookup = geometry_frame.set_index(JOIN_KEY_COLUMN)[geometry_name]
    merged[geometry_name] = merged[JOIN_KEY_COLUMN].map(geometry_lookup)

    return gpd.GeoDataFrame(merged, geometry=geometry_name, crs=geometry_frame.crs)


def _load_vector_dataframe(wd: Path, relpath: str) -> gpd.GeoDataFrame:
    source_path = materialize_path_if_archive(str(wd), relpath, purpose="export")
    try:
        frame = gpd.read_file(source_path)
    except (OSError, RuntimeError, ValueError) as exc:
        raise MaterializationContractError(
            "Failed to read carrier geometry source.",
            details=f"source={relpath!r}; error={exc}",
        ) from exc

    geometry_name = frame.geometry.name
    if geometry_name not in frame.columns:
        raise MaterializationContractError(
            "Carrier geometry source is missing geometry column.",
            details=f"source={relpath!r}",
        )

    return frame


__all__ = [
    "CanonicalGeometryCarrier",
    "attach_geometry_once",
    "build_canonical_geometry_carrier",
]
