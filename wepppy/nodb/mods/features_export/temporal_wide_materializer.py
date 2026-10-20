"""Temporal wide-column reshaping helpers for key-first features export."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
import re

import numpy as np
import pandas as pd

from .column_selection import identity_column_token, normalize_join_token
from .contracts import NormalizedTemporalEvent
from .join_planner import MaterializationContractError, canonical_join_value

_TOKEN_SANITIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_EVENT_CONTROL_TOKENS = frozenset(
    {
        "date",
        "eventdate",
        "calendaryear",
        "year",
        "fireyear",
        "month",
        "mo",
        "day",
        "dayofmonth",
        "da",
        "julian",
        "dayofyear",
        "doy",
        "returnperiod",
        "returnperiodyears",
        "recurrenceinterval",
        "recurrenceintervalyears",
        "eventid",
    }
)
_YEARLY_CONTROL_TOKENS = frozenset(
    {
        "calendaryear",
        "year",
        "fireyear",
        "event",
        "date",
        "month",
        "mo",
        "day",
        "dayofmonth",
        "da",
        "julian",
        "dayofyear",
        "doy",
        "eventid",
        "returnperiod",
        "returnperiodyears",
    }
)


@dataclass(frozen=True)
class TemporalWideMaterialization:
    """One temporal-reshaped frame plus updated selected-column/unit metadata."""

    frame: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]


def materialize_temporal_layer_wide(
    *,
    frame: pd.DataFrame,
    layer_id: str,
    temporal_mode: str | None,
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    join_key_column: str,
    event_selector: NormalizedTemporalEvent | None,
) -> TemporalWideMaterialization:
    """Reshape event/yearly rows to one-row-per-join-key wide attributes."""

    mode = str(temporal_mode or "").strip().lower()
    if mode not in {"annual_average", "event", "yearly"}:
        return TemporalWideMaterialization(
            frame=frame,
            selected_columns=tuple(selected_columns),
            unit_mapping=dict(unit_mapping),
        )

    if join_key_column not in frame.columns:
        raise MaterializationContractError(
            "Temporal wide materialization requires canonical join key.",
            details=f"layer={layer_id!r}; key={join_key_column!r}",
        )

    working = frame.copy()
    working = working.loc[working[join_key_column].notna()].reset_index(drop=True)
    if working.empty:
        return TemporalWideMaterialization(
            frame=working,
            selected_columns=tuple(
                column_name for column_name in selected_columns if column_name in working.columns
            ),
            unit_mapping={
                column_name: unit
                for column_name, unit in unit_mapping.items()
                if column_name in working.columns
            },
        )

    # Local WAT dates are independent of the primary joined source's dates.
    # Resolve them before generic filtering can discard valid observations.
    local_flux = _daily_water_fluxes(
        working, join_key_column, layer_id, mode, event_selector, selected_columns,
    )
    identity_source = working
    temporal_tokens, ordered_tokens, temporal_column = _resolve_temporal_tokens(
        frame=working,
        temporal_mode=mode,
        event_selector=event_selector,
        layer_id=layer_id,
    )
    if temporal_tokens is None:
        if mode == "annual_average":
            # Some datasets ship pre-aggregated annual-average rows without
            # an explicit year column. Preserve those rows and compute a
            # per-key average across observed rows.
            temporal_tokens = pd.Series(
                [_sanitize_token(f"row{index}") for index in range(len(working.index))],
                index=working.index,
                dtype="string",
            )
            ordered_tokens = _ordered_observed_tokens(temporal_tokens)
            temporal_column = None
        elif local_flux.empty:
            raise MaterializationContractError(
                "Temporal wide materialization could not resolve selector dimension column.",
                details=(
                    f"layer={layer_id!r}; temporal_mode={mode!r}; "
                    "expected date/return_period/year columns "
                    "(calendar_year, year, or fire_year)"
                ),
            )
        else:
            # Only the local stream has usable dates. Routed fields retain an
            # empty generic stream rather than borrowing dates from WAT.
            temporal_tokens = pd.Series(pd.NA, index=working.index, dtype="string")

    working["__features_export_temporal_token__"] = temporal_tokens
    working = working.loc[working["__features_export_temporal_token__"].notna()].reset_index(drop=True)
    if working.empty and local_flux.empty:
        return TemporalWideMaterialization(
            frame=working,
            selected_columns=(),
            unit_mapping={},
        )
    local_tokens = local_flux.attrs.get("ordered_tokens", ordered_tokens)
    working = _collapse_terminal_ofe_rows(
        frame=working,
        join_key_column=join_key_column,
    )

    selected_existing = [
        column_name
        for column_name in selected_columns
        if column_name in working.columns and column_name != join_key_column
    ]
    identity_columns = _identity_columns(
        selected_columns=selected_existing,
        temporal_column=temporal_column,
    )
    measure_columns = _measure_columns(
        selected_columns=selected_existing,
        temporal_mode=mode,
        temporal_column=temporal_column,
        identity_columns=identity_columns,
    )

    identity_rows = working
    if not local_flux.empty:
        admitted_keys = pd.concat([working[join_key_column], local_flux[join_key_column]])
        identity_rows = identity_source.loc[identity_source[join_key_column].isin(admitted_keys)]
    base = _collapse_identity_columns(
        frame=identity_rows,
        join_key_column=join_key_column,
        identity_columns=identity_columns,
        layer_id=layer_id,
    )

    if mode == "annual_average":
        averaged_columns: list[str] = []
        averaged_unit_mapping: dict[str, str] = {}
        for measure_column in measure_columns:
            averaged = _collapse_measure_annual_average(
                frame=local_flux if measure_column in local_flux.columns else working,
                join_key_column=join_key_column,
                measure_column=measure_column,
                layer_id=layer_id,
            )
            if averaged.empty and measure_column in local_flux.columns:
                averaged = pd.DataFrame({join_key_column: base[join_key_column],
                                         measure_column: np.nan})
            if averaged.empty:
                continue

            base = base.merge(averaged, on=join_key_column, how="left")
            averaged_columns.append(measure_column)
            unit_value = str(unit_mapping.get(measure_column) or "").strip()
            if unit_value:
                averaged_unit_mapping[measure_column] = unit_value

        selected_output = tuple([*identity_columns, *_dedupe_preserve_order(averaged_columns)])
        identity_unit_mapping = {
            column_name: str(unit_mapping.get(column_name) or "").strip()
            for column_name in identity_columns
            if str(unit_mapping.get(column_name) or "").strip()
        }
        merged_unit_mapping = {**identity_unit_mapping, **averaged_unit_mapping}
        return TemporalWideMaterialization(
            frame=base,
            selected_columns=selected_output,
            unit_mapping=merged_unit_mapping,
        )

    wide_columns: list[str] = []
    wide_unit_mapping: dict[str, str] = {}
    for measure_column in measure_columns:
        pivoted = _pivot_measure_wide(
            frame=local_flux if measure_column in local_flux.columns else working,
            join_key_column=join_key_column,
            measure_column=measure_column,
            ordered_tokens=local_tokens if measure_column in local_flux.columns else ordered_tokens,
            layer_id=layer_id,
            temporal_mode=mode,
        )
        if pivoted.empty and measure_column in local_flux.columns:
            pivoted = pd.DataFrame({join_key_column: base[join_key_column],
                                    **{token: np.nan for token in local_tokens}})
        if pivoted.empty:
            continue

        rename_map: dict[str, str] = {}
        measure_tokens = local_tokens if measure_column in local_flux.columns else ordered_tokens
        for token in measure_tokens:
            if token not in pivoted.columns:
                continue
            wide_column_name = f"{measure_column}_{token}"
            rename_map[token] = wide_column_name
            wide_columns.append(wide_column_name)
            unit_value = str(unit_mapping.get(measure_column) or "").strip()
            if unit_value:
                wide_unit_mapping[wide_column_name] = unit_value
        pivoted = pivoted.rename(columns=rename_map)
        base = base.merge(pivoted, on=join_key_column, how="left")

    ordered_wide_columns = _dedupe_preserve_order(wide_columns)
    selected_output = tuple([*identity_columns, *ordered_wide_columns])

    identity_unit_mapping = {
        column_name: str(unit_mapping.get(column_name) or "").strip()
        for column_name in identity_columns
        if str(unit_mapping.get(column_name) or "").strip()
    }
    merged_unit_mapping = {**identity_unit_mapping, **wide_unit_mapping}

    return TemporalWideMaterialization(
        frame=base,
        selected_columns=selected_output,
        unit_mapping=merged_unit_mapping,
    )


def _resolve_temporal_tokens(
    *,
    frame: pd.DataFrame,
    temporal_mode: str,
    event_selector: NormalizedTemporalEvent | None,
    layer_id: str,
) -> tuple[pd.Series | None, list[str], str | None]:
    if temporal_mode in {"annual_average", "yearly"}:
        year_column = _first_matching_column(frame.columns, ("calendar_year", "year", "fire_year"))
        if year_column is None:
            return None, [], None

        year_values = pd.to_numeric(frame[year_column], errors="coerce")
        tokens = year_values.map(_year_token_from_value)
        ordered_tokens = _ordered_observed_tokens(tokens)
        return tokens, ordered_tokens, year_column

    selector = event_selector.selector if event_selector is not None else "date"
    candidate_orders: tuple[tuple[str, ...], ...]
    if selector == "return_period":
        candidate_orders = (
            (
                "return_period",
                "return_period_years",
                "recurrence_interval",
                "recurrence_interval_years",
            ),
            ("date", "event_date", "eventdate"),
        )
    else:
        candidate_orders = (
            ("date", "event_date", "eventdate"),
            (
                "return_period",
                "return_period_years",
                "recurrence_interval",
                "recurrence_interval_years",
            ),
        )

    for candidates in candidate_orders:
        temporal_column = _first_matching_column(frame.columns, candidates)
        if temporal_column is None:
            continue

        if _is_return_period_column(temporal_column):
            values = pd.to_numeric(frame[temporal_column], errors="coerce")
            tokens = values.map(_return_period_token_from_value)
            ordered_tokens = _event_ordered_tokens(
                observed_tokens=tokens,
                event_selector=event_selector,
                selector="return_period",
            )
        else:
            parsed = pd.to_datetime(frame[temporal_column], errors="coerce")
            tokens = parsed.dt.strftime("%Y_%m_%d")
            ordered_tokens = _event_ordered_tokens(
                observed_tokens=tokens,
                event_selector=event_selector,
                selector="date",
            )

        if ordered_tokens:
            return tokens, ordered_tokens, temporal_column

    if selector == "date":
        year_column = _first_matching_column(frame.columns, ("calendar_year", "year", "fire_year"))
        month_column = _first_matching_column(frame.columns, ("month", "mo"))
        day_column = _first_matching_column(frame.columns, ("day_of_month", "day", "da"))
        julian_column = _first_matching_column(frame.columns, ("julian", "day_of_year", "doy"))
        parsed: pd.Series | None = None
        if year_column and month_column and day_column:
            parsed = pd.to_datetime(
                {
                    "year": pd.to_numeric(frame[year_column], errors="coerce"),
                    "month": pd.to_numeric(frame[month_column], errors="coerce"),
                    "day": pd.to_numeric(frame[day_column], errors="coerce"),
                },
                errors="coerce",
            )
        elif year_column and julian_column:
            year = pd.to_numeric(frame[year_column], errors="coerce").astype("Int64")
            julian = pd.to_numeric(frame[julian_column], errors="coerce").astype("Int64")
            ordinal = year.astype("string").str.zfill(4) + julian.astype("string").str.zfill(3)
            parsed = pd.to_datetime(ordinal, format="%Y%j", errors="coerce")

        if parsed is not None:
            tokens = parsed.dt.strftime("%Y_%m_%d")
            ordered_tokens = _event_ordered_tokens(
                observed_tokens=tokens,
                event_selector=event_selector,
                selector="date",
            )
            if ordered_tokens:
                return tokens, ordered_tokens, "date"

    return None, [], None


def _event_ordered_tokens(
    *,
    observed_tokens: pd.Series,
    event_selector: NormalizedTemporalEvent | None,
    selector: str,
) -> list[str]:
    selected_tokens: list[str] = []
    if event_selector is not None and event_selector.selector == selector:
        if selector == "date":
            for date_value in event_selector.dates:
                parsed = pd.to_datetime(date_value, errors="coerce")
                if pd.isna(parsed):
                    continue
                token = parsed.strftime("%Y_%m_%d")
                if token:
                    selected_tokens.append(token)
        elif selector == "return_period":
            for period_value in event_selector.return_periods:
                token = _return_period_token_from_value(period_value)
                if token:
                    selected_tokens.append(token)

    observed = _ordered_observed_tokens(observed_tokens)
    return _dedupe_preserve_order([*selected_tokens, *observed])


def _ordered_observed_tokens(tokens: pd.Series) -> list[str]:
    ordered: list[str] = []
    for token in tokens.tolist():
        token_text = str(token or "").strip()
        if not token_text or token_text.lower() == "nan":
            continue
        if token_text not in ordered:
            ordered.append(token_text)
    return ordered


def _identity_columns(
    *,
    selected_columns: cabc.Sequence[str],
    temporal_column: str | None,
) -> tuple[str, ...]:
    identity: list[str] = []
    temporal_token = normalize_join_token(str(temporal_column or ""))
    for column_name in selected_columns:
        if normalize_join_token(column_name) == temporal_token:
            continue
        if identity_column_token(column_name):
            identity.append(column_name)
    return tuple(_dedupe_preserve_order(identity))


def _measure_columns(
    *,
    selected_columns: cabc.Sequence[str],
    temporal_mode: str,
    temporal_column: str | None,
    identity_columns: cabc.Sequence[str],
) -> tuple[str, ...]:
    controls = _EVENT_CONTROL_TOKENS if temporal_mode == "event" else _YEARLY_CONTROL_TOKENS
    identity_set = set(identity_columns)
    temporal_token = normalize_join_token(str(temporal_column or ""))
    measures: list[str] = []
    for column_name in selected_columns:
        if column_name in identity_set:
            continue
        normalized = normalize_join_token(column_name)
        if normalized == temporal_token or normalized in controls:
            continue
        measures.append(column_name)
    return tuple(_dedupe_preserve_order(measures))


def _collapse_identity_columns(
    *,
    frame: pd.DataFrame,
    join_key_column: str,
    identity_columns: cabc.Sequence[str],
    layer_id: str,
) -> pd.DataFrame:
    base = frame[[join_key_column]].drop_duplicates(subset=[join_key_column]).reset_index(drop=True)
    if not identity_columns:
        return base

    for identity_column in identity_columns:
        collapsed_rows: list[tuple[object, object]] = []
        for join_value, group in frame.groupby(join_key_column, dropna=False, sort=False):
            series = group[identity_column]
            non_null = series.loc[series.notna()]
            unique_tokens = {
                canonical_join_value(value) if canonical_join_value(value) is not None else str(value)
                for value in non_null.tolist()
            }
            unique_tokens.discard("None")
            if len(unique_tokens) > 1:
                raise MaterializationContractError(
                    "Temporal wide materialization found conflicting identity values per key.",
                    details=(
                        f"layer={layer_id!r}; column={identity_column!r}; "
                        f"join_key={join_value!r}"
                    ),
                )

            value = non_null.iloc[0] if not non_null.empty else None
            collapsed_rows.append((join_value, value))

        collapsed = pd.DataFrame(collapsed_rows, columns=[join_key_column, identity_column])
        base = base.merge(collapsed, on=join_key_column, how="left")

    return base


def _pivot_measure_wide(
    *,
    frame: pd.DataFrame,
    join_key_column: str,
    measure_column: str,
    ordered_tokens: cabc.Sequence[str],
    layer_id: str,
    temporal_mode: str,
) -> pd.DataFrame:
    subset = frame[[join_key_column, "__features_export_temporal_token__", measure_column]].copy()
    if subset.empty:
        return pd.DataFrame(columns=[join_key_column])

    collapsed = _collapse_measure_slices(
        subset=subset,
        join_key_column=join_key_column,
        measure_column=measure_column,
        layer_id=layer_id,
        temporal_mode=temporal_mode,
    )

    pivoted = collapsed.pivot(
        index=join_key_column,
        columns="__features_export_temporal_token__",
        values=measure_column,
    )
    pivoted = pivoted.reindex(columns=list(ordered_tokens))
    pivoted = pivoted.reset_index()
    pivoted.columns = [str(column_name) for column_name in pivoted.columns]
    return pivoted


def _collapse_terminal_ofe_rows(
    *,
    frame: pd.DataFrame,
    join_key_column: str,
) -> pd.DataFrame:
    ofe_column = _first_matching_column(frame.columns, ("ofe_id", "ofe"))
    if ofe_column is None:
        return frame

    working = frame.copy()
    working["__features_export_ofe_numeric__"] = pd.to_numeric(
        working[ofe_column],
        errors="coerce",
    )
    group_cols = [join_key_column, "__features_export_temporal_token__"]
    max_ofe = working.groupby(group_cols, dropna=False)["__features_export_ofe_numeric__"].transform("max")
    group_has_numeric = working.groupby(group_cols, dropna=False)["__features_export_ofe_numeric__"].transform(
        lambda series: series.notna().any()
    )
    keep_mask = (
        (~group_has_numeric & working["__features_export_ofe_numeric__"].isna())
        | (
            group_has_numeric
            & working["__features_export_ofe_numeric__"].notna()
            & (working["__features_export_ofe_numeric__"] == max_ofe)
        )
    )
    reduced = working.loc[keep_mask].drop(columns=["__features_export_ofe_numeric__"])
    if reduced.empty:
        return frame
    return reduced.reset_index(drop=True)


def _collapse_measure_slices(
    *,
    subset: pd.DataFrame,
    join_key_column: str,
    measure_column: str,
    layer_id: str,
    temporal_mode: str,
) -> pd.DataFrame:
    group_cols = [join_key_column, "__features_export_temporal_token__"]
    if temporal_mode == "yearly":
        return _collapse_measure_yearly(
            subset=subset,
            group_cols=group_cols,
            measure_column=measure_column,
            layer_id=layer_id,
        )

    conflict_rows: list[tuple[object, str]] = []
    for (join_value, token), group in subset.groupby(group_cols, dropna=False, sort=False):
        values = group[measure_column].dropna().tolist()
        if not values:
            continue
        canonical = {
            canonical_join_value(value) if canonical_join_value(value) is not None else str(value)
            for value in values
        }
        if len(canonical) > 1:
            conflict_rows.append((join_value, str(token)))

    if conflict_rows:
        sample = ", ".join(
            f"{join_value}:{token}" for join_value, token in conflict_rows[:8]
        )
        raise MaterializationContractError(
            "Temporal wide materialization found conflicting values for one key/time slice.",
            details=(
                f"layer={layer_id!r}; column={measure_column!r}; "
                f"conflicts={sample}"
            ),
        )

    return (
        subset.groupby(group_cols, dropna=False, sort=False)[measure_column]
        .first()
        .reset_index()
    )


def _collapse_measure_yearly(
    *,
    subset: pd.DataFrame,
    group_cols: cabc.Sequence[str],
    measure_column: str,
    layer_id: str,
) -> pd.DataFrame:
    series = subset[measure_column]
    numeric_series = _coerce_numeric_series(series)

    if numeric_series is not None:
        numeric_subset = subset.copy()
        numeric_subset[measure_column] = numeric_series
        return (
            numeric_subset.groupby(list(group_cols), dropna=False, sort=False)[measure_column]
            .sum(min_count=1)
            .reset_index()
        )

    conflict_rows: list[tuple[object, str]] = []
    for (join_value, token), group in subset.groupby(list(group_cols), dropna=False, sort=False):
        values = group[measure_column].dropna().tolist()
        if not values:
            continue
        canonical = {
            canonical_join_value(value) if canonical_join_value(value) is not None else str(value)
            for value in values
        }
        if len(canonical) > 1:
            conflict_rows.append((join_value, str(token)))
    if conflict_rows:
        sample = ", ".join(
            f"{join_value}:{token}" for join_value, token in conflict_rows[:8]
        )
        raise MaterializationContractError(
            "Yearly wide materialization found conflicting non-numeric values for one key/year slice.",
            details=(
                f"layer={layer_id!r}; column={measure_column!r}; "
                f"conflicts={sample}"
            ),
        )
    return (
        subset.groupby(list(group_cols), dropna=False, sort=False)[measure_column]
        .first()
        .reset_index()
    )


def _collapse_measure_annual_average(
    *,
    frame: pd.DataFrame,
    join_key_column: str,
    measure_column: str,
    layer_id: str,
) -> pd.DataFrame:
    subset = frame[[join_key_column, "__features_export_temporal_token__", measure_column]].copy()
    if subset.empty:
        return pd.DataFrame(columns=[join_key_column, measure_column])

    yearly_collapsed = _collapse_measure_yearly(
        subset=subset,
        group_cols=[join_key_column, "__features_export_temporal_token__"],
        measure_column=measure_column,
        layer_id=layer_id,
    )
    if yearly_collapsed.empty:
        return pd.DataFrame(columns=[join_key_column, measure_column])

    series = yearly_collapsed[measure_column]
    numeric_series = _coerce_numeric_series(series)
    if numeric_series is not None:
        numeric_yearly = yearly_collapsed.copy()
        numeric_yearly[measure_column] = numeric_series
        return (
            numeric_yearly.groupby(join_key_column, dropna=False, sort=False)[measure_column]
            .mean()
            .reset_index()
        )

    conflict_rows: list[object] = []
    collapsed_rows: list[tuple[object, object]] = []
    for join_value, group in yearly_collapsed.groupby(join_key_column, dropna=False, sort=False):
        values = group[measure_column].dropna().tolist()
        if not values:
            collapsed_rows.append((join_value, None))
            continue
        canonical = {
            canonical_join_value(value) if canonical_join_value(value) is not None else str(value)
            for value in values
        }
        if len(canonical) > 1:
            conflict_rows.append(join_value)
            continue
        collapsed_rows.append((join_value, values[0]))

    if conflict_rows:
        sample = ", ".join(str(join_value) for join_value in conflict_rows[:8])
        raise MaterializationContractError(
            "Annual-average materialization found conflicting non-numeric values across years.",
            details=(
                f"layer={layer_id!r}; column={measure_column!r}; "
                f"conflicts={sample}"
            ),
        )

    return pd.DataFrame(collapsed_rows, columns=[join_key_column, measure_column])


def _coerce_numeric_series(series: pd.Series) -> pd.Series | None:
    if pd.api.types.is_numeric_dtype(series):
        return series

    non_null_mask = series.notna()
    if not non_null_mask.any():
        return None

    coerced = pd.to_numeric(series, errors="coerce")
    if coerced.loc[non_null_mask].notna().all():
        return coerced
    return None


def _first_matching_column(columns: cabc.Iterable[object], candidates: cabc.Sequence[str]) -> str | None:
    lookup = {normalize_join_token(str(column_name)): str(column_name) for column_name in columns}
    for candidate in candidates:
        token = normalize_join_token(candidate)
        if token in lookup:
            return lookup[token]
    return None


def _is_return_period_column(column_name: str) -> bool:
    normalized = normalize_join_token(column_name)
    return normalized in {
        "returnperiod",
        "returnperiodyears",
        "recurrenceinterval",
        "recurrenceintervalyears",
    }


def _return_period_token_from_value(value: object) -> str | None:
    canonical = canonical_join_value(value)
    if canonical is None:
        return None
    return _sanitize_token(f"rp{canonical}")


def _year_token_from_value(value: object) -> str | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return _sanitize_token(f"yr{int(numeric)}")


def _sanitize_token(value: str) -> str:
    token = _TOKEN_SANITIZE_PATTERN.sub("_", str(value).strip().lower()).strip("_")
    return token or ""


def _dedupe_preserve_order(values: cabc.Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


__all__ = [
    "TemporalWideMaterialization",
    "materialize_temporal_layer_wide",
]


def derive_water_et(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive the advertised local ET depth without changing interchange files."""
    if not {"Ep", "Es", "Er"}.issubset(frame.columns):
        raise MaterializationContractError("H.wat ET requires Ep, Es and Er.")
    result = frame.copy()
    components = result[["Ep", "Es", "Er"]].apply(pd.to_numeric, errors="raise").fillna(0.0)
    result["ET"] = components.sum(axis=1)
    return result


