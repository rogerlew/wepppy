"""OSM roads service package with persistent cache support."""

from .cache import OSMRoadsCacheConfig
from .contracts import DEFAULT_INCLUDE_TAGS, OSMRoadsRequest, OSMRoadsResult, OSMRoadsService
from .errors import (
    OSMRoadsCacheError,
    OSMRoadsError,
    OSMRoadsReprojectionError,
    OSMRoadsUpstreamError,
    OSMRoadsValidationError,
)
from .overpass import OverpassClient, OverpassConfig
from .service import OSMRoadsModuleService, TerrainProcessorRoadsResolver, build_default_service

__all__ = [
    "DEFAULT_INCLUDE_TAGS",
    "OSMRoadsCacheConfig",
    "OSMRoadsCacheError",
    "OSMRoadsError",
    "OSMRoadsModuleService",
    "OSMRoadsReprojectionError",
    "OSMRoadsRequest",
    "OSMRoadsResult",
    "OSMRoadsService",
    "OSMRoadsUpstreamError",
    "OSMRoadsValidationError",
    "OverpassClient",
    "OverpassConfig",
    "TerrainProcessorRoadsResolver",
    "build_default_service",
]
