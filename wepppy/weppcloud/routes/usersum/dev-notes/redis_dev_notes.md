# WEPPcloud Redis Developer Notes

- Date: 9-22-2025
- Author: Roger (outline) CODEX gpt-5-codex (high) content

Prompt:
```
Let's work on developer documentation. 

I drafted an outline in notes/redis_dev_notes.md for a document containing redis information and patterns for the wepppy.

1. please review this draft
# WEPPcloud Redis Developer Notes
## Databases used and their applications
## `wepppy` modules with Redis reliance
## `wepppy` redis patterns
### file-locking
### nodb cache
### status messenger to microservices.status
### RedisPrep and NoDb file locking to microservices.preflight
### WEPPcloud README.md editor
## Useful debugging commands with `redis-cli`

2. please review the code base for redis usage

3. go through the sections in the `redis_dev_notes.md` document and author detailed, descriptive and helpful developer documentation. provide code snippets to add in communication. let's forgo code citations as they are likely to become outdated.

4. review the document and edit for readability and for potential missing informaiton that a developer should know
```

Redis underpins WEPPcloud's run orchestration, caching, and collaborative tooling. This guide captures where we lean on Redis, the patterns that recur across the codebase, and the operational practices that keep those pieces healthy.

## Databases used and their applications

| DB | Primary role | Typical writers | Typical readers | Notes |
|----|--------------|----------------|-----------------|-------|
| 0  | Run-scoped state, timestamps, and file-lock flags (`RedisPrep`) | `wepppy.nodb.redis_prep`, `wepppy.nodb.base`, RQ tasks | `microservices/preflight`, `wepppy` services, CLI utilities | Hash per run ID storing `attrs:*`, `timestamps:*`, `rq:*`, `archive:*`, and `locked:*`. Requires Redis keyspace notifications (`notify-keyspace-events` should include `Kh`) for live preflight updates. |
| 2  | Real-time status streaming via Pub/Sub | `StatusMessenger`, long-running RQ jobs, climate/soil builders | `microservices/status`, web clients subscribed over WebSockets | Channels follow `<runid>:<channel>` (examples: `:wepp`, `:archive`, `:omni`). No persistence—messages disappear if no subscriber is listening. |
| 9  | RQ queues and job metadata | `wepppy.weppcloud.routes.rq.api`, worker callbacks, `wepppy.rq.*` helpers | RQ workers, dashboards, jobinfo APIs, admin scripts | Holds queue lists (`rq:m4`) plus job hashes (`rq:job:<id>`). Make sure `RQ_DB` stays consistent across web, workers, and CLI tooling. |
| 11 | Server-side Flask sessions (`Flask-Session`) | WEPPcloud web app | WEPPcloud web app | Keys prefixed `session:` with 12-hour TTL. Configurable via `SESSION_REDIS_URL`, `SESSION_REDIS_DB`, or the shared `REDIS_*` settings. |
| 13 | NoDb JSON cache to accelerate repeated object loads | `wepppy.nodb.base` when saving or rebuilding | Same modules when calling `NoDbBase.getInstance` | Values are JSONPickle payloads keyed `<runid>:<filename>`, TTL 72h. Fails open: if the cache is missing or corrupt we fall back to disk. |
| 14 | README editor session coordination and distributed locks | `wepppy.weppcloud.routes.readme_md` blueprint | README editor SPA, admin pages | Keys such as `readme:lock:<runid>:<config>` and `readme:client:<runid>:<config>:<uuid>` carry TTLs to clean up abandoned sessions. |
| 15 | Per-run log level configuration | Command bar endpoints, debugging utilities | NoDb logger initialization, file handlers | Keys formatted as `loglevel:<runid>` store string values (debug, info, warning, error, critical) that control logging verbosity for specific runs. No TTL—levels persist until explicitly changed.

Most synchronous modules read the host from `REDIS_HOST` (default `localhost`). The async microservices rely on `REDIS_URL` (default `redis://localhost`). When in doubt, prefer these helpers so deployments can override endpoints without touching code.

```python
import os
import redis

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
prep_store = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
```

```python
import os
import redis.asyncio as aioredis

redis_url = os.getenv("REDIS_URL", "redis://localhost")
status_conn = aioredis.from_url(redis_url, db=2, decode_responses=True)
```

## `wepppy` modules with Redis reliance