def prepare_water_geometry(frame: pd.DataFrame) -> pd.DataFrame:
    """Retain full native topology before any temporal selector or mapped join."""
    result = frame.copy()
    ofe = next((name for name in ("ofe_id", "OFE", "OFE (#)") if name in frame), None)
    if "wepp_id" not in frame or ofe is None or "Area" not in frame:
        return result  # Local-only legacy selections do not require outlet keys.
    if frame.empty:
        result.attrs["hwat_geometry"] = {}
        return result
    area = pd.to_numeric(frame["Area"], errors="coerce")
    if (~np.isfinite(area) | (area <= 0)).any():
        raise MaterializationContractError("H.wat Area must be finite and positive.")
    if frame[["wepp_id", ofe]].isna().any().any():
        raise MaterializationContractError("H.wat outlet geometry requires native IDs.")
    groups = frame.groupby(["wepp_id", ofe])["Area"]
    if (groups.nunique() != 1).any():
        raise MaterializationContractError("H.wat Area must be stationary.")
    areas = groups.first().reset_index()
    geometry = {}
    for native, rows in areas.groupby("wepp_id"):
        total = rows.Area.sum()
        if not np.isfinite(total):
            raise MaterializationContractError("H.wat area overflow.")
        geometry[native] = (rows[ofe].max(), total)
    result.attrs["hwat_geometry"] = geometry
    return result


