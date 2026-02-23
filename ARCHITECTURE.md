# WEPPpy Architecture Guide

> Last Modified: 2026-02-09
> Maintained by: Codex
> Development-focused architecture reference for contributors and coding agents.

## Scope

This document is intentionally focused on software development concerns:

- Runtime topology and service boundaries
- State management and persistence contracts
- Background job orchestration
- Source tree ownership and integration points

It omits end-user workflows and product messaging.

## Runtime Topology

```text
Browser
  -> Caddy (/weppcloud, /rq-engine, /query-engine, /status, /preflight, ...)
    -> Flask app (wepppy.weppcloud.app)
      -> NoDb controllers (wepppy.nodb.*)
      -> RQ enqueue (Redis DB 9)
      -> Microservice calls (elevationquery, browse, metquery, wmesque2, dtale)
    -> rq-engine FastAPI (wepppy.microservices.rq_engine)
      -> Job polling, cancel, enqueue API surface
    -> query-engine Starlette (wepppy.query_engine.app)
      -> DuckDB-backed run analytics and MCP routes

RQ worker pool (wepppy.rq.WepppyRqWorker)
  -> Executes long-running tasks (DEM prep, climate, WEPP, exports, Omni, SWAT)
  -> Writes run artifacts under /wc1/runs
  -> Publishes status/log events to Redis DB 2

Go services
  -> status2 (WebSocket proxy for log/status channels)
  -> preflight2 (preflight/checklist streaming)
```

## Core Components

| Component | Path | Runtime | Responsibility |
| --- | --- | --- | --- |
| Web app | `wepppy/weppcloud/` | Flask + Gunicorn | UI routes, API routes, template composition, session/auth wiring |
| NoDb controllers | `wepppy/nodb/` | Python | Run-scoped singleton state model with locking and JSON persistence |
| RQ tasks/worker | `wepppy/rq/` | RQ on Redis | Background execution, dependency trees, status publication |
| rq-engine | `wepppy/microservices/rq_engine/` | FastAPI | Job-centric API (`/rq-engine/api/*`), auth/scopes, canonical errors |
| Query engine | `wepppy/query_engine/` | Starlette + DuckDB | Run analytics over Parquet/GeoJSON + MCP-compatible routes |
| Microservices | `wepppy/microservices/` | Starlette/FastAPI | Lightweight services (`elevationquery`, `browse`, support helpers) |
| Webservices | `wepppy/webservices/` | Flask/FastAPI | Dataset and raster services (`metquery`, `wmesque2`, `dtale`) |
| Telemetry proxies | `services/status2`, `services/preflight2` | Go | Redis pub/sub to WebSocket fan-out |
| Rust acceleration | `/workdir/wepppyo3`, `/workdir/peridot`, `/workdir/weppcloud-wbt` | Rust/PyO3 | Raster ops, watershed abstraction, delineation performance |
| Model binaries | `/workdir/wepp-forest`, `/workdir/wepp-forest-revegetation`, `/workdir/wepppy2` | Fortran + wrappers | Core WEPP simulation executables and runner integration |

## State Model

### NoDb Contract

- Controllers are mutable singleton objects keyed by working directory (`getInstance(wd)`).
- State is persisted to disk and cached in Redis (DB 13, 72-hour TTL).
- Mutations must run under controller locks and finish with `dump_and_unlock()`.
- Distributed lock keys live in Redis DB 0 with `locked:*.nodb` patterns.

### Run Directory Contract

- Canonical run root: `/wc1/runs/`
- Run path shape: `/wc1/runs/<prefix>/<runid>/` where `<prefix>` is the first two runid characters.
- Historical paths under `/geodata/weppcloud_runs/` are legacy and may still exist for archived runs.

### Redis Database Allocation

| DB | Purpose |
| --- | --- |
| 0 | Run metadata and distributed locks |
| 2 | Status pub/sub streaming |
| 9 | RQ jobs and queues |
| 11 | Flask sessions and WD cache |
| 13 | NoDb JSON cache (72-hour TTL) |
| 14 | README editor locks |
| 15 | Log-level control |

## Async Job Flow (Development View)

1. A route (Flask or rq-engine) receives a mutation/build request.
2. The route validates payloads and enqueues one or more RQ jobs in Redis DB 9.
3. `WepppyRqWorker` executes task modules from `wepppy/rq/*.py`.
4. Tasks acquire NoDb locks, mutate state, call binaries/services, persist updates.
5. Tasks publish status/log events to Redis DB 2 channels.
6. `status2` streams those events to browsers via WebSocket.
7. Front-end controllers (`controllers_js`) update status panels and progress UX.

For canonical response/error structure, use `docs/schemas/rq-response-contract.md`.

## Telemetry Pipeline

```text
NoDb logger / RQ task logger
  -> QueueHandler + QueueListener
    -> StatusMessengerHandler
      -> Redis DB 2 pub/sub
        -> services/status2 WebSocket fan-out
          -> controllers_js/status_stream.js + controlBase
            -> panel logs, progress, checklist updates
```

Correlation request tracing and debug workflow: `docs/dev-notes/correlation-id-debugging.md`.

## Repository Development Map

```text
wepppy/
  AGENTS.md                    # Agent + coding conventions (authoritative)
  ARCHITECTURE.md              # This document
  docker/                      # Compose stacks, images, entrypoints
  services/                    # Go + infra services (status2, preflight2, cao, cap)
  tests/                       # pytest suites mirroring source tree
  wctl/                        # Canonical dev/test wrapper commands
  wepppy/
    nodb/                      # Run-state controllers
    rq/                        # Queue tasks + worker
    microservices/             # rq-engine, elevationquery, browse
    query_engine/              # DuckDB analytics API + MCP
    webservices/               # metquery, wmesque2, dtale
    weppcloud/                 # Flask app, routes, templates, controllers_js
```

## Development Boundaries and Contracts

- `AGENTS.md` is the authoritative development contract and workflow guide.
- Update `wepppy/rq/job-dependencies-catalog.md` whenever queue wiring changes.
- Keep `docs/schemas/rq-response-contract.md` aligned with route payload behavior.
- Front-end controller behavior/contract lives in `wepppy/weppcloud/controllers_js/README.md` and `docs/ui-docs/controller-contract.md`.
- Query engine API shape lives in `wepppy/query_engine/docs/mcp_openapi.yaml` and companion docs.

## Baseline Developer Workflow

```bash
# Start development stack
./wctl/wctl.sh up -d

# Python tests
wctl run-pytest tests/<target>

# Front-end quality gates
wctl run-npm lint
wctl run-npm test

# Worker/job diagnostics
wctl logs -f rq-worker
wctl logs -f rq-engine
```

Use `docker/docker-compose.dev.yml` as source-of-truth topology during development.
