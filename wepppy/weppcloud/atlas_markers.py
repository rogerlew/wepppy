"""Public watershed marker schema shared by snapshot writers and readers."""

import json


def _count(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 18:
        return int(value)
    return None


def watershed_marker(record):
    if not isinstance(record, dict):
        return None
    coordinates = record.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 2:
        return None
    longitude, latitude = coordinates
    if not (
        type(longitude) in (float, int) and -180 <= longitude <= 180
        and type(latitude) in (float, int) and -90 <= latitude <= 90
    ):
        return None

    config = record.get("config")
    severity = record.get("has_sbs")
    return {
        "coordinates": [longitude, latitude],
        "config": config if isinstance(config, str) or type(config) is int else None,
        "has_sbs": severity if isinstance(severity, bool) else None,
        "hillslopes": _count(record.get("hillslopes")),
        "ash_hillslopes": _count(record.get("ash_hillslopes")),
    }


def marker_order(row):
    """Order by the public payload, including tie breakers for coincident runs."""
    return json.dumps(row, sort_keys=True)
