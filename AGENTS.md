# AGENTS.md
> AI Coding Agent Guide for wepppy

## Authorship
**This document is maintained by GitHub Copilot (Codex agent) which retains full authorship rights for all AGENTS.md content revisions.**

## Repository Overview

wepppy is a DevOps-focused erosion modeling stack that fuses Python orchestration, Rust geospatial kernels, and Redis-first observability. The system automates Water Erosion Prediction Project (WEPP) runs, wildfire response analytics, and watershed-scale geospatial preprocessing by gluing together legacy Fortran executables, modern Python services, and Rust-accelerated tooling.

## Core Architecture Patterns

### NoDb Philosophy
Instead of a monolithic database, run state is serialized to disk, memoized in Redis, and surfaced through microservices. Every component can inspect, replay, or recover long-lived scenarios with minimal coupling.

- `NoDbBase.getInstance(wd)` guarantees a singleton per working directory
- Instances are serialized to disk and mirrored into Redis DB 13 for 72 hours
- Locking via Redis hashes in DB 0 (`locked:*.nodb`) prevents concurrent writers
- Log verbosity controlled through Redis DB 15

### Redis Database Allocation
- **DB 0**: Run metadata and distributed locks
- **DB 2**: Status message pub/sub streaming
- **DB 9**: Redis Queue (RQ) job management
- **DB 11**: Flask session storage
- **DB 13**: NoDb JSON caching (72-hour TTL)
- **DB 14**: README editor locks
- **DB 15**: Log level configuration

### High Performance Telemetry Pipeline
```text
NoDb subclass logger
  ↓ QueueHandler + QueueListener (async fan-out)
  ↓ StatusMessengerHandler pushes to Redis DB 2 Pub/Sub
  ↓ services/status2 Go WebSocket service
  ↓ WSClient (controllers.js) WebSocket bridge
  ↓ controlBase panels update logs, checklists, charts
```

## Key Components

