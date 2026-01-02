"""Thin HTTP client for the USGS National Map elevation service."""

from __future__ import annotations

import requests

_ELEVATION_URL = 'https://epqs.nationalmap.gov/v1/json'


def elevationquery(lng: float, lat: float) -> float:
    """Return the elevation (meters) for a lon/lat coordinate."""

    params = {
        'x': lng,
        'y': lat,
        'wkid': 4326,
        'units': 'Meters',
        'includeDate': 'false'
    }

    response = requests.get(_ELEVATION_URL, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"Elevation service returned HTTP {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Cannot parse JSON from elevation response") from exc

    if 'value' not in payload:
        raise RuntimeError(f"Elevation response missing value: {payload}")

    return float(payload['value'])
