# Centralize Redis Configuration

## Rationale
- **Eliminate duplicated literals**: Redis DB numbers and connection strings are hard-coded across `nodb/base.py`, RQ workers, Flask helpers, and the WebSocket microservices. Typos or future changes require hunting through multiple files.
- **Clarify intent**: Named enums communicate the meaning of each DB slot (locks, NoDb cache, RQ, etc.) far better than anonymous integers.
- **Prevent drift**: A single helper for `REDIS_HOST` ensures every component respects the same environment override. Today the string "localhost" is scattered everywhere, which makes switching hosts brittle.
- **Minimal overhead**: Because Redis is intrinsic infrastructure, a light-weight module is sufficient—no need for a heavier config system or runtime schema.

## Current Module (Implemented)
`wepppy/config/redis_settings.py` defines DB aliases plus host/URL helpers:

```python
# wepppy/config/redis_settings.py
import os
from enum import IntEnum
from functools import lru_cache

class RedisDB(IntEnum):
    NODB_CACHE = 13
    STATUS = 2
    LOCK = 0
    LOG_LEVEL = 15
    RQ = 9
    WD_CACHE = 11
    SESSION = 11

@lru_cache(maxsize=1)
def redis_host() -> str:
    return os.getenv("REDIS_HOST", "localhost")

def redis_port() -> int:
    return int(os.getenv("REDIS_PORT", 6379))

def redis_url(db: RedisDB) -> str:
    return f"redis://{redis_host()}:{redis_port()}/{int(db)}"

def session_redis_url(db_default: RedisDB = RedisDB.SESSION) -> str:
    """Prefer SESSION_REDIS_URL/SESSION_REDIS_DB, otherwise use REDIS_URL host with DB 11."""
    ...
```

## Usage Notes
- `RedisDB.SESSION` aliases DB 11 (shared with `WD_CACHE`).
- `session_redis_url()` enforces DB 11 unless `SESSION_REDIS_DB` overrides it.
- `SESSION_REDIS_URL` takes precedence; if omitted, session URLs inherit host/credentials from `REDIS_URL` (or `RQ_REDIS_URL`) while swapping in the session DB.
- Weppcloud session storage uses `session_redis_url()` to avoid `REDIS_URL` path drift.

## Env knobs and precedence

### Client connection knobs (WEPPcloud + workers)

Prefer setting one “top-level” URL where possible:

- `RQ_REDIS_URL` is the primary deployment-level knob for RQ and is expected to point at DB 9 (example: `redis://:password@redis:6379/9`).
- `REDIS_URL` is the primary URL for async Redis consumers (microservices). In the docker stacks it commonly defaults to `RQ_REDIS_URL` so host/credentials remain consistent; DB selection is then done per feature.
- `SESSION_REDIS_URL` and `SESSION_REDIS_DB` override where Flask sessions are stored. Precedence is:
  1) `SESSION_REDIS_URL` + `SESSION_REDIS_DB`,
  2) `SESSION_REDIS_URL` alone (DB defaults to `RedisDB.SESSION` / 11),
  3) derive from `REDIS_URL` / `RQ_REDIS_URL` and force DB 11.
  Do not change `SESSION_REDIS_DB` in isolation: rq-engine and session-marker consumers still assume DB 11 unless migrated together.
- `REDIS_HOST` / `REDIS_PORT` are used by synchronous Redis clients. In containerized deployments, keep these consistent with URL-based knobs to avoid different components talking to different Redis endpoints.

### Redis persistence knobs (Redis server container only)

Stacks that define a `redis` service configure durability via `docker/redis-entrypoint.sh` using env vars (defaults shown):

- `REDIS_APPENDONLY=yes`
- `REDIS_APPENDFSYNC=everysec`
- `REDIS_AOF_USE_RDB_PREAMBLE=yes`
- `REDIS_SAVE_SCHEDULE="900 1 300 10 60 10000"`

Precedence is “explicit env in compose” → “entrypoint defaults” → “Redis server defaults”.

### Deploy-time RQ DB9 flush policy

Deploy automation includes an explicit “flush only DB 9 (RQ)” step. The host-side helper is `scripts/redis_flush_rq_db.sh`:

- Always flushes DB 9 only (`FLUSHDB` on DB 9), never `FLUSHALL`.
- Fails closed if `REDIS_DB` is provided and is not `9`.
- Best-effort skip by default when Redis is unreachable; use `--require-redis` to fail instead.

`scripts/redis_flush_rq_db.sh` supports these env overrides (subset):

- `REDIS_HOST`, `REDIS_PORT` (or infer from `RQ_REDIS_URL` / `REDIS_URL`)
- `REDIS_PASSWORD_FILE` (preferred) or `REDIS_PASSWORD` (discouraged)
- `REDIS_TIMEOUT_SECONDS`, `REDIS_PING_ATTEMPTS`, `REDIS_PING_DELAY_SECONDS`
- `RQ_REDIS_URL`, `REDIS_URL` (used only to infer host/port; DB is still forced to 9)
