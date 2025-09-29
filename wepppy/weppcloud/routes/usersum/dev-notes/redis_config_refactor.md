# Centralize Redis Configuration

## Rationale
- **Eliminate duplicated literals**: Redis DB numbers and connection strings are hard-coded across `nodb/base.py`, RQ workers, Flask helpers, and Tornado microservices. Typos or future changes require hunting through multiple files.
- **Clarify intent**: Named enums communicate the meaning of each DB slot (locks, NoDb cache, RQ, etc.) far better than anonymous integers.
- **Prevent drift**: A single helper for `REDIS_HOST` ensures every component respects the same environment override. Today the string "localhost" is scattered everywhere, which makes switching hosts brittle.
- **Minimal overhead**: Because Redis is intrinsic infrastructure, a light-weight module is sufficient—no need for a heavier config system or runtime schema.

## Proposed Module
Create `wepppy/config/redis_settings.py` to define DB aliases and expose host/URL helpers:

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

@lru_cache(maxsize=1)
def redis_host() -> str:
    return os.getenv("REDIS_HOST", "localhost")

def redis_port() -> int:
    return int(os.getenv("REDIS_PORT", 6379))

def redis_url(db: RedisDB) -> str:
    return f"redis://{redis_host()}:{redis_port()}/{int(db)}"
```

## Rollout Plan
1. **Add module** under `wepppy/config/` and include it in the controller bundle build (if necessary for JS) or simply import wherever Redis clients are constructed.
2. **Update Redis clients** to use the shared helpers:
   - `wepppy/nodb/base.py` for NoDb cache/status/locks/log-level connections.
   - `wepppy/rq/rq_worker.py` for queue DB usage.
   - `wepppy/weppcloud/utils/helpers.py` for working-directory cache.
   - `wepppy/microservices/status.py` (and other microservices) for WebSocket pub/sub.
3. **Avoid redundant env reads**: remove direct `os.getenv("REDIS_HOST", ...)` calls in these modules and defer to `redis_host()` / `redis_port()`.
4. **Smoke test** by running the Flask app and background workers with the default host, then override `REDIS_HOST` in the environment to confirm all services still connect.
5. **Document the change** in deployment notes—`REDIS_HOST` remains the only knob; DB IDs are now part of the enum and are centralized if they ever need to change.

## Follow-up Ideas
- Provide an optional `redis_client(db: RedisDB)` helper that builds a configured `StrictRedis` instance to reduce boilerplate even further.
- Add a quick unit test verifying that `redis_url(RedisDB.RQ)` reflects an overridden `REDIS_HOST`/`REDIS_PORT`.
