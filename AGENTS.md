# AGENTS.md
> AI Coding Agent Guide for wepppy

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Core Directives
- `??` in prompt is a directive to provide critical response and not to implement in code.
- If you need clarification or additional debug information from a human, just ask.

## Repository Overview

wepppy is a DevOps-focused erosion modeling stack that fuses Python orchestration, Rust geospatial kernels, and Redis-first observability. The system automates Water Erosion Prediction Project (WEPP) runs, wildfire response analytics, and watershed-scale geospatial preprocessing by gluing together legacy Fortran executables, modern Python services, and Rust-accelerated tooling. The architechture as a whole strives for openness, flexibility, and observability.

## Core Architecture Patterns

### NoDb Philosophy
Instead of a monolithic database, run state is serialized to disk, memoized in Redis, and surfaced through microservices. Every component can inspect, replay, or recover long-lived scenarios with minimal coupling.

- `NoDbBase.getInstance(wd)` guarantees a singleton per working directory
- Instances are serialized to disk and mirrored into Redis DB 13 for 72 hours
- Locking via Redis hashes in DB 0 (`locked:*.nodb`) prevents concurrent writers
- Log verbosity controlled through Redis DB 15
- Non-canonical pattern. It is a model, It is a view model. Mutable by design (with safeguards).

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
  - `duckdb_agents.py` - Fast query agents for parquet summaries (< 80 ms request)
  
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
- **wepppy/topo/** - Watershed delineation (TOPAZ, Peridot/Rust, WhiteboxTools; )

#### Webservices
Run on production server to provide access to large geospatial datasets
- **wepppy/microservices/elevationquery** - run-scoped elevation service powered by Starlette
  - Mirrors legacy payloads and surfaces descriptive JSON errors via custom exception handlers for transparency.
- **wepppy/webservices/metquery** - queries monthly data
- **wepppy/webservices/wmesque** - raster server (deprecated)
- **wepppy/webservices/wmesque2** - raster server (fastapi)
- **wepppy/webservices/dtale.py** - WEPP run-aware D-Tale wrapper for interactive tabular exploration

### Go Microservices
- **services/preflight2** - Preflight checklist WebSocket streamer
- **services/status2** - Log/status WebSocket proxy with heartbeat

### Rust Integration
- **/workdir/wepppyo3/wepppyo3** - Python bindings for climate interpolation, raster lookups, soil loss grids
- **/workdir/peridot/peridot** - Watershed abstraction engine
- **/workdir/weppcloud-wbt** - WhiteboxTools Hillslope delineation, FindOutlet, other tools

### Fixed FORTRAN 77
- **/workdir/wepp-forest** -  WEPP Watershed with baseflow model
- **/workdir/wepp-forest-revegetation** -  WEPP Watershed with revegetation modeling and baseflow (Beta)

### Other Stack Components
- **/workdir/wepppy2** - Contains WEPP Runner (python wrapper) and WEPP binaries (separate to support FSWEPP2)
- **/workdir/rosetta** - Soil Pedotransfer model with duckdb to avoid sqlite concurrency

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

### Type Hints
Core NoDb modules use comprehensive type hints following Python 3.12+ conventions:
- Import types from `typing` module: `Optional`, `Dict`, `List`, `Tuple`, `Any`
- Add parameter type hints: `def method(self, value: str) -> None:`
- Add return type hints to all methods and properties
- Use `Optional[T]` for values that can be None
- Properties should have return type annotations
- `mypy.ini` provides configuration for type checking

Example NoDb class with type hints:
```python
from typing import Optional, Dict, List
from wepppy.nodb.base import NoDbBase

class MyController(NoDbBase):
    def __init__(
        self, 
        wd: str, 
        cfg_fn: str, 
        run_group: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group)
        self._data: Dict[str, Any] = {}
    
    @property
    def data(self) -> Dict[str, Any]:
        return self._data
    
    def process(self, items: List[str]) -> None:
        # Implementation
        pass
```

