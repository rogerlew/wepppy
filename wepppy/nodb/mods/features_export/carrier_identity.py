"""Align carrier keys and fill Topaz and WEPP identities from run data."""

from __future__ import annotations

import collections.abc as cabc
from pathlib import Path

import pandas as pd

from wepppy.project_assets import WATERSHED_HILLSLOPES
from wepppy.runtime_paths import pick_existing_parquet_path

from .join_planner import (
    JOIN_KEY_COLUMN,
    MaterializationContractError,
    canonical_join_value,
    normalize_join_token,
)

_TOPAZ_ID_COLUMN = "topaz_id"
_WEPP_ID_COLUMN = "wepp_id"


def align_core_to_geometry_identity(
    frame: pd.DataFrame,
    *,
    geometry_key_column: str,
    carrier_layer: str | None,
) -> pd.DataFrame:
    """Retarget merged hill/channel keys to the resolved geometry ID domain."""
    if carrier_layer not in {"sbs_map-subcatchments", "chan_map-channels"}:
        return frame
    identity_column = {
        "topazid": _TOPAZ_ID_COLUMN,
        "weppid": _WEPP_ID_COLUMN,
    }.get(normalize_join_token(geometry_key_column))
    if identity_column is None:
        return frame
    if identity_column not in frame.columns:
        raise MaterializationContractError(
            "Carrier core is missing the resolved geometry identity.",
            details=f"identity_column={identity_column!r}",
        )
    identities = frame[identity_column].map(canonical_join_value)
    keys = frame[JOIN_KEY_COLUMN].map(canonical_join_value)
    mapping = pd.DataFrame({"key": keys, "identity": identities}).drop_duplicates()
    if (
        mapping.isna().any().any()
        or mapping["key"].duplicated().any()
        or mapping["identity"].duplicated().any()
    ):
        raise MaterializationContractError(
            "Carrier geometry identity mapping must be complete and one-to-one.",
            details=f"identity_column={identity_column!r}",
        )
    result = frame.copy()
    result[JOIN_KEY_COLUMN] = identities
    return result


def backfill_identity_from_geometry_key(
    frame: pd.DataFrame,
    *,
    geometry_key_column: str,
    consolidated_join_key_column: str,
) -> pd.DataFrame:
    if consolidated_join_key_column not in frame.columns:
        return frame

    key_token = normalize_join_token(geometry_key_column)
    if not key_token:
        return frame

    result = frame.copy()
    join_values = result[consolidated_join_key_column]
    for column_name in result.columns:
        if column_name == consolidated_join_key_column:
            continue
        if normalize_join_token(column_name) != key_token:
            continue

        series = result[column_name]
        missing_mask = series.isna()
        if not missing_mask.any():
            continue

        if pd.api.types.is_numeric_dtype(series):
            fill_values = pd.to_numeric(join_values, errors="coerce")
        else:
            fill_values = join_values
        result.loc[missing_mask, column_name] = fill_values.loc[missing_mask]

    return result


