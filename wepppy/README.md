# wepppy Package

> Core Python library for erosion modeling, watershed analysis, and WEPP orchestration with Redis-backed state management and Rust-accelerated geospatial processing.

> **See also:** [AGENTS.md](../AGENTS.md) for comprehensive coding conventions, architecture patterns, and development workflows.

## Overview

The `wepppy` package is the computational heart of WEPPcloud, providing:

- **NoDb state management** - File-backed, Redis-cached singleton controllers for run state
- **WEPP model integration** - Python wrappers for WEPP Fortran executables and model file generation
- **Geospatial processing** - Watershed delineation, DEM analysis, and raster operations
- **Climate data integration** - CLIGEN, Daymet, GridMET, PRISM climate data providers
- **Soil and landuse databases** - SSURGO, STATSGO2, NLCD, RAP integration
- **Web application framework** - Flask app with routes, templates, and frontend controllers
- **Background job orchestration** - Redis Queue (RQ) task management and status streaming
- **Microservices** - FastAPI and Starlette services for elevation queries and raster serving

This package is designed for watershed-scale erosion modeling, wildfire response analytics, and agricultural runoff prediction. It glues together legacy Fortran executables, modern Python services, and Rust-accelerated tooling to deliver repeatable, high-throughput simulations.

## Package Structure

```
wepppy/
├── nodb/                    # NoDb state management controllers
│   ├── base.py             # Core NoDb singleton implementation
│   ├── core/               # Primary controllers (Climate, Wepp, Watershed, etc.)
│   ├── mods/               # Optional extensions and location-specific mods
│   ├── redis_prep.py       # Redis-backed run initialization
│   ├── duckdb_agents.py    # Fast query agents for Parquet summaries
│   └── status_messenger.py # Redis pub/sub status streaming
├── weppcloud/              # Flask web application
│   ├── app.py              # Application factory
│   ├── routes/             # Flask blueprints (API, UI, batch processing)
│   ├── templates/          # Jinja2 HTML templates
│   ├── controllers_js/     # Frontend JavaScript controllers
│   └── static/             # Static assets (CSS, vendor libs)
├── wepp/                   # WEPP model file management
│   ├── soils/              # Soil database and .sol file generation
│   ├── management/         # Management practice files
│   ├── interchange/        # WEPP input/output file parsing
│   └── reports/            # Loss report generation
├── climates/               # Climate data providers
│   ├── cligen/             # CLIGEN climate generator
│   ├── daymet/             # Daymet gridded observations
│   ├── gridmet/            # GridMET reanalysis data
│   └── prism/              # PRISM monthly normals
├── soils/                  # Soil database integrations
│   ├── ssurgo/             # SSURGO soil survey data
│   └── statsgo/            # STATSGO2 generalized data
├── topo/                   # Watershed delineation and topographic analysis
│   ├── topaz/              # TOPAZ watershed delineation
│   ├── peridot/            # Rust-based watershed abstraction
│   └── wbt/                # WhiteboxTools integration
├── rq/                     # Background job modules
│   ├── project_rq.py       # Project-level orchestration
│   ├── wepp_rq.py          # WEPP model execution tasks
│   └── rq_worker.py        # Custom worker implementation
├── microservices/          # Standalone microservices
│   └── elevationquery/     # Starlette elevation query service
├── webservices/            # FastAPI/Flask services
│   ├── metquery/           # Monthly climate data service
│   ├── wmesque2/           # Raster tile server
│   └── dtale.py            # D-Tale wrapper for interactive data exploration
├── query_engine/           # DuckDB-powered query system for Parquet data
├── tools/                  # Migration scripts and utilities
└── all_your_base/          # Shared utility functions and helpers
```

## Core Components

### 1. NoDb State Management

The NoDb pattern replaces traditional databases with file-backed, Redis-cached singleton objects:

```python
from wepppy.nodb.core import Wepp, Landuse, Watershed

# Singleton pattern - always returns same instance for a working directory
wepp = Wepp.getInstance("/path/to/run")

# Distributed locking for mutations
with wepp.locked():
    wepp.phosphorus_opts = {"fallout": True}
    wepp.dump_and_unlock()

# Cross-instance access
watershed = wepp.watershed_instance  # Lazy load sibling controller
```

**Key features:**
- Singleton per working directory (`wd`)
- JSONPickle serialization to `<runid>/<name>.nodb`
- Redis caching (DB 13, 72-hour TTL)
- Distributed locking via Redis (DB 0)
- Structured logging to Redis pub/sub (DB 2)

