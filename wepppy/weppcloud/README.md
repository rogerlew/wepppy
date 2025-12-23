# WEPPcloud Web Application

> The Flask-based web application that serves as the primary user interface and API for the wepppy erosion modeling ecosystem.

> **See also:** [AGENTS.md](../../AGENTS.md) for Flask web application structure, NoDb integration patterns, and frontend development guidelines.

## Overview

The `weppcloud` application is the core web component of the `wepppy` stack. It provides a user-friendly interface for:
- Creating and configuring erosion modeling projects (runs).
- Managing project state (climate, soils, land use, watershed delineation).
- Triggering and monitoring background jobs (e.g., WEPP runs, post-processing).
- Visualizing model inputs and outputs on maps and charts.
- Accessing and exporting run results in multiple formats.

The application bridges the gap between the WEPP (Water Erosion Prediction Project) Fortran models and modern web technologies, making sophisticated erosion modeling accessible to hydrologists, land managers, and researchers without requiring command-line expertise.

It serves multiple audiences:
- **End Users**: Hydrologists and land managers who need to model erosion scenarios and generate reports.
- **API Consumers**: Automation scripts and batch workflows that create and manage runs programmatically.
- **Developers**: Contributors extending the platform with new features, data sources, or integrations.

## Architecture

The application is built around the Flask web framework and follows a modular structure using Blueprints. This architecture enables clear separation of concerns and makes the codebase maintainable as features grow.

### Core Components

- **`app.py`**: The application factory. It initializes the Flask app, configures extensions (e.g., Flask-Login, Redis, Flask-Security), and registers all the feature blueprints. It should be kept minimal, focusing on wiring and shared helpers.

- **`routes/`**: Feature-specific route modules are organized as Flask Blueprints. Each blueprint encapsulates a logical feature area (e.g., `reports`, `batch_runner`, `nodb_api`). Blueprints can be either single-file modules or packages with sub-modules for larger features.

- **`templates/`**: Jinja2 templates for rendering HTML pages. Templates are co-located in subdirectories that mirror the blueprint structure (e.g., `templates/reports/rhem/`) for maintainability.

- **`controllers_js/`**: Frontend JavaScript controllers that manage UI interactivity. These are bundled into a single `controllers-gl.js` file and loaded on pages that require them. See [controllers_js/README.md](controllers_js/README.md) for details.

- **`static/`**: Static assets like CSS, images, and third-party JavaScript libraries. Built assets (bundled JavaScript, compiled CSS) are served via Caddy reverse proxy.

- **`utils/`**: Shared helper functions and utilities (e.g., `authorize` for permission checks, `get_wd` for working directory resolution) that can be used across multiple blueprints.

- **`webservices/`**: Internal microservices (FastAPI and Flask) for specialized tasks like raster querying, elevation lookups, and D-Tale integration.

### Request Flow

1. **User request** → Caddy reverse proxy → Flask app
2. **Route handler** (Blueprint) validates authentication and authorization
3. **NoDb controller** accessed via `get_wd()` to retrieve/modify run state
4. **Background job** (RQ) triggered for long-running tasks
5. **WebSocket** streams status updates back to the browser
6. **Response** rendered as HTML template or JSON payload

## Quick Start

### Running Locally with Docker Compose

```bash
# 1. Navigate to the docker directory
cd docker

# 2. Create environment file (if not already present)
cat > .env <<EOF
UID=$(id -u)
GID=$(id -g)
EXTERNAL_HOST=localhost
POSTGRES_PASSWORD=localdev
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
SECURITY_PASSWORD_SALT=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
EOF

# 3. Start the development stack
docker compose -f docker-compose.dev.yml up --build

# 4. Visit http://localhost:8080/weppcloud
```

### Creating a New Run (API Example)

```python
import requests

# Create a new run
response = requests.post('http://localhost:8080/weppcloud/batch/api/create-run', json={
    'config': 'tahoe',
    'overrides': {
        'general:dem_db': 'ned1/2016',
        'general:climate_mode': 'gridmet'
    }
})

run_data = response.json()
print(f"Created run: {run_data['run_url']}")
```

### Accessing a Run's NoDb State

```python
from wepppy.nodb.core import Watershed, Climate

# Get working directory for a run
wd = '/geodata/weppcloud_runs/<runid>/<config>'

# Access NoDb controllers
watershed = Watershed.getInstance(wd)
climate = Climate.getInstance(wd)

print(f"Outlet: {watershed.outlet}")
print(f"Climate mode: {climate.climate_mode}")
```

## Configuration

### Environment Variables

