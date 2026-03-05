from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest
from shapely.geometry import LineString

from wepppy.topo.osm_roads.cache import (
    InMemoryMetadataStore,
    TileRecord,
    advisory_lock_id,
    build_request_key,
    build_tile_key,
    cleanup_expired,
    evaluate_ttl,
    highway_filter_hash,
    normalize_highway_filter,
    read_tile_payload,
    tile_cover_for_geojson,
    tile_cover_hash,
    utc_now,
    write_tile_payload,
)
from wepppy.topo.osm_roads.errors import OSMRoadsCacheError
from wepppy.topo.osm_roads.errors import OSMRoadsValidationError

pytestmark = pytest.mark.unit


def _sample_aoi() -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [-116.000, 46.000],
            [-115.985, 46.000],
            [-115.985, 46.015],
            [-116.000, 46.015],
            [-116.000, 46.000],
        ]],
    }


def test_keying_is_deterministic() -> None:
    filt = normalize_highway_filter(("TrUnK", "motorway", " trunk "))
    fhash = highway_filter_hash(filt)
    cover = ("z0_1_2", "z0_1_3")
    c_hash = tile_cover_hash(cover)

    assert filt == ("motorway", "trunk")
    assert fhash == highway_filter_hash(("motorway", "trunk"))
    assert build_tile_key("z0_1_2", fhash).startswith("osm_roads_v1:tile:")
    assert build_request_key(c_hash, fhash).startswith("osm_roads_v1:req:")


def test_highway_filter_rejects_unsupported_tokens() -> None:
    with pytest.raises(OSMRoadsValidationError):
        normalize_highway_filter(("track", "foo|bar"))


def test_tile_cover_spans_multiple_tiles() -> None:
    tile_ids = tile_cover_for_geojson(_sample_aoi(), tile_degrees=0.01)
    assert len(tile_ids) >= 2


def test_ttl_decisions_cover_fresh_stale_expired() -> None:
    now = utc_now()

    fresh = evaluate_ttl(
        fetched_at_utc=now - timedelta(days=1),
        now_utc=now,
        soft_ttl_days=30,
        hard_ttl_days=90,
        max_expired_staleness_days=30,
        force_refresh=False,
        allow_stale_on_error=True,
        allow_expired_on_error=True,
    )
    assert fresh.status == "fresh"
    assert fresh.should_refresh is False

    stale = evaluate_ttl(
        fetched_at_utc=now - timedelta(days=45),
        now_utc=now,
        soft_ttl_days=30,
        hard_ttl_days=90,
        max_expired_staleness_days=30,
        force_refresh=False,
        allow_stale_on_error=True,
        allow_expired_on_error=True,
    )
    assert stale.status == "stale"
    assert stale.should_refresh is True
    assert stale.fallback_kind == "stale"

    expired = evaluate_ttl(
        fetched_at_utc=now - timedelta(days=100),
        now_utc=now,
        soft_ttl_days=30,
        hard_ttl_days=90,
        max_expired_staleness_days=30,
        force_refresh=False,
        allow_stale_on_error=True,
        allow_expired_on_error=True,
    )
    assert expired.status == "expired"
    assert expired.should_refresh is True
    assert expired.fallback_kind == "expired"


def test_payload_round_trip(tmp_path: Path) -> None:
    payload = tmp_path / "tile.parquet"
    features = [{"osm_id": "1", "geometry": LineString([(-116.0, 46.0), (-115.99, 46.01)]), "highway": "track"}]

    write_tile_payload(payload, features)
    loaded = read_tile_payload(payload)

    assert len(loaded) == 1
    assert loaded[0]["osm_id"] == "1"
    assert loaded[0]["geometry"].geom_type == "LineString"


def test_cleanup_expired_removes_metadata_and_payload(tmp_path: Path) -> None:
    store = InMemoryMetadataStore()
    now = utc_now()

    payload = tmp_path / "tiles" / "z0_1_1" / "abc.parquet"
    write_tile_payload(payload, [{"osm_id": "1", "geometry": LineString([(0, 0), (1, 1)])}])

    record = TileRecord(
        tile_key="tile-key",
        tile_id="z0_1_1",
        highway_filter_hash="abc",
        payload_path=str(payload),
        fetched_at_utc=now - timedelta(days=200),
        feature_count=1,
    )
    store.upsert_tile(record)

    removed = cleanup_expired(
        metadata_store=store,
        cache_dir=tmp_path,
        hard_ttl_days=90,
        max_expired_staleness_days=30,
        now_utc=now,
    )

    assert removed == 1
    assert store.get_tile("tile-key") is None
    assert not payload.exists()


def test_in_memory_lock_timeout() -> None:
    store = InMemoryMetadataStore()
    blocker_started = threading.Event()

    def _blocker() -> None:
        with store.acquire_lock("abc", timeout_sec=1, poll_ms=10):
            blocker_started.set()
            time.sleep(0.2)

    thread = threading.Thread(target=_blocker)
    thread.start()
    blocker_started.wait(timeout=1)

    with pytest.raises(OSMRoadsCacheError):
        with store.acquire_lock("abc", timeout_sec=0, poll_ms=10):
            pass

    thread.join(timeout=1)


def test_advisory_lock_id_is_stable() -> None:
    first = advisory_lock_id("osm_roads_v1:tile:z0_1_2:abc")
    second = advisory_lock_id("osm_roads_v1:tile:z0_1_2:abc")
    assert first == second
