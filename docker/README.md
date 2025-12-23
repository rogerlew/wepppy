# Docker Compose Developer Guide

> **See also:** [AGENTS.md](../AGENTS.md) for Development Workflow, Docker Compose (Recommended), and Common Docker tasks sections.

This guide covers both the development (`docker-compose.dev.yml`) and production (`docker-compose.prod.yml`) Docker Compose stacks for WEPPcloud.

## Deployment Environments

| Environment | Host | Domain | Compose File | Notes |
|-------------|------|--------|--------------|-------|
| **Test Production** | `forest1.local` | `wc-prod.bearhive.duckdns.org` | `docker-compose.prod.yml` | Primary test production server |
| **Development** | `forest.local` | `wc.bearhive.duckdns.org` | `docker-compose.dev.yml` | Development with bind mounts |

### Test Production (forest1.local)

The test production server at `forest1.local` (accessible via `wc-prod.bearhive.duckdns.org`) should **always** use the production compose file:

```bash
cd /workdir/wepppy
./scripts/deploy-production.sh
# Or manually:
docker compose --env-file docker/.env -f docker/docker-compose.prod.yml up -d
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
- A populated `docker/.env` file containing at least `POSTGRES_PASSWORD` and optionally `UID`/`GID`.

```bash
cat > docker/.env <<EOF
UID=$(id -u)          # customize to match the user you want inside the containers
GID=$(id -g)
POSTGRES_PASSWORD=localdev
EOF
```

> To run everything as `roger:docker`, set `UID=1000` and `GID=$(getent group docker | cut -d: -f3)` (typically `993`). Ensure the group exists on the host; Compose passes numeric ids straight through.

## wctl (weppcloud control)
Wrapper for running docker compose commands

e.g

```
wctl logs weppcloud
```

## Service Catalog

| Service        | Purpose | Ports | Notes |
|----------------|---------|-------|-------|
| `weppcloud`    | Main Flask application served via Gunicorn | 8000 | Depends on Redis & Postgres; receives `/weppcloud/*` traffic from Caddy. |
| `status`       | Go WebSocket bridge (`services/status2`) for live run telemetry | 9002 | Consumes Redis pub/sub (DB 2). |
| `preflight`    | Go microservice (`services/preflight2`) that streams readiness state | 9001 | Requires Redis keyspace notifications (`notify-keyspace-events Kh`). |
| `browse`       | Starlette browse/download microservice | 9009 | Handles `/weppcloud/runs/.../browse|download|gdalinfo`. |
| `query-engine` | FastAPI (Uvicorn) for analytical lookups | 8041 | Reload enabled for dev loop. |
| `weppcloudr`   | R (Plumber) renderer for WEPPcloud reports | 8050 | Serves `/weppcloudr/*`; mounts R templates and run volumes; caches rendered HTML in run export dirs. |
| `rq-worker`    | RQ worker pool servicing Redis queue DB 9 | — | Shares code volume; respects `UID`/`GID`. |
| `redis`        | Redis 7.4 | 6379 | Dev: `.docker-data/redis`, Prod: `redis-data` volume |
| `postgres`     | PostgreSQL 16 | 5432 | Dev: `.docker-data/postgres`, Prod: `postgres-data` volume |
| `caddy`        | Reverse proxy + TLS terminator (dev: HTTP only) | 8080 | Serves static assets and forwards to upstream services. |
| Legacy profiles (`elevationquery`, `metquery`, `wmesque`, `wmesque2`) | Optional legacy web services | 8002, 8004, 8003, 8030 | Activated via `--profile legacy`. |
| `webpush`      | Placeholder container for future WebPush service | — | No-op until implemented. |
| `f-esri`       | Auxiliary image for ESRI tooling | — | Stays idle (`tail -f /dev/null`). |

### Networking
- All services share the default Compose network; Caddy resolves others by container name.
- External access happens through Caddy on `http://localhost:8080`. It proxies:
- `/weppcloud/static/*` directly from the mounted repo (`wepppy/weppcloud/static`) using Caddy’s `file_server`.
- `/weppcloud/*` to the Flask app, preserving `X-Forwarded-*` headers.
- `/upload/*` to the Flask app with a 20-minute upstream timeout for file uploads; Caddy strips `/upload` and forwards `X-Forwarded-Prefix: /upload` so Flask can distinguish upload traffic.
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
  `docker compose -f docker/docker-compose.dev.yml exec redis redis-cli`

- **Stop everything**  
  `docker compose -f docker/docker-compose.dev.yml down`

## Troubleshooting
- **Static assets 404** — ensure the Caddy container is up and the repo is mounted. The file server path is `/srv/weppcloud/static`; missing files there won’t be proxied to Flask.
- **Browse service returns “Run '' either doesn’t exist” on `/browse/` URLs** — this means Caddy routed the request to the Flask app instead of the browse microservice (you’ll see `Server: gunicorn` in the response). Verify in `docker/caddy/Caddyfile` that the browse/dtale/download/gdalinfo matchers stay **above** the catch-all `handle_path /weppcloud*` block; re-ordering those blocks causes this symptom.
- **Permission denied when writing to bind-mounted directories** — double-check `UID`/`GID` in `docker/.env` and recreate containers. Existing files created with old ids may need a `chown`.
- **`I have no name!` shell prompt** — indicates the uid lacks an `/etc/passwd` entry. Adjust the Dockerfile if cosmetic prompts matter.
- **Redis connection errors on startup** — the microservices depend on Redis; ensure `redis` comes up cleanly, that keyspace notifications include `Kh`, or restart dependent containers (`docker compose ... restart status preflight browse`).

Refer back to this document whenever you add services, change ports, or adjust the proxy topology so the Compose stack stays in sync with production expectations.

---

## Production Deployment Guide

> **Target Audience:** AI agents and human operators deploying to test/production servers.

This section provides a step-by-step checklist for deploying WEPPcloud to production environments using `docker-compose.prod.yml`.

### Pre-Deployment Checklist

**1. Environment File Setup**

Create or verify `docker/.env` with production credentials:

```bash
# Navigate to docker directory
cd /workdir/wepppy/docker

# Generate secure secrets
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')
SECURITY_PASSWORD_SALT=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
DTALE_INTERNAL_TOKEN=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Create .env file
cat > .env <<EOF
# User/Group for container runtime
UID=$(id -u)
GID=$(id -g)

# External host configuration (use wc-prod for test production)
EXTERNAL_HOST=wc-prod.bearhive.duckdns.org
EXTERNAL_HOST_DESCRIPTION="WEPPcloud Test Production Server"

# Database credentials
POSTGRES_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Flask secrets
SECRET_KEY=${SECRET_KEY}
SECURITY_PASSWORD_SALT=${SECURITY_PASSWORD_SALT}

# D-Tale security token
DTALE_INTERNAL_TOKEN=${DTALE_INTERNAL_TOKEN}

# JWT secret for authentication
WEPP_AUTH_JWT_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')

# WeppcloudR container name (must match actual container name from docker compose)
WEPPCLOUDR_CONTAINER=docker-weppcloudr-1

# Optional: Override default ports if needed
# WEPPCLOUD_PORT=8000
# REDIS_PORT=6379
# POSTGRES_PORT=5432
EOF

# Secure the .env file
chmod 600 .env
```

**2. Build Static Assets**

⚠️ **CRITICAL:** Production uses bind mounts for static files. You MUST build assets on the host before deployment.

```bash
# Navigate to static-src directory
cd /workdir/wepppy/wepppy/weppcloud/static-src

# Install dependencies (only needed once or when package.json changes)
npm ci --legacy-peer-deps

# Build production assets (vendor libraries)
npm run build

# Copy vendor assets to static directory
cp -r dist/vendor/* ../static/vendor/

# Build controllers-gl.js and unitizer_map.js
cd /workdir/wepppy/wepppy/weppcloud/controllers_js
python build_controllers_js.py

# Verify critical files exist
ls -la /workdir/wepppy/wepppy/weppcloud/static/js/controllers-gl.js
ls -la /workdir/wepppy/wepppy/weppcloud/static/js/unitizer_map.js
ls -la /workdir/wepppy/wepppy/weppcloud/static/vendor/purecss/pure-min.css
ls -la /workdir/wepppy/wepppy/weppcloud/static/vendor/bootstrap/bootstrap.css
ls -la /workdir/wepppy/wepppy/weppcloud/static/vendor/jquery/jquery.js
ls -la /workdir/wepppy/wepppy/weppcloud/static/vendor/leaflet/leaflet.js
```

**Expected output:** All vendor directories (bootstrap, bootstrap-toc, datatables, jquery, leaflet, purecss, spin) should exist in `wepppy/weppcloud/static/vendor/`.

**3. Verify Data Directories**

Production requires access to geodata and run storage:

```bash
# Verify required mounts exist
ls -ld /geodata
ls -ld /wc1

# If directories don't exist, create them with proper permissions
sudo mkdir -p /geodata /wc1
sudo chown $(id -u):$(id -g) /geodata /wc1
```

### Deployment Steps

**Step 1: Pull Latest Code**

```bash
cd /workdir/wepppy

# Fetch latest changes
git fetch origin

# Check current branch and status
git status

# Pull updates (or checkout specific tag/commit)
git pull origin master

# Verify you're on the intended commit
git log -1 --oneline
```

**Step 2: Build Docker Images**

```bash
# Build all images (this will take 10-15 minutes on first build)
docker compose -f docker/docker-compose.prod.yml build

# Check for build errors
echo "Build exit code: $?"

# Verify images were created
docker images | grep -E "wepppy|wepppy-status|wepppy-preflight|weppcloudr"
```

**Expected behavior:**
- First build: ~10-15 minutes (includes apt packages, Python dependencies, vendor repos)
- Subsequent builds: 2-5 minutes (Docker layer caching)
- The `chown` step (step 15/16) takes 5-8 minutes due to ~115K files

**Step 3: Stop Existing Services**

```bash
# Gracefully stop all containers
docker compose -f docker/docker-compose.prod.yml down

# Verify all containers are stopped
docker compose -f docker/docker-compose.prod.yml ps -a

# Optional: Remove old volumes (DATA LOSS WARNING)
# docker compose -f docker/docker-compose.prod.yml down -v
```

**Step 4: Start Services**

```bash
# Start all services in detached mode
docker compose -f docker/docker-compose.prod.yml up -d

# Monitor startup logs
docker compose -f docker/docker-compose.prod.yml logs -f

# Wait for services to become healthy (Ctrl+C to exit logs)
```

**Step 5: Verify Deployment**

```bash
# Check service status
docker compose -f docker/docker-compose.prod.yml ps

# Verify critical services are running
docker compose -f docker/docker-compose.prod.yml ps | grep -E "weppcloud|redis|postgres|caddy|status|preflight"

# Check individual service health
docker compose -f docker/docker-compose.prod.yml exec weppcloud curl -f http://localhost:8000/health || echo "FAILED"
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli ping
docker compose -f docker/docker-compose.prod.yml exec postgres pg_isready -U wepppy

# Verify static assets are accessible through Caddy
docker compose -f docker/docker-compose.prod.yml exec caddy ls -la /srv/weppcloud/static/vendor/purecss/
```

**Step 6: Smoke Test**

```bash
# Test HTTP endpoints (replace with your actual host)
curl -I http://localhost:8080/health
curl -I http://localhost:8080/weppcloud/
curl -I http://localhost:8080/weppcloud/static/vendor/purecss/pure-min.css

# Expected: All should return 200 or 30x (not 404/500)
```

### Post-Deployment Verification

**Check Application Logs:**

```bash
# View recent logs from all services
docker compose -f docker/docker-compose.prod.yml logs --tail=100

# Monitor for errors in specific services
docker compose -f docker/docker-compose.prod.yml logs -f weppcloud
docker compose -f docker/docker-compose.prod.yml logs -f rq-worker
```

**Verify Database Connectivity:**

```bash
# Check Postgres connection from weppcloud container
docker compose -f docker/docker-compose.prod.yml exec weppcloud bash -c \
  "python -c 'from wepppy.weppcloud.app import app; print(\"DB OK\" if app else \"FAILED\")'"
```

**Check Redis:**

```bash
# Verify Redis is responding
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli INFO | grep -E "redis_version|connected_clients"

# Check keyspace notifications are enabled
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli CONFIG GET notify-keyspace-events
# Expected: "Kh"
```

**Monitor Resource Usage:**

```bash
# Check container resource consumption
docker stats --no-stream

# Check disk usage
df -h /wc1
df -h /geodata
```

### Rollback Procedure

If deployment fails, rollback to previous version:

```bash
# Stop new deployment
docker compose -f docker/docker-compose.prod.yml down

# Revert to previous git commit
git log --oneline -5  # Find previous commit
git checkout <previous-commit-hash>

# Rebuild images from previous code
docker compose -f docker/docker-compose.prod.yml build

# Start services
docker compose -f docker/docker-compose.prod.yml up -d

# Verify rollback
docker compose -f docker/docker-compose.prod.yml logs -f
```

### Common Issues & Solutions

**Issue: 404 for static assets (pure-min.css, controllers-gl.js, etc.)**

**Cause:** Static vendor assets or JavaScript bundles not built on host filesystem.

**Solution:**
```bash
# Build vendor assets
cd /workdir/wepppy/wepppy/weppcloud/static-src
npm ci --legacy-peer-deps
npm run build
cp -r dist/vendor/* ../static/vendor/

# Build controllers-gl.js and unitizer_map.js
cd /workdir/wepppy/wepppy/weppcloud/controllers_js
python build_controllers_js.py

# Restart Caddy to pick up changes
docker compose -f docker/docker-compose.prod.yml restart caddy
```

**Issue: `ModuleNotFoundError` in elevationquery or other services**

**Cause:** New Python files added but image not rebuilt.

**Solution:**
```bash
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d
```

**Issue: Container user permission errors**

**Cause:** `UID`/`GID` in `.env` doesn't match file ownership.

**Solution:**
```bash
# Check current ownership
ls -la /workdir/wepppy/wepppy/weppcloud/static

# Update .env with correct UID/GID
# Then rebuild
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d
```

**Issue: Database migration needed**

**Solution:**
```bash
docker compose -f docker/docker-compose.prod.yml exec weppcloud bash -c \
  "cd /workdir/wepppy && python -m wepppy.weppcloud.migrations.run_migrations"
```

**Issue: Slow build times (chown step taking >10 minutes)**

**Cause:** Docker processing ~115K files during ownership change.

**Mitigation:**
- This is normal for first build
- Subsequent builds use layer caching (much faster)
- Dockerfile optimization removed `/tmp` from chown (saves ~60s)

### Maintenance Commands

**View container resource usage:**
```bash
docker stats
```

**Clean up old images:**
```bash
docker image prune -a --filter "until=720h"  # Remove images >30 days old
```

**Backup database:**
```bash
docker compose -f docker/docker-compose.prod.yml exec postgres \
  pg_dump -U wepppy -Fc wepppy > backup-$(date +%Y%m%d).dump
```

**Restore database:**
```bash
docker compose -f docker/docker-compose.prod.yml exec -T postgres \
  pg_restore -U wepppy -d wepppy --clean < backup-20251030.dump
```

**Update a single service:**
```bash
# Rebuild and restart just one service
docker compose -f docker/docker-compose.prod.yml up -d --build weppcloud
```

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

1. **Pre-flight checks:**
   - Verify git branch/commit
   - Check `.env` file exists with required secrets
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

- [ ] Environment file (`docker/.env`) configured with secure secrets
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