### Python Stack
- **wepppy/nodb/** - NoDb controller modules
  - `base.py` - Core NoDb implementation with logging, caching, locking
  - `core/` - Primary controllers (Climate, Wepp, Watershed, Landuse, Soils, etc.)
  - `mods/` - Optional extensions and location-specific customizations
  - `duckdb_agents.py` - Fast query agents for parquet summaries
  
- **wepppy/weppcloud/** - Flask web application
  - `app.py` - Flask application factory
  - `routes/` - Blueprints for web endpoints
  - `controllers_js/` - Front-end controller modules (bundled via Jinja)
  - `templates/` - Jinja templates for UI
  - `static/` - Static assets (CSS, vendor libs)

- **wepppy/rq/** - Background job modules
  - `project_rq.py` - Project-level orchestration
  - `wepp_rq.py` - WEPP model execution tasks
  - `rq_worker.py` - Worker entry point

- **wepppy/climates/** - Climate data modules (CLIGEN, Daymet, GridMET, PRISM)
- **wepppy/soils/** - Soil database integrations
- **wepppy/wepp/** - WEPP model file management and validation
- **wepppy/topo/** - Watershed delineation (TOPAZ, Peridot/Rust, WhiteboxTools)

### Go Microservices
- **services/preflight2** - Preflight checklist WebSocket streamer
- **services/status2** - Log/status WebSocket proxy with heartbeat

### Rust Integration
- **wepppyo3** - Python bindings for climate interpolation, raster lookups, soil loss grids
- **peridot** - Watershed abstraction engine
- **WhiteboxTools** - Hillslope delineation (custom TOPAZ implementation)

## Module Organization Best Practices

### NoDb Module Exports
Every NoDb controller module declares an explicit `__all__` that captures the public surface:
- The primary `NoDbBase` subclass
- Companion enums, exceptions, and helper utilities used outside the module

**When adding new public functions or classes, update the module's `__all__` immediately.**

Package aggregators (`wepppy.nodb.core`, `wepppy.nodb.mods`) build their own `__all__` from per-module lists, keeping the top-level namespace tidy while preserving ergonomic imports like:
```python
from wepppy.nodb.core import Wepp
from wepppy.nodb.mods import Disturbed
```

### Legacy Module Redirects
Legacy `.nodb` payloads still deserialize because `wepppy.nodb.base` builds `_LEGACY_MODULE_REDIRECTS` by walking the package tree and binding old module paths to their new homes. The `NoDbBase._ensure_legacy_module_imports()` hook loads those modules on demand before jsonpickle decodes.

If a refactor moves or renames a module, the redirect map updates automatically as long as the file lives under `wepppy/nodb/`. For one-off overrides, call `NoDbBase._import_mod_module('mod_name')` to pre-load the replacement.

### Import Conventions
- Prefer absolute imports: `from wepppy.nodb.core.climate import Climate`
- Keep module-level side effects lightweight
- Treat anything underscored as private (stays out of `__all__`)
- The `__getattr__` hook in `wepppy.nodb.mods` lazily imports mod packages, keeping optional dependencies truly optional

## Development Workflow

### Docker Compose (Recommended)
The repository ships with multi-container development stacks that mirror production topology:

**Development Stack** (`docker/docker-compose.dev.yml`):
```bash
# 1. Create .env file
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
SECURITY_PASSWORD_SALT=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
cat > docker/.env <<EOF
UID=$(id -u)
GID=$(id -g)
POSTGRES_PASSWORD=localdev
SECRET_KEY=$SECRET_KEY
SECURITY_PASSWORD_SALT=$SECURITY_PASSWORD_SALT
EOF

# 2. Bring up the stack
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build

# 3. Visit http://localhost:8080/weppcloud
```

Services include:
- Flask app (weppcloud) with bind mounts for live reloads
- Go microservices (status, preflight)
- Redis, PostgreSQL
- RQ worker pool
- Caddy reverse proxy serving static assets

**Common Docker tasks**:
```bash
# Tail logs
docker compose -f docker/docker-compose.dev.yml logs -f weppcloud

# Shell into container
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml exec weppcloud bash

# Rebuild service
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build weppcloud
```

**Production Stack** (`docker/docker-compose.prod.yml`):
- Vendors all dependencies directly into the image
- Minimal bind mounts (only data volumes)
- Non-root `wepp` user for security
- Health checks at `/health`

### File Structure Navigation
```
wepppy/
├── docker/                  # Docker configs and entrypoints
├── services/                # Go microservices (preflight2, status2)
├── tests/                   # pytest test suite
├── wctl/                    # CLI utilities
├── wepppy/                  # Core Python package
│   ├── nodb/               # NoDb controllers
│   │   ├── base.py         # Core NoDb base class
│   │   ├── core/           # Primary controllers
│   │   ├── mods/           # Optional extensions
│   │   └── duckdb_agents.py # Parquet query utilities
│   ├── weppcloud/          # Flask web application
│   │   ├── app.py          # Application factory
│   │   ├── controllers_js/ # Front-end modules
│   │   ├── routes/         # Flask blueprints
│   │   └── templates/      # Jinja templates
│   ├── rq/                 # Background job modules
│   ├── climates/           # Climate data integrations
│   ├── soils/              # Soil databases
│   ├── topo/               # Watershed delineation
│   └── wepp/               # WEPP model interfaces
└── readme.md               # Primary documentation
```

## Working with NoDb Controllers

### Creating/Modifying NoDb Controllers
NoDb controllers are singletons that manage run state. Key patterns:

```python
from wepppy.nodb.base import NoDbBase

class MyController(NoDbBase):
    def __init__(self, wd):
        super().__init__(wd)
        self.my_data = {}
        
    def my_operation(self):
        with self.locked():  # Distributed lock
            # Mutate state
            self.my_data['key'] = 'value'
            self.dump_and_unlock()  # Persist to disk + Redis

# Usage
controller = MyController.getInstance(wd)
controller.my_operation()
```

**Important conventions**:
- Always use `with self.locked():` for state mutations
- Call `self.dump_and_unlock()` after changes
- Update module's `__all__` when adding public classes
- Keep singleton pattern via `getInstance(wd)`

### Logging in NoDb Controllers
Every NoDb instance has a logger wired to the telemetry pipeline:

```python
self._logger.info("Operation started")
self._logger.debug("Detailed info")  # Respects Redis DB 15 log level
self._logger.error("Something failed", exc_info=True)
```

Logs automatically flow to:
- Local file: `<runid>/_logs/`
- Console output
- Redis pub/sub (DB 2)
- WebSocket clients via status2 service

## Testing and Validation

### Test Structure
Tests live in `tests/` and use pytest:
```bash
# Run all tests
pytest tests/

# Run specific module
pytest tests/test_wepp_top_translator.py

# Run with coverage
pytest --cov=wepppy tests/
```

### NoDb Testing Patterns
When testing NoDb controllers:
1. Create isolated working directories (use tempfile)
2. Test serialization round-trips (`dump()` then `getInstance()`)
3. Verify singleton behavior
4. Test locking mechanisms if applicable

Example:
```python
def test_nodb_controller(tmpdir):
    wd = str(tmpdir)
    
    # First instance
    controller = MyController.getInstance(wd)
    controller.my_data['test'] = 'value'
    controller.dump_and_unlock()
    
    # Verify singleton
    controller2 = MyController.getInstance(wd)
    assert controller is controller2
    assert controller2.my_data['test'] == 'value'
```

### Redis Testing
Tests involving Redis should use Redis DB 0-15 carefully. Consider:
- Flushing test keys after tests
- Using unique prefixes for test data
- Mocking Redis connections for unit tests

## Front-End Development

### Controller Bundling
Controllers live in `wepppy/weppcloud/controllers_js/` and export singletons:

```javascript
class MyController {
    static getInstance() {
        if (!MyController.instance) {
            MyController.instance = new MyController();
        }
        return MyController.instance;
    }
    
    constructor() {
        this.base = controlBase;  // Inherit async ergonomics
    }
}
```

Controllers are bundled via `build_controllers_js.py` which runs during Gunicorn's `on_starting` hook. The bundle is generated from `controllers.js.j2` with an ISO timestamp header.

**After modifying controllers**:
```bash
# Rebuild bundle
python wepppy/weppcloud/_scripts/build_controllers_js.py

# Or restart Gunicorn (auto-rebuilds)
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml restart weppcloud
```

### Static Assets
- Source: `wepppy/weppcloud/static-src/`
- Built: `wepppy/weppcloud/static/`
- Build command: `wctl build-static-assets`

Caddy serves `/weppcloud/static/*` directly in both dev and production.

## Common Tasks

### Adding a New Climate Data Source
1. Create module in `wepppy/climates/<source_name>/`
2. Implement client class following existing patterns (e.g., `cligen_client.py`)
3. Add to `Climate` NoDb controller in `wepppy/nodb/core/climate.py`
4. Update `__all__` exports
5. Add tests in `tests/climates/`

### Adding a New NoDb Mod
1. Create package in `wepppy/nodb/mods/<mod_name>/`
2. Implement NoDb controller subclass
3. Define `__all__` with public exports
4. Add to `wepppy/nodb/mods/__init__.py` aggregator
5. Document in mod's README
6. Add integration tests

### Modifying WEPP Model Integration
1. Locate relevant file in `wepppy/wepp/` (soils, management, interchange)
2. Ensure backward compatibility with existing `.wepp` files
3. Add translator tests in `tests/test_wepp_top_translator.py`
4. Update NoDb controllers if state changes

### Adding an RQ Background Task
1. Create function in appropriate `wepppy/rq/*_rq.py` module
2. Follow existing patterns with `@job` decorator
3. Emit status updates via NoDb logger
4. Update Redis DB keys with progress metadata
5. Add task orchestration in route handlers

### Debugging WebSocket Streaming
1. Check Redis DB 2 for pub/sub activity: `redis-cli -n 2 PUBSUB CHANNELS`
2. Verify status2 service is running and connected
3. Check browser console for WebSocket connection state
4. Inspect `controlBase` event handlers in controllers.js
5. Review NoDb logger output and handler chain

## Security Considerations

### Never Commit Secrets
- Secrets go in `docker/.env` (gitignored)
- Use environment variables for tokens, passwords
- Regenerate `SECRET_KEY` and `SECURITY_PASSWORD_SALT` per deployment

### Input Validation
- Sanitize all user inputs before file operations
- Validate working directory paths to prevent traversal
- Use parameterized queries for any SQL (PostgreSQL usage)
- Validate JSON payloads before deserialization

### Redis Security
- Production should use Redis AUTH
- Bind Redis to localhost or private network only
- Set appropriate `maxmemory` policies
- Monitor keyspace for unexpected growth

### Container Security
- Production image runs as non-root `wepp` user
- Keep base images updated
- Scan images with `docker scan` or Trivia
- Minimize secrets in environment variables

## Code Style and Conventions

### Python Style
- Follow PEP 8
- Use type hints where practical
- Docstrings for public functions and classes
- Keep functions focused (single responsibility)
- Prefer composition over inheritance for NoDb mods

### Structured Logging
Emit structured logs using logger extras:
```python
self._logger.info("Task completed", extra={
    'topaz_id': topaz_id,
    'duration_s': elapsed,
    'status': 'success'
})
```

### Error Handling
- Catch specific exceptions, not bare `except:`
- Log exceptions with `exc_info=True`
- Emit user-friendly error messages to Redis status
- Clean up resources in `finally` blocks

### Git Commit Messages
- Use present tense: "Add feature" not "Added feature"
- First line: concise summary (≤50 chars)
- Body: explain why, not what (code shows what)
- Reference issues: "Fixes #123"

## Performance Optimization

### Rust Acceleration
When adding compute-intensive operations:
1. Profile Python implementation first
2. Consider adding to `wepppyo3` if hot path
3. Implement fallback for missing Rust wheel
4. Benchmark speedup with `pytest --benchmark`

### Redis Caching Strategy
- Use Redis DB 13 for hot NoDb payloads (72-hour TTL)
- Cache expensive query results with sensible expiry
- Implement cache invalidation on mutations
- Monitor hit rates with Redis INFO

### Async Task Design
- Break long tasks into progress checkpoints
- Emit incremental status updates (every 5-10%)
- Allow cancellation via RQ job signals
- Store intermediate results for resumability

## Integration with External Tools

### WEPP Fortran Executables
Located in `deps/linux/` or system-installed:
- `wepp` - Main WEPP model
- `topaz` - Watershed delineation
- Input/output via file I/O (no direct bindings)

### WhiteboxTools Integration
Rust-based geospatial tools via `wepppy/topo/wbt/`:
- Exposed via Python subprocess calls
- Custom hillslope TOPAZ implementation
- Raster analysis operations

### Peridot (Rust Watershed Abstraction)
Python calls Rust binary for watershed abstraction:
```python
from wepppy.topo.peridot.runner import run_peridot
run_peridot(wd, config)
```

## Deployment Notes

### Kubernetes Migration (Pending)
When resuming Kubernetes work:
- Duplicate static build stage for proxy image
- Use init containers for shared assets
- Eliminate shared volume mounts
- Configure Redis keyspace notifications in ConfigMap
- Set resource limits based on profiling

### Health Checks
- Endpoint: `/health`
- Returns 200 OK when ready
- Checks Redis connectivity
- Use for liveness/readiness probes

### Logging in Production
- Structured logs to stdout (captured by Docker/K8s)
- Per-run logs in working directory
- Centralized aggregation via Loki/ELK if needed
- Redis status messages ephemeral (72-hour retention)

## Further Reading

### Essential Documentation
- `readme.md` - Comprehensive architecture overview
- `wepppy/nodb/base.py` - NoDb implementation details
- `wepppy/weppcloud/routes/usersum/dev-notes/` - Developer notes:
  - `redis_dev_notes.md` - Redis usage patterns
  - `controllers_js.md` - Controller bundling
  - `style-guide.md` - Coding conventions
  - `kubernetes-deployment-strategy.md` - K8s planning

### Key Implementation Files
- `wepppy/nodb/base.py` - Core NoDb abstractions
- `wepppy/nodb/core/wepp.py` - WEPP model controller
- `wepppy/nodb/core/watershed.py` - Watershed abstraction
- `wepppy/weppcloud/app.py` - Flask application factory
- `wepppy/rq/project_rq.py` - Project orchestration
- `services/status2/cmd/preflight2/main.go` - Go WebSocket service

### External Projects
- [wepppyo3](https://github.com/wepp-in-the-woods/wepppyo3) - Rust Python bindings
- [peridot](https://github.com/wepp-in-the-woods/peridot) - Watershed abstraction
- [WhiteboxTools](https://github.com/rogerlew/whitebox-tools) - Custom TOPAZ fork

## Getting Help

### When Stuck
1. Check `readme.md` for high-level architecture
2. Review relevant dev-notes in `wepppy/weppcloud/routes/usersum/dev-notes/`
3. Examine existing implementations for patterns
4. Use `git log` to understand change history
5. Search codebase for similar functionality: `git grep "pattern"`

### Common Pitfalls
- **NoDb locking**: Always use `with self.locked()` for mutations
- **Redis DB selection**: Use correct DB number (0, 2, 9, 11, 13, 14, 15)
- **Singleton violations**: Never call `__init__` directly, use `getInstance()`
- **Path handling**: Use `os.path.join`, never string concatenation
- **Legacy imports**: Update `__all__` when refactoring module structure

### Making Changes
- Start with minimal, focused changes
- Test locally with Docker Compose dev stack
- Run relevant tests before committing
- Update documentation if behavior changes
- Follow existing patterns in the codebase

## Agent-Specific Guidance

### Code Generation Principles
- **Preserve existing patterns**: Match the style of surrounding code
- **Minimal changes**: Edit only what's necessary for the task
- **Test coverage**: Add tests for new functionality
- **Documentation**: Update docstrings and README files
- **Backward compatibility**: Don't break existing `.nodb` payloads

### When Modifying NoDb Controllers
1. Check if legacy modules need redirects
2. Update `__all__` exports
3. Maintain singleton pattern
4. Preserve locking semantics
5. Test serialization round-trips

### When Adding Dependencies
1. Add to `docker/requirements-uv.txt`
2. Rebuild Docker images
3. Document in relevant README
4. Consider optional vs required status
5. Check for security vulnerabilities

### When Changing APIs
1. Search for all call sites: `git grep "function_name"`
2. Maintain backward compatibility if possible
3. Update all callers atomically
4. Add deprecation warnings if phasing out
5. Update integration tests

### Quality Checklist
Before submitting changes:
- [ ] Code follows existing patterns
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Redis usage follows DB allocation
- [ ] NoDb exports in `__all__`
- [ ] Docker builds successfully
- [ ] No breaking changes to serialization

---

## Credits
University of Idaho 2015-Present, Swansea University 2019-Present (Wildfire Ash Transport And Risk estimation tool, WATAR).

Contributors: Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frakenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller.

License: BSD-3 Clause (see `license.txt`).
