"""Unitized output-column naming helpers for features export."""

from __future__ import annotations

import collections.abc as cabc
import re

import pandas as pd

from .column_selection import infer_display_unit_for_column

_UNIT_TOKEN_SANITIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_NON_UNITIZED_UNIT_TOKENS = frozenset(
    {
        "non_unitized",
        "nonunitized",
        "unitless",
        "dimensionless",
        "none",
        "na",
        "n_a",
    }
)
_DISPLAY_UNIT_SUFFIX_MAP: dict[str, str] = {
    "mm": "mm",
    "cm": "cm",
    "m": "m",
    "m2": "m2",
    "m_2": "m2",
    "m3": "m3",
    "m_3": "m3",
    "kg_ha": "kg_ha",
    "kgha": "kg_ha",
    "kg_m2": "kg_m2",
    "kg_m_2": "kg_m2",
    "kgm2": "kg_m2",
    "kg": "kg",
    "ha": "ha",
    "c": "c",
    "deg_c": "c",
    "degc": "c",
    "cms": "cms",
    "m3_s": "cms",
    "m_3_s": "cms",
    "m3_per_s": "cms",
    "pct": "pct",
    "percent": "pct",
    "percentage": "pct",
}
_UNIT_SUFFIX_ALIASES: dict[str, frozenset[str]] = {
    "mm": frozenset({"mm"}),
    "cm": frozenset({"cm"}),
    "m": frozenset({"m"}),
    "m2": frozenset({"m2", "m_2"}),
    "m3": frozenset({"m3", "m_3"}),
    "kg_ha": frozenset({"kg_ha", "kgha"}),
    "kg_m2": frozenset({"kg_m2", "kg_m_2", "kgm2"}),
    "kg": frozenset({"kg"}),
    "ha": frozenset({"ha"}),
    "c": frozenset({"c", "deg_c", "degc"}),
    "cms": frozenset({"cms", "m3_s", "m_3_s", "m3_per_s"}),
    "pct": frozenset({"pct", "percent", "percentage"}),
}


def apply_unitized_column_suffixes(
    *,
    frame: pd.DataFrame,
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    geometry_name: str,
    consolidated_join_key_column: str,
) -> tuple[pd.DataFrame, tuple[str, ...], dict[str, str]]:
    """Append unit suffixes for unitized selected columns and align metadata keys."""

    rename_map: dict[str, str] = {}
    renamed_selected_columns: list[str] = []
    renamed_unit_mapping: dict[str, str] = {}
    used_names = {str(column_name) for column_name in frame.columns}

    for column_name in selected_columns:
        token = _as_string(column_name)
        if (
            not token
            or token == geometry_name
            or token == consolidated_join_key_column
            or token not in frame.columns
        ):
            continue

        unit_value = _as_string(unit_mapping.get(token))
        if not unit_value:
            unit_value = infer_display_unit_for_column(token)

        resolved_name = token
        unit_suffix = _unit_suffix_for_display_unit(unit_value)
        if unit_suffix and not _column_name_has_unit_suffix(token, unit_suffix):
            candidate_name = f"{token}_{unit_suffix}"
            used_names.discard(token)
            resolved_name = _dedupe_column_name(candidate_name, used_names)
            used_names.add(resolved_name)
            if resolved_name != token:
                rename_map[token] = resolved_name
        else:
            used_names.add(token)

        if resolved_name not in renamed_selected_columns:
            renamed_selected_columns.append(resolved_name)
        if unit_value:
            renamed_unit_mapping[resolved_name] = unit_value

    renamed_frame = frame.rename(columns=rename_map) if rename_map else frame
    return renamed_frame, tuple(renamed_selected_columns), renamed_unit_mapping


def _unit_suffix_for_display_unit(display_unit: str) -> str | None:
    normalized_unit = _normalize_unit_token(display_unit)
    if not normalized_unit or normalized_unit in _NON_UNITIZED_UNIT_TOKENS:
        return None
    return _DISPLAY_UNIT_SUFFIX_MAP.get(normalized_unit, normalized_unit)


def _column_name_has_unit_suffix(column_name: str, unit_suffix: str) -> bool:
    normalized_name = _normalize_unit_token(column_name)
    if not normalized_name:
        return False

    alias_tokens = _UNIT_SUFFIX_ALIASES.get(unit_suffix, frozenset({unit_suffix}))
    for alias in alias_tokens:
        if normalized_name == alias or normalized_name.endswith(f"_{alias}"):
            return True
    return False


def _normalize_unit_token(value: str) -> str:
    return _UNIT_TOKEN_SANITIZE_PATTERN.sub("_", str(value).strip().lower()).strip("_")


def _dedupe_column_name(candidate: str, used_names: set[object]) -> str:
    base = candidate
    suffix = 2
    while candidate in used_names:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _as_string(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = ["apply_unitized_column_suffixes"]