### Type Stub Management
- Build, review, and install missing `.pyi` files with `stubgen`, keeping outputs under the matching package directory (for example `wepppy/nodb/core/`).
- When modifying a source module, update its companion `.pyi` file in the same change so exported signatures stay in sync.
- Use `stubtest` to validate stubs against the runtime implementation before finishing a change. The helper script `python tools/sync_stubs.py` keeps `stubs/wepppy/` in sync and ensures `wepppy/py.typed` exists.

- Run `mypy`/`stubtest` inside the Docker dev container so stub-only wheels from `docker/requirements-stubs-uv.txt` are available. Use the `wctl` helpers instead of manually invoking `docker compose exec`:

```bash
wctl run-pytest                      # pytest tests
wctl run-stubtest wepppy.nodb.core    # stubtest target module/package
wctl run-stubgen                      # sync stubs/wepppy/
```

### American English Normalization
- When you modify files, run the `uk2us` tool to normalize any British spellings (for example, `colour` → `color`).
  - **Always preview changes first** using diff to avoid breaking code blocks or making nonsensical substitutions:
    ```bash
    diff -u path/to/file.py <(uk2us path/to/file.py)
    ```
  - Review the diff output carefully to ensure changes are appropriate for prose, comments, and docstrings
  - Avoid applying uk2us if changes would affect code identifiers, string literals, or technical terms
  - Targeted update: `uk2us -i path/to/file.py`
  - Batch update: `find wepppy/all_your_base -type f -name '*.py' -print0 | xargs -0 uk2us -i`
- If you encounter incorrect or missing substitutions, adjust `/workdir/uk2us/config/uk2us_rules.json`.
  - `skip_replacements` prevents unwanted conversions.
  - `forced_mappings` adds explicit word mappings.
  - Agents have authority to edit this file; rerun `uk2us` after changes to confirm the fix.

### README.md Authoring and Maintenance
Every module, service, and significant package should have a README.md that serves multiple audiences: GitHub visitors, web indexers, domain experts (hydrologists, land managers), and developers (human and AI agents).

**Template and Guidance**:
- Comprehensive README template: [`docs/prompt_templates/readme_authoring_template.md`](docs/prompt_templates/readme_authoring_template.md)
- Module type templates: NoDb controllers, microservices, routes/blueprints, utilities
- Audience-specific guidance: Tailoring content for different reader types
- Quality checklist and maintenance workflow

**When to Create/Update README.md**:
1. **New module or service**: Always create a README.md before committing
2. **Significant refactoring**: Update README.md to reflect new patterns or structure
3. **API changes**: Document breaking changes and migration paths
4. **User-reported confusion**: If users can't understand usage, improve the README.md

**Key Principles**:
- **Start with the why**: Explain the problem before the solution
- **Use examples**: Concrete code snippets are more valuable than prose
- **Link strategically**: Cross-reference AGENTS.md for coding conventions, main readme.md for architecture
- **Serve all audiences**: Include sections for different reader types (overview for visitors, developer notes for contributors)
- **Keep it updated**: README.md should evolve with the code

**README.md Structure** (adapt as needed):
```markdown
# [Module Name]
> Brief tagline (1-2 sentences)
> **See also:** [AGENTS.md](path) for [relevant section]

## Overview
[What, why, who, key capabilities]

## [Core Section: Architecture/API/Usage/Workflow]
[Main technical content]

## Quick Start / Examples
[Concrete usage examples]

## Developer Notes
[Implementation details, patterns, testing]

## Further Reading
[Related docs, dev-notes, external refs]
```

**Quality Standards**:
- Clear title and tagline answering "what is this?"
- Concrete, runnable examples
- Cross-references to AGENTS.md where appropriate
- Tables for structured data (parameters, endpoints)
- Code blocks with language specification for syntax highlighting
- American English spelling (run `uk2us` after completion)
- No confidential information or hardcoded secrets

**Audit and Improvement**:
- The template includes an audit of existing README.md files with improvement recommendations
- Prioritize READMEs for user-facing components and frequently-modified modules
- When touching a module with a minimal README.md, consider expanding it
- AI agents have authority to create and revise README.md files per authorship policy


## Development Environment Assumptions

