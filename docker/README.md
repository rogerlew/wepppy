# Docker Compose Developer Guide

> **See also:** [AGENTS.md](../AGENTS.md) for Development Workflow, Docker Compose (Recommended), and Common Docker tasks sections.

This guide covers both the development (`docker-compose.dev.yml`) and production (`docker-compose.prod.yml`) Docker Compose stacks for WEPPcloud.
It also covers the production worker pool stack (`docker-compose.prod.worker.yml`) used on dedicated RQ worker hosts.

## Deployment Environments

| Environment | Host | Domain | Compose File | Notes |
|-------------|------|--------|--------------|-------|
| **Test Production** | `forest1.local` | `wc-prod.bearhive.duckdns.org` | `docker-compose.prod.yml` | Primary test production server |
| **Development** | `forest.local` | `wc.bearhive.duckdns.org` | `docker-compose.dev.yml` | Development with bind mounts |
| **Prod Worker Pool** | (separate worker host) | — | `docker-compose.prod.worker.yml` | Dedicated RQ workers connected to an external Redis (no Redis/Postgres services). |

### Test Production (forest1.local)

The test production server at `forest1.local` (accessible via `wc-prod.bearhive.duckdns.org`) should **always** use the production compose file:

```bash
cd /workdir/wepppy
./scripts/deploy-production.sh
# Or manually:
docker compose --env-file docker/.env -f docker/docker-compose.prod.yml up -d
```

### Production Worker Pool (Dedicated RQ Hosts)

Worker-only stacks (no Flask/Caddy/Redis/Postgres) use:
- Compose file: `docker/docker-compose.prod.worker.yml`
- Guide: `docker/prod-worker-deploy-guide.md`

Key `docker/.env` requirements for `docker-compose.prod.worker.yml`:
- `RQ_REDIS_URL` must point at a reachable Redis (DB 9). If unset, the compose default falls back to `redis:6379`, which only works when a `redis` service exists on the same Compose network.
- `WC1_DIR` and `GEODATA_DIR` must match the host mount points (shared run storage + geodata).
- `WEPPPY_ENV_FILE` controls the `env_file:` path for services. `wctl` sets it automatically; if running raw `docker compose`, set `WEPPPY_ENV_FILE=.env` and run from `docker/` to avoid `docker/docker/.env` path resolution failures.

Recommended: pin `wctl` on worker hosts and use it for ops (it generates a temporary env file and sets `WEPPPY_ENV_FILE` so `env_file:` paths resolve correctly).

```bash
cd /workdir/wepppy
./wctl/install.sh worker
wctl up -d rq-worker rq-worker-batch
wctl rq-info
```

Optional: keep `weppcloudr` behind a profile (so `wctl up -d` doesn’t start it unless requested):

```bash
export WCTL_COMPOSE_FILE_EXTRAS=docker/docker-compose.prod.worker.override.yml
wctl up -d rq-worker rq-worker-batch
```

### Development (Local)

For local development with live code reloading:

```bash
cd /workdir/wepppy
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build
```

## Dev vs Prod Differences

| Aspect | Dev (`docker-compose.dev.yml`) | Prod (`docker-compose.prod.yml`) |
|--------|-------------------------------|----------------------------------|
| **Redis storage** | Bind mount: `.docker-data/redis` | Named volume: `redis-data` |
| **Postgres data** | Bind mount: `.docker-data/postgres` | Named volume: `postgres-data` |
| **Postgres backups** | Bind mount: `.docker-data/postgres-backups` | Named volume: `postgres-backups` |
| **Code** | Bind-mounted (live reload) | Baked into image |
| **Container names** | `wepppy-*` prefix | `docker-*-1` (compose default) |

## Redis durability policy + RQ DB9 deploy flush policy

WEPPcloud uses a single Redis instance with multiple logical databases (DBs). Stacks that run a `redis` service enable Redis persistence by default so non-RQ state (especially Flask sessions in DB 11) survives routine redeploys and host restarts. Separately, deploy automation can intentionally clear only the RQ database (DB 9) during a deploy to drop queued/active jobs without wiping other Redis DBs.

### Behavior by environment

