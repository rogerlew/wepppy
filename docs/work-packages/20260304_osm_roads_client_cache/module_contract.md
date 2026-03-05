# WEPPpy OSM Roads Module Contract (v1)

## Purpose

This contract defines the production interface for fetching OpenStreetMap road vectors with a persistent server-side cache. The module must be deterministic, lock-safe for concurrent requests, and suitable for terrain preprocessing workflows that require road geometry in project CRS.

## Contract Version

- `contract_version`: `osm_roads_v1`

## Module Location (Target)

- `wepppy/topo/osm_roads/contracts.py`
- `wepppy/topo/osm_roads/service.py`
- `wepppy/topo/osm_roads/cache.py`
- `wepppy/topo/osm_roads/overpass.py`
- `wepppy/topo/osm_roads/errors.py`

## Public API

### Request Type

```python
@dataclass(frozen=True)
class OSMRoadsRequest:
    aoi_wgs84_geojson: dict[str, Any]            # Polygon/MultiPolygon in EPSG:4326
    target_epsg: int                             # output CRS, e.g., project UTM
    highway_filter: tuple[str, ...]              # e.g. ("motorway", "trunk", ...)
    include_tags: tuple[str, ...] = (
        "highway", "name", "surface", "width", "lanes", "bridge", "tunnel"
    )
    force_refresh: bool = False                  # always attempt upstream refresh; still writes cache
    allow_stale_on_error: bool = True            # serve stale cache on upstream failure
    allow_expired_on_error: bool = True          # serve expired cache on upstream failure when policy bounds allow
```

### Response Type

```python
@dataclass(frozen=True)
class OSMRoadsResult:
    roads_geojson_path: str                      # authoritative consumer artifact in target EPSG (GeoJSON)
    cache_key: str                               # request-level canonical stable key
    cache_hit: bool                              # True if served from cache entry
    stale_served: bool                           # True if stale or expired entry served after upstream error
    fetched_at_utc: str                          # ISO timestamp of source fetch
    source: Literal["cache", "overpass", "stale_cache", "expired_cache"]
    feature_count: int
    target_epsg: int
    bbox_wgs84: tuple[float, float, float, float]
```

### Service Interface

```python
class OSMRoadsService(Protocol):
    def get_roads(self, req: OSMRoadsRequest, *, logger: logging.Logger | None = None) -> OSMRoadsResult: ...
```

## Error Contract

The service must raise typed exceptions (no silent fallback wrappers):

- `OSMRoadsValidationError`: invalid AOI, invalid CRS, unsupported highway filter.
- `OSMRoadsCacheError`: cache index corruption, lock failure, storage write/read failure.
- `OSMRoadsUpstreamError`: Overpass timeout/429/5xx and no acceptable stale entry.
- `OSMRoadsReprojectionError`: CRS transformation failure.

All exceptions should include:
- stable `code` string,
- concise `message`,
- optional context dict (`cache_key`, `bbox`, `upstream_status`).

## Persistent Cache Contract

## Cache Scope

- Server-wide (shared across runs/projects/users on same host).
- Production deployment expectation: default cache root is under `/wc1`, which is mounted persistently across deploys.
- Cache root remains configurable for non-standard environments.

## Storage Layout

- Root dir (configurable): `WEPPPY_OSM_ROADS_CACHE_DIR`
- Default: `/wc1/cache/osm_roads`
- Metadata index + lock coordination (PostgreSQL): shared WEPPpy postgres instance using module-owned schema/tables.
- Recommended schema: `osm_roads_cache`.
- PostGIS extension is not required for v1 hybrid mode.
- Payloads (GeoParquet preferred): `<cache_root>/tiles/<tile_id>/<filter_hash>.parquet`
- Optional materialized request artifacts: `<cache_root>/requests/<request_key>.geojson`

## Tiling Contract

- Grid CRS: EPSG:4326.
- Grid alignment origin: `(-180.0, -90.0)` (lon/lat).
- Tile width/height: `WEPPPY_OSM_ROADS_TILE_DEGREES` (default `0.01`).
- Tile index formula:
  - `ix = floor((lon + 180.0) / tile_degrees)`
  - `iy = floor((lat + 90.0) / tile_degrees)`
- `tile_id` format: `z0_{ix}_{iy}` (fixed scheme for v1).
- Multi-tile AOIs are supported by deriving a sorted unique tile cover set from AOI bounds/intersection.

## Cache Keys

Canonical key components:
- `tile_id` for payload-level caching.
- `tile_cover_hash` (hash of sorted tile ids) for request-level identity.
- `highway_filter_hash` (hash of sorted normalized filter list).
- `contract_version`.
- optional `snapshot_date` (future extension).

Key formats:
- Tile key (payload row identity): `osm_roads_v1:tile:{tile_id}:{highway_filter_hash}`
- Request key (returned as `OSMRoadsResult.cache_key`): `osm_roads_v1:req:{tile_cover_hash}:{highway_filter_hash}`

## TTL Policy

- `soft_ttl_days` default: `30`
- `hard_ttl_days` default: `90`
- `max_expired_staleness_days` default: `30`

Behavior:
- Fresh entry (`age <= soft_ttl`): return cached.
- Stale but valid (`soft_ttl < age <= hard_ttl`): attempt refresh; if refresh fails and `allow_stale_on_error=True`, return stale with `stale_served=True`.
- Expired (`age > hard_ttl`): attempt refresh first.
- Expired fallback on refresh failure is allowed only when all are true:
  - `allow_expired_on_error=True`,
  - effective age `<= hard_ttl + max_expired_staleness_days`,
  - upstream failure is timeout/rate-limit/5xx/network class (`OSMRoadsUpstreamError` path).