**See:** [wepppy/nodb/README.md](nodb/README.md) for comprehensive NoDb documentation.

### 2. WEPP Model Integration

Python wrappers for WEPP Fortran executables and model file generation:

```python
from wepppy.wepp.soils.utils import WeppSoilUtil

# Generate WEPP soil file
soil_util = WeppSoilUtil()
soil_data = soil_util.build_soil(mukey, texture_class)

# Parse WEPP output
from wepppy.wepp.stats import HillSummary
hill_summary = HillSummary("/path/to/run", hillslope_id)
total_loss = hill_summary.avg_annual_soil_loss  # Mg/ha
```

**Components:**
- `wepp/soils/` - Soil database queries and .sol file generation
- `wepp/management/` - Management practice templates (disturbed, forest, agriculture)
- `wepp/interchange/` - WEPP input file (.man, .slp, .cli) generation
- `wepp/reports/` - Loss report aggregation and statistics

### 3. Geospatial Processing

Watershed delineation, DEM analysis, and raster operations:

```python
from wepppy.topo.peridot import run_peridot

# Rust-accelerated watershed abstraction
run_peridot(wd, config={
    'method': 'peridot',
    'min_channel_length': 100
})

# WhiteboxTools integration
from wepppy.topo.wbt import Topaz
topaz = Topaz.getInstance(wd)
topaz.delineate_hillslopes()
```

**Acceleration:**
- Rust bindings via `wepppyo3` for climate interpolation and raster lookups
- `peridot` for watershed abstraction (3-10x faster than Python)
- Custom `whitebox-tools` fork with TOPAZ-compatible hillslope delineation

### 4. Climate Data Integration

Multiple climate data providers with unified interface:

```python
from wepppy.climates import CligenStationsManager

# Query nearest CLIGEN station
cligen_mgr = CligenStationsManager()
stations = cligen_mgr.find_closest(lng=-116.5, lat=43.8, n=3)

# Generate climate files
from wepppy.nodb.core import Climate
climate = Climate.getInstance(wd)
climate.build_climate_files()  # Uses configured provider (CLIGEN/Daymet/GridMET)
```

**Providers:**
- **CLIGEN** - Stochastic weather generator
- **Daymet** - 1km gridded observations (North America)
- **GridMET** - 4km gridded surface meteorology
- **PRISM** - Monthly climate normals

### 5. Flask Web Application

Full-stack web application for interactive modeling:

```python
from wepppy.weppcloud import create_app

app = create_app()
app.run(host='0.0.0.0', port=5000)
```

**Features:**
- Route blueprints for project management, run configuration, and results viewing
- Jinja2 templates with PureCSS responsive design
- JavaScript controllers bundled via `build_controllers_js.py`
- WebSocket status streaming via Go microservices
- D-Tale integration for interactive Parquet/CSV exploration

**See:** [wepppy/weppcloud/README.md](weppcloud/README.md) for Flask app documentation.

### 6. Background Job Orchestration

Redis Queue (RQ) integration for long-running tasks:

```python
from wepppy.rq.wepp_rq import run_wepp_watershed

# Queue background job
job = run_wepp_watershed.queue(wd, clean=True)

# Check status via Redis
from wepppy.nodb.core import RedisPrep
prep = RedisPrep.getInstance(wd)
job_id = prep.query_rq_status('run_wepp_watershed')
```

**Task modules:**
- `project_rq.py` - Project creation, configuration, and cleanup
- `wepp_rq.py` - WEPP model execution and results processing
- Custom `WepppyRqWorker` with graceful shutdown and job cleanup

### 7. Query Engine

DuckDB-powered analytics for large Parquet datasets:

```python
from wepppy.nodb.duckdb_agents import LossQueryEngine

# Fast aggregation queries (< 80ms)
engine = LossQueryEngine(wd)
results = engine.query_total_loss(wepp_ids=[1, 2, 3])
```

**Performance:**
- Sub-100ms queries on Parquet files
- Lazy column loading for memory efficiency
- Spatial joins between watersheds and loss grids

## Installation

The `wepppy` package is not published to PyPI. Install from source:

```bash
# Clone repository
git clone https://github.com/rogerlew/wepppy.git
cd wepppy

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

**Dependencies:**
- Python 3.12+
- Redis 7.0+
- GDAL 3.8+
- PostgreSQL 16+ (for user management)
- Optional: `wepppyo3` for Rust acceleration

## Configuration

Core configuration is managed via `.cfg` files in each run directory:

```ini
[general]
project_name = My Watershed Project
description = Erosion modeling for wildfire response

