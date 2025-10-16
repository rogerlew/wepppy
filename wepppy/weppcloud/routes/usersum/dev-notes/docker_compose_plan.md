# Docker Compose Topology Plan

## Goals
- Run the WEPP monolith (Flask app, RQ workers, Go microservices, legacy webservices) with one `docker compose` command.
- Share the same Python environment across containers using [`uv`](https://github.com/astral-sh/uv) for fast dependency installs and rebuilds.
- Mount the local `wepppy/` source tree into every service container for live-edit development.
- Centralize environment via the existing project `.env` so all services inherit identical settings.

## Services (first pass)
| Service | Purpose | Port |
| --- | --- |
| `weppcloud` | Gunicorn/Flask primary web app + static assets | 8000 |
| `status` | Go WebSocket proxy (`services/status2`) for Redis status channels | 9002 |
| `preflight` | Go preflight microservice (`services/preflight2`) | 9001 |
| `browse` | Starlette File browser service | 9009 |
| `webpush` | Push notifications/webpush worker | 9003 |
| `elevationquery` | Elevation lookup microservice | 8002 |
| `wmesque` | Legacy WMESque interface (deprecated but kept for parity) | 8003 |
| `wmesque2` | WMESque v2 service | 8030 |
| `metquery` | Meteorological (MET) query service | 8004 |
| `postgres` | Application database (shared) |
| `redis` | Redis broker/cache (if not using external instance) | 6379 |
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

## Automated Postgres Backups
- `docker-compose.dev.yml` and `docker-compose.prod.yml` now ship with a `postgres-backup` sidecar that runs `pg_dump -h postgres -U wepppy -d wepppy -Fc` once every 24 hours.
- Dev backups are written to `./.docker-data/postgres-backups/` on the host; production uses the named volume `postgres-backups`.
- Tune the schedule via `BACKUP_INTERVAL_SECONDS` (default `86400` seconds) and retention via `BACKUP_KEEP_DAYS` (default `7` days) directly in Compose.
- Check the latest dumps with `docker compose exec postgres-backup ls -l /backups`.
- Trigger an ad-hoc snapshot without waiting a day: `docker compose run --rm postgres-backup bash -lc 'pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -Fc -f "/backups/wepppy-manual-$(date +%Y%m%d-%H%M%S).dump"'`.

### Restoring Postgres from a Backup Dump
1. Pick the dump to restore:
   - Dev: look in `./.docker-data/postgres-backups/wepppy-YYYYMMDD-HHMMSS.dump`.
   - Prod: list the named volume with `docker compose exec postgres-backup ls -l /backups` and copy the file out if needed.
2. Quiesce writers (`docker compose stop weppcloud rq-worker ...`) so nothing modifies the database mid-restore.
3. Copy the dump into the running Postgres container (example for dev):
   ```bash
   docker compose -f docker/docker-compose.dev.yml cp ./.docker-data/postgres-backups/wepppy-YYYYMMDD-HHMMSS.dump postgres:/tmp/restore.dump
   ```
4. Run `pg_restore` inside the container to replace the schema/data:
   ```bash
   docker compose -f docker/docker-compose.dev.yml exec postgres \
     bash -lc 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/restore.dump'
   ```
   (`--clean --if-exists` drops prior objects before importing, matching typical snapshot semantics.)
5. Optionally remove the temp file: `docker compose -f docker/docker-compose.dev.yml exec postgres rm /tmp/restore.dump`.
6. Restart the services you stopped in step 2.

## Startup Workflow
1. Ensure `.env` is populated with Redis host, Postgres creds, and any feature flags.
2. Run `docker compose build` (uses `uv` to install Python deps).
3. Bring up the stack: `docker compose up weppcloud status preflight ...` (or `docker compose up --profile core`). Remember to start Redis with keyspace notifications (`--notify-keyspace-events Kh`) so preflight2 receives checklist updates.
4. Run migrations inside the `weppcloud` container if needed: `docker compose run --rm weppcloud flask db upgrade`.

## Open Questions / Next Steps
- Confirm which services absolutely need to run in development vs. deployment profiles.
- Decide whether Redis should run inside Compose or assume an external instance (current code treats Redis host as the only variable).
- Script helper commands (`make compose-up`, `compose-down`) to streamline onboarding.
- Document how to seed Postgres and Redis in dev (fixtures, sample data, etc.).

## References
- `wepppy/weppcloud/routes/usersum/dev-notes/redis_config_refactor.md` for central Redis configuration.

## postgres database restoration from bare metal - DON'T DELETE
base) roger@wepp1:~$ sudo -u postgres psql -c "SHOW data_directory;"
[sudo] password for roger: 
Sorry, try again.
[sudo] password for roger: 
       data_directory        
-----------------------------
 /var/lib/postgresql/16/main


### dump and restore database
sudo systemctl start postgresql.service 
pg_dump -h localhost -U wepppy -d wepppy -f /tmp/wepppy.sql
sudo systemctl stop postgresql.service 
docker cp /tmp/wepppy.sql wepppy-postgres:/tmp/wepppy.sql
docker compose -f docker/docker-compose.dev.yml exec postgres \
  psql -U wepppy -d wepppy -f /tmp/wepppy.sql
docker compose -f docker/docker-compose.dev.yml exec postgres \
  psql -U wepppy -d wepppy -c "ALTER USER wepppy WITH PASSWORD 'password';"

  docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up 
