"""Temporal wide-column reshaping helpers for key-first features export."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
import re

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
    if mode not in {"event", "yearly"}:
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

    temporal_tokens, ordered_tokens, temporal_column = _resolve_temporal_tokens(
        frame=working,
        temporal_mode=mode,
        event_selector=event_selector,
        layer_id=layer_id,
    )
    if temporal_tokens is None:
        raise MaterializationContractError(
            "Temporal wide materialization could not resolve selector dimension column.",
            details=(
                f"layer={layer_id!r}; temporal_mode={mode!r}; "
                "expected date/return_period/year columns"
            ),
        )

    working["__features_export_temporal_token__"] = temporal_tokens
    working = working.loc[working["__features_export_temporal_token__"].notna()].reset_index(drop=True)
    if working.empty:
        return TemporalWideMaterialization(
            frame=working,
            selected_columns=(),
            unit_mapping={},
        )
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

    base = _collapse_identity_columns(
        frame=working,
        join_key_column=join_key_column,
        identity_columns=identity_columns,
        layer_id=layer_id,
    )

    wide_columns: list[str] = []
    wide_unit_mapping: dict[str, str] = {}
    for measure_column in measure_columns:
        pivoted = _pivot_measure_wide(
            frame=working,
            join_key_column=join_key_column,
            measure_column=measure_column,
            ordered_tokens=ordered_tokens,
            layer_id=layer_id,
            temporal_mode=mode,
        )
        if pivoted.empty:
            continue

        rename_map: dict[str, str] = {}
        for token in ordered_tokens:
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
    if temporal_mode == "yearly":
        year_column = _first_matching_column(frame.columns, ("calendar_year", "year"))
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
        year_column = _first_matching_column(frame.columns, ("calendar_year", "year"))
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
    if pd.api.types.is_numeric_dtype(series):
        return (
            subset.groupby(list(group_cols), dropna=False, sort=False)[measure_column]
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
