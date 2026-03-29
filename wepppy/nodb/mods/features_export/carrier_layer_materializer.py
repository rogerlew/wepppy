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
from .join_planner import MaterializationContractError, canonical_join_value
from .temporal_wide_materializer import materialize_temporal_layer_wide


@dataclass(frozen=True)
class CarrierLayerCoreMaterialization:
    """Projected carrier core table plus selected-column metadata."""

    frame: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]
    warnings: tuple[ExportWarning, ...]


@dataclass(frozen=True)
class _EventSelectorMaskResult:
    """Internal selector mask payload with optional derived return-period values."""

    mask: pd.Series | None
    derived_return_period: pd.Series | None = None


_CANONICAL_CTA_DAYS_PER_YEAR = 365.25
_CANONICAL_GRINGORTEN_RANK_OFFSET = 0.44


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
    return_period_lookup = (
        _build_event_return_period_lookup(sources)
        if selector.selector == "return_period"
        else None
    )
    filtered_sources: list[DiscoveredSourceFrame] = []
    for source in sources:
        if (
            selector.selector == "return_period"
            and _is_return_period_lookup_only_source(source)
        ):
            continue
        filtered = _filter_source_for_event_selector(
            source=source,
            layer_id=layer.layer_id,
            selector=selector,
            return_period_lookup=return_period_lookup,
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
    return_period_lookup: cabc.Mapping[str, frozenset[float]] | None = None,
) -> DiscoveredSourceFrame | None:
    mask_result = _event_selector_mask(
        source.dataframe,
        selector=selector,
        return_period_lookup=return_period_lookup,
    )
    if mask_result.mask is None:
        if source.required:
            raise MaterializationContractError(
                "Required source does not expose columns compatible with event selector filtering.",
                details=(
                    f"layer={layer_id!r}; source_id={source.source_id!r}; "
                    f"selector={selector.selector!r}; reason=selector_columns_missing"
                ),
            )
        return None

    filtered_frame = source.dataframe.loc[mask_result.mask].copy()
    if (
        mask_result.derived_return_period is not None
        and "return_period" not in filtered_frame.columns
    ):
        derived_values = mask_result.derived_return_period.loc[mask_result.mask]
        filtered_frame["return_period"] = derived_values.values
    filtered_frame = filtered_frame.reset_index(drop=True)
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
    return_period_lookup: cabc.Mapping[str, frozenset[float]] | None = None,
) -> _EventSelectorMaskResult:
    if selector.selector == "date":
        return _EventSelectorMaskResult(
            mask=_date_selector_mask(frame, selected_dates=selector.dates)
        )
    if selector.selector == "return_period":
        return _return_period_selector_mask(
            frame,
            selected_return_periods=selector.return_periods,
            return_period_lookup=return_period_lookup,
        )
    return _EventSelectorMaskResult(mask=None)


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
    return_period_lookup: cabc.Mapping[str, frozenset[float]] | None = None,
) -> _EventSelectorMaskResult:
    lookup = _normalized_column_lookup(frame.columns)
    # `rank` is an order statistic in WEPP outputs, not a return-period year token.
    # Restrict selector matching to explicit return-period interval columns.
    period_column = _first_matching_column(
        lookup,
        (
            "return_period",
            "return_period_years",
            "recurrence_interval",
            "recurrence_interval_years",
        ),
    )
    selected = [float(value) for value in selected_return_periods]
    if period_column is not None:
        values = pd.to_numeric(frame[period_column], errors="coerce")
        interval_matches = _resolve_return_period_interval_matches(
            selected_periods=selected,
            available_periods=values.tolist(),
        )
        if interval_matches:
            available_to_requested = _available_period_to_requested_map(interval_matches)
            available_tokens = values.map(canonical_join_value)
            requested_periods = available_tokens.map(
                lambda token: available_to_requested.get(token)
            )
            mask = requested_periods.notna().fillna(False)
        else:
            requested_periods = pd.Series([None] * len(frame.index), index=frame.index)
            mask = pd.Series([False] * len(frame.index), index=frame.index, dtype=bool)
        return _EventSelectorMaskResult(
            mask=mask,
            derived_return_period=requested_periods,
        )

    event_id_column = _first_matching_column(lookup, ("event_id", "eventid"))
    if event_id_column is None or not return_period_lookup:
        return _EventSelectorMaskResult(mask=None)

    preferred_matches = _resolve_return_period_interval_matches(
        selected_periods=selected,
        available_periods=_lookup_available_return_periods(return_period_lookup),
    )
    if not preferred_matches:
        return _EventSelectorMaskResult(
            mask=pd.Series([False] * len(frame.index), index=frame.index, dtype=bool),
        )
    event_tokens = frame[event_id_column].map(_canonical_event_id_token)
    derived_periods = event_tokens.map(
        lambda token: _preferred_selected_return_period(
            event_token=token,
            interval_matches=preferred_matches,
            return_period_lookup=return_period_lookup,
        )
    )
    return _EventSelectorMaskResult(
        mask=derived_periods.notna().fillna(False),
        derived_return_period=derived_periods,
    )