- Agents should assume a Linux host with Docker and Docker Compose available.
- The `wctl` utility (Docker command wrapper) is installed on the host and should be used to manage containers, execute commands (e.g., `wctl exec weppcloud bash`), and run tests (`wctl run-pytest …`). This keeps workflows aligned with the team’s tooling.
- The host filesystem mirrors the dev container layout under `/workdir/<repo>`, so relative paths such as `/workdir/wepppy/...` are safe to reference.
- The repository includes `docker/docker-compose.dev.yml`; expect it to exist and be the primary entry point for local orchestration.


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
EXTERNAL_HOST=wc.bearhive.duckdns.org
POSTGRES_PASSWORD=localdev
SECRET_KEY=$SECRET_KEY
SECURITY_PASSWORD_SALT=$SECURITY_PASSWORD_SALT
EOF

# 2. Bring up the stack
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build

# or install and use wctl utility

# 3. Visit http://localhost:8080/weppcloud
```

Development Server and Test Production are behind pfSense/Haproxy with TLS termination

Services include:
- Flask app (weppcloud) with bind mounts for live reloads
- Go microservices (status2, preflight2)
- Redis, PostgreSQL
- RQ worker pool with custom worker `WepppyRqWorker(rq.Worker)`
- D-Tale explorer (`dtale`) for large Parquet/CSV inspection at `/weppcloud/dtale`
  - Runs as a single Gunicorn worker; D-Tale keeps state in-process and will misbehave with multiple workers
  - Loader auto-registers watershed/AgField GeoJSON so Maps → Location Mode defaults to the current run's subcatchments (channels and ag fields stay one click away)
- Caddy reverse proxy serving static assets

**Common Docker tasks**:
```bash
# Tail logs
wctl logs -f weppcloud

# Shell into container
wctl exec weppcloud bash

# Full rebuild service
wctl down && wctl build --no-cache && wctl up -d
```

**Production Stack** (`docker/docker-compose.prod.yml`):
- Vendors all dependencies directly into the image
- Minimal bind mounts (only data volumes)
- Non-root `www-data` user for security
- Health checks at `/health`

### File Structure Navigation
```
wepppy/
├── docker/                  # Docker configs and entrypoints
├── services/                # Go microservices (preflight2, status2)
├── tests/                   # pytest test suite
├── wctl/                    # CLI utilities
├── wepppy/                  # Core Python package
│   ├── nodb/                # NoDb controllers
│   │   ├── base.py          # Core NoDb base class
│   │   ├── core/            # Primary controllers
│   │   ├── mods/            # Optional extensions
│   │   └── duckdb_agents.py # Parquet query utilities
│   ├── weppcloud/           # Flask web application
│   │   ├── app.py           # Application factory
│   │   ├── controllers_js/  # Front-end modules
│   │   ├── controllers_js/  # Front-end modules
│   │   ├── routes/          # Flask blueprints
│   │   ├── templates/       # Jinja templates
│   │   └── webservices/     # fastapi, flask services
│   ├── rq/                  # Background job modules
│   ├── climates/            # Climate data integrations
│   ├── soils/               # Soil databases
│   ├── topo/                # Watershed delineation
│   └── wepp/                # WEPP model interfaces
└── readme.md                # Primary documentation
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

### Execution Workflow
- **Always use the Docker wrapper.** Run suites with `wctl run-pytest …` so pytest executes inside the `weppcloud` container with the same dependency set and environment variables as production.
- **Minimum cadence.**
  - While iterating: `wctl run-pytest tests/<path or module>`
  - Before handoff or commit: `wctl run-pytest tests --maxfail=1`
- `wctl` merges `docker/.env`, an optional project-root `.env` (or `WCTL_HOST_ENV`), and any exported shell variables. Keep `docker/.env` authoritative; use the host override for machine-specific values (API keys, host paths).

### Suite Layout
- `tests/README.md` — human quick-start (how to run tests, structure overview).
- `tests/AGENTS.md` — agent playbook covering fixtures, serialization patterns, Flask patching, microservice mocking, and expectations for new suites.
- Tests mirror the source tree. New module under `wepppy/foo/bar.py` → add `tests/foo/test_bar.py`.
- **Frontend checks** should go through `wctl run-npm …` (host command wrapping `npm --prefix wepppy/weppcloud/static-src`). Run `wctl run-npm lint` and `wctl run-npm test` (or `wctl run-npm check`) before shipping controller changes.