def align_carrier_identity_join_key(
    *,
    frame: pd.DataFrame,
    wd: Path,
    carrier_layer: str | None,
    cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
) -> pd.DataFrame:
    if JOIN_KEY_COLUMN not in frame.columns:
        return frame

    carrier_token = str(carrier_layer or "").strip().lower()
    if carrier_token not in {"sbs_map-subcatchments", "chan_map-channels"}:
        return frame

    has_topaz = _TOPAZ_ID_COLUMN in frame.columns
    has_wepp = _WEPP_ID_COLUMN in frame.columns
    if not has_topaz and not has_wepp:
        return frame

    result = frame.copy()
    if not has_topaz:
        result[_TOPAZ_ID_COLUMN] = pd.Series(
            [None] * len(result.index),
            index=result.index,
            dtype="object",
        )
    if not has_wepp:
        result[_WEPP_ID_COLUMN] = pd.Series(
            [None] * len(result.index),
            index=result.index,
            dtype="object",
        )

    result = backfill_tabular_identity_from_watershed(
        frame=result,
        wd=wd,
        carrier_layer=carrier_layer,
        cache=cache,
    )

    normalized_join = result[JOIN_KEY_COLUMN].map(canonical_join_value)
    preferred_identity_order = (_TOPAZ_ID_COLUMN, _WEPP_ID_COLUMN)
    # Allow retargeting onto synthesized identity columns when watershed lookup
    # backfill resolved them and the one-to-one guardrails below are satisfied.
    retargetable_identity_columns = {
        _TOPAZ_ID_COLUMN: bool(result[_TOPAZ_ID_COLUMN].map(canonical_join_value).notna().any()),
        _WEPP_ID_COLUMN: bool(result[_WEPP_ID_COLUMN].map(canonical_join_value).notna().any()),
    }

    existing_join_non_null = normalized_join.dropna()
    existing_join_unique_count = int(existing_join_non_null.nunique())

    for identity_column in preferred_identity_order:
        if not retargetable_identity_columns.get(identity_column, False):
            continue

        identity_series = result[identity_column].map(canonical_join_value)
        identity_non_null = identity_series.dropna()
        if identity_non_null.empty:
            continue

        if existing_join_unique_count == 0:
            normalized_join = identity_series
            existing_join_non_null = normalized_join.dropna()
            existing_join_unique_count = int(existing_join_non_null.nunique())
            break

        overlap_mask = normalized_join.notna() & identity_series.notna()
        if not overlap_mask.any():
            continue

        overlap_frame = pd.DataFrame(
            {
                "join": normalized_join.loc[overlap_mask],
                "identity": identity_series.loc[overlap_mask],
            }
        ).drop_duplicates()

        # Retarget only when the identity domain covers every resolved join key
        # and preserves one-to-one key cardinality.
        if int(overlap_frame["join"].nunique()) != existing_join_unique_count:
            continue
        if int(overlap_frame["identity"].nunique()) != int(identity_non_null.nunique()):
            continue
        if int(overlap_frame["identity"].nunique()) != existing_join_unique_count:
            continue

        normalized_join = identity_series
        existing_join_non_null = normalized_join.dropna()
        existing_join_unique_count = int(existing_join_non_null.nunique())
        break

    fill_identity_order = list(preferred_identity_order)
    if normalized_join.notna().any():
        scored_order: list[tuple[int, int, str]] = []
        for order_index, identity_column in enumerate(preferred_identity_order):
            identity_series = result[identity_column].map(canonical_join_value)
            overlap_mask = normalized_join.notna() & identity_series.notna()
            match_score = 0
            if overlap_mask.any():
                match_score = int(
                    (normalized_join.loc[overlap_mask] == identity_series.loc[overlap_mask]).sum()
                )
            scored_order.append((-match_score, order_index, identity_column))
        scored_order.sort()
        fill_identity_order = [entry[2] for entry in scored_order]

    missing_join_mask = normalized_join.isna()
    if missing_join_mask.any():
        for identity_column in fill_identity_order:
            identity_series = result[identity_column].map(canonical_join_value)
            fill_mask = missing_join_mask & identity_series.notna()
            if fill_mask.any():
                normalized_join.loc[fill_mask] = identity_series.loc[fill_mask]
                missing_join_mask = normalized_join.isna()
            if not missing_join_mask.any():
                break

    if not normalized_join.notna().any():
        return result

    result[JOIN_KEY_COLUMN] = normalized_join
    return result


def backfill_tabular_identity_from_watershed(
    *,
    frame: pd.DataFrame,
    wd: Path,
    carrier_layer: str | None,
    cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
) -> pd.DataFrame:
    if _TOPAZ_ID_COLUMN not in frame.columns or _WEPP_ID_COLUMN not in frame.columns:
        return frame

    missing_topaz = frame[_TOPAZ_ID_COLUMN].isna()
    missing_wepp = frame[_WEPP_ID_COLUMN].isna()
    if not missing_topaz.any() and not missing_wepp.any():
        return frame

    lookup = _load_watershed_identity_lookup(
        wd=wd,
        carrier_layer=carrier_layer,
        cache=cache,
    )
    if lookup is None:
        return frame
    topaz_by_wepp, wepp_by_topaz = lookup
    if not topaz_by_wepp and not wepp_by_topaz:
        return frame

    result = frame.copy()
    result[_TOPAZ_ID_COLUMN] = _fill_missing_identity_values(
        target_series=result[_TOPAZ_ID_COLUMN],
        source_series=result[_WEPP_ID_COLUMN],
        lookup=topaz_by_wepp,
    )
    result[_WEPP_ID_COLUMN] = _fill_missing_identity_values(
        target_series=result[_WEPP_ID_COLUMN],
        source_series=result[_TOPAZ_ID_COLUMN],
        lookup=wepp_by_topaz,
    )
    result[_TOPAZ_ID_COLUMN] = _fill_missing_identity_values(
        target_series=result[_TOPAZ_ID_COLUMN],
        source_series=result[_WEPP_ID_COLUMN],
        lookup=topaz_by_wepp,
    )
    return result