The application is configured via environment variables, typically defined in `docker/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Flask secret key for session encryption |
| `SECURITY_PASSWORD_SALT` | *(required)* | Salt for password hashing |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL database password |
| `EXTERNAL_HOST` | `localhost` | External hostname for URL generation |
| `REDIS_HOST` | `redis` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `WEPPCLOUD_RUNS_DIR` | `/geodata/weppcloud_runs` | Directory for run storage |
| `TEST_SUPPORT_ENABLED` | `false` | Enable test support endpoints |
| `DTALE_INTERNAL_TOKEN` | *(optional)* | Token for D-Tale integration |

### Flask Extensions

- **Flask-Login**: User session management
- **Flask-Security**: Authentication and authorization framework
- **Flask-Session**: Server-side session storage (Redis-backed)
- **Redis**: Caching, pub/sub messaging, and distributed locking

### URL Structure

All run-scoped routes follow the pattern:
```
/runs/<runid>/<config>/<feature>/<endpoint>
```

Examples:
- `/runs/abc123/tahoe/tasks/set_outlet`
- `/runs/abc123/tahoe/query/subcatchments.json`
- `/runs/abc123/tahoe/rq/api/build_climate`

## Key Concepts

### Run Lifecycle

A typical WEPPcloud run progresses through these stages:

1. **Project Creation**: User creates a new run with a configuration (e.g., `tahoe`, `disturbed`)
2. **Delineation**: User sets an outlet point; watershed is delineated
3. **Data Acquisition**: Climate, soil, and land use data are retrieved
4. **Model Building**: WEPP input files are generated
5. **Execution**: WEPP model runs (hillslope and watershed simulations)
6. **Post-Processing**: Results are aggregated, exported, and visualized

### NoDb Integration

The application relies heavily on the NoDb pattern for managing run state. NoDb controllers are singletons that:
- Serialize/deserialize state to `.nodb` files in the run directory
- Cache state in Redis (DB 13, 72-hour TTL)
- Use distributed locks to prevent concurrent mutations
- Emit structured logs that flow to WebSocket clients

**Common pattern in routes:**
```python
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.core import Watershed

@blueprint.route('/tasks/set_outlet', methods=['POST'])
def set_outlet():
    wd = get_wd(request)
    watershed = Watershed.getInstance(wd)
    
    with watershed.locked():
        watershed.set_outlet(lng, lat)
        watershed.dump_and_unlock()
    
    return jsonify({'success': True})
```

### Background Jobs (RQ)

Long-running operations are offloaded to Redis Queue (RQ) workers:
- **Job submission**: Routes enqueue tasks with `rq.enqueue(task_fn, args...)`
- **Progress updates**: Jobs emit logs via NoDb controllers, which stream to WebSocket clients
- **Job tracking**: Metadata stored in Redis DB 0 (`run:<runid>:status`)

### WebSocket Streaming

Status updates flow from backend to frontend via WebSocket:
1. NoDb logger emits log message
2. `StatusMessengerHandler` publishes to Redis pub/sub (DB 2)
3. `status2` Go service relays to WebSocket clients
4. Frontend `controlBase.attach_status_stream()` updates UI panels

## Operational Notes

### Health Checks

The application exposes a health check endpoint:
```
GET /health
```

Returns `200 OK` with JSON payload when the application is ready. Checks:
- Redis connectivity
- File system access to runs directory

Use this endpoint for Kubernetes liveness/readiness probes or load balancer health checks.

### Logging

- **Application logs**: Structured logs to stdout (captured by Docker/Kubernetes)
- **Run logs**: Per-run logs stored in `<runid>/_logs/` directory
- **Status messages**: Ephemeral messages published to Redis pub/sub (DB 2) with 72-hour retention

### Static Asset Building

Static assets must be built before deployment:

```bash
# Build frontend assets (controller bundles, vendor libraries)
wctl build-static-assets

