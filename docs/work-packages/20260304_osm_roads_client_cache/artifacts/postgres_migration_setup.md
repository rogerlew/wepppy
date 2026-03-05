# OSM Roads Cache PostgreSQL Migration and Deployment Setup

**Date**: 2026-03-05  
**Scope**: `docs/work-packages/20260304_osm_roads_client_cache/`  
**Audience**: operators deploying on forest1 and production

## Purpose

Document the PostgreSQL schema setup, verification, and rollout steps for the OSM roads hybrid cache module.

This module uses:
- PostgreSQL for metadata and advisory-lock coordination.
- file payloads on `/wc1` for tile parquet/request GeoJSON artifacts.

## Migration Model

Current migration model is module-owned, idempotent DDL executed by `PostgresMetadataStore.ensure_schema()`.

The runtime creates (if missing):
- schema: `WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA` (default `osm_roads_cache`)
- table: `<schema>.tiles`
- table: `<schema>.requests`

No Alembic migration is required for v1.

## Runtime Environment Variables

Required for Postgres-backed runtime:
- `WEPPPY_OSM_ROADS_CACHE_DB_URL` (recommended explicit URL)

Optional (with defaults):
- `WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA` (default `osm_roads_cache`)
- `WEPPPY_OSM_ROADS_CACHE_DIR` (default `/wc1/cache/osm_roads`)

If `WEPPPY_OSM_ROADS_CACHE_DB_URL` is unset, service code attempts fallback from runtime DB env (`SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, or `POSTGRES_*`). For production deployments, set `WEPPPY_OSM_ROADS_CACHE_DB_URL` explicitly.

## Forest1 Deployment Steps

Run from repo root (`/workdir/wepppy`):

1. Ensure postgres service is healthy.

    docker compose -f docker/docker-compose.dev.yml up -d postgres
    docker compose -f docker/docker-compose.dev.yml exec -T postgres pg_isready -U wepppy -d wepppy

2. Export OSM roads DB URL for the weppcloud runtime (or inject through your env-file/secrets pipeline).

    export WEPPPY_OSM_ROADS_CACHE_DB_URL='postgresql://wepppy:<password>@postgres:5432/wepppy'

3. Run one-shot schema initialization in weppcloud container.

    docker compose -f docker/docker-compose.dev.yml exec -T weppcloud \
      bash -lc 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python - <<"PY"
from wepppy.topo.osm_roads.cache import PostgresMetadataStore
import os

store = PostgresMetadataStore(
    db_url=os.environ["WEPPPY_OSM_ROADS_CACHE_DB_URL"],
    schema=os.getenv("WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA", "osm_roads_cache"),
)
store.ensure_schema()
print("osm_roads_schema_ready=1")
PY'

4. Verify schema objects exist.

    docker compose -f docker/docker-compose.dev.yml exec -T postgres \
      psql -U wepppy -d wepppy -c "\dt osm_roads_cache.*"

5. Verify advisory lock path.

    docker compose -f docker/docker-compose.dev.yml exec -T postgres \
      psql -U wepppy -d wepppy -c "SELECT pg_try_advisory_lock(123456789), pg_advisory_unlock(123456789);"

## Production Deployment Steps

Use your production compose/orchestration equivalent (`docker/docker-compose.prod.yml` or deployment platform env injection):

1. Set `WEPPPY_OSM_ROADS_CACHE_DB_URL` in the weppcloud runtime environment.
2. Set `WEPPPY_OSM_ROADS_CACHE_DB_SCHEMA` if non-default schema is desired.
3. Ensure `/wc1/cache/osm_roads` (or overridden cache dir) is writable and persistent.
4. Execute the same one-shot schema initialization command against the production weppcloud container.
5. Run smoke check:
   - one OSM request populates cache (`source=overpass`),
   - repeated request hits cache (`source=cache`),
   - metadata rows appear in `<schema>.tiles` and `<schema>.requests`.

## Validation Command for New Integration Test

Use the dedicated Postgres integration suite:

    wctl run-pytest tests/topo/test_osm_roads_postgres_integration.py

If you want the same tests included in broader selections (for example `tests/topo` or full `tests`), set:

    OSM_ROADS_POSTGRES_INTEGRATION=1

Expected behavior:
- metadata store round-trip succeeds,
- advisory lock contention test passes,
- service first-call miss then second-call cache hit passes.

## Rollback and Recovery

If schema deployment needs rollback:

1. Stop OSM roads usage in callers.
2. Drop schema (destructive):

    DROP SCHEMA IF EXISTS osm_roads_cache CASCADE;

3. Remove payload directory if needed:

    rm -rf /wc1/cache/osm_roads

4. Reinitialize by rerunning schema setup and smoke test.

## Future Migration Notes

For v2+ schema changes, keep migrations additive/idempotent and update this artifact with:
- exact DDL deltas,
- backfill steps,
- forward/rollback commands,
- compatibility notes for mixed-version workers.
