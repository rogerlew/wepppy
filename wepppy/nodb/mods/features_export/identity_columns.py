"""Canonical identity-column normalization for features export outputs."""

from __future__ import annotations

import collections.abc as cabc

import pandas as pd

from .column_selection import normalize_join_token

CANONICAL_IDENTITY_COLUMNS: tuple[str, ...] = ("topaz_id", "wepp_id")

_IDENTITY_TOKEN_TO_CANONICAL: dict[str, str] = {
    "topazid": "topaz_id",
    "weppid": "wepp_id",
}


def normalize_identity_output_columns(
    *,
    frame: pd.DataFrame,
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    geometry_name: str | None,
    consolidated_join_key_column: str,
) -> tuple[pd.DataFrame, tuple[str, ...], dict[str, str]]:
    """Normalize identity aliases to canonical ids and enforce leading order."""

    normalized_frame = frame.copy()
    unit_map = {
        str(column_name): str(unit_value).strip()
        for column_name, unit_value in unit_mapping.items()
        if isinstance(column_name, str) and isinstance(unit_value, str) and unit_value.strip()
    }

    aliases_by_canonical: dict[str, list[str]] = {token: [] for token in CANONICAL_IDENTITY_COLUMNS}
    for column_name in normalized_frame.columns:
        if column_name in {geometry_name, consolidated_join_key_column}:
            continue
        canonical = _canonical_identity_for_column(column_name)
        if canonical is None:
            continue
        aliases_by_canonical.setdefault(canonical, []).append(column_name)

    columns_to_drop: set[str] = set()
    for canonical in CANONICAL_IDENTITY_COLUMNS:
        candidates = _ordered_identity_candidates(
            aliases_by_canonical.get(canonical, ()),
            canonical=canonical,
        )
        if canonical not in normalized_frame.columns:
            if candidates:
                normalized_frame[canonical] = _coalesced_series(normalized_frame, candidates)
            else:
                normalized_frame[canonical] = pd.Series(
                    [None] * len(normalized_frame.index),
                    index=normalized_frame.index,
                    dtype="object",
                )
        else:
            fill_candidates = [column for column in candidates if column != canonical]
            if fill_candidates:
                base = normalized_frame[canonical]
                for column in fill_candidates:
                    base = base.where(base.notna(), normalized_frame[column])
                normalized_frame[canonical] = base

        for candidate in candidates:
            if candidate != canonical:
                columns_to_drop.add(candidate)
                unit_map.pop(candidate, None)

        unit_map[canonical] = "non-unitized"

    if columns_to_drop:
        normalized_frame = normalized_frame.drop(columns=sorted(columns_to_drop), errors="ignore")

    normalized_selected: list[str] = []
    seen: set[str] = set()

    for canonical in CANONICAL_IDENTITY_COLUMNS:
        if canonical in normalized_frame.columns and canonical not in seen:
            normalized_selected.append(canonical)
            seen.add(canonical)

    for column_name in selected_columns:
        token = str(column_name).strip()
        if not token:
            continue
        if token in {geometry_name, consolidated_join_key_column}:
            continue
        mapped = _canonical_identity_for_column(token) or token
        if mapped not in normalized_frame.columns or mapped in seen:
            continue
        normalized_selected.append(mapped)
        seen.add(mapped)

    filtered_units: dict[str, str] = {}
    for column_name in normalized_selected:
        unit_value = str(unit_map.get(column_name) or "").strip()
        if unit_value:
            filtered_units[column_name] = unit_value

    return normalized_frame, tuple(normalized_selected), filtered_units


def _coalesced_series(frame: pd.DataFrame, candidates: cabc.Sequence[str]) -> pd.Series:
    series = frame[candidates[0]]
    for candidate in candidates[1:]:
        series = series.where(series.notna(), frame[candidate])
    return series


def _ordered_identity_candidates(candidates: cabc.Iterable[str], *, canonical: str) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate).strip()
        if not token or token in seen:
            continue
        unique.append(token)
        seen.add(token)

    def _sort_key(column_name: str) -> tuple[int, str]:
        if column_name == canonical:
            return (0, column_name)
        lowered = column_name.lower()
        if lowered == canonical:
            return (1, column_name)
        return (2, column_name)

    return sorted(unique, key=_sort_key)


def _canonical_identity_for_column(column_name: str) -> str | None:
    base_name = str(column_name).split("__", 1)[0].strip()
    normalized = normalize_join_token(base_name)
    return _IDENTITY_TOKEN_TO_CANONICAL.get(normalized)


__all__ = ["CANONICAL_IDENTITY_COLUMNS", "normalize_identity_output_columns"]