[climate]
type = gridmet
start_year = 2010
end_year = 2024

[watershed]
delineation_backend = peridot
min_channel_length = 100

[wepp]
runs = 100  # CLIGEN realizations
phosphorus = True
```

**Global settings** are controlled via environment variables:

```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379

# Flask app
SECRET_KEY=your-secret-key
SECURITY_PASSWORD_SALT=your-salt

# D-Tale token for iframe handshakes
DTALE_INTERNAL_TOKEN=shared-secret
```

## Quick Start

### Running a Basic WEPP Simulation

```python
from wepppy.nodb.core import RedisPrep, Climate, Landuse, Soils, Wepp, Watershed

# 1. Initialize run directory
wd = "/tmp/my-run"
prep = RedisPrep(wd, cfg_fn="config.cfg")

# 2. Configure watershed
watershed = Watershed(wd, cfg_fn="config.cfg")
watershed.set_outlet(lng=-116.5, lat=43.8)
watershed.delineate()

# 3. Configure inputs
landuse = Landuse(wd, cfg_fn="config.cfg")
landuse.mode = "gridded"
landuse.build()

soils = Soils(wd, cfg_fn="config.cfg")
soils.mode = "gridded"
soils.build()

climate = Climate(wd, cfg_fn="config.cfg")
climate.input_years = 30
climate.build()

# 4. Run WEPP
wepp = Wepp(wd, cfg_fn="config.cfg")
wepp.prep_hillslopes()
wepp.run_hillslopes()
wepp.run_watershed()

# 5. Extract results
from wepppy.wepp.stats import HillSummary
summary = HillSummary(wd, topaz_id=1)
print(f"Avg annual loss: {summary.avg_annual_soil_loss} Mg/ha")
```

### Using with Docker

```bash
# Start development stack
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up

# Visit http://localhost:8080/weppcloud
```

## Redis Database Allocation

wepppy uses multiple Redis databases for separation of concerns:

| DB | Purpose | TTL | Key Examples |
|----|---------|-----|--------------|
| 0 | Run metadata, locks | Persistent | `<runid>:*`, `locked:wepp.nodb` |
| 2 | Status pub/sub | Ephemeral | `<runid>:wepp`, `<runid>:climate` |
| 9 | RQ job queue | Job lifetime | `rq:job:<uuid>`, `rq:queue:default` |
| 11 | Flask sessions | Session lifetime | `session:<session_id>` |
| 13 | NoDb JSON cache | 72 hours | `<runid>:wepp.nodb`, `<runid>:landuse.nodb` |
| 14 | README editor locks | Ephemeral | `readme_lock:<runid>` |
| 15 | Log level config | Persistent | `<runid>:log_level` |

**See:** [docs/dev-notes/redis_dev_notes.md](../docs/dev-notes/redis_dev_notes.md) for operational details.

## Telemetry Pipeline

Structured logging flows from NoDb controllers to browser in milliseconds:

```text
NoDb instance logger
  ↓ QueueHandler (async, non-blocking)
  ↓ QueueListener (dedicated thread)
  ↓ StatusMessengerHandler (Redis DB 2 pub/sub)
  ↓ services/status2 (Go WebSocket proxy)
  ↓ StatusStream helper (browser WebSocket client)
  ↓ controlBase.updateStatus() (DOM update)
```

**Key features:**
- Async log emission from worker processes
- Redis pub/sub for multi-subscriber fan-out
- Go WebSocket service handles 1000+ concurrent connections
- Browser receives real-time updates without polling

## Module-Specific Lazy Loading

The `wepppy` package uses lazy imports for heavy submodules:

```python
# __init__.py __getattr__ hook
import wepppy.rq        # Lazy - imports on first access
import wepppy.climates  # Lazy - imports on first access

# Direct imports still work
from wepppy.nodb.core import Wepp  # Eager
```

**Benefits:**
- Faster import times for CLI tools
- Reduced memory footprint for workers that don't need all modules
- Optional dependencies stay truly optional

## Testing

Run tests via the Docker wrapper to ensure environment consistency:

```bash
# Run all tests
wctl run-pytest tests

# Run specific module tests
wctl run-pytest tests/nodb/core/test_wepp.py

# Run with coverage
wctl run-pytest tests --cov=wepppy --cov-report=html
```

**See:** [tests/README.md](../tests/README.md) and [tests/AGENTS.md](../tests/AGENTS.md) for testing conventions.

## Type Hints and Stubs

The `wepppy` package includes comprehensive type hints and stub files:

- `py.typed` marker enables type checking for consumers
- Stub files in `stubs/wepppy/` for external validation
- `mypy.ini` at repository root configures type checking

```bash
# Validate types
wctl run "mypy wepppy/nodb/core"

