# Mini Work Package: WEPPcloud idle transactions + FD leak hardening
Status: Implemented (deployed)
Last Updated: 2026-01-20
Primary Areas: `wepppy/nodb/base.py`, `wepppy/nodb/core/ron.py`, `wepppy/weppcloud/routes/user.py`, `wepppy/weppcloud/routes/admin.py`, `wepppy/weppcloud/_context_processors.py`, `wepppy/weppcloud/configuration.py`

## Objective
Prevent WEPPcloud workers from stalling due to runaway NoDb log handlers and long-lived PostgreSQL "idle in transaction" sessions during run listing and template rendering.

## Scope
- Add detached NoDb loading helpers that avoid per-run logging initialization.
- Update run listing and context processors to use detached loading and avoid lazy DB work after query execution.
- Close SQLAlchemy sessions immediately after run listing queries complete.
- Restore ORM run listing to avoid duplicate runs and unstable counts.
- Update admin run lookup to use detached loading.
- Add a DB-level safety net by configuring `idle_in_transaction_session_timeout` via SQLAlchemy engine options.

## Non-goals
- Altering NoDb serialization or file formats.
- Refactoring the broader NoDb caching model.
- Changing front-end behavior, templates, or run metadata layout.

## Symptoms
- Gunicorn workers accumulate open file descriptors (e.g., hundreds of `ron.log`/`wepp.log` handles per worker).
- PostgreSQL shows `idle in transaction` sessions for hours on run listing queries.
- Health checks hang as workers block on I/O and logging fan-out.
- `/runs/catalog` shows duplicate runs and inconsistent totals.

## Empirical Findings (2026-01-20)

### Production State Before Restart (wepp1.tail305ec9.ts.net)

**Server Metrics:**
- Load average: 4.04, 3.43, 3.09
- Memory: 23GB used / 251GB total
- Disk: 92% full (868GB / 1000GB)
- Uptime: 26 days

**File Descriptor Accumulation (after ~11 hours uptime):**
| Worker | Total FDs | Log Files |
|--------|-----------|-----------|
| 8 | 439 | ~200+ |
| 9 | 1,356 | 532 |
| 10 | 330 | ~150+ |
| 11 | 769 | ~350+ |

Worker 9 had 532 open log files (`ron.log`, `wepp.log`, etc.) pointing to different runs.

**PostgreSQL Idle Transactions:**
```
Duration    | State               | Query Pattern
10h 31m     | idle in transaction | SELECT run... JOIN runs_users...
9h 24m      | idle in transaction | SELECT run... JOIN runs_users...
7h 53m      | idle in transaction | SELECT run... JOIN runs_users...
```

**Stuck Health Checks:**
- 412 zombie `curl -fsS http://localhost:8000/health` processes
- Health endpoint is trivial (`return jsonify('OK')`) but workers couldn't respond

**Redis:**
- 197 connected clients
- 20 blocked clients (BLPOP/BRPOP)
- 0 rejected connections

### Post-Restart Accumulation Rate

After container restart at 18:07 UTC:

| Time | Worker 10 FDs | Worker 10 Log Files |
|------|---------------|---------------------|
| +15 min | 315 | 289 |
| +30 min | 319 | 293 |

**Estimated leak rate:** ~10-19 log file handles/minute on busy workers.

**Traffic volume:** 147 unique runs accessed in 11 hours (~13 runs/hour).

### Evidence of Log Handler Leak Source

Open file descriptors in Worker 9 showed handles to many different runs:
```
/wc1/runs/rl/rlew-sedimentary-blur/ron.log
/geodata/weppcloud_runs/lt_202012_21_Tunnel_Creek_PrescFire/ron.log
/wc1/runs/rl/rlew-perineal-probable/ron.log
/geodata/weppcloud_runs/lt_202012_57_McKinney_Creek_ModSev/wepp.log
... (530+ more)
```

