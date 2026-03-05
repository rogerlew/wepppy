"""Cache keying, TTL, metadata store, and payload helpers for OSM roads."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping, Protocol, Sequence

import pandas as pd

from .errors import OSMRoadsCacheError, OSMRoadsValidationError

CONTRACT_VERSION = "osm_roads_v1"
DEFAULT_CACHE_DIR = Path("/wc1/cache/osm_roads")
DEFAULT_DB_SCHEMA = "osm_roads_cache"


@dataclass(frozen=True)
class OSMRoadsCacheConfig:
    """Runtime configuration for OSM roads caching."""

    cache_dir: Path = DEFAULT_CACHE_DIR
    db_url: str | None = None
    db_schema: str = DEFAULT_DB_SCHEMA
    soft_ttl_days: int = 30
    hard_ttl_days: int = 90
    max_expired_staleness_days: int = 30
    tile_degrees: float = 0.01
    max_tiles_per_query: int = 64
    lock_timeout_sec: int = 120
    lock_poll_ms: int = 250
    cleanup_min_interval_sec: int = 3600

    @classmethod
    def from_env(cls) -> "OSMRoadsCacheConfig":
        return cls(
            cache_dir=Path(os.getenv("WEPPPY_OSM_ROADS_CACHE_DIR", str(DEFAULT_CACHE_DIR))).resolve(),
            db_url=(os.getenv("WEPPPY_OSM_ROADS_CACHE_DB_URL") or "").strip() or None,
            db_schema=(os.getenv("WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA") or DEFAULT_DB_SCHEMA).strip() or DEFAULT_DB_SCHEMA,
            soft_ttl_days=_env_int("WEPPPY_OSM_ROADS_SOFT_TTL_DAYS", 30, minimum=1),
            hard_ttl_days=_env_int("WEPPPY_OSM_ROADS_HARD_TTL_DAYS", 90, minimum=1),
            max_expired_staleness_days=_env_int("WEPPPY_OSM_ROADS_MAX_EXPIRED_STALENESS_DAYS", 30, minimum=0),
            tile_degrees=_env_float("WEPPPY_OSM_ROADS_TILE_DEGREES", 0.01, minimum=0.000001),
            max_tiles_per_query=_env_int("WEPPPY_OSM_ROADS_MAX_TILES_PER_QUERY", 64, minimum=1),
            lock_timeout_sec=_env_int("WEPPPY_OSM_ROADS_LOCK_TIMEOUT_SEC", 120, minimum=1),
            lock_poll_ms=_env_int("WEPPPY_OSM_ROADS_LOCK_POLL_MS", 250, minimum=1),
            cleanup_min_interval_sec=_env_int("WEPPPY_OSM_ROADS_CLEANUP_MIN_INTERVAL_SEC", 3600, minimum=1),
        )


@dataclass(frozen=True)
class TTLDecision:
    """Result of TTL evaluation for one cache entry."""

    status: Literal["missing", "fresh", "stale", "expired"]
    should_refresh: bool
    fallback_kind: Literal["none", "stale", "expired"]
    age_days: float | None


@dataclass(frozen=True)
class TileRecord:
    """Tile cache metadata row."""

    tile_key: str
    tile_id: str
    highway_filter_hash: str
    payload_path: str
    fetched_at_utc: datetime
    feature_count: int


@dataclass(frozen=True)
class RequestRecord:
    """Request artifact metadata row."""

    request_key: str
    tile_cover_hash: str
    highway_filter_hash: str
    roads_geojson_path: str
    fetched_at_utc: datetime
    feature_count: int


class OSMRoadsMetadataStore(Protocol):
    """Metadata/locking contract for the cache index backend."""

    def ensure_schema(self) -> None:
        ...

    def get_tile(self, tile_key: str) -> TileRecord | None:
        ...

    def upsert_tile(self, record: TileRecord) -> None:
        ...

    def delete_tile(self, tile_key: str) -> None:
        ...

    def list_tiles_older_than(self, cutoff_utc: datetime) -> list[TileRecord]:
        ...

    def get_request(self, request_key: str) -> RequestRecord | None:
        ...

    def upsert_request(self, record: RequestRecord) -> None:
        ...

    def delete_request(self, request_key: str) -> None:
        ...

    @contextmanager
    def acquire_lock(self, lock_key: str, timeout_sec: int, poll_ms: int) -> Iterator[None]:
        ...


class InMemoryMetadataStore:
    """Thread-safe in-memory metadata store used by tests and local flows."""

    def __init__(self) -> None:
        self._guard = threading.RLock()
        self._tiles: dict[str, TileRecord] = {}
        self._requests: dict[str, RequestRecord] = {}
        self._locks: dict[str, threading.Lock] = {}

    def ensure_schema(self) -> None:
        return None

    def get_tile(self, tile_key: str) -> TileRecord | None:
        with self._guard:
            return self._tiles.get(tile_key)

    def upsert_tile(self, record: TileRecord) -> None:
        with self._guard:
            self._tiles[record.tile_key] = record

    def delete_tile(self, tile_key: str) -> None:
        with self._guard:
            self._tiles.pop(tile_key, None)

    def list_tiles_older_than(self, cutoff_utc: datetime) -> list[TileRecord]:
        with self._guard:
            return [row for row in self._tiles.values() if row.fetched_at_utc <= cutoff_utc]

    def get_request(self, request_key: str) -> RequestRecord | None:
        with self._guard:
            return self._requests.get(request_key)

    def upsert_request(self, record: RequestRecord) -> None:
        with self._guard:
            self._requests[record.request_key] = record

    def delete_request(self, request_key: str) -> None:
        with self._guard:
            self._requests.pop(request_key, None)

    @contextmanager
    def acquire_lock(self, lock_key: str, timeout_sec: int, poll_ms: int) -> Iterator[None]:
        with self._guard:
            lock = self._locks.setdefault(lock_key, threading.Lock())
        deadline = time.monotonic() + max(0.0, float(timeout_sec))
        poll_sec = max(0.001, poll_ms / 1000.0)
        while True:
            acquired = lock.acquire(blocking=False)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise OSMRoadsCacheError(
                    f"Timed out waiting for cache lock: {lock_key}",
                    code="lock_timeout",
                    context={"lock_key": lock_key, "timeout_sec": timeout_sec},
                )
            time.sleep(poll_sec)
        try:
            yield
        finally:
            lock.release()


class PostgresMetadataStore:
    """PostgreSQL metadata backend with advisory-lock based single-flight."""

    _IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(self, *, db_url: str, schema: str = DEFAULT_DB_SCHEMA) -> None:
        if not db_url:
            raise OSMRoadsCacheError(
                "WEPPPY_OSM_ROADS_CACHE_DB_URL is required for PostgresMetadataStore",
                code="db_url_required",
            )
        if not self._IDENT_RE.match(schema):
            raise OSMRoadsCacheError(
                f"Invalid schema identifier: {schema}",
                code="invalid_schema",
                context={"schema": schema},
            )
        self._db_url = db_url
        self._schema = schema
        self._db_kind, self._db_module = _import_postgres_driver()

    def _connect(self) -> Any:
        if self._db_kind == "psycopg":
            return self._db_module.connect(self._db_url)
        return self._db_module.connect(self._db_url)

    def _qualified(self, table: str) -> str:
        return f"{self._schema}.{table}"

    def ensure_schema(self) -> None:
        with self._connection() as (conn, cur):
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self._schema}")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._qualified('tiles')} (
                    tile_key TEXT PRIMARY KEY,
                    tile_id TEXT NOT NULL,
                    highway_filter_hash TEXT NOT NULL,
                    payload_path TEXT NOT NULL,
                    fetched_at_utc TIMESTAMPTZ NOT NULL,
                    feature_count INTEGER NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._qualified('requests')} (
                    request_key TEXT PRIMARY KEY,
                    tile_cover_hash TEXT NOT NULL,
                    highway_filter_hash TEXT NOT NULL,
                    roads_geojson_path TEXT NOT NULL,
                    fetched_at_utc TIMESTAMPTZ NOT NULL,
                    feature_count INTEGER NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            conn.commit()

    def get_tile(self, tile_key: str) -> TileRecord | None:
        with self._connection() as (_, cur):
            cur.execute(
                f"SELECT tile_key, tile_id, highway_filter_hash, payload_path, fetched_at_utc, feature_count "
                f"FROM {self._qualified('tiles')} WHERE tile_key = %s",
                (tile_key,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return TileRecord(
            tile_key=row[0],
            tile_id=row[1],
            highway_filter_hash=row[2],
            payload_path=row[3],
            fetched_at_utc=_coerce_utc(row[4]),
            feature_count=int(row[5]),
        )

    def upsert_tile(self, record: TileRecord) -> None:
        with self._connection() as (conn, cur):
            cur.execute(
                f"""
                INSERT INTO {self._qualified('tiles')}
                    (tile_key, tile_id, highway_filter_hash, payload_path, fetched_at_utc, feature_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tile_key) DO UPDATE SET
                    tile_id = EXCLUDED.tile_id,
                    highway_filter_hash = EXCLUDED.highway_filter_hash,
                    payload_path = EXCLUDED.payload_path,
                    fetched_at_utc = EXCLUDED.fetched_at_utc,
                    feature_count = EXCLUDED.feature_count,
                    updated_at = NOW()
                """,
                (
                    record.tile_key,
                    record.tile_id,
                    record.highway_filter_hash,
                    record.payload_path,
                    record.fetched_at_utc,
                    record.feature_count,
                ),
            )
            conn.commit()

    def delete_tile(self, tile_key: str) -> None:
        with self._connection() as (conn, cur):
            cur.execute(f"DELETE FROM {self._qualified('tiles')} WHERE tile_key = %s", (tile_key,))
            conn.commit()

    def list_tiles_older_than(self, cutoff_utc: datetime) -> list[TileRecord]:
        with self._connection() as (_, cur):
            cur.execute(
                f"SELECT tile_key, tile_id, highway_filter_hash, payload_path, fetched_at_utc, feature_count "
                f"FROM {self._qualified('tiles')} WHERE fetched_at_utc <= %s",
                (cutoff_utc,),
            )
            rows = cur.fetchall()
        return [
            TileRecord(
                tile_key=row[0],
                tile_id=row[1],
                highway_filter_hash=row[2],
                payload_path=row[3],
                fetched_at_utc=_coerce_utc(row[4]),
                feature_count=int(row[5]),
            )
            for row in rows
        ]

    def get_request(self, request_key: str) -> RequestRecord | None:
        with self._connection() as (_, cur):
            cur.execute(
                f"SELECT request_key, tile_cover_hash, highway_filter_hash, roads_geojson_path, fetched_at_utc, feature_count "
                f"FROM {self._qualified('requests')} WHERE request_key = %s",
                (request_key,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return RequestRecord(
            request_key=row[0],
            tile_cover_hash=row[1],
            highway_filter_hash=row[2],
            roads_geojson_path=row[3],
            fetched_at_utc=_coerce_utc(row[4]),
            feature_count=int(row[5]),
        )

    def upsert_request(self, record: RequestRecord) -> None:
        with self._connection() as (conn, cur):
            cur.execute(
                f"""
                INSERT INTO {self._qualified('requests')}
                    (request_key, tile_cover_hash, highway_filter_hash, roads_geojson_path, fetched_at_utc, feature_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_key) DO UPDATE SET
                    tile_cover_hash = EXCLUDED.tile_cover_hash,
                    highway_filter_hash = EXCLUDED.highway_filter_hash,
                    roads_geojson_path = EXCLUDED.roads_geojson_path,
                    fetched_at_utc = EXCLUDED.fetched_at_utc,
                    feature_count = EXCLUDED.feature_count,
                    updated_at = NOW()
                """,
                (
                    record.request_key,
                    record.tile_cover_hash,
                    record.highway_filter_hash,
                    record.roads_geojson_path,
                    record.fetched_at_utc,
                    record.feature_count,
                ),
            )
            conn.commit()

    def delete_request(self, request_key: str) -> None:
        with self._connection() as (conn, cur):
            cur.execute(f"DELETE FROM {self._qualified('requests')} WHERE request_key = %s", (request_key,))
            conn.commit()

    @contextmanager
    def acquire_lock(self, lock_key: str, timeout_sec: int, poll_ms: int) -> Iterator[None]:
        lock_id = advisory_lock_id(lock_key)
        conn = self._connect()
        poll_sec = max(0.001, poll_ms / 1000.0)
        deadline = time.monotonic() + max(0.0, float(timeout_sec))
        try:
            cur = conn.cursor()
            while True:
                cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
                row = cur.fetchone()
                if bool(row[0]):
                    break
                if time.monotonic() >= deadline:
                    raise OSMRoadsCacheError(
                        f"Timed out waiting for advisory lock: {lock_key}",
                        code="lock_timeout",
                        context={"lock_key": lock_key, "lock_id": lock_id},
                    )
                time.sleep(poll_sec)
            try:
                yield
            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
                conn.commit()
                cur.close()
        except OSMRoadsCacheError:
            raise
        except (AttributeError, RuntimeError, ValueError, TypeError) as exc:
            raise OSMRoadsCacheError(
                "PostgreSQL advisory lock failure",
                code="lock_error",
                context={"lock_key": lock_key, "error": str(exc)},
            ) from exc
        finally:
            conn.close()

    @contextmanager
    def _connection(self) -> Iterator[tuple[Any, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            yield conn, cur
        finally:
            cur.close()
            conn.close()


def _import_postgres_driver() -> tuple[str, Any]:
    try:
        import psycopg  # type: ignore

        return "psycopg", psycopg
    except ImportError:
        pass

    try:
        import psycopg2  # type: ignore

        return "psycopg2", psycopg2
    except ImportError as exc:
        raise OSMRoadsCacheError(
            "No PostgreSQL driver is installed (tried psycopg and psycopg2)",
            code="postgres_driver_missing",
        ) from exc


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw.strip())
    except ValueError:
        return default
    return max(minimum, parsed)


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = float(raw.strip())
    except ValueError:
        return default
    return max(minimum, parsed)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_highway_filter(highway_filter: Sequence[str]) -> tuple[str, ...]:
    raw_values = sorted({item.strip().lower() for item in highway_filter if item and item.strip()})
    if not raw_values:
        raise OSMRoadsValidationError("highway_filter must include at least one value", code="invalid_highway_filter")
    invalid = [token for token in raw_values if re.fullmatch(r"[a-z0-9_]+", token) is None]
    if invalid:
        raise OSMRoadsValidationError(
            "highway_filter contains unsupported tokens",
            code="invalid_highway_filter",
            context={"invalid_tokens": invalid},
        )
    return tuple(raw_values)


def canonical_hash(parts: Sequence[str], *, digest_size: int = 16) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[: max(8, digest_size)]


def highway_filter_hash(highway_filter: Sequence[str]) -> str:
    return canonical_hash(normalize_highway_filter(highway_filter))


def tile_cover_hash(tile_ids: Sequence[str]) -> str:
    return canonical_hash(sorted(tile_ids))


def build_tile_id(ix: int, iy: int) -> str:
    return f"z0_{ix}_{iy}"


def parse_tile_id(tile_id: str) -> tuple[int, int]:
    match = re.match(r"^z0_(-?\d+)_(-?\d+)$", tile_id)
    if not match:
        raise OSMRoadsValidationError("Invalid tile_id", code="invalid_tile_id", context={"tile_id": tile_id})
    return int(match.group(1)), int(match.group(2))


def tile_bounds(tile_id: str, tile_degrees: float) -> tuple[float, float, float, float]:
    ix, iy = parse_tile_id(tile_id)
    minx = -180.0 + ix * tile_degrees
    miny = -90.0 + iy * tile_degrees
    return (minx, miny, minx + tile_degrees, miny + tile_degrees)


def tile_cover_for_geojson(aoi_wgs84_geojson: Mapping[str, Any], tile_degrees: float) -> tuple[str, ...]:
    try:
        from shapely.geometry import box, shape
    except ImportError as exc:
        raise OSMRoadsValidationError("shapely is required to compute tile cover", code="missing_shapely") from exc

    geom = shape(aoi_wgs84_geojson)
    if geom.is_empty:
        raise OSMRoadsValidationError("AOI geometry is empty", code="empty_aoi")

    minx, miny, maxx, maxy = geom.bounds
    min_ix = math.floor((minx + 180.0) / tile_degrees)
    max_ix = math.floor((maxx + 180.0) / tile_degrees)
    min_iy = math.floor((miny + 90.0) / tile_degrees)
    max_iy = math.floor((maxy + 90.0) / tile_degrees)

    tile_ids: list[str] = []
    for ix in range(min_ix, max_ix + 1):
        for iy in range(min_iy, max_iy + 1):
            tb = tile_bounds(build_tile_id(ix, iy), tile_degrees)
            tile_poly = box(*tb)
            if geom.intersects(tile_poly):
                tile_ids.append(build_tile_id(ix, iy))

    unique = sorted(set(tile_ids))
    if not unique:
        raise OSMRoadsValidationError("AOI did not intersect any tiles", code="tile_cover_empty")
    return tuple(unique)


def build_tile_key(tile_id: str, filter_hash: str) -> str:
    return f"{CONTRACT_VERSION}:tile:{tile_id}:{filter_hash}"


def build_request_key(tile_cover_hash_value: str, filter_hash: str) -> str:
    return f"{CONTRACT_VERSION}:req:{tile_cover_hash_value}:{filter_hash}"


def advisory_lock_id(lock_key: str) -> int:
    raw = sha256(lock_key.encode("utf-8")).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


def evaluate_ttl(
    *,
    fetched_at_utc: datetime | None,
    now_utc: datetime,
    soft_ttl_days: int,
    hard_ttl_days: int,
    max_expired_staleness_days: int,
    force_refresh: bool,
    allow_stale_on_error: bool,
    allow_expired_on_error: bool,
) -> TTLDecision:
    if fetched_at_utc is None:
        return TTLDecision(status="missing", should_refresh=True, fallback_kind="none", age_days=None)

    fetched_at = _coerce_utc(fetched_at_utc)
    age_days = max(0.0, (now_utc - fetched_at).total_seconds() / 86400.0)

    if age_days <= soft_ttl_days:
        status: Literal["fresh", "stale", "expired"] = "fresh"
    elif age_days <= hard_ttl_days:
        status = "stale"
    else:
        status = "expired"

    if status == "fresh" and not force_refresh:
        return TTLDecision(status="fresh", should_refresh=False, fallback_kind="none", age_days=age_days)

    if status == "stale" and allow_stale_on_error:
        fallback_kind: Literal["none", "stale", "expired"] = "stale"
    elif status == "expired" and allow_expired_on_error and age_days <= (hard_ttl_days + max_expired_staleness_days):
        fallback_kind = "expired"
    else:
        fallback_kind = "none"

    return TTLDecision(status=status, should_refresh=True, fallback_kind=fallback_kind, age_days=age_days)


def split_batches(values: Sequence[str], batch_size: int) -> list[tuple[str, ...]]:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    return [tuple(values[i : i + batch_size]) for i in range(0, len(values), batch_size)]


def bbox_for_tiles(tile_ids: Sequence[str], tile_degrees: float) -> tuple[float, float, float, float]:
    minx: float | None = None
    miny: float | None = None
    maxx: float | None = None
    maxy: float | None = None
    for tile_id in tile_ids:
        tx0, ty0, tx1, ty1 = tile_bounds(tile_id, tile_degrees)
        minx = tx0 if minx is None else min(minx, tx0)
        miny = ty0 if miny is None else min(miny, ty0)
        maxx = tx1 if maxx is None else max(maxx, tx1)
        maxy = ty1 if maxy is None else max(maxy, ty1)
    if None in {minx, miny, maxx, maxy}:
        raise OSMRoadsValidationError("Cannot compute bbox for empty tile set", code="empty_tile_set")
    return (float(minx), float(miny), float(maxx), float(maxy))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, separators=(",", ":"))
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_tile_payload(path: Path, features: Sequence[Mapping[str, Any]]) -> None:
    """Write normalized tile features to parquet on disk."""

    from shapely.geometry.base import BaseGeometry
    from shapely.wkb import dumps as dump_wkb

    rows: list[dict[str, Any]] = []
    for feature in features:
        geometry = feature.get("geometry")
        if not isinstance(geometry, BaseGeometry):
            raise OSMRoadsCacheError(
                "Tile payload requires shapely geometries",
                code="invalid_feature_geometry",
            )
        props = dict(feature)
        props.pop("geometry", None)
        rows.append(
            {
                "osm_id": str(feature.get("osm_id", "")),
                "geometry_wkb": dump_wkb(geometry, hex=False),
                "properties_json": json.dumps(props, separators=(",", ":")),
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=["osm_id", "geometry_wkb", "properties_json"])

    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp)
    try:
        os.close(fd)
        frame.to_parquet(tmp_path, index=False)
        os.replace(tmp_path, path)
    except (OSError, ValueError, TypeError) as exc:
        raise OSMRoadsCacheError(
            "Failed writing tile payload",
            code="payload_write_error",
            context={"path": str(path), "error": str(exc)},
        ) from exc
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def read_tile_payload(path: Path) -> list[dict[str, Any]]:
    """Read tile payload from parquet and reconstruct shapely geometries."""

    from shapely.wkb import loads as load_wkb

    try:
        frame = pd.read_parquet(path)
    except (OSError, ValueError, TypeError) as exc:
        raise OSMRoadsCacheError(
            "Failed reading tile payload",
            code="payload_read_error",
            context={"path": str(path), "error": str(exc)},
        ) from exc

    records: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        try:
            props = json.loads(row.get("properties_json") or "{}")
        except json.JSONDecodeError as exc:
            raise OSMRoadsCacheError(
                "Invalid tile payload properties_json",
                code="payload_decode_error",
                context={"path": str(path)},
            ) from exc
        geom = load_wkb(row["geometry_wkb"])
        props["osm_id"] = str(row.get("osm_id") or props.get("osm_id") or "")
        records.append({"geometry": geom, **props})
    return records


def write_request_geojson(path: Path, *, features: Sequence[Mapping[str, Any]], target_epsg: int) -> None:
    """Persist request-level GeoJSON artifact for consumers."""

    from shapely.geometry import mapping

    feature_rows: list[dict[str, Any]] = []
    for feature in features:
        geom = feature.get("geometry")
        props = dict(feature)
        props.pop("geometry", None)
        feature_rows.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": props,
        })

    payload = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": f"EPSG:{target_epsg}"},
        },
        "features": feature_rows,
    }
    _atomic_write_json(path, payload)


def cleanup_expired(
    *,
    metadata_store: OSMRoadsMetadataStore,
    cache_dir: Path,
    hard_ttl_days: int,
    max_expired_staleness_days: int,
    now_utc: datetime | None = None,
    lock_timeout_sec: int = 30,
    lock_poll_ms: int = 250,
) -> int:
    """Delete expired payload + metadata rows beyond retention window."""

    now = now_utc or utc_now()
    max_age_days = hard_ttl_days + max_expired_staleness_days
    cutoff = now - timedelta(days=max_age_days)
    removed = 0

    for row in metadata_store.list_tiles_older_than(cutoff):
        with metadata_store.acquire_lock(row.tile_key, lock_timeout_sec, lock_poll_ms):
            current = metadata_store.get_tile(row.tile_key)
            if current is None:
                continue
            if current.fetched_at_utc > cutoff:
                continue
            payload_path = Path(current.payload_path)
            try:
                if payload_path.exists():
                    payload_path.unlink()
            except OSError as exc:
                raise OSMRoadsCacheError(
                    "Failed removing expired payload file",
                    code="cleanup_payload_delete_error",
                    context={"path": str(payload_path), "tile_key": current.tile_key, "error": str(exc)},
                ) from exc
            metadata_store.delete_tile(current.tile_key)
            removed += 1

    requests_root = cache_dir / "requests"
    if requests_root.exists():
        for candidate in requests_root.glob("*.geojson"):
            try:
                modified = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if modified <= cutoff:
                candidate.unlink(missing_ok=True)

    return removed


__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_DB_SCHEMA",
    "OSMRoadsCacheConfig",
    "OSMRoadsMetadataStore",
    "InMemoryMetadataStore",
    "PostgresMetadataStore",
    "RequestRecord",
    "TTLDecision",
    "TileRecord",
    "advisory_lock_id",
    "bbox_for_tiles",
    "build_request_key",
    "build_tile_key",
    "build_tile_id",
    "canonical_hash",
    "cleanup_expired",
    "evaluate_ttl",
    "highway_filter_hash",
    "normalize_highway_filter",
    "parse_tile_id",
    "read_tile_payload",
    "split_batches",
    "tile_bounds",
    "tile_cover_for_geojson",
    "tile_cover_hash",
    "utc_now",
    "write_request_geojson",
    "write_tile_payload",
]
