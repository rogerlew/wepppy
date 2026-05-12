"""Column selection and unit metadata helpers for features export layers."""

from __future__ import annotations

import collections.abc as cabc

import geopandas as gpd
import pandas as pd

from .contracts import ResolvedExportPlan, ResolvedLayerPlan

_IDENTITY_COLUMN_TOKENS = frozenset({"topazid", "chnid", "channelid", "weppid", "id"})


def resolve_selected_columns(
    *,
    layer: ResolvedLayerPlan,
    frame: pd.DataFrame,
    catalog_layer_raw: cabc.Mapping[str, object],
    request_plan: ResolvedExportPlan,
    discovered_units: cabc.Mapping[str, str] | None = None,
    consolidated_join_key_column: str,
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Resolve selected output columns and display units for one layer frame."""

    geometry_name = frame.geometry.name if isinstance(frame, gpd.GeoDataFrame) else None
    available_columns = [
        column_name
        for column_name in frame.columns
        if column_name != geometry_name and column_name != consolidated_join_key_column
    ]
    available_set = set(available_columns)

    required_columns = required_identity_columns(catalog_layer_raw)
    required_temporal = required_temporal_columns(
        layer=layer,
        available_columns=available_columns,
        request_plan=request_plan,
    )
    required_temporal_set = set(required_temporal)
    required_selected = [
        column_name for column_name in available_columns if column_name in required_columns
    ]
    required_selected.extend(
        column_name
        for column_name in available_columns
        if column_name in required_temporal_set and column_name not in required_selected
    )

    columns_meta = column_metadata_by_id(catalog_layer_raw)
    selection = request_plan.request.column_selection_for(layer.layer_id)

    selected_optional: list[str]
    if selection is not None and selection.include is not None:
        include = set(selection.include)
        selected_optional = [column_name for column_name in available_columns if column_name in include]
    elif selection is not None and selection.exclude is not None:
        excluded = set(selection.exclude)
        selected_optional = [
            column_name for column_name in available_columns if column_name not in excluded
        ]
    else:
        defaults = [
            column_name
            for column_name in available_columns
            if columns_meta.get(column_name, {}).get("default_selected") is True
        ]
        selected_optional = defaults if defaults else list(available_columns)

    selected_columns: list[str] = []
    for column_name in [*required_selected, *selected_optional]:
        if column_name in available_set and column_name not in selected_columns:
            selected_columns.append(column_name)

    for column_name in (*required_columns, *required_temporal):
        if column_name in available_set and column_name not in selected_columns:
            selected_columns.append(column_name)

    if not selected_columns:
        selected_columns = list(available_columns)

    unit_mapping: dict[str, str] = {}
    discovered_unit_map = discovered_units or {}
    for column_name in selected_columns:
        meta = columns_meta.get(column_name, {})
        unit_value = meta.get("display_unit")
        if isinstance(unit_value, str) and unit_value.strip():
            unit_mapping[column_name] = unit_value.strip()
            continue

        discovered_value = discovered_unit_map.get(column_name)
        if isinstance(discovered_value, str) and discovered_value.strip():
            unit_mapping[column_name] = discovered_value.strip()
            continue

        unit_mapping[column_name] = infer_display_unit_for_column(column_name)

    return tuple(selected_columns), unit_mapping


def required_temporal_columns(
    *,
    layer: ResolvedLayerPlan,
    available_columns: cabc.Sequence[str],
    request_plan: ResolvedExportPlan,
) -> tuple[str, ...]:
    """Return temporal identity columns that must be retained for selected mode."""

    if layer.temporal_mode != "event":
        return ()

    lookup = _normalized_column_lookup(available_columns)
    required: list[str] = []

    # Date selectors need an explicit date identity in output rows so multi-date
    # exports remain interpretable without date-pivoted column names.
    selector = None
    temporal_request = request_plan.request.temporal
    if temporal_request is not None and temporal_request.event is not None:
        selector = temporal_request.event.selector

    date_column = _first_matching_column(lookup, ("date", "event_date", "eventdate"))
    if date_column:
        required.append(date_column)
    else:
        year_column = _first_matching_column(lookup, ("calendar_year", "year"))
        month_column = _first_matching_column(lookup, ("month", "mo"))
        day_column = _first_matching_column(lookup, ("day_of_month", "day", "da"))
        julian_column = _first_matching_column(lookup, ("julian", "day_of_year", "doy"))
        if year_column and month_column and day_column:
            required.extend([year_column, month_column, day_column])
        elif year_column and julian_column:
            required.extend([year_column, julian_column])

    if selector == "return_period":
        return_period_column = _first_matching_column(
            lookup,
            (
                "return_period",
                "return_period_years",
                "recurrence_interval",
                "recurrence_interval_years",
            ),
        )
        if return_period_column:
            required.append(return_period_column)

    event_id_column = _first_matching_column(lookup, ("event_id",))
    if event_id_column:
        required.append(event_id_column)

    deduped: list[str] = []
    for column_name in required:
        if column_name in lookup.values() and column_name not in deduped:
            deduped.append(column_name)
    return tuple(deduped)


def required_identity_columns(catalog_layer_raw: cabc.Mapping[str, object]) -> set[str]:
    """Return required identity columns from join + geometry contracts."""

    required: set[str] = set()

    def _add_required(candidate: object) -> None:
        token = _as_string(candidate)
        if not token:
            return
        required.add(token)

    join_contract = _as_mapping(catalog_layer_raw.get("join"))
    primary_key = _as_string(join_contract.get("primary_key"))
    if primary_key:
        _add_required(primary_key)

    geometry_contract = _as_mapping(catalog_layer_raw.get("geometry"))
    for feature_key in _as_string_sequence(geometry_contract.get("feature_id_keys")):
        _add_required(feature_key)

    return required


def column_metadata_by_id(catalog_layer_raw: cabc.Mapping[str, object]) -> dict[str, dict[str, object]]:
    """Resolve column metadata keyed by column_id."""

    columns_raw = catalog_layer_raw.get("columns")
    if not isinstance(columns_raw, list):
        return {}

    metadata_by_id: dict[str, dict[str, object]] = {}
    for entry in columns_raw:
        if not isinstance(entry, cabc.Mapping):
            continue

        column_id = _as_string(entry.get("column_id"))
        if not column_id:
            continue

        unit_meta = _as_mapping(entry.get("unit"))
        metadata_by_id[column_id] = {
            "display_unit": (
                _as_string(unit_meta.get("display_unit"))
                or infer_display_unit_for_column(column_id)
            ),
            "default_selected": bool(entry.get("default_selected", False)),
            "description": _as_string(entry.get("description")),
        }

    return metadata_by_id


def infer_display_unit_for_column(column_name: str) -> str:
    """Infer one display unit token from a column name suffix."""

    token = _as_string(column_name).lower()
    if not token:
        return "non-unitized"

    suffix_units = (
        ("_mm", "mm"),
        ("_cm", "cm"),
        ("_m", "m"),
        ("_m2", "m2"),
        ("_m3", "m3"),
        ("_kg_ha", "kg/ha"),
        ("_kg_m2", "kg/m2"),
        ("_kg", "kg"),
        ("_ha", "ha"),
        ("_c", "C"),
        ("_cms", "cms"),
        ("_pct", "%"),
    )
    for suffix, unit in suffix_units:
        if token.endswith(suffix):
            return unit

    if token.startswith("pct_") or token.endswith("_percent") or token.endswith("_percentage"):
        return "%"

    return "non-unitized"


def dedupe_identity_selected_columns(columns: cabc.Sequence[str]) -> list[str]:
    """Drop duplicate identity columns while preserving first-seen ordering."""

    deduped: list[str] = []
    seen_columns: set[str] = set()
    seen_identity_tokens: set[str] = set()

    for column_name in columns:
        token = _as_string(column_name)
        if not token or token in seen_columns:
            continue

        identity_token = identity_column_token(token)
        if identity_token and identity_token in seen_identity_tokens:
            continue

        deduped.append(token)
        seen_columns.add(token)
        if identity_token:
            seen_identity_tokens.add(identity_token)

    return deduped


def identity_column_token(column_name: str) -> str | None:
    """Return normalized identity token for a selected column if recognized."""

    base_name = _as_string(column_name).split("__", 1)[0]
    normalized = normalize_join_token(base_name)
    if normalized in _IDENTITY_COLUMN_TOKENS:
        return normalized
    return None


def normalize_join_token(value: str) -> str:
    """Normalize a join token to lowercase alphanumerics only."""

    return "".join(ch for ch in value.lower() if ch.isalnum())


def _normalized_column_lookup(columns: cabc.Iterable[object]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in columns:
        token = _as_string(column)
        if not token:
            continue
        normalized = normalize_join_token(token)
        if not normalized or normalized in lookup:
            continue
        lookup[normalized] = token
    return lookup


def _first_matching_column(lookup: cabc.Mapping[str, str], candidates: cabc.Sequence[str]) -> str | None:
    for candidate in candidates:
        normalized = normalize_join_token(candidate)
        if normalized in lookup:
            return lookup[normalized]
    return None


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, cabc.Mapping):
        return {str(key): val for key, val in value.items()}
    return {}


def _as_string(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _as_string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        token = value.strip()
        return (token,) if token else ()
    if not isinstance(value, cabc.Sequence):
        return ()

    normalized: list[str] = []
    for item in value:
        token = _as_string(item)
        if token:
            normalized.append(token)
    return tuple(normalized)


__all__ = [
    "column_metadata_by_id",
    "dedupe_identity_selected_columns",
    "identity_column_token",
    "infer_display_unit_for_column",
    "normalize_join_token",
    "required_identity_columns",
    "resolve_selected_columns",
]
