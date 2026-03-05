"""Overpass client and response normalization for OSM roads."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

import requests
from shapely.geometry import LineString

from .cache import normalize_highway_filter
from .errors import OSMRoadsUpstreamError


@dataclass(frozen=True)
class OverpassConfig:
    """Runtime settings for Overpass API requests."""

    base_url: str = "https://overpass-api.de/api/interpreter"
    timeout_sec: int = 60
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "OverpassConfig":
        return cls(
            base_url=(os.getenv("WEPPPY_OSM_ROADS_OVERPASS_BASE_URL") or "https://overpass-api.de/api/interpreter").strip(),
            timeout_sec=_env_int("WEPPPY_OSM_ROADS_OVERPASS_TIMEOUT_SEC", 60, minimum=1),
            max_retries=_env_int("WEPPPY_OSM_ROADS_OVERPASS_MAX_RETRIES", 3, minimum=0),
        )


class OverpassClientProtocol(Protocol):
    """Abstract fetch contract used by the service for testability."""

    def fetch_roads(
        self,
        *,
        bbox_wgs84: tuple[float, float, float, float],
        highway_filter: Sequence[str],
        include_tags: Sequence[str],
    ) -> list[dict[str, Any]]:
        ...


class OverpassClient(OverpassClientProtocol):
    """HTTP client for Overpass road extraction."""

    _RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})

    def __init__(self, config: OverpassConfig | None = None) -> None:
        self.config = config or OverpassConfig.from_env()

    def fetch_roads(
        self,
        *,
        bbox_wgs84: tuple[float, float, float, float],
        highway_filter: Sequence[str],
        include_tags: Sequence[str],
    ) -> list[dict[str, Any]]:
        query = build_overpass_query(
            bbox_wgs84=bbox_wgs84,
            highway_filter=highway_filter,
            timeout_sec=self.config.timeout_sec,
        )
        retries = max(0, self.config.max_retries)

        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    self.config.base_url,
                    data={"data": query},
                    timeout=float(self.config.timeout_sec),
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt >= retries:
                    raise OSMRoadsUpstreamError(
                        "Overpass request failed",
                        code="upstream_network_error",
                        context={"attempt": attempt + 1, "error": str(exc)},
                    ) from exc
                time.sleep(_retry_backoff_seconds(attempt))
                continue

            if response.status_code in self._RETRYABLE_STATUS:
                if attempt >= retries:
                    raise OSMRoadsUpstreamError(
                        "Overpass request returned retryable error",
                        code="upstream_retryable_status",
                        context={"status": response.status_code},
                    )
                time.sleep(_retry_backoff_seconds(attempt))
                continue

            if response.status_code != 200:
                raise OSMRoadsUpstreamError(
                    "Overpass request failed",
                    code="upstream_http_error",
                    context={"status": response.status_code},
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise OSMRoadsUpstreamError(
                    "Overpass returned invalid JSON",
                    code="upstream_invalid_json",
                    context={"status": response.status_code},
                ) from exc

            return parse_overpass_payload(payload, highway_filter=highway_filter, include_tags=include_tags)

        raise OSMRoadsUpstreamError("Unexpected Overpass retry loop exit", code="upstream_retry_loop_exit")


def build_overpass_query(
    *,
    bbox_wgs84: tuple[float, float, float, float],
    highway_filter: Sequence[str],
    timeout_sec: int,
) -> str:
    """Build Overpass QL query for roads inside ``bbox_wgs84``."""

    minx, miny, maxx, maxy = bbox_wgs84
    west, south, east, north = minx, miny, maxx, maxy
    normalized = normalize_highway_filter(highway_filter)
    regex = "|".join(normalized)

    return (
        f"[out:json][timeout:{timeout_sec}];"
        "("
        f'way["highway"~"^({regex})$"]({south},{west},{north},{east});'
        ");"
        "out body;"
        ">;"
        "out skel qt;"
    )


def parse_overpass_payload(
    payload: Mapping[str, Any],
    *,
    highway_filter: Sequence[str],
    include_tags: Sequence[str],
) -> list[dict[str, Any]]:
    """Normalize Overpass JSON into line-only feature rows."""

    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise OSMRoadsUpstreamError(
            "Overpass payload missing 'elements' list",
            code="upstream_payload_invalid",
        )

    normalized_filter = set(normalize_highway_filter(highway_filter))
    nodes: dict[int, tuple[float, float]] = {}

    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("type") != "node":
            continue
        node_id = element.get("id")
        lon = element.get("lon")
        lat = element.get("lat")
        if isinstance(node_id, int) and isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
            nodes[node_id] = (float(lon), float(lat))

    features: list[dict[str, Any]] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("type") != "way":
            continue

        tags = element.get("tags")
        if not isinstance(tags, dict):
            continue
        highway = tags.get("highway")
        if not isinstance(highway, str) or highway.strip().lower() not in normalized_filter:
            continue

        node_ids = element.get("nodes")
        if not isinstance(node_ids, list):
            continue

        coords: list[tuple[float, float]] = []
        for node_id in node_ids:
            if isinstance(node_id, int) and node_id in nodes:
                coords.append(nodes[node_id])

        if len(coords) < 2:
            continue

        line = LineString(coords)
        if line.is_empty or not line.is_valid:
            continue

        record: dict[str, Any] = {
            "osm_id": str(element.get("id", "")),
            "geometry": line,
        }
        for tag_name in include_tags:
            value = tags.get(tag_name)
            if value is not None:
                record[tag_name] = str(value)

        features.append(record)

    return features


def _retry_backoff_seconds(attempt: int) -> float:
    # Bounded exponential backoff: 0.5, 1.0, 2.0, 4.0...
    return min(8.0, 0.5 * (2**attempt))


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw.strip())
    except ValueError:
        return default
    return max(minimum, parsed)


__all__ = [
    "OverpassClient",
    "OverpassClientProtocol",
    "OverpassConfig",
    "build_overpass_query",
    "parse_overpass_payload",
]
