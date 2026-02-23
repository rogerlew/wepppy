# Postfix Redis Runtime Inventory (After Changes)

Date: 2026-02-23
Work package: `20260224_redis_persistence_session_durability`

## Runtime Configuration State

`docker/redis-entrypoint.sh` now defaults to durable settings with env overrides:

- `REDIS_APPENDONLY=${REDIS_APPENDONLY:-yes}`
- `REDIS_APPENDFSYNC=${REDIS_APPENDFSYNC:-everysec}`
- `REDIS_SAVE_SCHEDULE=${REDIS_SAVE_SCHEDULE:-900 1 300 10 60 10000}`
- `REDIS_AOF_USE_RDB_PREAMBLE=${REDIS_AOF_USE_RDB_PREAMBLE:-yes}`

Redis startup arguments now include:

- `--notify-keyspace-events "Kh"` (preserved)
- `--appendonly "${REDIS_APPENDONLY}"`
- `--appendfsync "${REDIS_APPENDFSYNC}"`
- `--aof-use-rdb-preamble "${REDIS_AOF_USE_RDB_PREAMBLE}"`
- `--save "${REDIS_SAVE_SCHEDULE}"` (or empty when explicitly configured)
- `--requirepass "$REDIS_PASSWORD"` (preserved)

## Compose Wiring State

### `docker/docker-compose.dev.yml`

Redis service now wires durability env knobs:

- `REDIS_APPENDONLY`
- `REDIS_APPENDFSYNC`
- `REDIS_SAVE_SCHEDULE`
- `REDIS_AOF_USE_RDB_PREAMBLE`

### `docker/docker-compose.prod.yml`

Redis service now wires the same durability env knobs.

### `docker/docker-compose.prod.wepp1.yml`

- No local Redis service is defined in this override.
- File now carries a note + extension map documenting the same durability knobs for alignment with base prod compose.
- Added minimal image declarations/volume declaration so standalone `docker compose ... config` validation succeeds.

## Deploy Flow State

- Added `scripts/redis_flush_rq_db.sh`:
  - hard-scoped to DB 9 (`FLUSHDB` only)
  - rejects `REDIS_DB != 9`
  - optional `--require-redis` hard-fail mode
  - `--dry-run` support
- Updated `scripts/deploy-production.sh`:
  - default-on DB9 flush step (`Step 3b`)
  - `--no-flush-rq-db` opt-out
  - `--require-rq-redis` hard-fail option

## Session Durability Posture

- Session DB index remains DB 11 (no runtime index migration introduced).
- Durable Redis defaults now preserve DB 11 data across normal restarts/redeploys.
- Session contract docs now explicitly define migration impact if DB index is changed in the future.

## Verification Snapshots

Validated commands (all passed):

- `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml config`
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config`
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.wepp1.yml config`
- `wctl run-pytest tests/weppcloud/test_configuration.py`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
