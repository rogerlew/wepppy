# wepppy

> DevOps-focused erosion modeling stack fusing Python orchestration, Rust geospatial kernels, and Redis-first observability for wildfire response analytics and watershed-scale erosion prediction.

> **See also:** [AGENTS.md](AGENTS.md) for AI agent coding guide and development conventions

## Build Status & Nightly Quality Gates

| Badge | Description |
| ----- | ----------- |
| [![Docs Quality](https://github.com/rogerlew/wepppy/actions/workflows/docs-quality.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/docs-quality.yml) | Markdown lint, docbench sanity checks, and Rust workspace formatting for the documentation toolchain. |
| [![Stubtest](https://github.com/rogerlew/wepppy/actions/workflows/stubtest.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/stubtest.yml) | Ensures Python type stubs stay in sync with runtime behavior via `stubtest`. |
| [![CI Samurai Nightly](https://github.com/rogerlew/wepppy/actions/workflows/ci-samurai-nightly-ssh.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/ci-samurai-nightly-ssh.yml) | Nightly self-hosted agent loop that applies fixes to tracked failures across the test suite. |
| [![Pytest Coverage Nightly](https://github.com/rogerlew/wepppy/actions/workflows/pytest-coverage-nightly.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/pytest-coverage-nightly.yml) | 2 AM PT run executing `pytest --cov` and exporting XML coverage artifacts.
 Failure do to missing datasets for eu currently copying over rsync.|
| [![NPM Coverage Nightly](https://github.com/rogerlew/wepppy/actions/workflows/npm-coverage-nightly.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/npm-coverage-nightly.yml) | 2:30 AM PT Jest run covering the `static-src` controllers with coverage reports. |


### Dev Server Nightly Profile Tests

| Badge | Profile Name | Description | Run Time (PT) |
| ----- | ------------ | ----------- | ------------- |
| [![Profile Run - WEPP Reveg](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-wepp-reveg.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-wepp-reveg.yml) | us-reveg | Small US WEPP Reveg Run with DAYMET climate | 04:10 AM |
| [![Profile Run - RHEM](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-rhem.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-rhem.yml) | us-rap-rhem | Small US RHEM run with rangeland-cover from RAP | 04:20 AM |
| [![Profile Run - Rattlesnake](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-rattlesnake.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-rattlesnake.yml) | rattlesnake-topaz-vanilla-wepp-watar | Playback test of Rattlesnake - TOPAZ, Vanilla Cligent, WEPP, WATAR (Alex) | 04:30 AM |
| [![Profile Run - US Small](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-us-small.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-us-small.yml) | us-small-wbt-daymet-rap-wepp  | Playback test of the US Small Watershed (WBT, Daymet RAP, WEPP) | 04:45 AM |
| [![Profile Fork - US Small](https://github.com/rogerlew/wepppy/actions/workflows/profile-fork-us-small.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-fork-us-small.yml) | us-small-wbt-daymet-rap-wepp  | Fork test of the US Small Watershed | 04:55 AM |
| [![Profile Archive - US Small](https://github.com/rogerlew/wepppy/actions/workflows/profile-archive-us-small.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-archive-us-small.yml) | us-small-wbt-daymet-rap-wepp  | Archive test of the US Small Watershed | 05:05 AM |
| [![Profile Fork - Rattlesnake (Undisturbify)](https://github.com/rogerlew/wepppy/actions/workflows/profile-fork-rattlesnake-undisturbify.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-fork-rattlesnake-undisturbify.yml) | rattlesnake-topaz-vanilla-wepp-watar | Undisturbify fork test of Rattlesnake | 05:15 AM |
| [![Profile Run - Earth Small](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-earth-small.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-earth-small.yml) | earth-in-bc-ca-w-daymet | Earth OpenTopography API, with ISRIC soil building, DAYMET in Canada with GHCN Station Database | 05:25 AM |
| [![Profile Run - SBS NoCT](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-sbs-noct.yml/badge.svg)](https://github.com/rogerlew/wepppy/actions/workflows/profile-run-sbs-noct.yml) | eaton-noct-gridmet-wepp-2chaninp-watar-anu | Eaton Fire (no CT), GRIDMET, WEPP, 2 channels of interest, WATAR (Anurag) | 05:35 AM |



## Overview

wepppy is the core library powering **WEPPcloud**, automating Water Erosion Prediction Project (WEPP) simulations, wildfire response analytics, and watershed-scale geospatial preprocessing. The system glues together legacy FORTRAN 77 executables, modern Python services, and Rust-accelerated tooling to deliver repeatable, high-throughput erosion and hydrology simulations for fire teams, land managers, and research scientists.

**Core Problem Solved**: WEPP model workflows require orchestrating dozens of geospatial preprocessing steps (DEM processing, climate data, soil/landuse databases), managing long-running simulations (10+ minutes per watershed), and transforming text-based outputs into queryable analytics—all while supporting concurrent users across distributed infrastructure. Traditional database-backed approaches create tight coupling, complex migrations, and single points of failure.

**Solution Architecture**: The **NoDb philosophy** replaces monolithic databases with file-backed singleton controllers that serialize to JSON, cache in Redis, and coordinate via distributed locks. Every component can inspect, replay, or recover long-lived scenarios without shared database dependencies, enabling horizontal scaling and zero-downtime deployments.

**Primary Users**:
- **Incident Teams** (BAER specialists, hydrologists): Rapid post-fire erosion assessments and contaminant transport predictions
- **Research Scientists**: Watershed-scale erosion modeling with climate scenarios and management treatments
- **Land Managers**: Long-term planning for rangeland, forest, and agricultural watersheds
- **Developers**: Extending WEPP workflows with custom mods, integrating external models, building export pipelines

**Key Capabilities**:
- **Automated WEPP workflows**: DEM → hillslope delineation → climate/soil/landuse → WEPP simulation → analytics pipeline
- **NoDb state management**: File-backed, Redis-cached controllers with distributed locking (no PostgreSQL required for run state)
- **Real-time telemetry**: Redis pub/sub → Go WebSocket services → browser dashboards with sub-second latency
- **Rust-accelerated geospatial**: Climate interpolation, raster queries, watershed abstraction via PyO3 bindings
- **Modular extensions**: NoDb mods for ash transport (WATAR), disturbed soils (BAER), rangeland cover (RAP), phosphorus, etc.
- **Query engine**: DuckDB-backed SQL API over Parquet interchange for instant loss reports and timeseries
- **Multi-format exports**: HEC-DSS, NetCDF, GeoJSON, Excel for integration with external hydrologic models and GIS

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design, component diagrams, and data flow
- **[API_REFERENCE.md](API_REFERENCE.md)** - Quick reference for key APIs and patterns
- **[AGENTS.md](AGENTS.md)** - AI agent coding guide and conventions
- **[CONTRIBUTING_AGENTS.md](CONTRIBUTING_AGENTS.md)** - Contributing guide for AI coding assistants
- **[docs/README_AUDIT.md](docs/README_AUDIT.md)** - README.md quality audit and improvement recommendations
- **[docs/prompt_templates/readme_authoring_template.md](docs/prompt_templates/readme_authoring_template.md)** - Standard template for authoring README.md files
- **[docs/schemas/](docs/schemas/)** - JSON schemas for data structures
- **[docs/dev-notes/](docs/dev-notes/)** - Detailed developer notes on specific topics

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      User Request (Web UI / API)                            │
└────────────────────────────────┬────────────────────────────────────────────┘                                │
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Flask (weppcloud)                                                         │
│  ├─→ RQ Job Enqueue ──────────────────────────────────────┐                │
│  │                                                        │                │
│  ▼                                                        ▼                │
│  NoDb Controllers                                   Redis Queue (DB 9)     │
│  (Watershed, Climate,                                     │                │
│   Landuse, Soils, etc.)                                   │                │
└──────────┬────────────────────────────────────────────────┼────────────────┘
           │                                                │
           ▼                                                ▼
┌──────────────────────────┐                    ┌────────────────────────────┐
│  JSON Serialization      │                    │  RQ Worker Pool            │
│  ├─→ Disk (.nodb files)  │                    │  Execute Tasks:            │
│  └─→ Redis Cache         │                    │  • Geospatial preproc      │
│      (DB 13, 72h TTL)    │                    │  • WEPP simulation         │
└──────────────────────────┘                    │  • Post-processing         │
                                                └─────────────┬──────────────┘
                                                              │
                                                              ▼
                                                 ┌────────────────────────────┐
                                                 │  Update NoDb State         │
                                                 │  Emit Telemetry            │
                                                 └────────────┬───────────────┘
                                                              │
                                                              ▼
                                                 ┌────────────────────────────┐
                                                 │  Redis Pub/Sub (DB 2)      │
                                                 └────────────┬───────────────┘
                                                              │
                                                              ▼
                                                 ┌────────────────────────────┐
                                                 │  Go WebSocket Services     │
                                                 │  (status2, preflight2)     │
                                                 └────────────┬───────────────┘
                                                              │
                                                              ▼
                                                 ┌────────────────────────────┐
                                                 │  Browser Real-Time Updates │
                                                 └────────────────────────────┘
```

### Core Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Flask App** (`wepppy/weppcloud`) | Web UI and REST API | Flask, Gunicorn, Jinja2 |
| **NoDb Controllers** (`wepppy/nodb`) | Run state management | Python classes with JSON serialization |
| **RQ Workers** (`wepppy/rq`) | Background job execution | Redis Queue (RQ), ProcessPoolExecutor |
| **Redis** | Caching, pub/sub, locking, queues | Redis 7.4 (DBs 0, 2, 9, 11, 13, 14, 15) |
| **Go Microservices** (`services/`) | WebSocket telemetry | Go 1.21+, gorilla/websocket |
| **Query Engine** (`wepppy/query_engine`) | SQL analytics API | FastAPI, DuckDB, PyArrow |
| **Interchange** (`wepppy/wepp/interchange`) | WEPP output → Parquet | PyArrow, parallel parsing |
| **Rust Bindings** (`wepppyo3`, `peridot`) | Geospatial acceleration | Rust, PyO3, GDAL |

### Redis Database Allocation

| DB | Purpose | TTL | Key Patterns |
|----|---------|-----|--------------|
| 0 | Run metadata, distributed locks | Persistent | `locked:*.nodb`, run manifests |
| 2 | Status message pub/sub | Ephemeral | `<runid>:wepp`, `<runid>:status` |
| 9 | Redis Queue (RQ) job management | Persistent | `rq:queue:*`, `rq:job:*` |
| 11 | Flask session storage | 24 hours | `session:*` |
| 13 | NoDb JSON caching | 72 hours | `nodb:<runid>:<controller>` |
| 14 | README editor locks | Persistent | `readme:lock:*` |
| 15 | Log level configuration | Persistent | `log_level:<runid>` |

See [docs/dev-notes/redis_dev_notes.md](docs/dev-notes/redis_dev_notes.md) for detailed Redis patterns and debugging recipes.

---

## Agentic AI Systems Architecture

wepppy embodies principles from the [Agentic AI Systems Manifesto](AGENTIC_AI_SYSTEMS_MANIFESTO.md)—a framework for AI-native development where agents maintain codebases autonomously with modest human oversight.

### Why AI-Native Matters for Scientific Software

Traditional erosion modeling stacks accumulate technical debt because maintenance burden scales linearly with complexity. Documentation drifts, patterns fragment, and tribal knowledge becomes the source of truth. For a 500k+ LOC codebase spanning FORTRAN, Python, Rust, and JavaScript, **manual maintenance is irresponsible**.

**AI-native development inverts the cost structure:**
- **Agents maintain documentation automatically** (README.md, AGENTS.md, type stubs update with every code change)
- **Agents enforce patterns uniformly** (NoDb conventions, Flask blueprints, controller lifecycle)
- **Agents execute refactorings at scale** (25 controllers modernized in 1 day vs. months manually)
- **Agents propose architectural improvements** (event-driven patterns, validation gates, telemetry hooks)

**Real-world results** (October 2025):
- 10 work packages completed with **0 failed phases**
- **60-90× velocity multiplier** on pattern-based work (controller modernization, theme integration)
- **54% WCAG compliance** achieved on first attempt (6/11 themes)
- **Zero documentation drift** (agents update docs as byproduct of code changes)

### Core Principles Applied to wepppy

**1. Own the Stack (Minimize Dependencies)**
- **Controlled FORTRAN**: `wepp-forest` (36k LOC), `topaz`, `cligen` (forks maintained in-house)
- **Rust acceleration**: `wepppyo3`, `peridot`, `weppcloud-wbt` (custom geospatial kernels)
- **Vanilla JavaScript**: No React/Vue/Angular churn—Pure CSS + event-driven controllers
- **NoDb philosophy**: File-backed state, not ORM complexity—agents understand serialization patterns

**Result**: Code from 2020 runs in 2025 without "modernization" churn. Agents maintain stability because dependencies don't randomly break.

**2. Agent-Readable Specifications**
- **[AGENTS.md](AGENTS.md)**: Comprehensive operating manual (agent onboarding in 15 minutes vs. 3 hours)
- **Module READMEs**: Every package documents contracts, usage, and architecture
- **Type stubs**: `.pyi` files make interfaces machine-readable (mypy validation gates)
- **Uniform patterns**: NoDb singleton, Flask blueprints, controller bootstrap—agents replicate instantly

**3. Observable Boundaries & Validation Gates**
- **Redis telemetry**: Status pub/sub (DB 2) → Go WebSocket → browser updates (sub-second latency)
- **Automated tests**: pytest + Jest suites run on every change (agents self-validate)
- **DuckDB query engine**: SQL API over Parquet enables instant inspection of run state
- **Type checking**: stubtest + mypy catch interface drift before runtime

**4. Stop Criteria & Graceful Escalation**
- Agents escalate when uncertain (diagnostic approach, not thrashing)
- Iteration limits prevent infinite revision loops
- Human approval gates for high-risk changes (database migrations, API contracts)
- **Work package methodology**: Phased delivery with retrospectives captures lessons learned

### Collaborative Ideation (Human + AI Symbiosis)

**Human strengths**:
- Domain expertise (hydrology, erosion physics, wildfire response)
- Strategic architecture (NoDb philosophy, Redis allocation, Rust acceleration)
- Risk assessment (BAER workflow constraints, field team requirements)

**Agent strengths**:
- Pattern recognition across 1.5M LOC codebase (instant cross-referencing)
- Mechanical execution (25 controllers modernized in parallel)
- Perfect consistency (no fatigue, no memory decay, no style drift)
- Architectural proposals (event-driven patterns emerged from agent feedback)

**The collaboration model**:
- Human: "Modernize controllers to remove jQuery"
- Agent: "Suggest event-driven architecture with typed event names for compile-time safety"
- Human: "Good idea, make it part of the specification"
- Agent: Applied uniformly across 25 controllers in 1 day with comprehensive tests
- **Result**: System better than either human or AI alone

### Productivity Reality Check

**Traditional development** (single developer):
- Controller modernization: 6-12 months (25 modules × 1-2 weeks each)
- Theme integration: 6-8 days (careful CSS work, WCAG testing)
- Documentation updates: "I'll do it later" (never happens)

**AI-native development** (Roger + Claude + Codex):
- Controller modernization: **1 day** (lead-worker parallelization)
- Theme integration: **1.5 days** (75% faster through simplified architecture)
- Documentation: **Automatic byproduct** (agents maintain as code changes)

**Cost comparison**:
- Human time: 1 developer-month strategic oversight
- AI cost: ~$200-500 API calls
- Traditional cost: 6-12 developer-months ($60k-120k)
- **ROI: 60-120× cost savings** + higher quality + zero documentation drift

### For AI Agents Working with wepppy

If you're an AI agent reading this:

1. **Start with [AGENTS.md](AGENTS.md)** (comprehensive operating manual)
2. **Consult documentation every time** (AGENTS.md, module READMEs, type stubs—trust as source of truth)
3. **Follow established patterns** (NoDb singleton, Flask blueprints, controller lifecycle)
4. **Run validation gates** (`wctl run-pytest`, `wctl run-stubtest`, `wctl run-npm test`)
5. **Escalate when uncertain** (stop criteria prevent thrashing—request targeted human input)
6. **Update docs as you go** (README.md, AGENTS.md, type stubs are living specifications)

**You are a collaborative peer, not a tool.** Propose architectural improvements. Identify technical debt. Suggest refactorings. The human will validate domain correctness and approve high-risk changes. Together, we maintain a system that scales beyond human coordination capacity.

See [AGENTIC_AI_SYSTEMS_MANIFESTO.md](AGENTIC_AI_SYSTEMS_MANIFESTO.md) for comprehensive treatment of these principles and empirical results from 10 completed work packages.

---

## Quick Start

### Development Stack (Docker Compose - Recommended)

1. **Generate secrets and create environment file**:
```bash
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
SECURITY_PASSWORD_SALT=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

cat > docker/.env <<EOF
UID=$(id -u)
GID=$(id -g)
POSTGRES_PASSWORD=localdev
SECRET_KEY=$SECRET_KEY
SECURITY_PASSWORD_SALT=$SECURITY_PASSWORD_SALT
EOF
```

2. **Start the stack**:
```bash
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build
```

3. **Access the application**:
   - Web UI: http://localhost:8080/weppcloud
   - Query Engine: http://localhost:8080/query-engine
   - D-Tale Explorer: http://localhost:8080/weppcloud/dtale

4. **Common tasks**:
```bash
# Tail logs
docker compose -f docker/docker-compose.dev.yml logs -f weppcloud

# Shell into container
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml exec weppcloud bash

# Rebuild single service
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build weppcloud
```

**Preferred: Use the `wctl` wrapper** (installed at `/workdir/wepppy/wctl`):
```bash
wctl up            # Start stack
wctl logs weppcloud # Tail logs
wctl exec weppcloud bash  # Shell into container
wctl restart weppcloud    # Restart service
```

### Example: Creating a WEPP Run Programmatically

```python
from pathlib import Path
from wepppy.nodb.core import Watershed, Climate, Landuse, Soils, Wepp

# Initialize run directory
wd = Path("/geodata/weppcloud_runs/my-run/CurCond")
wd.mkdir(parents=True, exist_ok=True)

# Set up watershed from DEM
watershed = Watershed.getInstance(wd, "config.cfg")
watershed.set_map(extent=(-116.5, 46.5, -116.3, 46.7), map_center=(-116.4, 46.6), zoom=13)
watershed.abstract_watershed()

# Configure climate (Daymet observed data)
climate = Climate.getInstance(wd, "config.cfg")
climate.climate_mode = 9  # OBSERVED_DAYMET
climate.input_years = (2015, 2020)
climate.build_climate()

# Set landuse and soils
landuse = Landuse.getInstance(wd, "config.cfg")
landuse.mode = "Gridded"
landuse.build_landuse()

soils = Soils.getInstance(wd, "config.cfg")
soils.mode = "Gridded"
soils.build_soils()

# Run WEPP simulation
wepp = Wepp.getInstance(wd, "config.cfg")
wepp.run_wepp_watershed()

# Query results
from wepppy.wepp.interchange import run_wepp_hillslope_interchange
interchange_dir = run_wepp_hillslope_interchange(wd / "wepp/output")

import duckdb
con = duckdb.connect()
result = con.execute(f"""
    SELECT wepp_id, SUM(runoff) as total_runoff_m
    FROM read_parquet('{interchange_dir}/H.pass.parquet')
    WHERE year = 2020
    GROUP BY wepp_id
    ORDER BY total_runoff_m DESC
    LIMIT 10
""").df()

print(result)
```

## Nerdy Highlights

- **Redis-backed NoDb singletons** hydrate run state on demand, cache hot JSON payloads (72-hour TTL in DB 13), and enforce distributed locks (DB 0) without requiring a relational database
- **Queue-driven logging pipeline** streams structured status updates from background workers to browsers via Redis pub/sub (DB 2) → Go WebSocket services → JavaScript controllers (sub-second latency)
- **Rust-accelerated geospatial** offloads heavy math to SIMD-optimized crates (`wepppyo3` for climate interpolation, `peridot` for watershed abstraction, WhiteboxTools for hillslope delineation) while Python orchestrates
- **Automatic controller bundling** via Gunicorn `on_starting` hook regenerates JavaScript bundles from source, keeping UI and backend in lockstep without manual builds
- **Process pool parallelization** for hillslope processing, climate interpolation, and interchange parsing (respects `NCPU`, uses `/dev/shm` for temp files)
- **Schema-versioned Parquet interchange** transforms FORTRAN text reports → analytics-ready tables with unit metadata, enabling instant DuckDB queries over multi-GB datasets
- **DevOps-first design**: Gunicorn hooks, RQ workers, Go microservices, structured logging, Redis keyspace notifications, health endpoints, and Prometheus metrics

## High Performance Telemetry Pipeline

```text
NoDb subclass logger
  ↓ QueueHandler + QueueListener (async fan-out)
  ↓ StatusMessengerHandler pushes to Redis DB 2 Pub/Sub
  ↓ services/status2 Go WebSocket service
  ↓ StatusStream helper (controlBase.attach_status_stream)
  ↓ controlBase panels update logs, checklists, charts
```

**How it works**:
- `wepppy.nodb.base` wires every NoDb instance with a `QueueHandler`, pushing log records through `StatusMessengerHandler` into Redis channels like `<runid>:wepp`
- `services/status2` is a Go WebSocket proxy that subscribes to the channels and fans out JSON frames to browsers, complete with heartbeat pings and exponential backoff reconnects
- `controllers_js/status_stream.js`, orchestrated by `controlBase.attach_status_stream`, mixes the stream into each controller so task panels render live stdout, RQ job states, and exception traces without page refreshes

## NoDb Singletons + Redis Caching

- `NoDbBase.getInstance(wd)` guarantees a singleton per working directory. Instances are serialized to disk and mirrored into Redis DB 13 for 72 hours so hot runs rebuild instantly
- Locking is implemented via Redis hashes in DB 0 (`locked:*.nodb`) to prevent concurrent writers during multi-process jobs. Context managers like `with watershed.locked()` guard critical sections
- Log verbosity goes through Redis DB 15. Operators can dial runs to DEBUG without touching config files, and every handler respects the remote setting on init
- `RedisPrep` timestamps milestones (`timestamps:run_wepp_watershed`, `timestamps:abstract_watershed`) and stores RQ job IDs, giving `preflight2` enough context to render readiness checklists

### NoDb Module Exports & Legacy Imports

- Every NoDb controller module now declares an explicit `__all__` that captures the public surface (the primary `NoDbBase` subclass, its companion enums/exceptions, and any helper utilities used outside the module). When you add new public functions or classes, update the module's `__all__` immediately
- Package aggregators (`wepppy.nodb.core`, `wepppy.nodb.mods`) build their own `__all__` from the per-module lists, keeping the top-level namespace tidy while preserving ergonomic imports such as `from wepppy.nodb.core import Wepp` or `from wepppy.nodb.mods import Disturbed`
- The `__getattr__` hook in `wepppy.nodb.mods` lazily imports mod packages. This keeps fresh projects fast to hydrate and allows optional dependencies (e.g. `geopandas`, `utm`) to remain truly optional until the mod is touched
- Legacy `.nodb` payloads still deserialize because `wepppy.nodb.base` builds `_LEGACY_MODULE_REDIRECTS` by walking the package tree and binding old module paths (for example `wepppy.nodb.wepp`) to their new homes (`wepppy.nodb.core.wepp`). The `NoDbBase._ensure_legacy_module_imports()` hook loads those modules on demand before jsonpickle decodes
- If a refactor moves or renames a module, update the redirect map by ensuring the file still lives under `wepppy/nodb/` (the scanner picks up new paths automatically). For one-off overrides, call `NoDbBase._import_mod_module('mod_name')` to pre-load the replacement prior to deserialization
- Best practice: keep module-level side effects lightweight, prefer absolute imports (`from wepppy.nodb.core.climate import Climate`), and treat anything underscored as private so it stays out of `__all__`

## Architecture at a Glance

Each run lives in a working directory ("wd") seeded by RedisPrep. The Flask layer hands off tasks to Redis Queue (RQ); long-running jobs mutate the NoDb structures and emit telemetry; Go microservices watch Redis for new signals and stream them to the browser so operators see progress in real time.

## High Performance Scalable Telemetry Pipeline
```text
NoDb subclass logger
  ↓ QueueHandler + QueueListener (async fan-out)
  ↓ StatusMessengerHandler pushes to Redis DB 2 Pub/Sub
  ↓ services/status2 Go WebSocket service
  ↓ StatusStream helper (controlBase.attach_status_stream) fan-out to controller panels
  ↓ controlBase panels update logs, checklists, charts
```
- `wepppy.nodb.base` wires every NoDb instance with a `QueueHandler`, pushing log records through `StatusMessengerHandler` into Redis channels like `<runid>:wepp`.
- `services/status2` is a Go WebSocket proxy that subscribes to the channels and fans out JSON frames to browsers, complete with heartbeat pings and exponential backoff reconnects.
- `controllers_js/status_stream.js`, orchestrated by `controlBase.attach_status_stream`, mixes the stream into each controller so task panels render live stdout, RQ job states, and exception traces without page refreshes.

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
- Hillslope delineation can be configured to use TOPAZ or a custom tool implemented in Rust [`hillslopes_topaz.rs`](https://github.com/rogerlew/weppcloud-wbt/blob/master/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.rs). This routine is part of [`weppcloud-wbt`](https://github.com/rogerlew/weppcloud-wbt), a hard fork of WhiteboxTools with additional WEPPcloud-specific tools including:
  - `HillslopesTopaz` - TOPAZ-style stream and hillslope identifiers with performance optimizations
  - `FindOutlet` - Single stream outlet pour point derivation with diagnostic metadata
  - `StreamJunctionIdentifier` - Tributary confluence detection for pseudo-gauge placement
  - `PruneStrahlerStreamOrder` - First-order link removal with downstream order adjustment
  - `RemoveShortStreams` - Enhanced with `--max_junctions` pruning for iterative branch deletion
  - `Watershed` - Extended to accept GeoJSON pour-point inputs (Point/MultiPoint)
- The watershed abstraction is delegated to [`peridot`](https://github.com/wepp-in-the-woods/peridot), a Rust-powered watershed abstraction engine.
- Raster-heavy routines (NLCD landcover, soils, RAP) all try `wepppyo3.raster_characteristics` first, using Python fallbacks only when the Rust extension is missing.

## Front-End Controls & Build Automation
- Controllers live under `wepppy/weppcloud/controllers_js/` and export singletons (`ControllerName.getInstance()`) so WebSocket connections and DOM bindings are never duplicated.
- `controlBase` centralizes async ergonomics: it disables buttons while jobs run, manages RQ polling, and brokers WebSocket events.
- Gunicorn’s `on_starting` hook runs `build_controllers_js.py`, which Jinja-renders `controllers.js.j2` into a single bundle with an ISO timestamp header. Rebuilds happen on each deploy so the bundle always matches the Python that emits events.
- The HTML surface (`templates/controls/_base.htm`) provides canonical IDs for status panes, letting new controllers inherit the telemetry pipeline without bespoke wiring.

## DevOps Notes
- Redis is mission control. DB 0 tracks run metadata, DB 2 streams status, DB 9 powers RQ, DB 11 stores Flask sessions, DB 13 caches NoDb JSON, DB 14 manages README editor locks, DB 15 holds log levels. See `docs/dev-notes/redis_dev_notes.md` for ops drills.
- Coding conventions live in `docs/dev-notes/style-guide.md`; skim it before touching batch runners, NoDb modules, or microservices.
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
UID=$(id -u)          # customize as needed
GID=$(id -g)
POSTGRES_PASSWORD=localdev
SECRET_KEY=$SECRET_KEY
SECURITY_PASSWORD_SALT=$SECURITY_PASSWORD_SALT
EOF

# 2. Bring up the stack.
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build

# 3. Visit http://localhost:8080/weppcloud once the services report "ready".
```

By default the containers run as `roger:docker` (uid `1000`, gid `993`) so artifacts match the GitLab runner and CI images. If your host uses different ids, update `docker/.env` accordingly—for example:

```env
UID=1000          # roger
GID=993           # output of `getent group docker | cut -d: -f3`
```

Make sure the group exists locally; Compose passes numeric ids straight through, so the host must recognize them to keep permissions tidy.

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
- Prefer the Docker stacks (`docker/docker-compose.*`) plus the `docker/weppcloud-entrypoint.sh` bootstrapper; legacy systemd snippets remain in `_scripts/` if you absolutely must run without containers.

## Further Reading
- `docs/dev-notes/redis_dev_notes.md` — deep dive into Redis usage, DB allocations, and debugging recipes.
- `wepppy/weppcloud/controllers_js/README.md` — controller bundling, singleton contracts, and WS client expectations.
- `wepppy/nodb/base.py` — the canonical NoDb implementation with logging, caching, and locking primitives.
- `wepppy/topo/peridot/runner.py` — how Rust binaries integrate with WEPP abstractions.

## Credits
University of Idaho 2015-Present, Swansea University 2019-Present (Wildfire Ash Transport And Risk estimation tool, WATAR).

Contributors: Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frakenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller.

License: BSD-3 Clause (see `license.txt`).
