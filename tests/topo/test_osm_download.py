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
    monkeypatch.setattr(OverpassClient, "fetch_download_ways", lambda self, bounds, *, process: process([way]))
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
    monkeypatch.setattr(OverpassClient, "fetch_download_ways", lambda self, bounds, *, process: process([way]))
    with pytest.raises(OSMRoadsUpstreamError):
        download_osm_roads([0, 0, 1, 1])


@pytest.mark.parametrize(("value", "expected"), [("60", 60), ("", None), ("bad-date", None), ("0", 0)])
def test_retry_after_seconds(value, expected):
    from wepppy.topo.osm_roads._foreground import _retry_after
    assert _retry_after(value) == expected


def test_interpreter_read_timeout_is_reported_as_retryable():
    import asyncio
    from wepppy.topo.osm_roads._foreground import fetch_ways

    async def exercise():
        done = asyncio.Event()

        async def stall(reader, writer):
            try:
                await reader.readuntil(b"\r\n\r\n")
                await done.wait()
            finally:
                writer.close()
                await writer.wait_closed()

        async with await asyncio.start_server(stall, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            try:
                with pytest.raises(OSMRoadsUpstreamError) as error:
                    await fetch_ways(f"http://127.0.0.1:{port}/interpreter", "test", 1, list)
                assert error.value.code == "upstream_timeout"
                assert error.value.context["retryable"] is True
                assert error.value.context["attempts"] == 1
                assert error.value.context["reference"]
            finally:
                done.set()

    asyncio.run(exercise())
