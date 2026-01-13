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

## Follow-up Ideas
- Add a doc blurb in deployment notes listing `SESSION_REDIS_URL` and `SESSION_REDIS_DB` as supported overrides.
