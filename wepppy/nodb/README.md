# NoDb State Management

> File-backed, Redis-cached singleton controllers for WEPPcloud run state management with distributed locking and zero-downtime serialization.

> **See also:** [NoDb Persistence and Concurrency Contract](../../docs/schemas/nodb-persistence-concurrency-contract.md), [AGENTS.md](../../AGENTS.md) for coding conventions, and [docs/dev-notes/style-guide.md](../../docs/dev-notes/style-guide.md) for clarity expectations.

## Overview

The NoDb module replaces traditional relational databases with a constellation of file-backed singleton objects for managing WEPPcloud run state. Each NoDb controller:

- **Serializes to JSON** - Human-readable `.nodb` files in the working directory
- **Caches in Redis** - 72-hour TTL in DB 13 for instant hydration
- **Distributed locking** - Redis-backed locks (DB 0) serialize participating commit sections
- **Singleton per process** - `getInstance(wd)` reuses a per-process cached object for repeated calls in the same worker process
- **Structured telemetry** - Per-controller log files (`<wd>/<controller>.log`) and Redis pub/sub (DB 2)

Instead of SQL queries, developers interact with rich Python objects that expose domain-specific methods and properties. Redis provides coarse-grained locking and caching, while durable-state refresh and stale-write rejection protect whole-object commits across workers and RQ tasks.

**Why NoDb?**
- **Portability** - Zip a run directory and move it anywhere
- **Schema flexibility** - Add attributes without migrations
- **Developer ergonomics** - Python methods instead of SQL queries
- **Crash safety** - Redis caching with disk fallback
- **Distributed coordination** - Redis locks, durable refresh, and stale-write rejection coordinate participating writers

**Tradeoffs:**
- No relational queries or foreign keys
- Lock discipline required for all mutations
- JSON payloads can grow large
- Learning curve for bespoke patterns

## NoDbBase Core Responsibilities

`wepppy/nodb/base.py` provides the `NoDbBase` superclass that every controller inherits from. Important behaviors:

- **Singleton lifecycle** – `NoDbBase.getInstance(wd)` maintains one process-local cached controller per working directory for writable paths and refreshes from cache/disk when signatures drift.
- **Distributed locking** – `with controller.locked():` acquires a Redis-backed lock (DB 0), mirrors legacy hash flags, and raises `NoDbAlreadyLockedError` when re-entrancy is unsafe.
- **Persistence helpers** – `dump_and_unlock()` fsyncs and atomically replaces the JSON payload, releases the lock, then sanity-checks persisted state via `getInstance()` signature/hydration paths.
- **Telemetry wiring** – `_init_logging()` attaches a QueueListener fan-out to StatusMessenger, controller-scoped log files, and a console error stream; `try_redis_set_log_level()` dynamically adjusts levels via DB 15.
- **Status channels** – `_status_channel` resolves to `<runid>:<controller>` (pup runs routed to `runid:omni`).
- **Trigger events** – `TriggerEvents` enum documents lifecycle hooks (e.g., `LANDUSE_BUILD_COMPLETE`) that mods and UI components listen for when orchestrating runs.

When extending NoDb, prefer these utilities over bespoke implementations—custom locking or logging code frequently regresses cross-worker behavior. See the module docstring in `wepppy/nodb/base.py` for deeper context and example usage.

## Authoritative Contract

`NoDbBase` lock ownership, stale-write rejection, atomic write behavior, cache hydration, and NFS-focused durability/error classification are specified in:

- `docs/schemas/nodb-persistence-concurrency-contract.md`

If this README and implementation behavior diverge, treat the schema contract as authoritative and update this README in the same change set.

## Writer Ownership, Contention, and Retry

Prefer one writer per NoDb file during a concurrent orchestration phase. For
parallel RQ work, each worker should write its own per-run artifact and use RQ
metadata for live job state. A dependency finalizer should merge those results
into the shared controller after workers reach terminal states.

Different attributes or dictionary keys are not independent write scopes. A
NoDb dump replaces the whole serialized controller, so two workers updating
different `_runs[run_id]` entries can still lose one another's changes if they
commit from independently hydrated objects.

Multiple writers are permitted when a single writer or finalizer is
impractical. Use this transaction shape for every shared mutation:

1. Complete expensive work outside the lock.
2. Acquire the distributed lock.
3. Refresh the controller from durable state while holding the lock.
4. Apply a small, idempotent mutation that preserves unrelated fields.
5. Atomically dump and unlock.

Use bounded backoff for `NoDbAlreadyLockedError`. On
`NoDbStaleWriteError`, discard the stale mutation base, reload current durable
state, and reapply the entire operation; never retry `dump()` on the stale
object. If the update cannot be safely merged or reapplied, fail explicitly.

Keep locks out of model execution, raster processing, remote requests, and
other long-running work. Multi-writer paths require concurrency regression
coverage demonstrating that representative interleavings do not lose unrelated
updates. See the authoritative contract's "Writer Ownership and Mutation
Topology" section for the normative requirements.

## WEPP Hillslope Timeout Policy

Continuous hillslope runs use the default 60-second `wepp_runner.run_hillslope` timeout for single-OFE projects. MOFE projects route continuous hillslope execution through `WeppRunService` with a 300-second timeout because each WEPP invocation can route many OFEs for one hillslope. The timeout appears in the service log line as `Running Hillslopes with max_workers=..., timeout=...s` and is passed unchanged to the runner so timeout errors continue to report the command, run file, error file, attempts, and last observed WEPP output.

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
