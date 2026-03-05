"""TerrainProcessor-style consumer seam for OSM roads resolution."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from wepppy.topo.osm_roads.contracts import OSMRoadsRequest, OSMRoadsService
from wepppy.topo.osm_roads.errors import OSMRoadsValidationError


def resolve_roads_source(
    *,
    roads_source: str | None,
    roads_path: str | None,
    osm_service: OSMRoadsService,
    aoi_wgs84_geojson: Mapping[str, Any] | None,
    target_epsg: int | None,
    osm_highway_filter: Sequence[str],
) -> str | None:
    """Resolve uploaded versus OSM-derived roads artifact path.

    This function is intentionally small and strict so TerrainProcessor callers can
    enforce the contract that `roads_source="osm"` always delegates to
    `OSMRoadsService.get_roads`.
    """

    if roads_source is None:
        return None

    if roads_source == "upload":
        if not roads_path:
            raise OSMRoadsValidationError(
                "roads_path is required when roads_source='upload'",
                code="missing_uploaded_roads",
            )
        return roads_path

    if roads_source == "osm":
        if aoi_wgs84_geojson is None:
            raise OSMRoadsValidationError("aoi_wgs84_geojson is required", code="missing_aoi")
        if target_epsg is None:
            raise OSMRoadsValidationError("target_epsg is required", code="missing_target_epsg")
        result = osm_service.get_roads(
            OSMRoadsRequest(
                aoi_wgs84_geojson=dict(aoi_wgs84_geojson),
                target_epsg=int(target_epsg),
                highway_filter=tuple(osm_highway_filter),
            )
        )
        return result.roads_geojson_path

    raise OSMRoadsValidationError(
        "roads_source must be one of: None, 'upload', 'osm'",
        code="unsupported_roads_source",
        context={"roads_source": roads_source},
    )


__all__ = ["resolve_roads_source"]
