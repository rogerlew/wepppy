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

The WEPPcloud Roads download uses a bounded foreground operation with one interpreter attempt per POST and up to two per click, with an advisory slot check before each and a minimum 55-second browser cooldown before the retry, independent of the PostgreSQL tile cache. It retains all source tags, clips lines to the project extent, and limits input to one degree per side and 8 MiB of decoded upstream data. See the [download contract](../../../docs/schemas/roads-osm-download-contract.md). TerrainProcessor shares the default vehicular classes, including service roads, forest tracks and road links.

## Future option: self-hosted worldwide roads

If Roads downloads or terrain hydroenforcement regularly fail after Overpass retries across projects, it may become necessary to self-host the weekly worldwide OpenStreetMap dataset. Use the official Planet PBF as the source. Import each weekly release independently of project requests so that a download can query roads by extent even during a public Overpass outage. [Weekly Planet OSM downloads](https://planet.openstreetmap.org/)

Use `rogerlew/soil-data-access` as the implementation reference. It separates the official-source importer from a Rust API backed by PostgreSQL/PostGIS, defines the supported queries in a contract, and exposes readiness and the active dataset release. For roads, stage and spatially index each dated release, record its source and checksum, and keep serving the last verified release until its replacement passes validation. Expose the dataset date so operators can identify stale imports. [Soil Data Access architecture](https://github.com/rogerlew/soil-data-access#status-and-architecture) · [Runtime contract](https://github.com/rogerlew/soil-data-access/blob/main/docs/runtime-contract.md)

The service should be usable by both WEPPcloud Compose and the open-wepp-org Kubernetes deployment through a configurable endpoint. Before switching either deployment, replay representative extents against a known snapshot and verify way IDs, clipped geometry, all original OSM tags, editable Roads fields and attribution in the downloaded GeoJSON. Verify terrain hydroenforcement against its existing road-class selection as well. [Roads acquisition contract](../../../docs/schemas/roads-osm-download-contract.md)