def _load_watershed_identity_lookup(
    *,
    wd: Path,
    carrier_layer: str | None,
    cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
) -> tuple[dict[str, object], dict[str, object]] | None:
    carrier_token = str(carrier_layer or "").strip().lower()
    cache_key = (str(wd.resolve()), carrier_token)
    cached = cache.get(cache_key)
    if cache_key in cache:
        return cached

    topaz_by_wepp: dict[str, object] = {}
    wepp_by_topaz: dict[str, object] = {}
    ambiguous_wepp_keys: set[str] = set()
    ambiguous_topaz_keys: set[str] = set()

    for relpath in _watershed_identity_relpaths_for_carrier(carrier_token):
        parquet_path = pick_existing_parquet_path(wd, relpath)
        if parquet_path is None:
            continue

        for topaz_value, wepp_value in _read_watershed_identity_pairs(parquet_path):
            _merge_watershed_identity_pair(
                topaz_value=topaz_value,
                wepp_value=wepp_value,
                topaz_by_wepp=topaz_by_wepp,
                wepp_by_topaz=wepp_by_topaz,
                ambiguous_wepp_keys=ambiguous_wepp_keys,
                ambiguous_topaz_keys=ambiguous_topaz_keys,
            )

    for ambiguous_wepp in ambiguous_wepp_keys:
        topaz_by_wepp.pop(ambiguous_wepp, None)
    for ambiguous_topaz in ambiguous_topaz_keys:
        wepp_by_topaz.pop(ambiguous_topaz, None)

    lookup: tuple[dict[str, object], dict[str, object]] | None = None
    if topaz_by_wepp or wepp_by_topaz:
        lookup = (topaz_by_wepp, wepp_by_topaz)

    cache[cache_key] = lookup
    return lookup


def _watershed_identity_relpaths_for_carrier(carrier_token: str) -> tuple[str, ...]:
    if carrier_token == "chan_map-channels":
        return ("watershed/channels.parquet", WATERSHED_HILLSLOPES.relative_path())
    return (WATERSHED_HILLSLOPES.relative_path(), "watershed/channels.parquet")


def _read_watershed_identity_pairs(parquet_path: Path) -> tuple[tuple[object, object], ...]:
    frame = pd.read_parquet(parquet_path)
    column_lookup = normalized_column_lookup(frame.columns)
    topaz_column = column_lookup.get("topazid")
    wepp_column = column_lookup.get("weppid")
    if topaz_column is None or wepp_column is None:
        return ()

    pairs_frame = frame[[topaz_column, wepp_column]].dropna(how="any")
    if pairs_frame.empty:
        return ()
    return tuple(pairs_frame.itertuples(index=False, name=None))


def _merge_watershed_identity_pair(
    *,
    topaz_value: object,
    wepp_value: object,
    topaz_by_wepp: dict[str, object],
    wepp_by_topaz: dict[str, object],
    ambiguous_wepp_keys: set[str],
    ambiguous_topaz_keys: set[str],
) -> None:
    topaz_key = canonical_join_value(topaz_value)
    wepp_key = canonical_join_value(wepp_value)
    if topaz_key is None or wepp_key is None:
        return

    existing_topaz = topaz_by_wepp.get(wepp_key)
    if existing_topaz is None:
        topaz_by_wepp[wepp_key] = topaz_value
    elif canonical_join_value(existing_topaz) != topaz_key:
        ambiguous_wepp_keys.add(wepp_key)

    existing_wepp = wepp_by_topaz.get(topaz_key)
    if existing_wepp is None:
        wepp_by_topaz[topaz_key] = wepp_value
    elif canonical_join_value(existing_wepp) != wepp_key:
        ambiguous_topaz_keys.add(topaz_key)


def _fill_missing_identity_values(
    *,
    target_series: pd.Series,
    source_series: pd.Series,
    lookup: cabc.Mapping[str, object],
) -> pd.Series:
    if not lookup:
        return target_series

    missing_mask = target_series.isna()
    if not missing_mask.any():
        return target_series

    source_keys = source_series.map(canonical_join_value)
    mapped_values = source_keys.map(lookup)
    fill_mask = missing_mask & mapped_values.notna()
    if not fill_mask.any():
        return target_series

    filled = target_series.copy()
    filled.loc[fill_mask] = mapped_values.loc[fill_mask]
    return filled


def normalized_column_lookup(columns: cabc.Iterable[object]) -> dict[str, str]:
    """Index string labels in order, retaining the first label for each key."""
    lookup: dict[str, str] = {}
    for column in columns:
        name = column.strip() if isinstance(column, str) else ""
        if not name:
            continue
        normalized = normalize_join_token(name)
        if not normalized or normalized in lookup:
            continue
        lookup[normalized] = name
    return lookup


__all__ = [
    "align_carrier_identity_join_key",
    "align_core_to_geometry_identity",
    "backfill_identity_from_geometry_key",
    "backfill_tabular_identity_from_watershed",
    "normalized_column_lookup",
]
