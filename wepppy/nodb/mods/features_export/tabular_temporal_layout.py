"""Helpers for tabular temporal layout transforms (wide <-> long)."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
import re

import geopandas as gpd
import pandas as pd

from .column_selection import identity_column_token
from .contracts import NormalizedTemporalEvent

_YEARLY_WIDE_COLUMN_RE = re.compile(r"^(?P<measure>.+)_yr(?P<year>\d{4})$")
_EVENT_DATE_WIDE_COLUMN_RE = re.compile(
    r"^(?P<measure>.+)_(?P<date>\d{4}_\d{2}_\d{2})$"
)
_EVENT_RETURN_PERIOD_WIDE_COLUMN_RE = re.compile(
    r"^(?P<measure>.+)_(?P<return_period>rp[a-z0-9_]+)$"
)


@dataclass(frozen=True)
class TabularTemporalLongResult:
    """Result bundle for one long-layout reshape."""

    frame: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]


def reshape_temporal_wide_to_long(
    *,
    frame: pd.DataFrame,
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    temporal_mode: str | None,
    event_selector: NormalizedTemporalEvent | None,
) -> TabularTemporalLongResult:
    """Convert temporal wide columns to long rows for one layer payload."""

    mode = str(temporal_mode or "").strip().lower()
    if mode not in {"event", "yearly"}:
        return TabularTemporalLongResult(
            frame=frame,
            selected_columns=tuple(selected_columns),
            unit_mapping=dict(unit_mapping),
        )

    is_geodataframe = isinstance(frame, gpd.GeoDataFrame)
    geometry_name = frame.geometry.name if is_geodataframe else None
    projected_columns = [
        column_name
        for column_name in selected_columns
        if column_name in frame.columns and column_name != geometry_name
    ]
    if not projected_columns:
        return TabularTemporalLongResult(
            frame=frame,
            selected_columns=tuple(),
            unit_mapping={},
        )

    temporal_selector = _event_selector_kind(mode=mode, event_selector=event_selector)
    temporal_column = _long_temporal_column_name(mode=mode, selector=temporal_selector)
    column_matches = _collect_temporal_wide_columns(
        projected_columns=projected_columns,
        mode=mode,
        selector=temporal_selector,
    )
    if not column_matches:
        return TabularTemporalLongResult(
            frame=frame,
            selected_columns=tuple(projected_columns),
            unit_mapping={column_name: value for column_name, value in unit_mapping.items()},
        )

    identity_columns = [
        column_name
        for column_name in projected_columns
        if identity_column_token(column_name)
    ]
    wide_columns = {match.column_name for match in column_matches}
    static_columns = [
        column_name
        for column_name in projected_columns
        if column_name not in wide_columns and column_name not in identity_columns
    ]
    measure_columns = _ordered_unique([match.measure_name for match in column_matches])
    ordered_tokens = _ordered_unique([match.temporal_token for match in column_matches])

    source = frame.reset_index(drop=True)
    base_columns = [*identity_columns, *static_columns]
    if geometry_name is not None:
        base_columns.append(geometry_name)
    base_values = source[base_columns]

    column_by_pair = {
        (match.measure_name, match.temporal_token): match.column_name
        for match in column_matches
    }
    decoded_temporal_values = [
        _decode_temporal_value(
            temporal_token=token,
            mode=mode,
            selector=temporal_selector,
        )
        for token in ordered_tokens
    ]
    token_frames: list[pd.DataFrame] = []
    for token, decoded_temporal in zip(ordered_tokens, decoded_temporal_values):
        present_columns = {
            measure_name: column_by_pair[(measure_name, token)]
            for measure_name in measure_columns
            if (measure_name, token) in column_by_pair
        }
        if present_columns:
            temporal_values = source[list(present_columns.values())].rename(
                columns={
                    source_column: measure_name
                    for measure_name, source_column in present_columns.items()
                }
            )
            temporal_values = temporal_values.reindex(columns=measure_columns)
        else:
            temporal_values = pd.DataFrame(index=source.index, columns=measure_columns)

        token_frame = pd.concat([base_values, temporal_values], axis=1, copy=False)
        token_frame[temporal_column] = decoded_temporal
        token_frames.append(token_frame)

    if not token_frames:
        return TabularTemporalLongResult(
            frame=frame,
            selected_columns=tuple(projected_columns),
            unit_mapping={column_name: value for column_name, value in unit_mapping.items()},
        )

    concatenated = pd.concat(token_frames, ignore_index=True)
    if geometry_name is not None:
        long_frame: pd.DataFrame = gpd.GeoDataFrame(
            concatenated,
            geometry=geometry_name,
            crs=source.crs,
        )
    else:
        long_frame = concatenated

    if measure_columns:
        keep_mask = long_frame[measure_columns].notna().any(axis=1)
        long_frame = long_frame.loc[keep_mask].reset_index(drop=True)
        if geometry_name is not None:
            long_frame = gpd.GeoDataFrame(long_frame, geometry=geometry_name, crs=source.crs)

    selected_output = tuple(
        [*identity_columns, *static_columns, temporal_column, *measure_columns]
    )
    resolved_units: dict[str, str] = {}
    for column_name in [*identity_columns, *static_columns]:
        unit_value = str(unit_mapping.get(column_name) or "").strip()
        if unit_value:
            resolved_units[column_name] = unit_value

    for measure_name in measure_columns:
        sample_column = column_by_pair.get((measure_name, ordered_tokens[0]))
        if sample_column is None:
            sample_column = next(
                (
                    match.column_name
                    for match in column_matches
                    if match.measure_name == measure_name
                ),
                None,
            )
        if sample_column is None:
            continue
        unit_value = str(unit_mapping.get(sample_column) or "").strip()
        if unit_value:
            resolved_units[measure_name] = unit_value

    return TabularTemporalLongResult(
        frame=long_frame,
        selected_columns=selected_output,
        unit_mapping=resolved_units,
    )


@dataclass(frozen=True)
class _WideTemporalColumnMatch:
    column_name: str
    measure_name: str
    temporal_token: str


def _collect_temporal_wide_columns(
    *,
    projected_columns: cabc.Sequence[str],
    mode: str,
    selector: str,
) -> tuple[_WideTemporalColumnMatch, ...]:
    matches: list[_WideTemporalColumnMatch] = []
    for column_name in projected_columns:
        parsed = _parse_temporal_wide_column(
            column_name=column_name,
            mode=mode,
            selector=selector,
        )
        if parsed is None:
            continue
        measure_name, temporal_token = parsed
        matches.append(
            _WideTemporalColumnMatch(
                column_name=column_name,
                measure_name=measure_name,
                temporal_token=temporal_token,
            )
        )
    return tuple(matches)


def _parse_temporal_wide_column(
    *,
    column_name: str,
    mode: str,
    selector: str,
) -> tuple[str, str] | None:
    token = str(column_name or "").strip()
    if not token:
        return None

    if mode == "yearly":
        match = _YEARLY_WIDE_COLUMN_RE.match(token)
        if match is None:
            return None
        measure_name = str(match.group("measure")).strip()
        year_token = str(match.group("year")).strip()
        if not measure_name or not year_token:
            return None
        return measure_name, f"yr{year_token}"

    if selector == "return_period":
        match = _EVENT_RETURN_PERIOD_WIDE_COLUMN_RE.match(token)
        if match is None:
            return None
        measure_name = str(match.group("measure")).strip()
        return_period = str(match.group("return_period")).strip().lower()
        if not measure_name or not return_period:
            return None
        return measure_name, return_period

    match = _EVENT_DATE_WIDE_COLUMN_RE.match(token)
    if match is None:
        return None
    measure_name = str(match.group("measure")).strip()
    date_token = str(match.group("date")).strip()
    if not measure_name or not date_token:
        return None
    return measure_name, date_token

def _decode_temporal_value(*, temporal_token: str, mode: str, selector: str) -> object:
    token = str(temporal_token or "").strip()
    if not token:
        return None

    if mode == "yearly":
        if token.startswith("yr"):
            year_value = token[2:]
            if year_value.isdigit():
                return int(year_value)
        return token

    if selector == "return_period":
        if token.startswith("rp"):
            raw_value = token[2:].replace("_", ".")
            try:
                return float(raw_value)
            except ValueError:
                return raw_value
        return token

    if re.fullmatch(r"\d{4}_\d{2}_\d{2}", token):
        return token.replace("_", "-")
    return token


def _event_selector_kind(*, mode: str, event_selector: NormalizedTemporalEvent | None) -> str:
    if mode != "event":
        return "yearly"
    if event_selector is not None and event_selector.selector == "return_period":
        return "return_period"
    return "date"


def _long_temporal_column_name(*, mode: str, selector: str) -> str:
    if mode == "yearly":
        return "year"
    if selector == "return_period":
        return "return_period"
    return "date"


def _ordered_unique(values: cabc.Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


__all__ = [
    "TabularTemporalLongResult",
    "reshape_temporal_wide_to_long",
]
