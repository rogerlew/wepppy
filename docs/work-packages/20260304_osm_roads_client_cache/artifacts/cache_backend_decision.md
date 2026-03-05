# Decision Record: Hybrid Cache Backend for OSM Roads Module (v1)

**Date**: 2026-03-05  
**Status**: Accepted  
**Scope**: `docs/work-packages/20260304_osm_roads_client_cache/`

## Decision

Adopt a hybrid cache backend for OSM roads:

- PostgreSQL for cache metadata, TTL state, and lock coordination.
- File payloads on `/wc1` for vector tile artifacts (GeoParquet) and request artifacts (GeoJSON).

## Context

The module needs durable multi-project cache reuse, strong cross-process coordination, explicit TTL lifecycle state, and practical cleanup/eviction behavior. The initial SQLite + file-index baseline worked for planning but is weaker under sustained multi-worker concurrency.

## Options Considered

1. SQLite + file payloads.
2. Full PostGIS/DB-centric storage for metadata and geometry payloads.
3. Hybrid Postgres metadata/locks + file payloads.

## Why Hybrid Was Selected

1. Better cross-process locking and concurrent coordination than SQLite file-index approach.
2. Easier operational cleanup with SQL-driven expiry scans while retaining file payload efficiency.
3. Minimal disruption to payload artifacts and existing `/wc1` deployment assumptions.
4. Keeps a clean forward path to PostGIS if DB-side spatial queries become necessary.

## Expired Fallback Policy

The module allows serving expired cache entries only when:

- upstream fetch fails (timeout/rate-limit/5xx/network class),
- request allows expired fallback,
- age is within `hard_ttl + max_expired_staleness_days`.

This preserves availability while bounding stale-data risk.

## Consequences

### Positive

- Stronger long-term reliability for shared cache usage.
- More deterministic cleanup and operational introspection.
- No immediate need to migrate to PostGIS.

### Trade-offs

- Requires DB schema migration and metadata query/index tuning.
- Introduces additional DB dependency for cache path.

## Revisit Criteria

Revisit full PostGIS adoption if one or more are true:

- cache operations require DB-side spatial joins/intersections for performance,
- file payload management becomes operationally burdensome,
- workload scale favors DB-native geometry persistence.

## References

- `docs/work-packages/20260304_osm_roads_client_cache/module_contract.md`
- `docs/work-packages/20260304_osm_roads_client_cache/tracker.md`
- `docs/work-packages/20260304_osm_roads_client_cache/prompts/completed/osm_roads_client_cache_execplan.md`
- `docker/docker-compose.dev.yml`
- `docker/docker-compose.prod.yml`
