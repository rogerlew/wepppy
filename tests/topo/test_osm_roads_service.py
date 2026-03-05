from __future__ import annotations

import json
import threading
from datetime import timedelta
from pathlib import Path
from typing import Sequence

import pytest
from shapely.geometry import LineString

from wepppy.topo.osm_roads import OSMRoadsCacheConfig, OSMRoadsRequest
from wepppy.topo.osm_roads.cache import InMemoryMetadataStore, utc_now
from wepppy.topo.osm_roads.errors import OSMRoadsUpstreamError
from wepppy.topo.osm_roads.service import OSMRoadsModuleService
from wepppy.topo.wbt.osm_roads_consumer import resolve_roads_source

pytestmark = pytest.mark.unit


class FakeOverpassClient:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False
        self.fail_on_calls: set[int] = set()
        self._lock = threading.Lock()

    def fetch_roads(
        self,
        *,
        bbox_wgs84: tuple[float, float, float, float],
        highway_filter: Sequence[str],
        include_tags: Sequence[str],
    ) -> list[dict]:
        with self._lock:
            self.calls += 1
            call_id = self.calls

        if self.fail or call_id in self.fail_on_calls:
            raise OSMRoadsUpstreamError("upstream failed", code="upstream_test_failure")

        minx, miny, maxx, maxy = bbox_wgs84
        midx = (minx + maxx) / 2.0
        return [
            {
                "osm_id": "1001",
                "geometry": LineString([(minx - 0.01, miny + 0.001), (maxx + 0.01, maxy - 0.001)]),
                "highway": "track",
                "name": "Test Road",
            },
            {
                "osm_id": "1002",
                "geometry": LineString([(midx, miny - 0.02), (midx, maxy + 0.02)]),
                "highway": "track",
            },
        ]


def _sample_request(*, force_refresh: bool = False, allow_stale: bool = True, allow_expired: bool = True) -> OSMRoadsRequest:
    return OSMRoadsRequest(
        aoi_wgs84_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-116.00, 46.00],
                [-115.98, 46.00],
                [-115.98, 46.02],
                [-116.00, 46.02],
                [-116.00, 46.00],
            ]],
        },
        target_epsg=3857,
        highway_filter=("track",),
        force_refresh=force_refresh,
        allow_stale_on_error=allow_stale,
        allow_expired_on_error=allow_expired,
    )


def _build_service(
    tmp_path: Path,
    *,
    now_ref: list,
    fake: FakeOverpassClient,
    max_tiles_per_query: int = 64,
) -> OSMRoadsModuleService:
    cache_config = OSMRoadsCacheConfig(
        cache_dir=tmp_path / "cache",
        db_url=None,
        db_schema="osm_roads_cache",
        soft_ttl_days=30,
        hard_ttl_days=90,
        max_expired_staleness_days=30,
        tile_degrees=0.01,
        max_tiles_per_query=max_tiles_per_query,
        lock_timeout_sec=5,
        lock_poll_ms=25,
        cleanup_min_interval_sec=3600,
    )

    return OSMRoadsModuleService(
        cache_config=cache_config,
        metadata_store=InMemoryMetadataStore(),
        overpass_client=fake,
        now_fn=lambda: now_ref[0],
    )


def test_service_single_flight_concurrency(tmp_path: Path) -> None:
    now_ref = [utc_now()]
    fake = FakeOverpassClient()
    service = _build_service(tmp_path, now_ref=now_ref, fake=fake)

    req = _sample_request()
    results = []

    def _worker() -> None:
        results.append(service.get_roads(req))

    threads = [threading.Thread(target=_worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert len(results) == 4
    assert fake.calls == 1
    assert {item.cache_key for item in results}.__len__() == 1


def test_stale_on_error_and_expired_on_error_bounds(tmp_path: Path) -> None:
    now_ref = [utc_now()]
    fake = FakeOverpassClient()
    service = _build_service(tmp_path, now_ref=now_ref, fake=fake)

    req = _sample_request()
    first = service.get_roads(req)
    assert first.source == "overpass"

    now_ref[0] = now_ref[0] + timedelta(days=45)
    fake.fail = True
    stale = service.get_roads(_sample_request())
    assert stale.source == "stale_cache"
    assert stale.stale_served is True

    now_ref[0] = now_ref[0] + timedelta(days=55)
    expired = service.get_roads(_sample_request())
    assert expired.source == "expired_cache"

    now_ref[0] = now_ref[0] + timedelta(days=40)
    with pytest.raises(OSMRoadsUpstreamError):
        service.get_roads(_sample_request(allow_expired=False))


def test_mixed_refresh_and_stale_fallback_marks_stale_source(tmp_path: Path) -> None:
    now_ref = [utc_now()]
    fake = FakeOverpassClient()
    service = _build_service(tmp_path, now_ref=now_ref, fake=fake, max_tiles_per_query=1)

    # First call hydrates all tile cache entries.
    service.get_roads(_sample_request())

    # Age entries into stale state, then fail the second refresh call only.
    now_ref[0] = now_ref[0] + timedelta(days=45)
    fail_call = fake.calls + 2
    fake.fail_on_calls = {fail_call}

    result = service.get_roads(_sample_request())
    assert result.source == "stale_cache"
    assert result.stale_served is True


def test_force_refresh_fetches_even_when_entry_is_fresh(tmp_path: Path) -> None:
    now_ref = [utc_now()]
    fake = FakeOverpassClient()
    service = _build_service(tmp_path, now_ref=now_ref, fake=fake)

    req = _sample_request()
    first = service.get_roads(req)
    assert first.cache_hit is False

    now_ref[0] = now_ref[0] + timedelta(days=1)
    second = service.get_roads(_sample_request(force_refresh=True))
    assert second.source == "overpass"
    assert fake.calls == 2


def test_clip_and_reproject_outputs_geojson_in_target_crs(tmp_path: Path) -> None:
    now_ref = [utc_now()]
    fake = FakeOverpassClient()
    service = _build_service(tmp_path, now_ref=now_ref, fake=fake)

    result = service.get_roads(_sample_request())

    payload = json.loads(Path(result.roads_geojson_path).read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert payload["crs"]["properties"]["name"] == "EPSG:3857"
    assert len(payload["features"]) > 0

    first_coord = payload["features"][0]["geometry"]["coordinates"][0]
    # EPSG:3857 projected meters should not look like lon/lat degrees.
    assert abs(first_coord[0]) > 1000
    assert abs(first_coord[1]) > 1000


def test_consumer_seam_routes_osm_source_to_service(tmp_path: Path) -> None:
    now_ref = [utc_now()]
    fake = FakeOverpassClient()
    service = _build_service(tmp_path, now_ref=now_ref, fake=fake)

    resolved = resolve_roads_source(
        roads_source="osm",
        roads_path=None,
        osm_service=service,
        aoi_wgs84_geojson=_sample_request().aoi_wgs84_geojson,
        target_epsg=3857,
        osm_highway_filter=("track",),
    )

    assert resolved is not None
    assert Path(resolved).exists()
