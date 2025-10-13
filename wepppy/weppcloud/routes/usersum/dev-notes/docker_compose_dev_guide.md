# Docker Compose Developer Guide

This guide walks through the local docker-compose stack (`docker/docker-compose.dev.yml`) that mirrors the WEPPcloud runtime. Use it as a map when onboarding new engineers or debugging environment issues.

## Prerequisites
- Docker Desktop or a recent Docker Engine.
- `docker compose` plugin (v2).
- A populated `docker/.env` file containing at least `POSTGRES_PASSWORD` and optionally `UID`/`GID`.

```bash
cat > docker/.env <<EOF
UID=$(id -u)          # customise to match the user you want inside the containers
GID=$(id -g)
POSTGRES_PASSWORD=localdev
EOF
```

> To run everything as `www-data:docker` set `UID=33` and `GID=<webgroup gid>` (retrieve the latter with `getent group docker`). Ensure the group exists on the host; Compose passes numeric ids straight through.

Start or rebuild the stack with:

```bash
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build
```

## Service Catalogue

| Service        | Purpose | Ports | Notes |
|----------------|---------|-------|-------|
| `weppcloud`    | Main Flask application served via Gunicorn | 8000 | Depends on Redis & Postgres; receives `/weppcloud/*` traffic from Caddy. |
| `status`       | Go WebSocket bridge (`services/status2`) for live run telemetry | 9002 | Consumes Redis pub/sub (DB 2). |
| `preflight`    | Go microservice (`services/preflight2`) that streams readiness state | 9001 | Requires Redis keyspace notifications (`notify-keyspace-events Kh`). |
| `browse`       | Starlette browse/download microservice | 9009 | Handles `/weppcloud/runs/.../browse|download|gdalinfo`. |
| `query-engine` | FastAPI (Uvicorn) for analytical lookups | 8041 | Reload enabled for dev loop. |
| `weppcloudr`   | R (Plumber) renderer for WEPPcloud reports | 8050 | Serves `/weppcloudr/*`; mounts R templates and run volumes; caches rendered HTML in run export dirs. |
| `rq-worker`    | RQ worker pool servicing Redis queue DB 9 | — | Shares code volume; respects `UID`/`GID`. |
| `redis`        | Redis 7.4 | 6379 | Persists under `../.docker-data/redis`. |
| `postgres`     | PostgreSQL 16 | 5432 | Data dir at `../.docker-data/postgres`. |
| `caddy`        | Reverse proxy + TLS terminator (dev: HTTP only) | 8080 | Serves static assets and forwards to upstream services. |
| Legacy profiles (`elevationquery`, `metquery`, `wmesque`, `wmesque2`) | Optional legacy web services | 8002, 8004, 8003, 8030 | Activated via `--profile legacy`. |
| `webpush`      | Placeholder container for future WebPush service | — | No-op until implemented. |
| `f-esri`       | Auxiliary image for ESRI tooling | — | Stays idle (`tail -f /dev/null`). |

### Networking
- All services share the default Compose network; Caddy resolves others by container name.
- External access happens through Caddy on `http://localhost:8080`. It proxies:
- `/weppcloud/static/*` directly from the mounted repo (`wepppy/weppcloud/static`) using Caddy’s `file_server`.
- `/weppcloud/*` to the Flask app, preserving `X-Forwarded-*` headers.
- `/weppcloud/runs/.../(browse|download|aria2c.spec|gdalinfo)` to the Starlette browse microservice.
- `/weppcloudr/*` to the Plumber renderer (port 8050) for report generation (Deval in the Details).
- `/weppcloud-microservices/status` and `/weppcloud-microservices/preflight` to the Go microservices.

### Volumes & Bind Mounts
- Source code (`../`) plus sibling repositories (`../../wepppy2`, `../../whitebox-tools`, etc.) are bind-mounted read-write into every Python container so code changes reflect instantly.
- Redis and Postgres use dedicated host directories under `../.docker-data/` for persistence.
- Caddy mounts the static assets read-only (`../wepppy/weppcloud/static:/srv/weppcloud/static:ro`).
- The `weppcloudr` container binds the R service repo (`../weppcloudR`), the legacy template repo (`../WEPPcloudR`), run storage mounts (`${GEODATA_DIR}`, `${WC1_DIR}`), and a persistent `weppcloudr-renv-cache` volume for R package caches.

## Runtime User and Group
The shared Compose anchor sets `user: "${UID:-1000}:${GID:-1000}"`, so every service runs with the numeric ids from `docker/.env`. This prevents root-owned artifacts on the host and lets you align container perms with whichever account manages the repository.

### Switching to `www-data:webgroup`
1. Confirm the ids on the host:  
   ```bash
   id www-data   # typically uid=33
   getent group webgroup
   ```
2. Update `docker/.env`:
   ```env
   UID=33
   GID=1234   # replace with webgroup gid
   ```
3. Recreate containers:  
   ```bash
   docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up -d --build
   ```

If you want shells inside the containers to show `www-data@...` instead of `I have no name!`, add a matching `/etc/passwd` entry in the Dockerfile or via an entrypoint script so the uid resolves to a username.

## Common Workflows
- **Rebuild only the core app**  
  `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build weppcloud`

- **Tail logs for the status microservice**  
  `docker compose -f docker/docker-compose.dev.yml logs -f status`

- **Run database migrations (inside app container)**  
  `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml exec weppcloud flask db upgrade`

- **Inspect Redis**  
  `docker compose -f docker/docker-compose.dev.yml exec redis redis-cli`

- **Stop everything**  
  `docker compose -f docker/docker-compose.dev.yml down`

## Troubleshooting
- **Static assets 404** — ensure the Caddy container is up and the repo is mounted. The file server path is `/srv/weppcloud/static`; missing files there won’t be proxied to Flask.
- **Permission denied when writing to bind-mounted directories** — double-check `UID`/`GID` in `docker/.env` and recreate containers. Existing files created with old ids may need a `chown`.
- **`I have no name!` shell prompt** — indicates the uid lacks an `/etc/passwd` entry. Adjust the Dockerfile if cosmetic prompts matter.
- **Redis connection errors on startup** — the microservices depend on Redis; ensure `redis` comes up cleanly, that keyspace notifications include `Kh`, or restart dependent containers (`docker compose ... restart status preflight browse`).

Refer back to this document whenever you add services, change ports, or adjust the proxy topology so the Compose stack stays in sync with production expectations.