| Environment | Redis service? | Persistence | DB9 flush-on-deploy | Notes |
|---|---:|---|---|---|
| Dev (`docker-compose.dev.yml`) | Yes | Enabled by default (entrypoint env knobs) | Off by default (manual) | Use a manual DB9 flush when you want a clean local RQ slate. |
| Test-prod (`docker-compose.prod.yml`) | Yes | Enabled by default (entrypoint env knobs) | On by default (opt-out) | `./scripts/deploy-production.sh` flushes DB9 unless `--no-flush-rq-db` is passed. |
| wepp1 (`docker-compose.prod.yml` + `docker-compose.prod.wepp1.yml`) | Yes | Enabled by default (entrypoint env knobs) | Off by default (opt-in) | `./scripts/deploy-production.sh` preserves DB9 unless `--flush-rq-db` is passed. |
| Prod (`docker-compose.prod.yml` + host overrides) | Yes | Enabled by default (entrypoint env knobs) | On by default (opt-out) | DB9 flush is always scoped to RQ only; never a full Redis wipe. |
| Worker host (`docker-compose.prod.worker.yml`) | No | N/A (external Redis) | Off by default (opt-in) | Worker-only stacks must set `RQ_REDIS_URL` and do not manage Redis durability. |

### Redis persistence knobs (Redis server container only)

Stacks that define a `redis` service configure durability via `docker/redis-entrypoint.sh` using env vars (defaults shown):

- `REDIS_APPENDONLY=yes`
- `REDIS_APPENDFSYNC=everysec`
- `REDIS_AOF_USE_RDB_PREAMBLE=yes`
- `REDIS_SAVE_SCHEDULE="900 1 300 10 60 10000"`

Keyspace notifications remain enabled (`notify-keyspace-events Kh`, required by preflight), and Redis auth remains enabled via the `redis_password` secret.

### Operator verification commands

Inspect durability settings (inside the Redis container):

```bash
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" CONFIG GET appendonly'
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" CONFIG GET appendfsync'
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" CONFIG GET aof-use-rdb-preamble'
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" CONFIG GET save'
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" INFO persistence'
```

Verify DB9 contents (before a flush):

```bash
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" -n 9 DBSIZE'
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" -n 9 --scan --pattern "rq:*" | head'
```

Run the deploy-policy flush (DB 9 only):

```bash
# Recommended: stop workers first to avoid races.
wctl down rq-worker rq-worker-batch

# Dry-run / require-redis controls are supported.
./scripts/redis_flush_rq_db.sh --dry-run
./scripts/redis_flush_rq_db.sh --require-redis
./scripts/redis_flush_rq_db.sh
```

### Production Backup Location

On the production host, postgres backups are stored in the Docker named volume:
```
/var/lib/docker/volumes/docker_postgres-backups/_data/
```

To inspect backups (requires root):
```bash
sudo ls -la /var/lib/docker/volumes/docker_postgres-backups/_data/
# Or via container:
docker exec docker-postgres-backup-1 ls -la /backups/
```

Backups run daily with 7-day retention. To trigger a manual backup:
```bash
docker logs docker-postgres-backup-1  # Check recent backup status
```

## Prerequisites
- Docker Desktop or a recent Docker Engine.
- `docker compose` plugin (v2).
- Secret files under `docker/secrets/` (gitignored) as defined in `docs/infrastructure/secrets.md`.
- Optional non-secret overrides in `docker/.env` (gitignored). Defaults live in `docker/defaults.env` (committed).

```bash
# Non-secret overrides only (optional).
cat > docker/.env <<EOF
UID=$(id -u)
GID=$(id -g)
WC1_DIR=/wc1
GEODATA_DIR=/wc1/geodata
CADDY_FILE=./caddy/Caddyfile
EXTERNAL_HOST=wc.bearhive.duckdns.org
EXTERNAL_HOST_DESCRIPTION=forest.local
CAP_SITE_KEY=your-public-site-key
EOF
chmod 600 docker/.env

# Secrets as files (examples; do not commit).
install -d -m 700 docker/secrets
python -c 'import secrets; print(secrets.token_urlsafe(64))' > docker/secrets/flask_secret_key
python -c 'import secrets; print(secrets.token_urlsafe(32))' > docker/secrets/flask_security_password_salt
python -c 'import secrets; print(secrets.token_urlsafe(64))' > docker/secrets/wepp_auth_jwt_secrets
python -c 'import secrets; print(secrets.token_urlsafe(64))' > docker/secrets/agent_jwt_secret
python -c 'import secrets; print(secrets.token_urlsafe(64))' > docker/secrets/wepp_mcp_jwt_secret
python -c 'import secrets; print(secrets.token_urlsafe(32))' > docker/secrets/postgres_password
python -c 'import secrets; print(secrets.token_urlsafe(32))' > docker/secrets/redis_password
python -c 'import secrets; print(secrets.token_urlsafe(32))' > docker/secrets/dtale_internal_token
python -c 'import secrets; print(secrets.token_urlsafe(32))' > docker/secrets/cap_secret

# Provider-issued API keys (required when using those integrations).
printf '%s\n' "your-opentopography-key" > docker/secrets/opentopography_api_key
printf '%s\n' "your-climate-engine-key" > docker/secrets/climate_engine_api_key

chmod 600 docker/secrets/*
```

