"""Carrier-layer source materialization helpers."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .column_selection import resolve_selected_columns
from .contracts import ExportWarning, NormalizedTemporalEvent, ResolvedExportPlan, ResolvedLayerPlan
from .discovery import DiscoveredSourceFrame, discover_layer_sources
from .duckdb_materializer import materialize_layer_attributes
from .join_planner import MaterializationContractError
from .temporal_wide_materializer import materialize_temporal_layer_wide


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
    discovered_sources = _apply_temporal_selector_filtering(
        layer=layer,
        request_plan=request_plan,
        sources=discovered_sources,
    )

    join_contract = _as_mapping(catalog_layer_raw.get("join"))
    allow_non_unique_layer_keys = _join_allows_non_unique_keys(join_contract) or (
        layer.temporal_mode in {"annual_average", "event", "yearly"}
    )
    layer_frame, discovered_units = materialize_layer_attributes(
        layer_id=layer.layer_id,
        carrier_layer=layer.carrier_layer,
        join_contract=join_contract,
        sources=discovered_sources,
        allow_non_unique_keys=allow_non_unique_layer_keys,
    )
    layer_frame = _ensure_event_date_column(layer_frame, temporal_mode=layer.temporal_mode)

    selected_columns, unit_mapping = resolve_selected_columns(
        layer=layer,
        frame=layer_frame,
        catalog_layer_raw=catalog_layer_raw,
        request_plan=request_plan,
        discovered_units=discovered_units,
        consolidated_join_key_column=consolidated_join_key_column,
    )
    event_selector = (
        request_plan.request.temporal.event
        if request_plan.request.temporal is not None
        else None
    )
    temporal_wide = materialize_temporal_layer_wide(
        frame=layer_frame,
        layer_id=layer.layer_id,
        temporal_mode=layer.temporal_mode,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        join_key_column=consolidated_join_key_column,
        event_selector=event_selector,
    )
    layer_frame = temporal_wide.frame
    selected_columns = temporal_wide.selected_columns
    unit_mapping = temporal_wide.unit_mapping

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


def _join_allows_non_unique_keys(join_contract: cabc.Mapping[str, object]) -> bool:
    flag = join_contract.get("allow_non_unique_keys")
    return isinstance(flag, bool) and flag


def _ensure_event_date_column(frame: pd.DataFrame, *, temporal_mode: str | None) -> pd.DataFrame:
    if temporal_mode != "event":
        return frame
    if "date" in frame.columns:
        return frame

    lookup = _normalized_column_lookup(frame.columns)
    year_column = _first_matching_column(lookup, ("calendar_year", "year"))
    month_column = _first_matching_column(lookup, ("month", "mo"))
    day_column = _first_matching_column(lookup, ("day_of_month", "day", "da"))
    julian_column = _first_matching_column(lookup, ("julian", "day_of_year", "doy"))

    parsed_dates: pd.Series | None = None
    if year_column is not None and month_column is not None and day_column is not None:
        parsed_dates = pd.to_datetime(
            {
                "year": pd.to_numeric(frame[year_column], errors="coerce"),
                "month": pd.to_numeric(frame[month_column], errors="coerce"),
                "day": pd.to_numeric(frame[day_column], errors="coerce"),
            },
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")
    elif year_column is not None and julian_column is not None:
        year = pd.to_numeric(frame[year_column], errors="coerce").astype("Int64")
        julian = pd.to_numeric(frame[julian_column], errors="coerce").astype("Int64")
        ordinal = year.astype("string").str.zfill(4) + julian.astype("string").str.zfill(3)
        parsed_dates = pd.to_datetime(ordinal, format="%Y%j", errors="coerce").dt.strftime("%Y-%m-%d")

    if parsed_dates is None:
        return frame

    result = frame.copy()
    result["date"] = parsed_dates.where(parsed_dates.notna(), None)
    return result


def _normalized_column_lookup(columns: cabc.Iterable[object]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in columns:
        token = str(column).strip()
        if not token:
            continue
        normalized = _normalize_token(token)
        if not normalized or normalized in lookup:
            continue
        lookup[normalized] = token
    return lookup


def _first_matching_column(lookup: cabc.Mapping[str, str], candidates: cabc.Sequence[str]) -> str | None:
    for candidate in candidates:
        normalized = _normalize_token(candidate)
        if normalized in lookup:
            return lookup[normalized]
    return None


def _normalize_token(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _apply_temporal_selector_filtering(
    *,
    layer: ResolvedLayerPlan,
    request_plan: ResolvedExportPlan,
    sources: cabc.Sequence[DiscoveredSourceFrame],
) -> tuple[DiscoveredSourceFrame, ...]:
    temporal_request = request_plan.request.temporal
    if layer.temporal_mode != "event" or temporal_request is None or temporal_request.event is None:
        return tuple(sources)

    selector = temporal_request.event
    filtered_sources: list[DiscoveredSourceFrame] = []
    for source in sources:
        filtered = _filter_source_for_event_selector(
            source=source,
            layer_id=layer.layer_id,
            selector=selector,
        )
        if filtered is not None:
            filtered_sources.append(filtered)

    if filtered_sources:
        return tuple(filtered_sources)

    raise MaterializationContractError(
        "No source tables remained after event selector filtering.",
        details=f"layer={layer.layer_id!r}; selector={selector.selector!r}",
    )


def _filter_source_for_event_selector(
    *,
    source: DiscoveredSourceFrame,
    layer_id: str,
    selector: NormalizedTemporalEvent,
) -> DiscoveredSourceFrame | None:
    mask = _event_selector_mask(source.dataframe, selector=selector)
    if mask is None:
        if source.required:
            raise MaterializationContractError(
                "Required source does not expose columns compatible with event selector filtering.",
                details=(
                    f"layer={layer_id!r}; source_id={source.source_id!r}; "
                    f"selector={selector.selector!r}; reason=selector_columns_missing"
                ),
            )
        return None

    filtered_frame = source.dataframe.loc[mask].reset_index(drop=True)
    if not filtered_frame.empty:
        return DiscoveredSourceFrame(
            source_id=source.source_id,
            source_kind=source.source_kind,
            required=source.required,
            dataframe=filtered_frame,
            units_by_column=dict(source.units_by_column),
        )

    if source.required:
        # Required sources stay in the plan even when no rows match the selected event.
        # Downstream materialization then emits a valid empty event core that can still
        # attach canonical geometry rows with null metrics instead of failing the job.
        return DiscoveredSourceFrame(
            source_id=source.source_id,
            source_kind=source.source_kind,
            required=source.required,
            dataframe=filtered_frame,
            units_by_column=dict(source.units_by_column),
        )
    return None


def _event_selector_mask(
    frame: pd.DataFrame,
    *,
    selector: NormalizedTemporalEvent,
) -> pd.Series | None:
    if selector.selector == "date":
        return _date_selector_mask(frame, selected_dates=selector.dates)
    if selector.selector == "return_period":
        return _return_period_selector_mask(
            frame,
            selected_return_periods=selector.return_periods,
        )
    return None


def _date_selector_mask(
    frame: pd.DataFrame,
    *,
    selected_dates: cabc.Sequence[str],
) -> pd.Series | None:
    selected = {str(value).strip() for value in selected_dates if str(value).strip()}
    if not selected:
        return pd.Series([False] * len(frame.index), index=frame.index, dtype=bool)

    lookup = _normalized_column_lookup(frame.columns)
    date_column = _first_matching_column(lookup, ("date", "event_date", "eventdate"))
    if date_column is not None:
        parsed_dates = pd.to_datetime(frame[date_column], errors="coerce").dt.strftime("%Y-%m-%d")
        return parsed_dates.isin(selected).fillna(False)

    year_column = _first_matching_column(lookup, ("calendar_year", "year"))
    month_column = _first_matching_column(lookup, ("month", "mo"))
    day_column = _first_matching_column(lookup, ("day_of_month", "day", "da"))
    if year_column is not None and month_column is not None and day_column is not None:
        year = pd.to_numeric(frame[year_column], errors="coerce")
        month = pd.to_numeric(frame[month_column], errors="coerce")
        day = pd.to_numeric(frame[day_column], errors="coerce")
        parsed_dates = pd.to_datetime(
            {
                "year": year,
                "month": month,
                "day": day,
            },
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")
        return parsed_dates.isin(selected).fillna(False)

    julian_column = _first_matching_column(lookup, ("julian", "day_of_year", "doy"))
    if year_column is not None and julian_column is not None:
        year = pd.to_numeric(frame[year_column], errors="coerce").astype("Int64")
        julian = pd.to_numeric(frame[julian_column], errors="coerce").astype("Int64")
        ordinal = year.astype("string").str.zfill(4) + julian.astype("string").str.zfill(3)
        parsed_dates = pd.to_datetime(ordinal, format="%Y%j", errors="coerce").dt.strftime("%Y-%m-%d")
        return parsed_dates.isin(selected).fillna(False)

    return None


def _return_period_selector_mask(
    frame: pd.DataFrame,
    *,
    selected_return_periods: cabc.Sequence[float],
) -> pd.Series | None:
    lookup = _normalized_column_lookup(frame.columns)
    period_column = _first_matching_column(
        lookup,
        (
            "return_period",
            "return_period_years",
            "recurrence_interval",
            "recurrence_interval_years",
        ),
    )
    if period_column is None:
        return None

    selected = {float(value) for value in selected_return_periods}
    values = pd.to_numeric(frame[period_column], errors="coerce")
    return values.isin(selected).fillna(False)


__all__ = [
    "CarrierLayerCoreMaterialization",
    "materialize_carrier_layer_core",
]
