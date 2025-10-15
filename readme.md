wepppy
======

> DevOps focused erosion modeling stack fusing Python orchestration, Rust geospatial kernels, and Redis-first observability.

## Overview
wepppy is the core library behind WEPPcloud, automating Water Erosion Prediction Project (WEPP) runs, wildfire response analytics, and watershed-scale geospatial preprocessing. The codebase glues together legacy Fortran executables, modern Python services, and Rust-accelerated tooling to deliver repeatable, high-throughput simulations for fire, erosion, and hydrology teams.

At the heart of the system is a "NoDb" philosophy: instead of a monolithic database, run state is serialized to disk, memoized in Redis, and surfaced through microservices so every component can inspect, replay, or recover long-lived scenarios with minimal coupling.

## Nerdy Highlights
- Redis-backed NoDb singletons hydrate run state on demand, cache hot JSON payloads, and enforce distributed locks without an RDBMS.
- A queue-driven logging pipeline streams structured status updates from background workers to the browser in milliseconds.
- Heavy geospatial math is offloaded to Rust crates (`wepppyo3`, `peridot`, WhiteboxTools bindings) so Python orchestrates while SIMD cores do the heavy lifting.
- Controllers are bundled from source via an automated Gunicorn hook, keeping the UI and back end in lockstep.
- Everything is wired for DevOps: gunicorn hooks, RQ workers, Go microservices (`preflight2`, `status2`), structured logging, and Redis keyspace notifications are treated as first-class infrastructure.

## Architecture at a Glance

Each run lives in a working directory ("wd") seeded by RedisPrep. The Flask layer hands off tasks to Redis Queue (RQ); long-running jobs mutate the NoDb structures and emit telemetry; Go microservices watch Redis for new signals and stream them to the browser so operators see progress in real time.

## High Performance Scalable Telemetry Pipeline
```text
NoDb subclass logger
  ↓ QueueHandler + QueueListener (async fan-out)
  ↓ StatusMessengerHandler pushes to Redis DB 2 Pub/Sub
  ↓ services/status2 Go WebSocket service
  ↓ WSClient (controllers.js) WebSocket bridge, offloads from flask workers, enables multiple gunicorn workers (unlike Flask-SocketIO)
  ↓ controlBase panels update logs, checklists, charts
```
- `wepppy.nodb.base` wires every NoDb instance with a `QueueHandler`, pushing log records through `StatusMessengerHandler` into Redis channels like `<runid>:wepp`.
- `services/status2` is a Go WebSocket proxy that subscribes to the channels and fans out JSON frames to browsers, complete with heartbeat pings and exponential backoff reconnects.
- `controllers_js/ws_client.js` mixes the stream into `controlBase`, so every task panel renders live stdout, RQ job states, and exception traces without page refreshes.

## NoDb Singletons + Redis Caching
- `NoDbBase.getInstance(wd)` guarantees a singleton per working directory. Instances are serialized to disk and mirrored into Redis DB 13 for 72 hours so hot runs rebuild instantly.
- Locking is implemented via Redis hashes in DB 0 (`locked:*.nodb`) to prevent concurrent writers during multi-process jobs. Context managers like `with watershed.locked()` guard critical sections.
- Log verbosity goes through Redis DB 15. Operators can dial runs to DEBUG without touching config files, and every handler respects the remote setting on init.
- `RedisPrep` time-stamps milestones (`timestamps:run_wepp_watershed`, `timestamps:abstract_watershed`) and stores RQ job IDs, giving `preflight2` enough context to render readiness checklists.

## NoDb Module Exports & Legacy Imports
- Every NoDb controller module now declares an explicit `__all__` that captures the public surface (the primary `NoDbBase` subclass, its companion enums/exceptions, and any helper utilities used outside the module). When you add new public functions or classes, update the module’s `__all__` immediately.
- Package aggregators (`wepppy.nodb.core`, `wepppy.nodb.mods`) build their own `__all__` from the per-module lists, keeping the top-level namespace tidy while preserving ergonomic imports such as `from wepppy.nodb.core import Wepp` or `from wepppy.nodb.mods import Disturbed`.
- The `__getattr__` hook in `wepppy.nodb.mods` lazily imports mod packages. This keeps fresh projects fast to hydrate and allows optional dependencies (e.g. `geopandas`, `utm`) to remain truly optional until the mod is touched.
- Legacy `.nodb` payloads still deserialize because `wepppy.nodb.base` builds `_LEGACY_MODULE_REDIRECTS` by walking the package tree and binding old module paths (for example `wepppy.nodb.wepp`) to their new homes (`wepppy.nodb.core.wepp`). The `NoDbBase._ensure_legacy_module_imports()` hook loads those modules on demand before jsonpickle decodes.
- If a refactor moves or renames a module, update the redirect map by ensuring the file still lives under `wepppy/nodb/` (the scanner picks up new paths automatically). For one-off overrides, call `NoDbBase._import_mod_module('mod_name')` to pre-load the replacement prior to deserialization.
- Best practice: keep module-level side effects lightweight, prefer absolute imports (`from wepppy.nodb.core.climate import Climate`), and treat anything underscored as private so it stays out of `__all__`.

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
- Redis is mission control. DB 0 tracks run metadata, DB 2 streams status, DB 9 powers RQ, DB 11 stores Flask sessions, DB 13 caches NoDb JSON, DB 14 manages README editor locks, DB 15 holds log levels. See `wepppy/weppcloud/routes/usersum/dev-notes/redis_dev_notes.md` for ops drills.
- Coding conventions live in `wepppy/weppcloud/routes/usersum/dev-notes/style-guide.md`; skim it before touching batch runners, NoDb modules, or microservices.
- The microservices are lightweight Go services (`services/preflight2`, `services/status2`) that boot via systemd or the dev scripts under `_scripts/`. They require Redis keyspace notifications (`notify-keyspace-events Kh`) for preflight streaming.
- Workers scale horizontally. `wepppy/rq/*.py` modules provide CLI entry points, while `wepppy/weppcloud/routes/rq/api` exposes REST endpoints for job orchestration, cancellation, and status polling.
- Structured logging is collected per run in the working directory (`<runid>/_logs/`). The queue handler replicates to console, file, and Redis so you get local artifacts plus live dashboards.

