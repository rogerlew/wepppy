import json

import pytest

from wepppy.nodb.mods.roads.osm_download import download_osm_roads
from wepppy.topo.osm_roads.errors import OSMRoadsUpstreamError, OSMRoadsValidationError
from wepppy.topo.osm_roads.overpass import OverpassClient

pytestmark = pytest.mark.unit


def test_multi_crossing_preserves_one_way_and_unknown_surface(monkeypatch):
    tags = {"highway": "service", "access": "private", "wepp:TRAFFIC": "surveyed"}
    coords = [(0.1, 0.1), (1.2, 0.2), (0.1, 0.3)]
    way = {"id": 8, "type": "way", "tags": tags,
           "geometry": [{"lon": x, "lat": y} for x, y in coords]}
    monkeypatch.setattr(OverpassClient, "fetch_download_ways", lambda self, bounds: [way])
    feature, = download_osm_roads([0, 0, 1, 1])["features"]
    assert feature["geometry"]["type"] == "MultiLineString"
    assert feature["properties"]["SURFACE"] is None
    assert json.loads(feature["properties"]["osm_tags"]) == tags


@pytest.mark.parametrize("extent", [None, [0, 0, 5, 1], [0, 0, 0, 1], [0, 0, float("nan"), 1]])
def test_invalid_download_extent_precedes_network_access(extent):
    with pytest.raises(OSMRoadsValidationError):
        download_osm_roads(extent)


def test_incomplete_download_geometry_is_not_an_empty_result(monkeypatch):
    way = {"id": 8, "type": "way", "tags": {"highway": "track"}}
    monkeypatch.setattr(OverpassClient, "fetch_download_ways", lambda self, bounds: [way])
    with pytest.raises(OSMRoadsUpstreamError):
        download_osm_roads([0, 0, 1, 1])