- `wepppy.nodb.redis_prep.RedisPrep`: owns the run-level hash in DB 0, timestamping major milestones, tracking job IDs, and snapshotting state to `redisprep.dump` for cold starts.

```python
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

prep = RedisPrep.getInstance(wd)
prep.timestamp(TaskEnum.run_wepp)
prep.set_rq_job_id("run_wepp", job.id)
```

- `wepppy.nodb.base.NoDbBase`: wraps JSON-backed project components with Redis-powered locks (`locked:<filename>`), caching (DB 13), and log fan-out via `StatusMessengerHandler`. Logger initialization automatically respects per-run log levels from DB 15.

```python
with nodb_instance.locked():
    nodb_instance.multi_ofe = True
    nodb_instance._check_and_set_phosphorus_map()
```

- `wepppy.nodb.status_messenger`: lightweight Pub/Sub helper used by long-running jobs to push progress into DB 2, which the status microservice forwards to browsers.

```python
from wepppy.nodb.status_messenger import StatusMessenger
StatusMessenger.publish(f"{runid}:wepp", f"rq:{job.id} STARTED run_wepp_rq({runid})")
```

- `wepppy.microservices.preflight`: async Tornado service that watches DB 0 keyspace notifications, recomputes the preflight checklist when hashes change, and streams updates to `/run/<runid>` WebSocket clients.

- `wepppy.microservices.status`: similar Tornado proxy that subscribes to DB 2 channels and relays those Pub/Sub messages to the browser for live log feeds.

- `wepppy.rq` workers (`wepp_rq.py`, `project_rq.py`, `land_and_soil_rq.py`, etc.): enqueue work in DB 9, publish lifecycle updates through `StatusMessenger`, and record metadata (job IDs, archive pointers) back into `RedisPrep`.

- `wepppy.weppcloud.routes.rq.api`: the Flask API surface that enqueues RQ work, checks queue health, and reads `RedisPrep` to guard against duplicate submissions.

- `wepppy.weppcloud.routes.readme_md`: collaborative README editor that uses DB 14 to enforce a soft lock, track active client sessions, and invalidate stale writers.

- `wepppy.weppcloud.routes.command_bar.command_bar`: provides power-user endpoints including log level control that stores configuration in DB 15 and validates levels against the `LogLevel` enum.

## `wepppy` redis patterns

### file-locking

Each NoDb struct (e.g., `wepp.nodb`, `climate.nodb`) exposes a `locked()` context manager. Entering the context sets `locked:<filename>` to `true` in the run hash on DB 0; `dump_and_unlock()` flips it back to `false` and writes the serialized payload to disk and cache. Locks are per run ID, so long-running tasks must select consistent `runid` prefixes.

```python
with wepp.locked():
    wepp._check_and_set_baseflow_map()
    wepp._check_and_set_phosphorus_map()
```

If Redis is unreachable the lock client is `None`, and callers receive a `RuntimeError`. Surface this early to avoid silent concurrent writes.

### nodb cache

`NoDbBase.getInstance` attempts to hydrate objects from DB 13 before touching disk. Cache keys combine run ID and filename (`03f60f2:wepp.nodb`). Successful loads refresh the TTL (72 hours) to keep hot projects in memory. Failed JSONPickle decoding triggers a cache eviction and a disk read so corrupted cache entries do not brick a run.

```python
cached = redis_nodb_cache_client.get(f"{runid}:{cls.filename}")
if cached:
    return cls._decode_jsonpickle(cached)
```

When saving, `dump()` writes to disk first and then mirrors the JSON into Redis so a crash during persistence never leaves us with cache-only state.

### per-run log level configuration

Dynamic log level control per run ID uses DB 15 with keys formatted as `loglevel:<runid>`. The `LogLevel` enum maps string values (debug, info, warning, error, critical) to Python logging constants. This enables granular debugging without affecting other concurrent runs.

```python
from wepppy.nodb.base import LogLevel, try_redis_set_log_level, try_redis_get_log_level

# Set log level for a specific run
try_redis_set_log_level(runid, "debug")

# Retrieve current log level (defaults to INFO if not set)
current_level = try_redis_get_log_level(runid, logging.INFO)
```

The NoDb logger initialization automatically respects these Redis-stored levels when creating file handlers. The pattern gracefully degrades—if Redis is unavailable, it falls back to the provided default level.

