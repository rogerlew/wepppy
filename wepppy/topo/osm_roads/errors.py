"""Typed errors for the OSM roads service."""

from __future__ import annotations

from typing import Any, Mapping


class OSMRoadsError(RuntimeError):
    """Base OSM roads exception with stable code and optional context."""

    default_code = "osm_roads_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.context = dict(context or {})


class OSMRoadsValidationError(OSMRoadsError):
    """Raised when request validation fails."""

    default_code = "validation_error"


class OSMRoadsCacheError(OSMRoadsError):
    """Raised when cache metadata, payload, or locking fails."""

    default_code = "cache_error"


class OSMRoadsUpstreamError(OSMRoadsError):
    """Raised when Overpass fetch fails and no cache fallback is allowed."""

    default_code = "upstream_error"


class OSMRoadsReprojectionError(OSMRoadsError):
    """Raised when reprojection fails."""

    default_code = "reprojection_error"


__all__ = [
    "OSMRoadsError",
    "OSMRoadsValidationError",
    "OSMRoadsCacheError",
    "OSMRoadsUpstreamError",
    "OSMRoadsReprojectionError",
]