### NoDb Testing Patterns
1. Use `tmp_path`/`tmpdir` for isolated working directories.
2. Wrap mutations with `with controller.locked():` and call `dump_and_unlock()` before inspecting persisted state.
3. Verify singleton behaviour by comparing identity of two `getInstance` calls.
4. Reset class-level caches between tests (clear `_instances` dicts) to prevent bleed-over.

Example:
```python
def test_nodb_round_trip(tmp_path):
    wd = str(tmp_path)
    controller = MyController.getInstance(wd)
    with controller.locked():
        controller.state = "value"
        controller.dump_and_unlock()

    clone = MyController.getInstance(wd)
    assert clone is controller
    assert clone.state == "value"
```

### Redis / External Services
- Leverage the Redis stub in `tests/conftest.py`; extend it when new client APIs are required rather than importing the real client.
- Network traffic is disallowed. Mock requests/responses explicitly (e.g., `responses`, `httpx.MockTransport`) and drop payload fixtures under `tests/data/`.
- Flush or namespace any temporary keys/files created during tests.

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

Controllers are bundled via `build_controllers_js.py`; the Docker entrypoint runs this script automatically whenever `wctl up weppcloud` (or a container restart) occurs. New `.js` files dropped under `controllers_js/` are detected automatically—manual edits to `controllers.js.j2` are no longer required. Because static assets are served through Caddy from a bind-mounted volume, you generally do **not** need to restart the app container after rebuilding; reloading the browser is enough once the bundle has been regenerated.

If you need to force a rebuild without bouncing the container, run:
```bash
wctl exec weppcloud bash -lc "python wepppy/weppcloud/controllers_js/build_controllers_js.py"
```

After creating or significantly editing a Pure control template, run the render smoke test to catch Jinja macro issues early:
```bash
wctl run "pytest tests/weppcloud/routes/test_pure_controls_render.py"
```
The fixture stubs required globals so most templates render without additional setup.

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
- Set `DTALE_INTERNAL_TOKEN` in stack environments; browse→D-Tale handshakes rely on it

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
3. Benchmark speedup with `pytest --benchmark`

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

## WEPPcloud Endpoints
- Keep request times short to not tie up gunicorn workers
- Offload long-running tasks to RQ or async services

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
- `docs/dev-notes/` - Developer notes:
  - `redis_dev_notes.md` - Redis usage patterns
  - `wepppy/weppcloud/controllers_js/README.md` - Controller bundling
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
2. Review relevant dev-notes in `docs/dev-notes/`
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

## Notes for Next Pass
- Static assets now build via `wctl build-static-assets`; re-run before image rebuilds so `controllers.js` and vendor bundles stay current.
- Kubernetes migration is still pending. When that work resumes, plan on duplicating the static build stage so the proxy image (or init container) ships with the same `/weppcloud/static` tree baked in—no shared volumes required.
- ID standardization: landuse/soils/watershed parquet export lowercase `topaz_id`/`wepp_id` Int32. Ensure docker deployments run the migration CLIs (`migrate_landuse_parquet`, `migrate_soils_parquet`, `migrate_watersheds_peridot_tables`, `migrate_wbt_geojson_ids`, `migrate_ashpost_pickles`) after rolling out the images so production runs comply.
- DuckDB/query-engine/report consumers now expect lowercase ids; DuckDB agents intentionally fail-fast if legacy columns remain. No auto-normalization—schema drift must be fixed via migrations.
- Wepppy/test suites require optional modules (`wepppyo3`, Flask `abort`) not bundled in minimal docker images; integration testing should occur in the same environment as production builds or with those extras installed.
- Strict naming philosophy: do not add helpers that coerce legacy casing; future contributions should honor the lowercase schema across parquet/GeoJSON assets. Document migrations in release notes before the next deploy.
- Loss reports for hillslopes/channels/impoundments must not reintroduce legacy shims; enforce strict schema via migrations and remove patch layers from the interchange path.


## Credits
University of Idaho 2015-Present, Swansea University 2019-Present (Wildfire Ash Transport And Risk estimation tool, WATAR).

Contributors: Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frakenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller.

License: BSD-3 Clause (see `license.txt`).