def _daily_water_fluxes(
    frame: pd.DataFrame, key: str, layer_id: str, mode: str,
    event_selector: NormalizedTemporalEvent | None, selected_columns: cabc.Sequence[str],
) -> pd.DataFrame:
    """Reduce local depths and independently selected native outlet volumes."""
    names = frame.attrs.get("hwat_columns")
    if names is None:
        if layer_id != "wepp.interchange.hill_wat":
            return pd.DataFrame()
        names = {name: name for name in frame.columns}
    local = [names[name] for name in ("P", "RM", "Irr", "Ep", "Es", "Er", "ET", "Dp")
             if name in names and names[name] in selected_columns]
    outlets = [name for name in ("Q", "latqcc")
               if name in names and names[name] in selected_columns]
    if not local and not outlets:
        return pd.DataFrame()
    geometry = frame.attrs.get("hwat_geometry")
    identity = frame.attrs.get("hwat_source_key")
    if identity is not None:
        # Left-join absence is not a malformed WAT observation. Keep the
        # geometry in the base table and leave its local metrics null.
        frame = frame.loc[frame[identity].notna()].copy()
        if frame.empty:
            return pd.DataFrame(columns=[key, "__features_export_temporal_token__", *local,
                                         *(names[name] for name in outlets)])
    area_column = names.get("Area")
    if area_column is None or area_column not in frame:
        raise MaterializationContractError("H.wat local flux aggregation requires Area.")
    area = pd.to_numeric(frame[area_column], errors="coerce")
    if (~np.isfinite(area) | (area <= 0)).any():
        raise MaterializationContractError("H.wat Area must be finite and positive.")
    # Use the WAT source's own daily identity, not a colliding joined year/date.
    daily_frame = frame[list(names.values())].rename(
        columns={actual: name for name, actual in names.items()}
    )
    days, _, _ = _resolve_temporal_tokens(
        frame=daily_frame, temporal_mode="event", event_selector=None, layer_id=layer_id,
    )
    if days is None or days.isna().any():
        raise MaterializationContractError("H.wat local flux aggregation requires valid daily dates.")
    validation_columns = list(local)
    if names.get("ET") in local:
        validation_columns.extend(names[name] for name in ("Ep", "Es", "Er")
                                  if name in names and names[name] not in validation_columns)
    try:
        values = frame[validation_columns].apply(pd.to_numeric, errors="raise").fillna(0.0)
    except (TypeError, ValueError) as exc:
        raise MaterializationContractError("H.wat local flux must be numeric.") from exc
    if not np.isfinite(values.to_numpy()).all():
        raise MaterializationContractError("H.wat local flux must be finite.")
    token = "__features_export_temporal_token__"
    weighted = values[local].mul(area, axis=0)
    weighted[key] = frame[key]
    water_tokens, water_order, _ = _resolve_temporal_tokens(
        frame=daily_frame, temporal_mode=mode, event_selector=event_selector, layer_id=layer_id,
    )
    if water_tokens is None or water_tokens.isna().any():
        raise MaterializationContractError("H.wat local flux requires valid temporal identity.")
    weighted[token] = water_tokens
    weighted["__water_day__"] = days
    weighted["__water_area__"] = area
    grouped = weighted.groupby([key, token, "__water_day__"], dropna=False).sum()
    result = grouped[local].div(grouped["__water_area__"], axis=0)
    if not np.isfinite(grouped.to_numpy()).all() or not np.isfinite(result.to_numpy()).all():
        raise MaterializationContractError("H.wat local flux aggregate overflow.")
    if outlets:
        ofe = next((name for name in ("ofe_id", "OFE", "OFE (#)") if name in daily_frame), None)
        if "wepp_id" not in daily_frame or ofe is None:
            raise MaterializationContractError("H.wat outlets require native WEPP/OFE identity.")
        if geometry is None:
            geometry = prepare_water_geometry(daily_frame).attrs["hwat_geometry"]
        routing = pd.DataFrame({key: frame[key], token: water_tokens,
                                "__water_day__": days, "native": daily_frame.wepp_id,
                                "ofe": daily_frame[ofe], "area": area})
        try:
            routing["terminal"] = routing.native.map(lambda value: geometry[value][0])
            routing["hill_area"] = routing.native.map(lambda value: geometry[value][1])
        except KeyError as exc:
            raise MaterializationContractError("Missing full H.wat outlet geometry.") from exc
        native_keys = [key, token, "__water_day__", "native"]
        if routing.duplicated([*native_keys, "ofe"]).any():
            raise MaterializationContractError("Duplicate H.wat daily native OFE observation.")
        selected = routing.ofe == routing.terminal
        terminals = routing.loc[selected].copy()
        if len(terminals) != len(routing[native_keys].drop_duplicates()):
            raise MaterializationContractError("Missing known H.wat terminal observation.")
        for field in outlets:
            values = pd.to_numeric(daily_frame.loc[selected, field], errors="raise")
            if not np.isfinite(values).all():
                raise MaterializationContractError("Nonfinite H.wat terminal flux.")
            terminals[names[field]] = values * terminals["hill_area" if field == "Q" else "area"]
        totals = terminals.groupby([key, token, "__water_day__"], dropna=False)[
            [*(names[field] for field in outlets), "hill_area"]].sum()
        for field in outlets:
            result[names[field]] = totals[names[field]] / totals.hill_area
        if not np.isfinite(result.to_numpy()).all():
            raise MaterializationContractError("H.wat outlet aggregate overflow.")
    result = result.reset_index().drop(columns="__water_day__")
    result.attrs["ordered_tokens"] = water_order
    return result
