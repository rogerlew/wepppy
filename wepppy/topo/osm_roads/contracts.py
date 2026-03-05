"""Public contracts for the OSM roads service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, Protocol

DEFAULT_INCLUDE_TAGS: tuple[str, ...] = (
    "highway",
    "name",
    "surface",
    "width",
    "lanes",
    "bridge",
    "tunnel",
)


@dataclass(frozen=True)
class OSMRoadsRequest:
    """Request payload for fetching/caching OSM roads."""

    aoi_wgs84_geojson: dict[str, Any]
    target_epsg: int
    highway_filter: tuple[str, ...]
    include_tags: tuple[str, ...] = DEFAULT_INCLUDE_TAGS
    force_refresh: bool = False
    allow_stale_on_error: bool = True
    allow_expired_on_error: bool = True


@dataclass(frozen=True)
class OSMRoadsResult:
    """Service response for roads retrieval."""

    roads_geojson_path: str
    cache_key: str
    cache_hit: bool
    stale_served: bool
    fetched_at_utc: str
    source: Literal["cache", "overpass", "stale_cache", "expired_cache"]
    feature_count: int
    target_epsg: int
    bbox_wgs84: tuple[float, float, float, float]


class OSMRoadsService(Protocol):
    """Protocol for OSM roads consumers."""

    def get_roads(
        self,
        req: OSMRoadsRequest,
        *,
        logger: logging.Logger | None = None,
    ) -> OSMRoadsResult:
        """Resolve roads for ``req`` using cache + upstream fetch as needed."""


__all__ = [
    "DEFAULT_INCLUDE_TAGS",
    "OSMRoadsRequest",
    "OSMRoadsResult",
    "OSMRoadsService",
]
