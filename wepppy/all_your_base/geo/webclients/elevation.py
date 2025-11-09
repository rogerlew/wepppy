"""Thin HTTP client for the hosted WEPP elevationquery service."""

from __future__ import annotations

import requests

_ELEVATION_URL = 'https://wepp.cloud/webservices/elevationquery'


def elevationquery(lng: float, lat: float) -> float:
    """Return the elevation (meters) for a lon/lat coordinate."""

    response = requests.post(_ELEVATION_URL, json={'lat': lat, 'lng': lng})
    if response.status_code != 200:
        raise RuntimeError(
            f"Elevation service returned HTTP {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Cannot parse JSON from elevation response") from exc

    if 'Elevation' not in payload:
        raise RuntimeError(f"Elevation response missing value: {payload}")

    return float(payload['Elevation'])
