"""NOAA Atlas 14 downloader using the publicly documented PFDS scrape endpoint."""

from __future__ import annotations

import ast
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

_CGI_READ_H5_URL = "https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py"

_ALLOWED_STATISTICS = frozenset({"mean", "upper", "lower", "all"})
_ALLOWED_DATA_TYPES = frozenset({"intensity", "depth"})
_ALLOWED_SERIES = frozenset({"pds", "ams"})
_ALLOWED_UNITS = frozenset({"metric", "english"})

_DURATION_LABELS: tuple[str, ...] = (
    "5-min",
    "10-min",
    "15-min",
    "30-min",
    "60-min",
    "2-hr",
    "3-hr",
    "6-hr",
    "12-hr",
    "24-hr",
    "2-day",
    "3-day",
    "4-day",
    "7-day",
    "10-day",
    "20-day",
    "30-day",
    "45-day",
    "60-day",
)

_SERIES_TO_ARI: dict[str, tuple[str, ...]] = {
    "pds": ("1", "2", "5", "10", "25", "50", "100", "200", "500", "1000"),
    "ams": ("2", "5", "10", "25", "50", "100", "200", "500", "1000"),
}

_STATISTIC_TO_PAYLOAD_KEY: dict[str, str] = {
    "mean": "quantiles",
    "upper": "upper",
    "lower": "lower",
}


def base_url() -> str:
    """Return the NOAA PFDS endpoint used to query Atlas 14 point estimates."""

    return _CGI_READ_H5_URL


def query_url(statistic: str = "mean") -> str:
    """Return the NOAA PFDS endpoint URL for Atlas 14 queries."""

    _normalize_option("statistic", statistic, _ALLOWED_STATISTICS)
    return _CGI_READ_H5_URL


def download(
    lat: float,
    lon: float,
    *,
    parent: str | Path | None = None,
    name: str | None = None,
    overwrite: bool = False,
    statistic: str = "mean",
    data: str = "intensity",
    series: str = "pds",
    units: str = "metric",
    timeout: float | tuple[float, float] | None = 10,
) -> Path:
    """Download NOAA Atlas 14 data and emit NOAA-style report CSV text.

    This client uses NOAA's publicly documented PFDS scraping endpoint:
    ``https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py``.
    """

    statistic_norm = _normalize_option("statistic", statistic, _ALLOWED_STATISTICS)
    data_norm = _normalize_option("data", data, _ALLOWED_DATA_TYPES)
    series_norm = _normalize_option("series", series, _ALLOWED_SERIES)
    units_norm = _normalize_option("units", units, _ALLOWED_UNITS)

    output_parent = Path("." if parent is None else parent)
    output_parent.mkdir(parents=True, exist_ok=True)

    output_name = name or f"noaa-atlas14-{statistic_norm}-{series_norm}-{data_norm}-{units_norm}.csv"
    output_path = output_parent / output_name
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"NOAA Atlas 14 output already exists: {output_path}")

    started_at = time.time()
    response = requests.get(
        base_url(),
        params={
            "lat": float(lat),
            "lon": float(lon),
            "type": "pf",
            "data": data_norm,
            "units": units_norm,
            "series": series_norm,
        },
        timeout=timeout,
    )
    response.raise_for_status()

    payload = _parse_payload_assignments(response.text)
    result = str(payload.get("result", "")).strip().lower()

    if result == "none":
        error_msg = str(payload.get("ErrorMsg") or "Selected location is not within a project area")
        raise ValueError(f"NOAA Atlas 14 data not available for this location ({error_msg})")

    if result in {"", "null"}:
        raise RuntimeError("NOAA Atlas 14 endpoint returned null results for this location")

    lines = _render_report_lines(
        payload=payload,
        statistic=statistic_norm,
        data=data_norm,
        series=series_norm,
        units=units_norm,
        runtime_seconds=time.time() - started_at,
    )

    output_path.write_text("\n".join(lines) + "\n")
    return output_path.resolve()


def _normalize_option(name: str, value: str, allowed: frozenset[str]) -> str:
    normalized = str(value).strip().lower()
    if normalized not in allowed:
        raise ValueError(f"Invalid {name} '{value}'. Allowed values: {sorted(allowed)}")
    return normalized


