"""Read and prepare the public landing atlas without exposing extra row fields."""

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path

from flask import current_app

_MERCATOR_MAX_LATITUDE = 85.05112878


def _count(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 18:
        return int(value)
    return None


def _access_time(value):
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def _atlas_row(record):
    if not isinstance(record, dict):
        return None
    run_id = record.get("runid")
    coordinates = record.get("coordinates")
    if not isinstance(run_id, str) or not run_id.strip():
        return None
    if not isinstance(coordinates, list) or len(coordinates) != 2:
        return None
    longitude, latitude = coordinates
    if not (
        type(longitude) in (float, int) and -180 <= longitude <= 180
        and type(latitude) in (float, int) and -90 <= latitude <= 90
    ):
        return None

    name = record.get("run_name")
    config = record.get("config")
    severity = record.get("has_sbs")
    return {
        "run_id": run_id,
        "name": name.strip() if isinstance(name, str) and name.strip() else None,
        "config": config if isinstance(config, str) or type(config) is int else None,
        "longitude": longitude,
        "latitude": latitude,
        "severity": severity if isinstance(severity, bool) else None,
        "hillslopes": _count(record.get("hillslopes")),
        "access_count": _count(record.get("access_count")),
        "last_accessed": _access_time(record.get("last_accessed")),
    }


def _read_atlas(path: Path):
    try:
        with path.open(encoding="utf-8") as handle:
            records = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RecursionError):
        current_app.logger.exception("Landing atlas snapshot unreadable: %s", path)
        return None

    if not isinstance(records, list):
        current_app.logger.warning("Landing atlas snapshot must be a list: %s", path)
        return None
    rows = [row for record in records if (row := _atlas_row(record)) is not None]
    skipped = len(records) - len(rows)
    if skipped:
        current_app.logger.warning("Landing atlas snapshot contains %d invalid rows: %s", skipped, path)
        if not rows:
            return None
    return rows


def build_landing_atlas(path: Path):
    """Return overall metrics and newest-first rows for the Atlas map."""
    rows = _read_atlas(path)
    if rows is None:
        return None

    oldest = datetime.min.replace(tzinfo=UTC)
    rows.sort(key=lambda row: row["last_accessed"] or oldest, reverse=True)

    quadrants = Counter((row["latitude"] >= 0, row["longitude"] >= 0) for row in rows)
    return {
        "run_count": len(rows),
        "hillslopes": sum(row["hillslopes"] or 0 for row in rows),
        "latest_access": rows[0]["last_accessed"] if rows else None,
        "map_rows": [
            {key: value for key, value in row.items() if key != "hillslopes"}
            for row in rows if abs(row["latitude"]) <= _MERCATOR_MAX_LATITUDE
        ],
        "quadrants": (
            ("North of the equator, west of Greenwich", quadrants[True, False]),
            ("North of the equator, east of Greenwich", quadrants[True, True]),
            ("South of the equator, west of Greenwich", quadrants[False, False]),
            ("South of the equator, east of Greenwich", quadrants[False, True]),
        ),
    }