- If expired fallback is served, set `source="expired_cache"` and `stale_served=True`.
- `force_refresh=True`: always attempt upstream refresh first (independent of freshness state). If refresh fails, stale/expired fallback remains bounded by request flags and TTL policy.

## Locking Contract

- Per-tile-key single-flight lock required (tile payload write granularity).
- Locking must be cross-process and use PostgreSQL advisory locks keyed from tile key hash.
- While one process populates a missing/stale tile key, others wait or poll until completion.
- Lock timeout/configs:
  - `WEPPPY_OSM_ROADS_LOCK_TIMEOUT_SEC` (default `120`)
  - `WEPPPY_OSM_ROADS_LOCK_POLL_MS` (default `250`)

## Query and Normalization Contract

1. Validate request and AOI geometry in EPSG:4326.
2. Canonicalize highway filter and compute request/tile keys.
3. Resolve covering tiles for AOI using the normalized fixed-origin grid.
4. Read metadata/TTL state from PostgreSQL, and read tile payload files for hits.
5. For misses/stale, issue bounded Overpass queries in batches:
   - batch by uncovered tile sets (`WEPPPY_OSM_ROADS_MAX_TILES_PER_QUERY`),
   - one query per batch bbox (not one query per tile),
   - retry/backoff applies per batch query.
6. Normalize features:
   - keep only line geometries,
   - preserve selected tags,
   - assign stable `osm_id` field,
   - drop invalid geometries with explicit counters.
7. Split normalized lines to tile payloads and persist GeoParquet per tile key.
8. Upsert tile/request metadata rows in PostgreSQL in the same logical write transaction boundary.
9. Merge tile payloads for request, clip merged roads to AOI, and reproject to `target_epsg`.
10. Materialize consumer-facing GeoJSON artifact in target CRS.
11. Return `OSMRoadsResult` with absolute `roads_geojson_path` in target CRS.

## Config Contract

Environment variables:
- `WEPPPY_OSM_ROADS_CACHE_DIR`
- `WEPPPY_OSM_ROADS_CACHE_DB_URL` (optional; defaults to WEPPpy Postgres runtime configuration)
- `WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA` (default `osm_roads_cache`)
- `WEPPPY_OSM_ROADS_SOFT_TTL_DAYS`
- `WEPPPY_OSM_ROADS_HARD_TTL_DAYS`
- `WEPPPY_OSM_ROADS_MAX_EXPIRED_STALENESS_DAYS` (default `30`)
- `WEPPPY_OSM_ROADS_TILE_DEGREES` (default `0.01`)
- `WEPPPY_OSM_ROADS_MAX_TILES_PER_QUERY` (default `64`)
- `WEPPPY_OSM_ROADS_LOCK_TIMEOUT_SEC`
- `WEPPPY_OSM_ROADS_LOCK_POLL_MS`
- `WEPPPY_OSM_ROADS_OVERPASS_TIMEOUT_SEC` (default `60`)
- `WEPPPY_OSM_ROADS_OVERPASS_MAX_RETRIES` (default `3`)
- `WEPPPY_OSM_ROADS_OVERPASS_BASE_URL`
- `WEPPPY_OSM_ROADS_CLEANUP_MIN_INTERVAL_SEC` (default `3600`)

## Cleanup Contract

- Expired tile payloads and metadata rows beyond fallback retention (`age > hard_ttl + max_expired_staleness_days`) must be eligible for deletion by module-owned cleanup.
- Cleanup entrypoint should be callable directly (`cleanup_expired(...)`) and also run opportunistically after successful writes when interval gating allows.
- Cleanup should scan candidates via PostgreSQL metadata first and then remove associated payload files.
- Cleanup must be lock-safe and idempotent; partial cleanup failures raise `OSMRoadsCacheError` with explicit context.

## Observability Contract

Required structured log fields:
- `event` (`osm_roads_fetch`, `osm_roads_cache_hit`, `osm_roads_cache_miss`, `osm_roads_refresh`, `osm_roads_error`)
- `cache_key`
- `tile_count`
- `cache_hit_count`
- `query_batch_count`
- `fetch_ms`
- `feature_count`
- `stale_served`
- `expired_served`

Recommended counters (future metrics endpoint):
- `osm_roads_cache_hit_total`
- `osm_roads_cache_miss_total`
- `osm_roads_overpass_error_total`
- `osm_roads_stale_served_total`
- `osm_roads_expired_served_total`

## Consumer Contract (TerrainProcessor)

When `roads_source="osm"`, TerrainProcessor consumer code must call only `OSMRoadsService.get_roads()` and treat returned path as authoritative roads input. TerrainProcessor must not issue direct Overpass calls.

## Testing Contract

Must include:
- unit tests for key canonicalization and TTL decisions,
- concurrency test proving single-flight fill with PostgreSQL advisory locks,
- stale-on-error behavior test,
- expired-on-error behavior test with age-bound enforcement,
- force-refresh behavior test (refresh attempted even when fresh cache exists),
- reprojection/clip correctness test,
- multi-tile request batching test (bounded query count),
- cleanup/eviction test for expired entries,
- integration test with mocked Overpass responses and persistent cache restart.

Acceptance:
- deterministic cache key for equivalent requests,
- repeated call with same request returns cache hit,
- no duplicate upstream call under concurrent identical requests,
- output geometries in requested EPSG and clipped to AOI.