def _parse_payload_assignments(response_text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in response_text.splitlines():
        stripped = line.strip()
        if not stripped or "=" not in stripped or not stripped.endswith(";"):
            continue

        key, raw_value = stripped[:-1].split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        try:
            parsed[key] = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError):
            parsed[key] = raw_value
    return parsed


def _render_report_lines(
    *,
    payload: dict[str, Any],
    statistic: str,
    data: str,
    series: str,
    units: str,
    runtime_seconds: float,
) -> list[str]:
    unit_label = _unit_label(data=data, units=units)
    data_label = "Precipitation intensity" if data == "intensity" else "Precipitation depth"
    series_label = "Partial duration" if series == "pds" else "Annual maximum"

    lines: list[str] = [
        f"Point precipitation frequency estimates ({unit_label})",
        f"NOAA Atlas 14 Volume {payload.get('volume', 'Unknown')} Version {payload.get('version', 'Unknown')}",
        f"Data type: {data_label}",
        f"Time series type: {series_label}",
        f"Project area: {payload.get('region', 'Unknown')}",
        "Location name (ESRI Maps): None",
        "Station Name: None",
        f"Latitude: {_format_coord(payload.get('lat'))} Degree",
        f"Longitude: {_format_coord(payload.get('lon'))} Degree",
        "Elevation (USGS): None None",
        "",
        "",
        "PRECIPITATION FREQUENCY ESTIMATES",
    ]

    tables = _tables_for_statistic(payload=payload, statistic=statistic)
    for table_index, (table_title, table_values) in enumerate(tables):
        if table_index == 0:
            lines.append(f"{table_title}:, " + ",".join(_ari_labels(series, table_values)))
        else:
            lines.extend(["", f"{table_title}:, " + ",".join(_ari_labels(series, table_values))])

        for duration, row in zip(_DURATION_LABELS, table_values):
            lines.append(f"{duration}:, " + ",".join(str(value) for value in row))

    lines.extend(
        [
            "",
            f"Date/time (GMT):  {datetime.now(timezone.utc).strftime('%a %b %d %H:%M:%S %Y')}",
            f"pyRunTime:  {runtime_seconds}",
        ]
    )
    return lines


def _ari_labels(series: str, table_values: list[list[str]]) -> tuple[str, ...]:
    defaults = _SERIES_TO_ARI.get(series, ())
    if table_values:
        width = len(table_values[0])
        if len(defaults) == width:
            return defaults
        if width == 10:
            return _SERIES_TO_ARI["pds"]
        if width == 9:
            return _SERIES_TO_ARI["ams"]
        return tuple(str(index + 1) for index in range(width))
    return defaults


def _tables_for_statistic(*, payload: dict[str, Any], statistic: str) -> list[tuple[str, list[list[str]]]]:
    if statistic == "all":
        return [
            ("mean by duration for ARI (years)", _extract_table(payload, "quantiles")),
            ("upper by duration for ARI (years)", _extract_table(payload, "upper")),
            ("lower by duration for ARI (years)", _extract_table(payload, "lower")),
        ]

    payload_key = _STATISTIC_TO_PAYLOAD_KEY[statistic]
    return [(f"by duration for ARI (years)", _extract_table(payload, payload_key))]


def _extract_table(payload: dict[str, Any], key: str) -> list[list[str]]:
    raw_table = payload.get(key)
    if not isinstance(raw_table, list):
        raise RuntimeError(f"NOAA Atlas 14 response missing '{key}' table")

    rows: list[list[str]] = []
    for raw_row in raw_table:
        if not isinstance(raw_row, list):
            raise RuntimeError(f"NOAA Atlas 14 response '{key}' row is not a list")
        rows.append([str(cell) for cell in raw_row])

    if len(rows) != len(_DURATION_LABELS):
        raise RuntimeError(
            f"NOAA Atlas 14 response '{key}' returned {len(rows)} rows; expected {len(_DURATION_LABELS)}"
        )

    return rows


def _unit_label(*, data: str, units: str) -> str:
    if units == "metric":
        return "millimeters/hour" if data == "intensity" else "millimeters"
    return "inches/hour" if data == "intensity" else "inches"


def _format_coord(value: Any) -> str:
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return "None"


__all__ = ["base_url", "download", "query_url"]