## Docker Compose Dev Stack (Recommended)
The repository ships with a multi-container development stack (`docker/docker-compose.dev.yml`) that mirrors the production topology: Flask (`weppcloud`), Go microservices (`status`, `preflight`), the Starlette browse service, Redis, PostgreSQL, an RQ worker pool, and a Caddy reverse proxy that fronts the entire bundle (and now serves `/weppcloud/static/*` directly). The dev image is built from `docker/Dockerfile.dev` so all repos under `/workdir` stay bind-mounted for instant reloads.

> docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up -d


### Quick start
```bash
# 1. Set the UID/GID you want the containers to use (defaults to 1000:1000).
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
SECURITY_PASSWORD_SALT=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
cat > docker/.env <<EOF
UID=$(id -u)          # customise as needed
GID=$(id -g)
POSTGRES_PASSWORD=localdev
SECRET_KEY=$SECRET_KEY
SECURITY_PASSWORD_SALT=$SECURITY_PASSWORD_SALT
EOF

# 2. Bring up the stack.
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build

# 3. Visit http://localhost:8080/weppcloud once the services report "ready".
```

By default the containers inherit your host UID/GID so any files written to the bind mounts stay editable from the host. To run everything as a service account such as `www-data:webgroup`, set those ids explicitly in `docker/.env`:

```env
UID=33            # www-data
GID=993           # output of `getent group docker | cut -d: -f3`
```

Make sure the group exists locally; Compose passes numeric ids straight through, so the host must recognise them to keep permissions tidy.

### Common tasks
- **Tail the main app logs**: `docker compose -f docker/docker-compose.dev.yml logs -f weppcloud`
- **Open a shell in the app container**: `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml exec weppcloud bash`
- **Reset a single service**: `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build weppcloud`
- **View static assets**: Caddy proxies `/weppcloud/static/*` from the repository mount; updates to `wepppy/weppcloud/static` land immediately without hitting Gunicorn.

## Docker Compose Production Stack
`docker/docker-compose.prod.yml` builds the production image (`docker/Dockerfile`) that vendors all Python dependencies, cloned sibling repositories, and `.pth` shims directly into the container. The compose file keeps bind mounts to a minimum (only data volumes for WC1/GeoData, Redis, and Postgres), sets `restart: unless-stopped`, and exposes only the required ports so the stack can drop behind a reverse proxy or a Kubernetes ingress later.

```bash
# Build the production image (tags as wepppy:latest by default)
docker compose -f docker/docker-compose.prod.yml build weppcloud

# Launch the full stack
docker compose -f docker/docker-compose.prod.yml up -d

# Override the published image/tag when deploying from CI
WEPPCLOUD_IMAGE=registry.example.com/wepppy:2025.02 docker compose -f docker/docker-compose.prod.yml up -d weppcloud
```

- The `.env` file in `docker/` continues to feed secrets and connection strings; update it (or set environment variables) before building so the values bake into the image metadata.
- WC1/GeoData are mounted as named volumes (`wc1-data`, `geodata-data`) by default. Swap them for bind mounts or CSI-backed volumes in Kubernetes as needed.
- Health checks (`/health`) gate container readiness. For Kubernetes, reuse the same endpoint for your liveness/readiness probes.
- The production image runs as the non-root `wepp` user (UID/GID configurable via build args) to satisfy PodSecurity/OCI hardening requirements.

## Baremetal (not recommended)
- Provision Python 3.10 + Poetry/conda (see `install/` and `wepppy/weppcloud/_baremetal/` for reference scripts).
- For deployment, see the gunicorn config (`wepppy/weppcloud/gunicorn.conf.py`), the systemd snippets under `_scripts/`, and the BareMetal notes for Ubuntu 24.04 provisioning.

## Further Reading
- `wepppy/weppcloud/routes/usersum/dev-notes/redis_dev_notes.md` — deep dive into Redis usage, DB allocations, and debugging recipes.
- `wepppy/weppcloud/routes/usersum/dev-notes/controllers_js.md` — controller bundling, singleton contracts, and WS client expectations.
- `wepppy/nodb/base.py` — the canonical NoDb implementation with logging, caching, and locking primitives.
- `wepppy/topo/peridot/runner.py` — how Rust binaries integrate with WEPP abstractions.

## Credits
University of Idaho 2015-Present, Swansea University 2019-Present (Wildfire Ash Transport And Risk estimation tool, WATAR).

Contributors: Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frakenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller.

License: BSD-3 Clause (see `license.txt`).