> To run everything as `roger:docker`, set `UID=1000` and `GID=$(getent group docker | cut -d: -f3)` (typically `993`). Ensure the group exists on the host; Compose passes numeric ids straight through.

## wctl (weppcloud control)
`wctl` is the supported wrapper for `docker compose` (see `wctl/install.sh`). It merges `docker/defaults.env` plus optional `docker/.env` + host overrides, escapes `$` for Compose interpolation, and sets `WEPPPY_ENV_FILE` for `env_file:` wiring.

One-time install (pins the default compose file for the host):

```bash
./wctl/install.sh dev|prod|wepp1|worker
```

Common commands:

```bash
wctl ps
wctl logs -f rq-worker
wctl rq-info
wctl docker compose config
```

## Service Catalog

| Service        | Purpose | Ports | Notes |
|----------------|---------|-------|-------|
| `weppcloud`    | Main Flask application served via Gunicorn | 8000 | Depends on Redis & Postgres; receives `/weppcloud/*` traffic from Caddy. |
| `status`       | Go WebSocket bridge (`services/status2`) for live run telemetry | 9002 | Consumes Redis pub/sub (DB 2). |
| `preflight`    | Go microservice (`services/preflight2`) that streams readiness state | 9001 | Requires Redis keyspace notifications (`notify-keyspace-events Kh`). |
| `browse`       | Starlette browse/download microservice | 9009 | Handles `/weppcloud/runs/.../browse|download|gdalinfo`. |
| `query-engine` | FastAPI (Uvicorn) for analytical lookups | 8041 | Reload enabled for dev loop. |
| `rq-engine`    | FastAPI (Uvicorn) for RQ job polling endpoints | 8042 | Serves `/rq-engine/api/*` jobinfo/jobstatus polling. |
| `weppcloudr`   | R (Plumber) renderer for WEPPcloud reports | 8050 | Serves `/weppcloudr/*`; mounts R templates and run volumes; caches rendered HTML in run export dirs. |
| `rq-worker`    | RQ worker pool servicing Redis queue DB 9 | — | Shares code volume; respects `UID`/`GID`. |
| `rq-worker-batch` | RQ worker pool for batch queue (long-running jobs) | — | 4 workers, 8GB shm, higher resource limits. |
| `redis`        | Redis 7.4 | 6379 | Dev: `.docker-data/redis`, Prod: `redis-data` volume |
| `postgres`     | PostgreSQL 16 | 5432 | Dev: `.docker-data/postgres`, Prod: `postgres-data` volume |
| `caddy`        | Reverse proxy + TLS terminator (dev: HTTP only) | 8080 | Serves static assets and forwards to upstream services. |
| Legacy profiles (`elevationquery`, `metquery`, `wmesque`, `wmesque2`) | Optional legacy web services | 8002, 8004, 8003, 8030 | Activated via `--profile legacy`. |
| `webpush`      | Placeholder container for future WebPush service | — | No-op until implemented. |
| `f-esri`       | Auxiliary image for ESRI tooling | — | Stays idle (`tail -f /dev/null`). |

### Scaling rq-worker-batch

In `docker-compose.dev.yml`, `rq-worker-batch` uses a fixed `container_name`, so Compose scaling is not available. To add a second pool without interrupting the stack, clone the existing batch worker configuration and start another container on the same network.

In `docker-compose.prod.worker.yml`, `rq-worker-batch` does not set `container_name`, so Compose scaling works (each container already runs a multi-process `rq worker-pool -n ...`).

Preparation (one-time):
```bash
# Store the batch worker env in the repo (ignored by git).
mv /tmp/wepppy-rq-worker-batch.env docker/wepppy-rq-worker-batch.env
```