# Or manually inside container
docker exec weppcloud bash -c "cd /workdir/wepppy/wepppy/weppcloud/static-src && npm install && npm run build"
```

The `build_controllers_js.py` script automatically runs on container startup in development mode.

### Performance Considerations

- **Keep routes fast**: Offload work to RQ for tasks >2 seconds
- **Minimize NoDb lock time**: Acquire locks, mutate, dump, and release quickly
- **Cache expensive queries**: Use Redis DB 13 for hot data
- **Limit file I/O**: Avoid repeatedly reading large files; use memoization

## Frontend Integration

The frontend relies on a combination of Jinja2-rendered templates and JavaScript controllers for dynamic behavior.

- **Controller Bundling**: JavaScript modules in `wepppy/weppcloud/controllers_js/` are automatically discovered and bundled into `wepppy/weppcloud/static/js/controllers-gl.js` by the `build_controllers_js.py` script. This script runs automatically when the `weppcloud` service starts.

- **Run-Scoped URLs**: All API calls made from the frontend that are specific to a run **must** use the `url_for_run()` JavaScript helper. This function correctly prepends the `/runs/<runid>/<config>/` prefix to the URL, which is essential for routing requests within the context of a specific project run.

- **`controlBase`**: A shared JavaScript utility that provides helpers for making asynchronous HTTP requests, handling status updates from the WebSocket stream, and managing UI state.

## Developer Notes

### Project Structure

```
weppcloud/
├── app.py                    # Application factory
├── routes/                   # Flask blueprints
│   ├── batch_runner/         # Batch run management
│   ├── browse/               # Run browsing and listing
│   ├── command_bar/          # Command bar API
│   ├── nodb_api/             # NoDb state API
│   ├── reports/              # Report generation
│   ├── rq/                   # Background job triggers
│   └── ...
├── templates/                # Jinja2 templates
│   ├── browse/
│   ├── reports/
│   └── ...
├── controllers_js/           # Frontend JavaScript controllers
│   ├── build_controllers_js.py
│   ├── mapController.js
│   ├── climateController.js
│   └── ...
├── static/                   # Static assets
│   ├── dist/                 # Built assets (controllers-gl.js, vendor bundles)
│   ├── css/
│   └── ...
├── static-src/               # Frontend source (build tooling)
│   ├── package.json
│   ├── webpack.config.js
│   └── ...
├── utils/                    # Shared utilities
│   ├── helpers.py            # Common route helpers
│   └── ...
├── webservices/              # Internal microservices
│   ├── elevationquery/
│   ├── wmesque2/
│   └── dtale.py
└── README.md                 # This file
```

### Creating Blueprints

To maintain a clean and modular structure, new features should be implemented in their own Blueprints.

**When to extract a blueprint:**
- Routes share a logical feature area (e.g., RHEM reporting, command bar APIs).
- They have dedicated templates/static files or are likely to grow.
- The code requires specialized authorization or request handling that is easier to reason about in isolation.

**Authoring a new blueprint:**
1. Create a module under `wepppy/weppcloud/routes/` and define the blueprint.
   ```python
   from flask import Blueprint

   feature_bp = Blueprint('feature', __name__, url_prefix='/runs/<string:runid>/<string:config>/feature')
   ```
2. Move the relevant route functions into the module. Keep imports minimal and prefer helpers from `weppcloud.utils.helpers` (e.g., `get_wd`, `authorize`) instead of pulling from `app.py`.
3. Preserve route decorators exactly. Bring over any try/except blocks or logging so behavior remains identical.
4. Register the blueprint in `wepppy/weppcloud/app.py`:
   ```python
   from .routes.feature import feature_bp

   app.register_blueprint(feature_bp)
   ```
5. Remove the original route definitions from `app.py`.
6. Search for and update `url_for()` calls in templates to use the blueprint-scoped endpoint (e.g., `url_for('feature.my_route')`).
7. Run `python -m compileall .` and any relevant tests to validate the refactor.

### Tips
- Avoid circular imports by keeping blueprint modules free of app-level objects.
- Blueprint names (`Blueprint('rhem', ...`) become part of endpoint IDs. Keep them short and consistent with the folder name.
- Use `render_template` for HTML responses; it gracefully falls back to JSON on error, matching existing app behavior.
- Document new patterns in this file to ensure future refactors stay consistent.

### Testing

Run the test suite from within the Docker environment:

```bash
# All weppcloud tests
wctl run-pytest tests/weppcloud

# Specific test module
wctl run-pytest tests/weppcloud/routes/test_browse_bp.py

# With coverage
wctl run-pytest tests/weppcloud --cov=wepppy.weppcloud
```

**Frontend tests** (smoke tests):
```bash
# Navigate to static-src and run Playwright tests
wctl exec weppcloud bash
cd /workdir/wepppy/wepppy/weppcloud/static-src
npm run smoke
```

See [tests/README.md](../../tests/README.md) and [static-src/README.md](static-src/README.md) for detailed testing guidance.

### Common Pitfalls

- **Circular imports**: Don't import `app` inside blueprints; use helpers from `utils/` instead
- **Missing `url_for_run()`**: Frontend API calls to run-scoped routes must use the `url_for_run()` helper
- **NoDb locking**: Always use `with controller.locked():` for mutations and call `dump_and_unlock()`
- **Long-running routes**: Offload work to RQ; don't block Gunicorn workers for >2 seconds
- **Static asset staleness**: Rebuild assets after JavaScript changes; restart container to trigger bundling

## Further Reading

- [AGENTS.md](../../AGENTS.md) - Comprehensive development guide for AI and human developers
- [controllers_js/README.md](controllers_js/README.md) - Frontend controller architecture and bundling
- [docker/README.md](../../docker/README.md) - Docker deployment and development workflow
- [tests/weppcloud/README.md](../../tests/weppcloud/README.md) - Testing patterns for routes and controllers
- [API_REFERENCE.md](../../API_REFERENCE.md) - Complete API endpoint documentation
- [../../readme.md](../../readme.md) - Repository overview and architecture

## Credits

University of Idaho (2015-Present), Swansea University (2019-Present)

Contributors: Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frankenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller

License: BSD-3 Clause (see [license.txt](../../license.txt))
