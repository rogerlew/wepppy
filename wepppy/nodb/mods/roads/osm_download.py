"""Build the editable Roads GeoJSON in the saved WGS84 map rectangle."""
import json
import math
from functools import partial

from shapely.geometry import LineString, MultiLineString, box, mapping

from wepppy.topo.osm_roads.contracts import VEHICULAR_HIGHWAYS
from wepppy.topo.osm_roads.errors import OSMRoadsUpstreamError, OSMRoadsValidationError
from wepppy.topo.osm_roads.overpass import OverpassClient
from wepppy.topo.osm_roads.service import _iter_line_parts
from ._constants import SURFACE_ALIASES


def download_osm_roads(extent):
    if not isinstance(extent, (list, tuple)) or len(extent) != 4:
        raise OSMRoadsValidationError("Set the project map extent before downloading roads.")
    if not all(type(value) in (float, int) and math.isfinite(value) for value in extent):
        raise OSMRoadsValidationError("The project map extent is invalid.")
    west, south, east, north = extent
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise OSMRoadsValidationError("The project map extent is invalid.")
    if east - west > 1 or north - south > 1:
        raise OSMRoadsValidationError("This map extent exceeds the download limit of one degree per side. Use a local road inventory.")
    features = OverpassClient().fetch_download_ways(tuple(extent), process=partial(_clip_features, box(*extent)))
    return {"type": "FeatureCollection", "attribution": "© OpenStreetMap contributors",
            "license": "https://www.openstreetmap.org/copyright", "features": features}


def _clip_features(bounds, ways):
    features = []
    for way in ways:
        try:
            tags = way["tags"]
            if (way["type"] != "way" or type(way["id"]) is not int or not isinstance(tags, dict)
                    or not all(isinstance(v, str) for v in tags.values())):
                raise ValueError("invalid OSM way")
            if tags["highway"] not in VEHICULAR_HIGHWAYS or tags.get("area") == "yes":
                continue
            coords = [(point["lon"], point["lat"]) for point in way["geometry"]]
            if len(coords) < 2 or not all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in coords):
                raise ValueError("invalid OSM coordinates")
            line = LineString(coords)
        except (TypeError, KeyError, ValueError) as exc:
            raise OSMRoadsUpstreamError("OpenStreetMap returned incomplete road geometry.", code="upstream_invalid_response") from exc
        props = {
            "osm_id": str(way["id"]), "osm_highway": tags["highway"], "osm_surface": tags.get("surface"),
            "osm_tags": json.dumps(tags, ensure_ascii=False, sort_keys=True),
            "DESIGN": None, "SURFACE": SURFACE_ALIASES.get(tags.get("surface")), "TRAFFIC": None,
        }
        parts = _iter_line_parts(line.intersection(bounds))
        if parts:
            geometry = parts[0] if len(parts) == 1 else MultiLineString(parts)
            features.append({"type": "Feature", "properties": props, "geometry": mapping(geometry)})
    return features