Start a second batch worker pool:
```bash
# docker/wepppy-rq-worker-batch.env should include non-secret env only (no passwords/tokens).
docker run -d \
  --name wepppy-rq-worker-batch-2 \
  --network wepppy-net \
  --cpuset-cpus "0-39" \
  --shm-size 8g \
  --ulimit nofile=1000000:1000000 \
  --user 1000:993 \
  --workdir /workdir/wepppy \
  --env-file docker/wepppy-rq-worker-batch.env \
  -v "$(pwd)/docker/secrets/redis_password:/run/secrets/redis_password:ro" \
  --volumes-from wepppy-rq-worker-batch \
  --init wepppy-dev \
  bash -lc 'set -euo pipefail; REDIS_PASSWORD="$(cat /run/secrets/redis_password)"; exec rq worker-pool -n "4" -u "redis://:${REDIS_PASSWORD}@redis:6379/9" --logging-level INFO --worker-class wepppy.rq.WepppyRqWorker batch'
```

Inspect and stop:
```bash
wctl rq-info
docker stop wepppy-rq-worker-batch-2
docker rm wepppy-rq-worker-batch-2
```

### Networking
- All services share the default Compose network; Caddy resolves others by container name.
- External access happens through Caddy on `http://localhost:8080`. It proxies:
- `/weppcloud/static/*` directly from the mounted repo (`wepppy/weppcloud/static`) using Caddy’s `file_server`.
- `/weppcloud/*` to the Flask app, preserving `X-Forwarded-*` headers.
- `/rq-engine/*` to the rq-engine FastAPI service for jobstatus/jobinfo polling and upload-capable endpoints (Caddy strips `/rq-engine` and forwards `X-Forwarded-Prefix: /rq-engine`; extended upstream timeouts apply there).
- `/weppcloud/runs/.../(browse|download|aria2c.spec|gdalinfo)` to the Starlette browse microservice.
- `/weppcloudr/*` to the Plumber renderer (port 8050) for report generation (Deval in the Details).
- `/weppcloud-microservices/status` and `/weppcloud-microservices/preflight` to the Go microservices.

### Volumes & Bind Mounts
- Source code (`../`) plus sibling repositories (`../../wepppy2`, `../../weppcloud-wbt`, etc.) are bind-mounted read-write into every Python container so code changes reflect instantly.
- Redis and Postgres use dedicated host directories under `../.docker-data/` for persistence.
- Caddy mounts the static assets read-only (`../wepppy/weppcloud/static:/srv/weppcloud/static:ro`).
- The `weppcloudr` container binds the R service repo (`../weppcloudR`), the legacy template repo (`../WEPPcloudR`), run storage mounts (`${GEODATA_DIR}`, `${WC1_DIR}`), and a persistent `weppcloudr-renv-cache` volume for R package caches.

## Runtime User and Group
The shared Compose anchor sets `user: "${UID:-1000}:${GID:-993}"`, so by default every service runs as `roger` (uid `1000`) and `docker` (gid `993`). Adjust `docker/.env` if your host uses different ids or you prefer to inherit the active shell user.

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
  `docker compose -f docker/docker-compose.dev.yml exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)"'`

- **Stop everything**  
  `docker compose -f docker/docker-compose.dev.yml down`

## Troubleshooting
- **Static assets 404** — ensure the Caddy container is up and the repo is mounted. The file server path is `/srv/weppcloud/static`; missing files there won’t be proxied to Flask.
- **Browse service returns “Run '' either doesn’t exist” on `/browse/` URLs** — this means Caddy routed the request to the Flask app instead of the browse microservice (you’ll see `Server: gunicorn` in the response). Verify in `docker/caddy/Caddyfile` that the browse/dtale/download/gdalinfo matchers stay **above** the catch-all `handle_path /weppcloud*` block; re-ordering those blocks causes this symptom.
- **Permission denied when writing to bind-mounted directories** — double-check `UID`/`GID` in `docker/.env` and recreate containers. Existing files created with old ids may need a `chown`.
- **`I have no name!` shell prompt** — indicates the uid lacks an `/etc/passwd` entry. Adjust the Dockerfile if cosmetic prompts matter.
- **Redis connection errors on startup** — the microservices depend on Redis; ensure `redis` comes up cleanly, that keyspace notifications include `Kh`, or restart dependent containers (`docker compose ... restart status preflight browse`).
- **Worker pools crash trying to connect to `redis:6379`** — `docker-compose.prod.worker.yml` does not run a `redis` service. If your worker stack is still env-based (pre-secrets migration), set `RQ_REDIS_URL=redis://:<password>@<redis_host>:6379/9` in `docker/.env`. If the secrets-as-files contract is enabled on the worker host, set `RQ_REDIS_URL=redis://<redis_host>:6379/9` and provide `docker/secrets/redis_password`. Use `wctl rq-info` to confirm workers registered.

