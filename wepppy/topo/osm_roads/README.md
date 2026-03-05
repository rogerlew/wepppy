# OSM Roads Module

This module provides a contract-driven OSM roads client for TerrainProcessor-style consumers.

## Public Entry Points

- `wepppy.topo.osm_roads.OSMRoadsRequest`
- `wepppy.topo.osm_roads.OSMRoadsResult`
- `wepppy.topo.osm_roads.OSMRoadsModuleService`
- `wepppy.topo.osm_roads.build_default_service()`
- `wepppy.topo.wbt.osm_roads_consumer.resolve_roads_source(...)`

## Runtime Model

- Metadata and lock coordination: PostgreSQL (`PostgresMetadataStore`) with advisory locks.
- Tile payload storage: `<cache_dir>/tiles/<tile_id>/<filter_hash>.parquet`.
- Request artifact storage: `<cache_dir>/requests/<request_key>.geojson`.
- Consumer output: absolute GeoJSON path in requested target EPSG.

## Key Environment Variables

- `WEPPPY_OSM_ROADS_CACHE_DIR` (default `/wc1/cache/osm_roads`)
- `WEPPPY_OSM_ROADS_CACHE_DB_URL` (required for default service)
- `WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA` (default `osm_roads_cache`)
- `WEPPPY_OSM_ROADS_SOFT_TTL_DAYS` (default `30`)
- `WEPPPY_OSM_ROADS_HARD_TTL_DAYS` (default `90`)
- `WEPPPY_OSM_ROADS_MAX_EXPIRED_STALENESS_DAYS` (default `30`)
- `WEPPPY_OSM_ROADS_TILE_DEGREES` (default `0.01`)
- `WEPPPY_OSM_ROADS_MAX_TILES_PER_QUERY` (default `64`)
- `WEPPPY_OSM_ROADS_LOCK_TIMEOUT_SEC` (default `120`)
- `WEPPPY_OSM_ROADS_LOCK_POLL_MS` (default `250`)
- `WEPPPY_OSM_ROADS_OVERPASS_TIMEOUT_SEC` (default `60`)
- `WEPPPY_OSM_ROADS_OVERPASS_MAX_RETRIES` (default `3`)
- `WEPPPY_OSM_ROADS_OVERPASS_BASE_URL` (default `https://overpass-api.de/api/interpreter`)
- `WEPPPY_OSM_ROADS_CLEANUP_MIN_INTERVAL_SEC` (default `3600`)

## Notes

- Highway filters are normalized to lowercase tokens matching `[a-z0-9_]+`.
- `force_refresh=True` always attempts upstream fetch first.
- Fallback behavior is explicit and bounded by TTL policy.
- Missing DB URL for default service is an explicit error (`db_url_required`).
