"""Read and prepare the public landing atlas without exposing extra row fields."""

from collections import Counter
import json
from pathlib import Path

from flask import current_app

from wepppy.weppcloud.atlas_markers import marker_order, watershed_marker

_MERCATOR_MAX_LATITUDE = 85.05112878


def read_atlas_markers(path: Path):
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
    rows = [row for record in records if (row := watershed_marker(record)) is not None]
    skipped = len(records) - len(rows)
    if skipped:
        current_app.logger.warning("Landing atlas snapshot contains %d invalid rows: %s", skipped, path)
        if not rows:
            return None
    return sorted(rows, key=marker_order)


def build_landing_atlas(path: Path):
    """Return overall metrics and public markers for the Atlas map."""
    rows = read_atlas_markers(path)
    if rows is None:
        return None

    quadrants = Counter((row["coordinates"][1] >= 0, row["coordinates"][0] >= 0) for row in rows)
    return {
        "run_count": len(rows),
        "hillslopes": sum(row["hillslopes"] or 0 for row in rows),
        "map_rows": [row for row in rows if abs(row["coordinates"][1]) <= _MERCATOR_MAX_LATITUDE],
        "quadrants": (
            ("North of the equator, west of Greenwich", quadrants[True, False]),
            ("North of the equator, east of Greenwich", quadrants[True, True]),
            ("South of the equator, west of Greenwich", quadrants[False, False]),
            ("South of the equator, east of Greenwich", quadrants[False, True]),
        ),
    }