Refer back to this document whenever you add services, change ports, or adjust the proxy topology so the Compose stack stays in sync with production expectations.

---

## Production Deployment Guide

See also: `docs/infrastructure/secrets.md`, `docs/mini-work-packages/20260213_secrets_migration.md`.

This stack uses Docker Compose `secrets:` mounted to `/run/secrets/<secret_id>` with `*_FILE` env vars.
Do not place secret values in `docker/.env`.

### Pre-Deployment Checklist

- Secrets: populate `docker/secrets/` on the host (mode `0600`), one file per secret ID.
- Non-secrets: keep host-specific overrides in `docker/.env` (optional). Base defaults live in `docker/defaults.env`.
- Static assets: run `wctl build-static-assets --prod` (or follow the static-src build steps if you are not using `wctl`).
- Data: verify `/wc1` and `/geodata` exist and are mounted correctly.

### Deploy (Recommended: wctl)

```bash
cd /workdir/wepppy
./wctl/install.sh prod
wctl down
wctl build
wctl up -d
wctl ps
wctl logs -f weppcloud
```

### Verify

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8080/health
wctl exec redis sh -lc 'redis-cli -a "$(cat /run/secrets/redis_password)" ping'
wctl exec postgres pg_isready -U wepppy -d wepppy
```

Notes:
- `wctl docker compose config` should only show `*_FILE` paths (no secret values).
- Rotate secrets by updating the underlying files and restarting all dependent services together.

### Production vs Development Differences

| Aspect | Development (`dev.yml`) | Production (`prod.yml`) |
|--------|------------------------|------------------------|
| **Code mounting** | Bind mount (live reload) | Copied into image |
| **Static assets** | Served by Flask (dev mode) | Pre-built, served by Caddy |
| **User** | `${UID}:${GID}` from env | `roger:docker` (1000:993) |
| **Vendors** | .pth files to sibling repos | Cloned into `/opt/vendor` |
| **Dependencies** | Shared host packages | Bundled in image |
| **Rebuild freq** | Rare (only for deps) | Every deployment |
| **Health checks** | Optional | Enforced |

### Agent Deployment Workflow

For AI agents performing deployments:

1. **Preflight checks:**
   - Verify git branch/commit
   - Confirm required secret files exist under `docker/secrets/` (mode `0600`)
   - Confirm static assets are built
   - Verify data directories (`/wc1`, `/geodata`) are accessible

2. **Build phase:**
   - Run `docker compose -f docker/docker-compose.prod.yml build`
   - Expect 10-15 min for fresh builds
   - Monitor for errors in build output

3. **Deploy phase:**
   - Stop existing containers: `docker compose -f docker/docker-compose.prod.yml down`
   - Start new containers: `docker compose -f docker/docker-compose.prod.yml up -d`
   - Wait for health checks to pass

4. **Verification phase:**
   - Run smoke tests (curl endpoints)
   - Check logs for errors
   - Verify services are responding

5. **Monitoring:**
   - Watch logs for 5-10 minutes post-deployment
   - Check resource usage with `docker stats`
   - Test critical user workflows

6. **Rollback trigger:**
   - If any critical service fails health checks after 5 minutes
   - If error rate in logs exceeds acceptable threshold
   - If user-reported issues indicate regression

### Production Checklist Summary

- [ ] Secret files (`docker/secrets/*`) configured (no secret values in `docker/.env`)
- [ ] Static assets built on host (`npm run build` + copy to static/)
- [ ] Latest code pulled from git
- [ ] Docker images built successfully
- [ ] Old containers stopped gracefully
- [ ] New containers started and healthy
- [ ] Smoke tests passing (HTTP 200 on key endpoints)
- [ ] Logs reviewed for errors
- [ ] Database connectivity verified
- [ ] Redis operational
- [ ] Static assets accessible (404s resolved)
- [ ] Monitoring established