# Generate/update stubs
wctl run-stubgen

# Check stub completeness
wctl run-stubtest wepppy.nodb.core
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| NoDb.getInstance() | 1-5ms | Cached in Redis DB 13 |
| Watershed delineation | 2-30s | DEM size dependent, Rust-accelerated |
| WEPP hillslope run | 0.5-5s | Per hillslope, depends on years |
| WEPP watershed run | 10-120s | Depends on subcatchment count |
| DuckDB loss query | 50-200ms | Multi-GB Parquet, spatial joins |
| Climate file generation | 5-60s | Provider and date range dependent |

**Optimization tips:**
- Use `wepppyo3` Rust bindings for raster-heavy operations
- Enable Redis caching for hot NoDb instances
- Run WEPP hillslopes in parallel via RQ workers
- Use DuckDB for analytics instead of loading full CSVs

## Developer Notes

### Code Organization
- **Core modules** (`nodb/core/`) are stable and widely used
- **Mods** (`nodb/mods/`) are optional extensions for specific use cases
- **Lazy imports** keep package loading fast
- **Explicit `__all__` exports** in every module for clean namespaces

### Singleton Pattern
NoDb controllers use `getInstance(wd)` instead of direct instantiation:

```python
# Correct - singleton pattern
wepp = Wepp.getInstance(wd)

# Incorrect - creates new instance, bypasses cache
wepp = Wepp(wd, cfg_fn)  # Only for initial creation
```

### Locking Discipline
Always use `with instance.locked():` for mutations:

```python
with wepp.locked():
    wepp.phosphorus_opts["fallout"] = True
    wepp.dump_and_unlock()  # Persist to disk + Redis
```

### Module Exports
Update `__all__` when adding public classes or functions:

```python
# my_module.py
__all__ = ["MyController", "MyEnum", "helper_function"]

class MyController(NoDbBase):
    ...
```

### Legacy Import Redirects
The `_LEGACY_MODULE_REDIRECTS` system maintains backward compatibility:

```python
# Old code still works
from wepppy.nodb.wepp import Wepp  # Redirects to wepppy.nodb.core.wepp

# New code uses explicit imports
from wepppy.nodb.core import Wepp
```

## Known Limitations

- **WEPP Fortran dependency** - Requires compiled WEPP executables in `deps/linux/`
- **Single-machine scaling** - No distributed WEPP execution (RQ workers must share filesystem)
- **Redis memory** - Large runs (>10,000 subcatchments) can exhaust Redis if cache eviction isn't tuned
- **GDAL version sensitivity** - Raster operations depend on GDAL 3.8+ for consistent projection handling

## Further Reading

### Architecture and Design
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design and component diagrams
- [API_REFERENCE.md](../API_REFERENCE.md) - Quick reference for key APIs
- [AGENTS.md](../AGENTS.md) - Comprehensive coding conventions and workflows

### Detailed Documentation
- [nodb/README.md](nodb/README.md) - NoDb singleton pattern and controllers
- [weppcloud/README.md](weppcloud/README.md) - Flask web application structure
- [weppcloud/controllers_js/README.md](weppcloud/controllers_js/README.md) - Frontend controller bundling
- [query_engine/README.md](query_engine/README.md) - DuckDB query system

### Developer Notes
- [docs/dev-notes/redis_dev_notes.md](../docs/dev-notes/redis_dev_notes.md) - Redis usage patterns
- [docs/dev-notes/style-guide.md](../docs/dev-notes/style-guide.md) - Coding conventions
- [docs/dev-notes/test-tooling-spec.md](../docs/dev-notes/test-tooling-spec.md) - Testing infrastructure
- [docker/README.md](../docker/README.md) - Docker development stack

### External Projects
- [wepppyo3](https://github.com/wepp-in-the-woods/wepppyo3) - Rust Python bindings for geospatial acceleration
- [peridot](https://github.com/wepp-in-the-woods/peridot) - Rust watershed abstraction engine
- [weppcloud-wbt](https://github.com/rogerlew/weppcloud-wbt) - Custom fork of whitebox-tools with TOPAZ compatibility

## Credits

**University of Idaho** (2015-Present), **Swansea University** (2019-Present)

**Contributors:** Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frankenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller

**License:** BSD-3 Clause (see [license.txt](../license.txt))
