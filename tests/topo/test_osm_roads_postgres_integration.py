from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from urllib.parse import quote

import pytest
from shapely.geometry import LineString

from wepppy.topo.osm_roads.cache import (
    OSMRoadsCacheConfig,
    PostgresMetadataStore,
    RequestRecord,
    TileRecord,
    utc_now,
)
from wepppy.topo.osm_roads.contracts import OSMRoadsRequest
from wepppy.topo.osm_roads.errors import OSMRoadsCacheError
from wepppy.topo.osm_roads.service import OSMRoadsModuleService

pytestmark = pytest.mark.integration

psycopg2 = pytest.importorskip("psycopg2")

_RUN_FLAG = "OSM_ROADS_POSTGRES_INTEGRATION"
_TRUE_VALUES = {"1", "true", "yes", "on"}
_SCHEMA_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _FakeOverpassClient:
    def __init__(self) -> None:
        self.calls = 0

    def fetch_roads(self, *, bbox_wgs84, highway_filter, include_tags):
        self.calls += 1
        minx, miny, maxx, maxy = bbox_wgs84
        return [
            {
                "osm_id": "9001",
                "geometry": LineString([(minx, miny), (maxx, maxy)]),
                "highway": "track",
            }
        ]


def _require_postgres_integration(pytestconfig: pytest.Config) -> None:
    if os.getenv(_RUN_FLAG, "").strip().lower() in _TRUE_VALUES:
        return

    # Allow direct invocation of this dedicated file without extra env wiring.
    invocation_args = tuple(str(arg) for arg in pytestconfig.invocation_params.args)
    if any(arg.endswith("test_osm_roads_postgres_integration.py") for arg in invocation_args):
        return

    pytest.skip(
        f"Set {_RUN_FLAG}=1 to include Postgres OSM roads integration tests in broader runs."
    )


def _resolve_postgres_db_url() -> str:
    explicit = (os.getenv("WEPPPY_OSM_ROADS_CACHE_DB_URL") or "").strip()
    if explicit:
        return explicit

    host = (os.getenv("POSTGRES_HOST") or "postgres").strip() or "postgres"
    port = (os.getenv("POSTGRES_PORT") or "5432").strip() or "5432"
    dbname = (os.getenv("POSTGRES_DB") or "wepppy").strip() or "wepppy"
    user = (os.getenv("POSTGRES_USER") or "wepppy").strip() or "wepppy"

    password = (os.getenv("POSTGRES_PASSWORD") or "").strip()
    if not password:
        password_files = []
        configured_password_file = (os.getenv("POSTGRES_PASSWORD_FILE") or "").strip()
        if configured_password_file:
            password_files.append(configured_password_file)
        password_files.append("/run/secrets/postgres_password")

        for password_file in password_files:
            path = Path(password_file)
            if not path.exists():
                continue
            password = path.read_text(encoding="utf-8").strip()
            if password:
                break

    user_enc = quote(user, safe="")
    if password:
        password_enc = quote(password, safe="")
        return f"postgresql://{user_enc}:{password_enc}@{host}:{port}/{dbname}"
    return f"postgresql://{user_enc}@{host}:{port}/{dbname}"


def _drop_schema(db_url: str, schema: str) -> None:
    if _SCHEMA_IDENT_RE.match(schema) is None:
        raise ValueError(f"Unsafe schema identifier: {schema}")

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    finally:
        conn.close()


@pytest.fixture
def postgres_db_url(pytestconfig: pytest.Config) -> str:
    _require_postgres_integration(pytestconfig)
    return _resolve_postgres_db_url()


@pytest.fixture
def postgres_schema(postgres_db_url: str) -> str:
    schema = f"osm_roads_it_{uuid.uuid4().hex[:12]}"
    try:
        yield schema
    finally:
        _drop_schema(postgres_db_url, schema)


def test_postgres_metadata_store_roundtrip_and_advisory_lock(
    postgres_db_url: str,
    postgres_schema: str,
) -> None:
    store = PostgresMetadataStore(db_url=postgres_db_url, schema=postgres_schema)
    store.ensure_schema()

    now = utc_now()
    tile = TileRecord(
        tile_key="osm_roads_v1:tile:z0_1_2:abc",
        tile_id="z0_1_2",
        highway_filter_hash="abc",
        payload_path="/tmp/tile.parquet",
        fetched_at_utc=now,
        feature_count=2,
    )
    request = RequestRecord(
        request_key="osm_roads_v1:req:coverhash:abc",
        tile_cover_hash="coverhash",
        highway_filter_hash="abc",
        roads_geojson_path="/tmp/req.geojson",
        fetched_at_utc=now,
        feature_count=2,
    )

    store.upsert_tile(tile)
    store.upsert_request(request)

    loaded_tile = store.get_tile(tile.tile_key)
    loaded_request = store.get_request(request.request_key)
    assert loaded_tile is not None
    assert loaded_request is not None
    assert loaded_tile.feature_count == 2
    assert loaded_request.feature_count == 2

    competing_store = PostgresMetadataStore(db_url=postgres_db_url, schema=postgres_schema)
    with store.acquire_lock(tile.tile_key, timeout_sec=5, poll_ms=20):
        with pytest.raises(OSMRoadsCacheError):
            with competing_store.acquire_lock(tile.tile_key, timeout_sec=0, poll_ms=20):
                pass


def test_osm_roads_service_hits_postgres_backed_cache(
    tmp_path: Path,
    postgres_db_url: str,
    postgres_schema: str,
) -> None:
    fake = _FakeOverpassClient()
    cache_dir = tmp_path / "osm_roads_pg_cache"

    service = OSMRoadsModuleService(
        cache_config=OSMRoadsCacheConfig(
            cache_dir=cache_dir,
            db_url=postgres_db_url,
            db_schema=postgres_schema,
            cleanup_min_interval_sec=999999,
        ),
        overpass_client=fake,
    )

    req = OSMRoadsRequest(
        aoi_wgs84_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-116.00, 46.00],
                [-115.99, 46.00],
                [-115.99, 46.01],
                [-116.00, 46.01],
                [-116.00, 46.00],
            ]],
        },
        target_epsg=3857,
        highway_filter=("track",),
    )

    first = service.get_roads(req)
    second = service.get_roads(req)

    assert first.source == "overpass"
    assert first.cache_hit is False
    assert second.source == "cache"
    assert second.cache_hit is True
    assert fake.calls == 1
    assert Path(second.roads_geojson_path).exists()

    if _SCHEMA_IDENT_RE.match(postgres_schema) is None:
        raise ValueError(f"Unsafe schema identifier: {postgres_schema}")

    conn = psycopg2.connect(postgres_db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {postgres_schema}.tiles")
            tile_count = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {postgres_schema}.requests")
            request_count = cur.fetchone()[0]
    finally:
        conn.close()

    assert tile_count >= 1
    assert request_count >= 1