Each run accessed creates loggers via `logging.getLogger(f'wepppy.run.{runid}.{controller}')`. Python's logging module holds these globally forever. The FileHandlers attached to each logger are never closed in the web server lifecycle.

**Key code path:** `_context_processors.py:current_ron_processor()` calls `Ron.getInstance()` and `Wepp.getInstance()` on every template render, triggering `_init_logging()` which creates FileHandlers.

## Root Causes
- `Ron.getInstance()` and `Wepp.getInstance()` initialize per-run logging (FileHandler + QueueListener) on read-only code paths.
- Template context processors and `/runs` JSON endpoints touch many runs, causing log handler/thread buildup.
- The run listing query executes first, then metadata I/O stalls, leaving the transaction open in "idle in transaction" state.
- Switching `/runs` queries to raw row joins removed ORM de-duplication, surfacing duplicate run rows in `/runs/catalog`.

## Changes
### Detached NoDb Loading
- Added `NoDbBase.load_detached()` and `NoDbBase.load_detached_from_runid()` to load NoDb objects without singleton caching or logging initialization (still uses Redis cache when available).
- `RonViewModel.getInstanceFromRunID()` now uses detached loading to avoid spawning log handlers.
- Admin `/dev/runid_query` uses detached Ron for name filtering and config lookup.

### Run Listing Query Closure
- `/runs`, `/runs/catalog`, and `/runs/map-data` now:
  - Query ORM `Run` objects (restoring identity de-duplication).
  - Resolve owner emails in a follow-up query and build metadata in-memory.
  - Call `db.session.remove()` once rows and owner emails are materialized.

### Context Processor Hardening
- `_get_run_name()` now uses detached Ron.
- `current_ron_processor()` uses detached `RonViewModel` and detached `Wepp` for `storm_event_analyzer_ready`.
- `_get_run_owner()` uses a short-lived engine connection instead of the scoped session.

### DB Safety Net
- `POSTGRES_IDLE_IN_TX_TIMEOUT` env var wires `idle_in_transaction_session_timeout` into `SQLALCHEMY_ENGINE_OPTIONS`.
  - Example: `POSTGRES_IDLE_IN_TX_TIMEOUT=15min`.
- **Not deployed, this might cause oauth and cap verify to break (correlational but not causal determination at this point).**

## Files Touched
- `wepppy/nodb/base.py` (add detached loaders)
- `wepppy/nodb/base.pyi` (stub updates)
- `wepppy/nodb/core/ron.py` (RonViewModel detached loading)
- `wepppy/weppcloud/routes/user.py` (run listing queries + session closure)
- `wepppy/weppcloud/routes/admin.py` (runid query detached loading)
- `wepppy/weppcloud/_context_processors.py` (detached loading + DB owner lookup)
- `wepppy/weppcloud/configuration.py` (idle-in-transaction timeout config)

## Validation Steps
- Restart weppcloud workers to clear existing FD/idle sessions.
- Hit `/weppcloud/runs?format=json` for a large user.
- Hit `/weppcloud/runs/catalog` and `/weppcloud/runs/map-data` for the same user.
- As admin, hit `/weppcloud/dev/runid_query?wc=<prefix>&name=<filter>` to exercise name filtering and config lookup.
- Confirm `/weppcloud/runs/catalog` totals are stable and no duplicate run IDs appear.
- Confirm in `pg_stat_activity` that run listing sessions close quickly (no long "idle in transaction").
- Check worker FD counts do not grow with repeated run listings.

## Rollout Notes
- Requires container restart to apply `POSTGRES_IDLE_IN_TX_TIMEOUT`.
- If desired, set the timeout at Postgres level using `ALTER SYSTEM` and `pg_reload_conf()`.

## Open Questions
- Should a default timeout be enforced even if `POSTGRES_IDLE_IN_TX_TIMEOUT` is unset?
- Do we want to add metrics/alerts for per-worker FD growth or idle transaction duration?
