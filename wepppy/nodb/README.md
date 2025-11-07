# NoDb State Management

> File-backed, Redis-cached singleton controllers for WEPPcloud run state management with distributed locking and zero-downtime serialization.

> **See also:** [AGENTS.md](../../AGENTS.md#working-with-nodb-controllers) for coding conventions and [docs/dev-notes/style-guide.md](../../docs/dev-notes/style-guide.md) for clarity expectations.

## Overview

The NoDb module replaces traditional relational databases with a constellation of file-backed singleton objects for managing WEPPcloud run state. Each NoDb controller:

- **Serializes to JSON** - Human-readable `.nodb` files in the working directory
- **Caches in Redis** - 72-hour TTL in DB 13 for instant hydration
- **Distributed locking** - Redis-backed locks (DB 0) prevent concurrent mutations
- **Singleton per run** - `getInstance(wd)` guarantees same object across workers
- **Structured telemetry** - Integrated logging pipeline to Redis pub/sub (DB 2)

Instead of SQL queries, developers interact with rich Python objects that expose domain-specific methods and properties. Redis provides coarse-grained locking and caching so these objects can be quickly deserialized and shared across workers and RQ tasks without conflicts.

**Why NoDb?**
- **Portability** - Zip a run directory and move it anywhere
- **Schema flexibility** - Add attributes without migrations
- **Developer ergonomics** - Python methods instead of SQL queries
- **Crash safety** - Redis caching with disk fallback
- **Distributed coordination** - Multi-worker safe via Redis locks

**Tradeoffs:**
- No relational queries or foreign keys
- Lock discipline required for all mutations
- JSON payloads can grow large
- Learning curve for bespoke patterns

## NoDbBase Core Responsibilities

`wepppy/nodb/base.py` provides the `NoDbBase` superclass that every controller inherits from. Important behaviors:

- **Singleton lifecycle** – `NoDbBase.getInstance(wd)` guarantees a single controller per working directory, hydrating from Redis (DB 13) before touching disk.
- **Distributed locking** – `with controller.locked():` acquires a Redis-backed lock (DB 0), mirrors legacy hash flags, and raises `NoDbAlreadyLockedError` when re-entrancy is unsafe.
- **Persistence helpers** – `dump_and_unlock()` fsyncs the JSON payload, refreshes Redis cache entries, and validates the round-trip before releasing locks.
- **Telemetry wiring** – `_init_logging()` attaches a QueueListener fan-out to StatusMessenger, run-scoped log files, and a console error stream; `try_redis_set_log_level()` dynamically adjusts levels via DB 15.
- **Trigger events** – `TriggerEvents` enum documents lifecycle hooks (e.g., `LANDUSE_BUILD_COMPLETE`) that mods and UI components listen for when orchestrating runs.

When extending NoDb, prefer these utilities over bespoke implementations—custom locking or logging code frequently regresses cross-worker behavior. See the module docstring in `wepppy/nodb/base.py` for deeper context and example usage.

## Path Placeholders in Configs

NoDb configs reference large, location-specific datasets through placeholders that
`config_get_path()` resolves at runtime:

- `MODS_DIR` expands to `wepppy/nodb/mods`, keeping legacy bundles inside the repo.
- `EXTENDED_MODS_DATA` points to heavy datasets that now live outside the repo. The
  resolver honors the `EXTENDED_MODS_DATA` environment variable, falling back to the
  default bind mounts (`/wc1/geodata/extended_mods_data`, `/geodata/extended_mods_data`)
  or the legacy `mods/locations` folder when the external volumes are unavailable.

Use the helper script `python wepppy/nodb/scripts/update_extended_mods_data.py --apply`
whenever locations (Portland, Seattle, Lake Tahoe) need to be relinked to the external
bundle; the script rewrites the `.cfg` files to use the placeholder consistently.
