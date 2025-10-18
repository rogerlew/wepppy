# WEPPpy Architecture Guide

> Comprehensive architectural overview for AI coding agents and developers

## Table of Contents
- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Component Interaction Patterns](#component-interaction-patterns)
- [Key Design Patterns](#key-design-patterns)
- [Directory Structure](#directory-structure)
- [Technology Stack](#technology-stack)

## System Overview

WEPPpy is a DevOps-focused erosion modeling stack that orchestrates Water Erosion Prediction Project (WEPP) simulations through a microservices architecture. The system integrates:

- **Python orchestration layer** (Flask, RQ)
- **Rust geospatial kernels** (wepppyo3, peridot)
- **Redis-first observability** (caching, pub/sub, job queuing)
- **Legacy Fortran executables** (WEPP, TOPAZ)
- **Go microservices** (WebSocket streaming)

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Web Browser (User)                           │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐       │
│  │   Flask UI  │  │  WebSocket   │  │   Static Assets     │       │
│  │  (Jinja)    │  │   Client     │  │   (controllers.js)  │       │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬──────────┘       │
└─────────┼─────────────────┼────────────────────┼──────────────────┘
          │                 │                     │
          │                 │                     │
┌─────────▼─────────────────▼────────────────────▼──────────────────┐
│                      Caddy Reverse Proxy                           │
│                   (Static Asset Server)                            │
└─────────┬──────────────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────────────┐
│                   Flask Application (Gunicorn)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐     │
│  │   Routes    │  │    NoDb      │  │   Background Jobs    │     │
│  │  Blueprints │  │ Controllers  │  │    (RQ Worker)       │     │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘     │
└─────────┼─────────────────┼────────────────────┼──────────────────┘
          │                 │                     │
          │                 │                     │
┌─────────▼─────────────────▼────────────────────▼──────────────────┐
│                           Redis                                    │
│  ┌────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │  DB 0  │  │  DB 2   │  │  DB 9   │  │  DB 13   │  │ DB 15  │ │
│  │ Locks  │  │ Pub/Sub │  │   RQ    │  │  Cache   │  │  Logs  │ │
│  └────────┘  └────┬────┘  └─────────┘  └──────────┘  └────────┘ │
└────────────────────┼───────────────────────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────────────────────┐
│               Go Microservices (status2, preflight2)               │
│                   WebSocket Streaming Layer                        │
└────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. NoDb Controllers (`wepppy/nodb/`)

**Purpose**: Stateful singleton controllers that manage run state without a traditional database.

**Key Characteristics**:
- Singleton pattern: `MyController.getInstance(wd)` per working directory
- Serialization: JSON to disk + Redis cache (72-hour TTL)
- Distributed locking via Redis DB 0
- Automatic logging pipeline integration

**Core NoDb Classes**:
```python
# Location: wepppy/nodb/base.py
class NoDbBase:
    """Base class for all NoDb controllers"""
    
    @classmethod
    def getInstance(cls, wd: str) -> 'NoDbBase':
        """Get singleton instance for working directory"""
        
    def locked(self) -> ContextManager:
        """Distributed lock context manager"""
        
    def dump_and_unlock(self) -> None:
        """Persist state to disk and Redis"""
```

**Controller Hierarchy**:
```
wepppy/nodb/
├── base.py              # NoDbBase foundation class
├── core/                # Primary controllers (always loaded)
│   ├── climate.py       # Climate data management
│   ├── wepp.py          # WEPP model configuration
│   ├── watershed.py     # Watershed abstraction
│   ├── landuse.py       # Land cover/use management
│   ├── soils.py         # Soil database integration
│   ├── topaz.py         # TOPAZ watershed delineation
│   └── ron.py           # Run configuration (Map)
└── mods/                # Optional extensions (lazy loaded)
    ├── disturbed/       # Fire/disturbance modeling
    ├── ash_transport/   # Ash transport simulation
    ├── baer/            # BAER assessment
    └── [20+ more mods]
```

### 2. Flask Web Application (`wepppy/weppcloud/`)

**Purpose**: Web UI for WEPP simulations, project management, and visualization.

**Structure**:
```
wepppy/weppcloud/
├── app.py                    # Flask application factory
├── routes/                   # Blueprint modules
│   ├── project/              # Project CRUD operations
│   ├── rq/                   # Background job API
│   ├── map/                  # Map interface
│   └── ...
├── templates/                # Jinja2 templates
│   ├── controls/             # Reusable control panels
│   └── ...
├── controllers_js/           # Front-end controllers (bundled)
│   ├── control_base.js       # Base async controller
│   ├── ws_client.js          # WebSocket client
│   └── [module controllers]
├── static/                   # Built static assets
├── static-src/               # Source static assets
└── webservices/              # FastAPI/Starlette services
    ├── wmesque2/             # Raster server
    ├── elevationquery/       # Elevation service
    └── dtale.py              # Data explorer
```

### 3. Background Job System (`wepppy/rq/`)

**Purpose**: Long-running tasks via Redis Queue (RQ).

**Key Components**:
```python
# Location: wepppy/rq/project_rq.py
@job('default', timeout=3600)
def run_project_task(runid: str, task_name: str) -> dict:
    """Execute project-level task"""
    
# Location: wepppy/rq/wepp_rq.py  
@job('default', timeout=7200)
def run_wepp_simulation(runid: str) -> dict:
    """Execute WEPP model simulation"""
```

**Job Lifecycle**:
1. Flask endpoint enqueues job → Redis DB 9
2. RQ worker picks up job
3. NoDb controller executes task
4. Logger emits progress → Redis DB 2 (pub/sub)
5. Go microservice streams to browser via WebSocket
6. Job completion updates Redis metadata

### 4. Telemetry Pipeline

**Purpose**: Real-time log streaming from background workers to browser.

**Flow Diagram**:
```
NoDb Controller Logger
        │
        ├─→ QueueHandler (async)
        │         │
        │         ├─→ FileHandler (disk logs)
        │         ├─→ StreamHandler (console)
        │         └─→ StatusMessengerHandler
        │                    │
        │                    ▼
        │         Redis DB 2 Pub/Sub Channel
        │                    │
        │                    ▼
        │         Go WebSocket Service (status2)
        │                    │
        │                    ▼
        │         Browser WebSocket Client (ws_client.js)
        │                    │
        │                    ▼
        └──────────→ UI Control Panels (logs, progress)
```

**Configuration**:
- Log levels: Redis DB 15 (dynamic per-run control)
- Channels: `{runid}:wepp`, `{runid}:climate`, etc.
- Retention: Ephemeral (pub/sub) + persistent (file logs in `{runid}/_logs/`)

### 5. Redis Database Allocation

WEPPpy uses Redis with purpose-specific database numbers:

| DB | Purpose | TTL | Data Types |
|----|---------|-----|------------|
| 0 | Run metadata, distributed locks | Varies | Hashes, Strings |
| 2 | Status message pub/sub | Ephemeral | Pub/Sub channels |
| 9 | Redis Queue (RQ) job management | Until complete | RQ structures |
| 11 | Flask session storage | Session lifetime | Flask-Session format |
| 13 | NoDb JSON cache | 72 hours | JSON strings |
| 14 | README editor locks | Manual | Hashes |
| 15 | Log level configuration | Manual | Hashes |

**Lock Key Pattern**:
```
locked:{runid}.nodb           # NoDb instance lock
locked:{runid}.climate.nodb   # Climate controller lock
locked:{runid}.wepp.nodb      # WEPP controller lock
```

### 6. Rust Integration

**Purpose**: High-performance geospatial operations.

**Components**:

| Crate | Location | Purpose |
|-------|----------|---------|
| wepppyo3 | `/workdir/wepppyo3` | Python bindings for raster ops, climate interpolation |
| peridot | `/workdir/peridot` | Watershed abstraction engine |
| whitebox-tools | `/workdir/weppcloud-wbt` | Hillslope delineation (custom TOPAZ fork) |

**Usage Pattern**:
```python
# Python falls back gracefully when Rust unavailable
try:
    from wepppyo3.raster_characteristics import extract_value
    result = extract_value(raster_path, x, y)
except ImportError:
    # Pure Python fallback
    result = python_extract_value(raster_path, x, y)
```

### 7. Query Engine (`wepppy/query_engine/`)

**Purpose**: MCP-compatible API for LLM agents to query WEPP run data.

**Architecture**:
```
Query Engine
├── Core (core.py)             # DuckDB execution engine
├── Catalog (catalog.py)       # Dataset discovery
├── Activation (activate.py)   # Parquet generation
├── MCP API (app/mcp/)         # LLM-friendly REST endpoints
└── Formatter (formatter.py)   # Result transformation
```

**Endpoints**:
- `GET /mcp/runs/{runid}` - Run metadata
- `GET /mcp/runs/{runid}/catalog` - Dataset catalog
- `POST /mcp/runs/{runid}/queries/execute` - Execute DuckDB query
- `POST /mcp/runs/{runid}/activate` - Generate parquet files

## Data Flow

### 1. New Project Creation

```
User Request
    ↓
Flask Route (routes/project/new)
    ↓
RedisPrep.create_working_directory(runid)
    ↓ 
Initialize NoDb Controllers (Ron, Climate, etc.)
    ↓
Serialize to disk + Redis cache
    ↓
Return runid to user
```

### 2. WEPP Simulation Execution

```
User Triggers "Run WEPP"
    ↓
Flask enqueues RQ job → Redis DB 9
    ↓
RQ Worker picks up job
    ↓
Load NoDb Controllers (Watershed, Wepp, etc.)
    ↓
Acquire distributed lock (Redis DB 0)
    ↓
Write WEPP input files (.man, .sol, .slp, .cli)
    ↓
Execute Fortran binary (subprocess)
    ↓
Parse output files (.wat, .soil_loss)
    ↓
Generate parquet/GeoJSON summaries
    ↓
Update NoDb state
    ↓
Dump + unlock
    ↓
Emit completion event → Redis DB 2
    ↓
Browser receives WebSocket notification
```

### 3. Real-Time Log Streaming

```
Background Task starts
    ↓
NoDb logger.info("Task started")
    ↓
QueueHandler (non-blocking)
    ↓
StatusMessengerHandler
    ↓
redis.publish(channel, json_message) → DB 2
    ↓
Go WebSocket service (status2) subscribed to channel
    ↓
WebSocket broadcast to connected browsers
    ↓
ws_client.js receives message
    ↓
controlBase updates UI (logs panel, progress bar)
```

## Component Interaction Patterns

### Pattern 1: NoDb Singleton Access

```python
from wepppy.nodb.core import Wepp

# Always use getInstance, never __init__ directly
wepp = Wepp.getInstance(wd)

# Mutations require locking
with wepp.locked():
    wepp.some_property = new_value
    wepp.dump_and_unlock()  # Persist to disk + Redis
```

### Pattern 2: RQ Background Task

```python
from wepppy.rq import job

@job('default', timeout=3600)
def my_task(runid: str, **kwargs):
    from wepppy.nodb.core import Wepp
    
    wepp = Wepp.getInstance(_join('/wc1/runs', runid))
    
    with wepp.locked():
        # Do work
        wepp._logger.info("Progress update")  # Auto-streams to browser
        wepp.dump_and_unlock()
    
    return {'success': True}
```

### Pattern 3: Controller Bundling (Front-End)

```javascript
// Location: wepppy/weppcloud/controllers_js/my_controller.js
class MyController {
    static getInstance() {
        if (!MyController.instance) {
            MyController.instance = new MyController();
        }
        return MyController.instance;
    }
    
    constructor() {
        this.base = controlBase;  // Inherit async utilities
        this.base.subscribeToStatus(this.handleStatus.bind(this));
    }
    
    handleStatus(msg) {
        // Update UI based on WebSocket message
    }
}
```

### Pattern 4: Lazy Module Loading

```python
# Location: wepppy/nodb/mods/__init__.py
def __getattr__(name):
    """Lazy load mod packages to keep optional dependencies optional"""
    if name in _MOD_PACKAGES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

## Key Design Patterns

### 1. NoDb Philosophy

**Principle**: State is serialized to disk, cached in Redis, not stored in traditional database.

**Benefits**:
- Replay-able: Any run can be reconstructed from disk
- Inspectable: Human-readable JSON files
- Distributable: Redis cache provides fast access
- Recoverable: File-based backups

**Tradeoffs**:
- No SQL queries across runs
- Manual locking required
- File I/O overhead

### 2. Distributed Locking

**Implementation**: Redis hashes with TTL and ownership tokens.

```python
# Lock structure in Redis DB 0
# Key: "locked:{runid}.wepp.nodb"
# Value: {"token": "uuid", "owner": "hostname:pid", "acquired_at": timestamp}

def _acquire_lock(runid, relpath, ttl=300):
    token = str(uuid.uuid4())
    lock_key = f"locked:{runid}.{relpath}"
    
    # Atomic set-if-not-exists
    success = redis_client.set(lock_key, token, nx=True, ex=ttl)
    return token if success else None
```

### 3. Event-Driven UI Updates

**Pattern**: Pub/Sub over WebSocket instead of polling.

```
Worker Logger → Redis Pub/Sub → Go Service → WebSocket → Browser
```

**Advantages**:
- Real-time updates (< 100ms latency)
- Scalable (Go handles 10k+ concurrent connections)
- No Flask-SocketIO (avoids single-worker constraint)

### 4. Module Exports Management

**Pattern**: Explicit `__all__` declarations with aggregation.

```python
# wepppy/nodb/core/wepp.py
__all__ = [
    'Wepp',
    'PhosphorusOpts',
    'BaseflowOpts',
    'WeppNoDbLockedException',
]

# wepppy/nodb/core/__init__.py
from .wepp import Wepp, PhosphorusOpts  # ...etc
__all__ = ['Wepp', 'PhosphorusOpts', ...]  # Aggregate from modules
```

**Benefits**:
- Clean public API surface
- IDE autocomplete friendly
- Legacy compatibility via redirects

## Directory Structure

```
wepppy/
├── ARCHITECTURE.md          # This file
├── AGENTS.md                # AI agent coding guide
├── readme.md                # User-facing documentation
├── license.txt              # BSD-3 Clause
│
├── wepppy/                  # Core Python package
│   ├── __init__.py
│   ├── nodb/                # NoDb controllers
│   │   ├── base.py          # Foundation class
│   │   ├── core/            # Primary controllers
│   │   ├── mods/            # Optional extensions
│   │   └── duckdb_agents.py # Query helpers
│   ├── weppcloud/           # Flask web app
│   │   ├── app.py           # Application factory
│   │   ├── routes/          # Blueprint modules
│   │   ├── templates/       # Jinja templates
│   │   ├── controllers_js/  # Front-end JS
│   │   └── webservices/     # Microservices
│   ├── rq/                  # Background jobs
│   ├── climates/            # Climate data clients
│   ├── soils/               # Soil database integrations
│   ├── topo/                # Watershed delineation
│   ├── wepp/                # WEPP model interfaces
│   ├── query_engine/        # MCP query API
│   └── config/              # Configuration modules
│
├── services/                # Go microservices
│   ├── status2/             # WebSocket status streamer
│   └── preflight2/          # Preflight checklist service
│
├── docker/                  # Docker configuration
│   ├── Dockerfile           # Production image
│   ├── Dockerfile.dev       # Development image
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── requirements-uv.txt  # Python dependencies
│
├── tests/                   # pytest test suite
│   ├── nodb/                # NoDb controller tests
│   ├── weppcloud/           # Flask app tests
│   ├── query_engine/        # Query engine tests
│   └── ...
│
├── docs/                    # Extended documentation
│   ├── dev-notes/           # Developer notes
│   ├── ui-reference/        # UI documentation
│   └── ...
│
├── deps/                    # Third-party binaries
│   └── linux/               # WEPP/TOPAZ executables
│
└── wctl/                    # CLI utilities
```

## Technology Stack

### Back-End
- **Python 3.10+**: Core language
- **Flask 2.x**: Web framework
- **Redis 6.x+**: Cache, pub/sub, locks, sessions
- **RQ (Redis Queue)**: Background job system
- **Gunicorn**: WSGI server
- **PostgreSQL**: User/project metadata (minimal use)
- **DuckDB**: In-process analytics (query engine)

### Front-End
- **Jinja2**: Template engine
- **Vanilla JavaScript**: Controller modules (no framework)
- **WebSockets**: Real-time communication
- **PureCSS**: Lightweight CSS framework
- **Leaflet**: Map rendering

### Geospatial
- **GDAL/OGR**: Raster/vector I/O
- **NumPy**: Array operations
- **Pandas**: Tabular data
- **GeoPandas**: Vector analysis
- **Rasterio**: Raster abstraction

### High-Performance Computing
- **Rust**: wepppyo3, peridot, whitebox-tools
- **Fortran 77**: WEPP/TOPAZ (legacy, unchanged)
- **Go**: status2, preflight2 microservices

### Infrastructure
- **Docker**: Containerization
- **Caddy**: Reverse proxy + static server
- **systemd**: Service management (bare metal)

### Development
- **pytest**: Test framework
- **mypy**: Type checking (partial adoption)
- **black**: Code formatting (optional)

## Additional Resources

- **AGENTS.md**: Detailed guide for AI coding agents
- **readme.md**: User-facing documentation
- **docs/dev-notes/**: Component-specific deep dives
  - `redis_dev_notes.md`: Redis usage patterns
  - `controllers_js.md`: Front-end architecture
  - `style-guide.md`: Coding conventions
- **wepppy/nodb/base.py**: NoDb implementation reference
- **wepppy/query_engine/README.md**: Query engine MCP API

---

**Last Updated**: 2025-10-18  
**Maintainers**: University of Idaho, Swansea University  
**License**: BSD-3 Clause
