# Baseline Redis Runtime Inventory (Before Changes)

Date: 2026-02-23
Work package: `20260224_redis_persistence_session_durability`

## Baseline Findings

### Redis entrypoint defaults (before)

`docker/redis-entrypoint.sh` launched Redis with:

- `--notify-keyspace-events "Kh"`
- `--save ""`
- `--appendonly "no"`
- `--requirepass "$REDIS_PASSWORD"`

Impact: Redis restarts dropped all logical DB state because persistence was disabled.

### Compose wiring (before)

- `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml` both mounted `docker/redis-entrypoint.sh` but did not expose durability knobs (`REDIS_APPENDONLY`, `REDIS_APPENDFSYNC`, `REDIS_SAVE_SCHEDULE`, `REDIS_AOF_USE_RDB_PREAMBLE`).
- `docker/docker-compose.prod.wepp1.yml` had no local Redis service definitions.

### Deploy behavior (before)

- `scripts/deploy-production.sh` had no explicit Redis DB9 flush hook.
- Operationally, jobs were often cleared indirectly by non-persistent Redis restarts rather than an explicit DB-scoped policy.

### Session DB baseline

- Session DB contract and enum mapping use Redis DB 11.
- Flask session URL helper supports `SESSION_REDIS_DB`, but other session marker consumers reference DB 11 directly.

## Baseline Conclusion

Before this package, session durability was weak due disabled Redis persistence, and there was no explicit deploy-time DB9-only RQ flush mechanism.
