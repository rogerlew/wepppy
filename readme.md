wepppy
======

> DevOps focused erosion modeling stack fusing Python orchestration, Rust geospatial kernels, and Redis-first observability.

## Overview
wepppy is the core library behind WEPPcloud, automating Water Erosion Prediction Project (WEPP) runs, wildfire response analytics, and watershed-scale geospatial preprocessing. The codebase glues together legacy Fortran executables, modern Python services, and Rust-accelerated tooling to deliver repeatable, high-throughput simulations for fire, erosion, and hydrology teams.

At the heart of the system is a "NoDb" philosophy: instead of a monolithic database, run state is serialized to disk, memoized in Redis, and surfaced through microservices so every component can inspect, replay, or recover long-lived scenarios with minimal coupling.

## Why Engineers Like It
- Redis-backed NoDb singletons hydrate run state on demand, cache hot JSON payloads, and enforce distributed locks without an RDBMS.
- A queue-driven logging pipeline streams structured status updates from background workers to the browser in milliseconds.
- Heavy geospatial math is offloaded to Rust crates (`wepppyo3`, `peridot`, WhiteboxTools bindings) so Python orchestrates while SIMD cores do the heavy lifting.
- Controllers are bundled from source via an automated Gunicorn hook, keeping the UI and back end in lockstep.
- Everything is wired for DevOps: gunicorn hooks, RQ workers, Tornado microservices, structured logging, and Redis keyspace notifications are treated as first-class infrastructure.

## Architecture at a Glance

Each run lives in a working directory ("wd") seeded by RedisPrep. The Flask layer hands off tasks to Redis Queue (RQ); long-running jobs mutate the NoDb structures and emit telemetry; Tornado apps watch Redis for new signals and stream them to the browser so operators see progress in real time.

## High Performance Scalable Telemetry Pipeline
```text
NoDb subclass logger
  ↓ QueueHandler + QueueListener (async fan-out)
  ↓ StatusMessengerHandler pushes to Redis DB 2 Pub/Sub
  ↓ microservices/status Tornado service
  ↓ WSClient (controllers.js) WebSocket bridge, offloads from flask workers, enables multiple gunicorn workers (unlike Flask-SocketIO)
  ↓ controlBase panels update logs, checklists, charts
```
- `wepppy.nodb.base` wires every NoDb instance with a `QueueHandler`, pushing log records through `StatusMessengerHandler` into Redis channels like `<runid>:wepp`.
- `microservices/status.py` is a Tornado WebSocket proxy that subscribes to the channels and fans out JSON frames to browsers, complete with heartbeat pings and exponential backoff reconnects.
- `controllers_js/ws_client.js` mixes the stream into `controlBase`, so every task panel renders live stdout, RQ job states, and exception traces without page refreshes.

## NoDb Singletons + Redis Caching
- `NoDbBase.getInstance(wd)` guarantees a singleton per working directory. Instances are serialized to disk and mirrored into Redis DB 13 for 72 hours so hot runs rebuild instantly.
- Locking is implemented via Redis hashes in DB 0 (`locked:*.nodb`) to prevent concurrent writers during multi-process jobs. Context managers like `with watershed.locked()` guard critical sections.
- Log verbosity goes through Redis DB 15. Operators can dial runs to DEBUG without touching config files, and every handler respects the remote setting on init.
- `RedisPrep` time-stamps milestones (`timestamps:run_wepp`, `timestamps:abstract_watershed`) and stores RQ job IDs, giving microservices/preflight enough context to render readiness checklists.

## Rust-Powered Geospatial Acceleration
- [`wepppyo3`](https://github.com/wepp-in-the-woods/wepppyo3) exposes Rust bindings for climate interpolation, raster mode lookups, and soil loss grids. Python falls back gracefully when the crate is absent, but production boxes pin the wheel for SIMD speedups.
- Hillslope delineation can be configured to use TOPAZ or a custom tool implmented in Rust [`hillslopes_topaz.rs`](https://github.com/rogerlew/whitebox-tools/blob/master/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.rs). The watershed abstraction is delegated to [`peridot`](https://github.com/wepp-in-the-woods/peridot)
- Raster-heavy routines (NLCD landcover, soils, RAP) all try `wepppyo3.raster_characteristics` first, using Python fallbacks only when the Rust extension is missing.

## Front-End Controls & Build Automation
- Controllers live under `wepppy/weppcloud/controllers_js/` and export singletons (`ControllerName.getInstance()`) so WebSocket connections and DOM bindings are never duplicated.
- `controlBase` centralizes async ergonomics: it disables buttons while jobs run, manages RQ polling, and brokers WebSocket events.
- Gunicorn’s `on_starting` hook runs `build_controllers_js.py`, which Jinja-renders `controllers.js.j2` into a single bundle with an ISO timestamp header. Rebuilds happen on each deploy so the bundle always matches the Python that emits events.
- The HTML surface (`templates/controls/_base.htm`) provides canonical IDs for status panes, letting new controllers inherit the telemetry pipeline without bespoke wiring.

## DevOps Notes
- Redis is mission control. DB 0 tracks run metadata, DB 2 streams status, DB 9 powers RQ, DB 11 stores Flask sessions, DB 13 caches NoDb JSON, DB 14 manages README editor locks, DB 15 holds log levels. See `notes/redis_dev_notes.md` for ops drills.
- The microservices are lightweight Tornado apps (`microservices/preflight.py`, `microservices/status.py`) that boot via systemd or the dev scripts under `_scripts/`. They require Redis keyspace notifications (`notify-keyspace-events Kh`) for preflight streaming.
- Workers scale horizontally. `wepppy/rq/*.py` modules provide CLI entry points, while `wepppy/weppcloud/routes/rq/api` exposes REST endpoints for job orchestration, cancellation, and status polling.
- Structured logging is collected per run in the working directory (`<runid>/_logs/`). The queue handler replicates to console, file, and Redis so you get local artifacts plus live dashboards.

## Getting Started (developer edition)
1. Provision Python 3.10 + Poetry/conda (see `install/` and `wepppy/weppcloud/_baremetal/` for reference scripts).

For deployment, see the gunicorn config (`wepppy/weppcloud/gunicorn.conf.py`), the systemd snippets under `_scripts/`, and the BareMetal notes for Ubuntu 24.04 provisioning.

## Further Reading
- `notes/redis_dev_notes.md` — deep dive into Redis usage, DB allocations, and debugging recipes.
- `notes/controllers_js.md` — controller bundling, singleton contracts, and WS client expectations.
- `wepppy/nodb/base.py` — the canonical NoDb implementation with logging, caching, and locking primitives.
- `wepppy/topo/peridot/runner.py` — how Rust binaries integrate with WEPP abstractions.

## Credits
University of Idaho 2015-Present, Swansea University 2019-Present (Wildfire Ash Transport And Risk estimation tool, WATAR).

Contributors: Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frakenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller.

License: BSD-3 Clause (see `license.txt`).
