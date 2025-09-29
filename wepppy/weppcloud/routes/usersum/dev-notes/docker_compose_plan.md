# Docker Compose Topology Plan

## Goals
- Run the WEPP monolith (Flask app, RQ workers, Tornado microservices, legacy webservices) with one `docker compose` command.
- Share the same Python environment across containers using [`uv`](https://github.com/astral-sh/uv) for fast dependency installs and rebuilds.
- Mount the local `wepppy/` source tree into every service container for live-edit development.
- Centralize environment via the existing project `.env` so all services inherit identical settings.

## Services (first pass)
| Service | Purpose |
| --- | --- |
| `weppcloud` | Gunicorn/Flask primary web app + static assets |
| `status` | Tornado WebSocket proxy for Redis status channels |
| `preflight` | Tornado preflight microservice |
| `browse` | Starlette File browser service |
| `webpush` | Push notifications/webpush worker |
| `elevationquery` | Elevation lookup microservice |
| `wmesque` | Legacy WMESque interface (deprecated but kept for parity) |
| `wmesque2` | WMESque v2 service |
| `metquery` | Meteorological (MET) query service |
| `postgres` | Application database (shared) |
| `redis` | Redis broker/cache (if not using external instance) |
| `caddy` | Reverse Proxy |

> All Python services consume the same repository mount and `.env` file. Profiles can be used to toggle optional services (e.g., omit `wmesque` by default).

## Shared Build Strategy
- Base image: start from Ubuntu/`python:3.11-slim` (or similar) with system deps (GDAL, WEPP binaries, Redis CLI if needed).
- Copy `pyproject.toml`/`requirements.txt` (if available) and run `uv pip install --requirement requirements.txt --system`. `uv` caches wheels within Docker layers, so code changes only affect the bind mount.
- Containers run as a non-root user to avoid permission drift on bind mounts.

## Volume Mounts
```yaml
services:
  weppcloud:
    volumes:
      - ./wepppy:/app/wepppy
      - ./.env:/app/.env:ro
  status:
    volumes:
      - ./wepppy:/app/wepppy
      - ./.env:/app/.env:ro
  # ...repeat for other Python services
```
- Use a named volume `uv-cache` if we want to persist the `uv` cache between rebuilds (optional).
- Static assets can be collected at runtime inside the container; the bind mount ensures edits propagate immediately.

## Postgres Persistence
- Attach a named volume for database state so container recreation does not wipe data:
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: weppcloud
      POSTGRES_USER: wepp
      POSTGRES_PASSWORD: change_me
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```
- For dev environments that should mirror production data, use `external: true` and point to an existing host path or managed volume.
- If an external Postgres is already provided (common in ops), drop the `postgres` service and set `POSTGRES_HOST` in `.env` accordingly.

## Startup Workflow
1. Ensure `.env` is populated with Redis host, Postgres creds, and any feature flags.
2. Run `docker compose build` (uses `uv` to install Python deps).
3. Bring up the stack: `docker compose up weppcloud status preflight ...` (or `docker compose up --profile core`).
4. Run migrations inside the `weppcloud` container if needed: `docker compose run --rm weppcloud flask db upgrade`.

## Open Questions / Next Steps
- Confirm which services absolutely need to run in development vs. deployment profiles.
- Decide whether Redis should run inside Compose or assume an external instance (current code treats Redis host as the only variable).
- Script helper commands (`make compose-up`, `compose-down`) to streamline onboarding.
- Document how to seed Postgres and Redis in dev (fixtures, sample data, etc.).

## References
- `wepppy/weppcloud/routes/usersum/dev-notes/redis_config_refactor.md` for central Redis configuration.