def _build_event_return_period_lookup(
    sources: cabc.Sequence[DiscoveredSourceFrame],
) -> dict[str, frozenset[float]]:
    by_event_id: dict[str, set[float]] = {}
    simulation_years = _estimate_simulation_years(sources)
    for source in sources:
        frame = source.dataframe
        lookup = _normalized_column_lookup(frame.columns)
        event_id_column = _first_matching_column(lookup, ("event_id", "eventid"))
        period_column = _first_matching_column(
            lookup,
            (
                "return_period",
                "return_period_years",
                "recurrence_interval",
                "recurrence_interval_years",
            ),
        )
        rank_column = _first_matching_column(lookup, ("rank", "event_rank", "event_rank_index"))
        if event_id_column is None or (period_column is None and rank_column is None):
            continue

        measure_id_column = _first_matching_column(lookup, ("measure_id", "measureid", "measure"))
        if measure_id_column is not None:
            measure_tokens = frame[measure_id_column].map(_normalized_measure_token)
            preferred_measure = _preferred_measure_token(measure_tokens.tolist())
            if preferred_measure is not None:
                frame = frame.loc[measure_tokens == preferred_measure].reset_index(drop=True)
                if frame.empty:
                    continue

        event_tokens = frame[event_id_column].map(_canonical_event_id_token)
        period_values = _resolve_source_return_period_values(
            frame=frame,
            lookup=lookup,
            period_column=period_column,
            rank_column=rank_column,
            simulation_years=simulation_years,
        )
        if period_values is None:
            continue
        for event_token, period_value in zip(event_tokens.tolist(), period_values.tolist()):
            if event_token is None or pd.isna(period_value):
                continue
            by_event_id.setdefault(event_token, set()).add(float(period_value))

    return {event_id: frozenset(values) for event_id, values in by_event_id.items() if values}


def _canonical_event_id_token(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float):
        if not value.is_integer():
            return str(value).strip() or None
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    token = str(value).strip()
    if not token:
        return None
    if token.isdigit():
        return str(int(token))
    try:
        float_value = float(token)
    except ValueError:
        return token
    if float_value.is_integer():
        return str(int(float_value))
    return token


def _preferred_selected_return_period(
    *,
    event_token: str | None,
    interval_matches: cabc.Sequence[tuple[float, float]],
    return_period_lookup: cabc.Mapping[str, frozenset[float]],
) -> float | None:
    if event_token is None:
        return None
    available = return_period_lookup.get(event_token)
    if not available:
        return None
    available_tokens = {
        canonical_join_value(value)
        for value in available
        if canonical_join_value(value) is not None
    }
    for requested_period, available_period in interval_matches:
        available_token = canonical_join_value(available_period)
        if available_token and available_token in available_tokens:
            return requested_period
    return None