```python
self._run_file_handler.setLevel(try_redis_get_log_level(self.runid, logging.INFO))
self._exception_file_handler.setLevel(try_redis_get_log_level(self.runid, logging.ERROR))
```

The command bar provides a web interface for changing log levels via the `/runs/<runid>/<config>/command_bar/loglevel` POST endpoint. Valid levels are validated against the enum before storage.

### status messenger to microservices.status

`StatusMessenger.publish` pushes plain strings onto `<runid>:<channel>` in DB 2. The `microservices/status` Tornado app subscribes to requested channels, forwards payloads as `{"type": "status", "data": ..}` JSON frames, and maintains heartbeat ping/pong to drop dead sockets. Channel naming consistency (`wepp`, `archive`, `omni`, `fork`, etc.) keeps the front-end selectors simple.
Jobs that want to surface command-bar notifications can embed the `COMMAND_BAR_RESULT` keyword in their payload. The WebSocket client peels off the message body and calls `commandBar.showResult(...)`, so long-running tasks (for example `set_run_readonly_rq`) can report `manifest.db creation finished`. Keep the leading `rq:<jobid>` prefix so troubleshooting still maps back to Redis job metadata.

### RedisPrep and NoDb file locking to microservices.preflight

The preflight microservice listens to `__keyspace@0__:*` events so it knows when the per-run hash changes. Whenever `RedisPrep` adds a timestamp or a lock flips state, the microservice fetches the updated hash, recomputes checklist booleans (`timestamps:build_soils` > `timestamps:abstract_watershed`, etc.), and pushes a `{"type": "preflight"}` payload to connected browsers. This depends on Redis being configured with keyspace notifications (e.g., `notify-keyspace-events Kh`).

### WEPPcloud README.md editor

The README blueprint keeps a soft lock in DB 14 so only one browser can save at a time. Creating a session writes the lock key and a client hash via a pipeline, stamping both with TTLs. Saves verify the stored UUID before touching disk; mismatches flip the client state to `invalidated` so the UI can alert the user.

```python
pipe = redis_readme_client.pipeline()
pipe.set(lock_key, client_uuid, ex=_LOCK_TTL_SECONDS)
pipe.hset(client_key, mapping={"status": "active", "updated_at": now})
pipe.expire(client_key, _CLIENT_STATE_TTL_SECONDS)
pipe.execute()
```

## Useful debugging commands with `redis-cli`

- Inspect a run hash on DB 0: `redis-cli -n 0 HGETALL <runid>`.
- Check a specific timestamp or lock flag: `redis-cli -n 0 HGET <runid> timestamps:run_wepp` and `redis-cli -n 0 HGET <runid> locked:wepp.nodb`.
- Verify keyspace notifications: `redis-cli CONFIG GET notify-keyspace-events` (expect `Kh` or superset) and watch live events with `redis-cli -n 0 PSUBSCRIBE '__keyspace@0__:*'`.
- Tail status traffic: `redis-cli -n 2 SUBSCRIBE <runid>:wepp` (or whatever channel you expect) to make sure `StatusMessenger` is publishing.
- Inspect RQ queue depth: `redis-cli -n 9 LLEN rq:m4` and fetch job metadata with `redis-cli -n 9 HGETALL rq:job:<id>`.
- Validate NoDb cache entries: `redis-cli -n 13 TTL <runid>:wepp.nodb` and `redis-cli -n 13 GET <runid>:wepp.nodb` (large output; pipe through `jq` for readability).
- Check README editor locks: `redis-cli -n 14 GET readme:lock:<runid>:<config>` and `redis-cli -n 14 HGETALL readme:client:<runid>:<config>:*`.
- Inspect run-specific log levels: `redis-cli -n 15 GET loglevel:<runid>` and set them manually with `redis-cli -n 15 SET loglevel:<runid> debug`.
- List all configured log levels: `redis-cli -n 15 KEYS 'loglevel:*'` (use `SCAN` in production to avoid blocking).
- Publish test events without the app stack: `redis-cli -n 2 PUBLISH <runid>:wepp 'ping from cli'` or `redis-cli -n 0 HSET <runid> timestamps:run_wepp $(date +%s)`.

When exploring production data prefer `SCAN` over `KEYS` to avoid blocking the server, and remember that Pub/Sub traffic is ephemeral—attach a subscriber before triggering work if you need to capture the full log stream.