def _resolve_source_return_period_values(
    *,
    frame: pd.DataFrame,
    lookup: cabc.Mapping[str, str],
    period_column: str | None,
    rank_column: str | None,
    simulation_years: float | None,
) -> pd.Series | None:
    if period_column is not None:
        return pd.to_numeric(frame[period_column], errors="coerce")

    if rank_column is None or simulation_years is None:
        return None

    rank_values = pd.to_numeric(frame[rank_column], errors="coerce")
    if rank_values.empty:
        return None

    daily_count = (simulation_years * _CANONICAL_CTA_DAYS_PER_YEAR) + 1.0
    period_values = (
        daily_count
        / (rank_values - _CANONICAL_GRINGORTEN_RANK_OFFSET)
    ) / _CANONICAL_CTA_DAYS_PER_YEAR
    valid_mask = rank_values.gt(_CANONICAL_GRINGORTEN_RANK_OFFSET)
    return period_values.where(valid_mask)


def _lookup_available_return_periods(
    return_period_lookup: cabc.Mapping[str, frozenset[float]],
) -> tuple[float, ...]:
    available: set[float] = set()
    for periods in return_period_lookup.values():
        available.update(float(value) for value in periods)
    return tuple(sorted(available))


def _resolve_return_period_interval_matches(
    *,
    selected_periods: cabc.Sequence[float],
    available_periods: cabc.Iterable[float],
) -> tuple[tuple[float, float], ...]:
    available = sorted(
        {
            float(value)
            for value in available_periods
            if not pd.isna(value) and float(value) > 0
        }
    )
    if not available:
        return ()

    used_available: set[str] = set()
    matches: list[tuple[float, float]] = []
    for requested in selected_periods:
        if pd.isna(requested):
            continue
        requested_value = float(requested)
        candidate = next(
            (
                value
                for value in available
                if value >= requested_value
                and canonical_join_value(value) not in used_available
            ),
            None,
        )
        if candidate is None:
            continue
        candidate_token = canonical_join_value(candidate)
        if candidate_token is None:
            continue
        used_available.add(candidate_token)
        matches.append((requested_value, candidate))
    return tuple(matches)


def _available_period_to_requested_map(
    interval_matches: cabc.Sequence[tuple[float, float]],
) -> dict[str, float]:
    mapping: dict[str, float] = {}
    for requested_period, available_period in interval_matches:
        available_token = canonical_join_value(available_period)
        if not available_token:
            continue
        mapping[available_token] = float(requested_period)
    return mapping


def _estimate_simulation_years(
    sources: cabc.Sequence[DiscoveredSourceFrame],
) -> float | None:
    best_year_count = 0
    for source in sources:
        frame = source.dataframe
        lookup = _normalized_column_lookup(frame.columns)
        year_column = _first_matching_column(lookup, ("calendar_year", "year"))
        if year_column is None:
            continue
        year_values = pd.to_numeric(frame[year_column], errors="coerce").dropna()
        if year_values.empty:
            continue
        year_count = len(set(int(value) for value in year_values.tolist()))
        if year_count > best_year_count:
            best_year_count = year_count

    if best_year_count <= 0:
        return None
    return float(best_year_count)


def _is_return_period_lookup_only_source(source: DiscoveredSourceFrame) -> bool:
    if source.required:
        return False
    lookup = _normalized_column_lookup(source.dataframe.columns)
    has_event_id = _first_matching_column(lookup, ("event_id", "eventid")) is not None
    has_rank = _first_matching_column(
        lookup,
        (
            "rank",
            "return_period",
            "return_period_years",
            "recurrence_interval",
            "recurrence_interval_years",
        ),
    ) is not None
    return has_event_id and has_rank


def _normalized_measure_token(value: object) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return ""
    return "".join(ch for ch in token if ch.isalnum() or ch == "_")


def _preferred_measure_token(measure_tokens: cabc.Sequence[str]) -> str | None:
    if not measure_tokens:
        return None
    available = {token for token in measure_tokens if token}
    if not available:
        return None
    preferred = (
        "runoff_depth",
        "runoff_volume",
        "runoff",
        "peak_discharge",
        "sediment_yield",
    )
    for token in preferred:
        if token in available:
            return token
    return None


__all__ = [
    "CarrierLayerCoreMaterialization",
    "materialize_carrier_layer_core",
]
