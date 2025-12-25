# wepp.cloud deploy plan (prod refresh)

> Goal: move wepp.cloud (wepp1) from bare-metal Flask to the docker-compose prod stack. wepp1 is running Ubuntu 24.04.3 LTS

## References
- `docker/docker-compose.prod.yml`
- `docker/Dockerfile` (vendored repos + static asset build)
- `docker/caddy/Caddyfile` (template, currently http://:8080)
- `docs/dev-notes/docker_compose_plan.md` (db backup/restore)
- `AGENTS.md` (run dirs, /wc1, /geodata)
- `wctl/README.md` (installing wctl)
- `scripts/README.docker_gid_993.md` (docker group GID enforcement)

## Preflight / inventory
- [x] Schedule maintenance window + downtime notice.
- [x] Record running services: `systemctl list-units --type=service | rg -i 'wepp|gunicorn|rq|redis|postgres|caddy|nginx'` (snapshot below).
- [x] Capture current env/secrets (OAuth, JWT, database creds, CAP keys).
- [x] Confirm `/wc1` path mapping (current host uses `/geodata/wc1`; ensure `/wc1` exists or bind-mount `/geodata/wc1` to `/wc1`).
- [x] Verify disk space on `/workdir`, `/wc1`, `/geodata`.
- [x] Verify DNS + firewall (80/443 open if Caddy terminates TLS).

## Current host snapshot (wepp1)
Service inventory:
```
● caddy.service                            loaded failed failed  Caddy
  gunicorn-elevationquery.service          loaded active running Gunicorn for elevationquery
  gunicorn-metquery.service                loaded active running Gunicorn for metquery
  gunicorn-preflight.service               loaded active running Gunicorn for weppcloud preflight microservice
  gunicorn-status.service                  loaded active running Gunicorn for weppcloud status microservice
  gunicorn-weppcloud.service               loaded active running Gunicorn for weppcloud
  gunicorn-wmesque.service                 loaded active running Gunicorn for wmesque
  gunicorn-wmesque2.service                loaded active running Gunicorn for WMSesque (FastAPI)
  irqbalance.service                       loaded active running irqbalance daemon
  postgresql.service                       loaded active exited  PostgreSQL RDBMS
  postgresql@16-main.service               loaded active running PostgreSQL Cluster 16-main
  redis-server.service                     loaded active running Advanced key-value store
  rq-wepppy-worker-pool.service            loaded active running RQ Worker Pool for Wepppy
```

Mount locations noted:
```
/workdir
/geodata
/geodata/wc1
```

Disk space:
```
Filesystem            Size  Used Avail Use% Mounted on
tmpfs                  26G  1.7M   26G   1% /run
/dev/sda1            1000G  746G  204G  79% /
tmpfs                 126G  1.7M  126G   1% /dev/shm
tmpfs                 5.0M     0  5.0M   0% /run/lock
tmpfs                 8.0G   95M  8.0G   2% /media/ramdisk
/dev/sdb1             3.5T  3.1T  205G  94% /ssd1
nas.rocket.net:/wepp   30T   29T  1.3T  96% /geodata
tmpfs                  26G   32K   26G   1% /run/user/1002
```

## Host updates
- [x] `sudo apt update && sudo apt -y upgrade`
- [x] Remove old docker/compose packages (if present):
  - `sudo apt-get remove -y docker docker-engine docker.io containerd runc docker-compose`
- [x] Install docker engine + compose plugin:
  - `sudo apt-get install -y ca-certificates curl gnupg`
  - `sudo install -m 0755 -d /etc/apt/keyrings`
  - `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg`
  - `echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null`
  - `sudo apt update`
  - `sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin`
  - `sudo systemctl enable --now docker`
- [x] Install git + tooling: `sudo apt-get install -y git rsync jq`
- [x] Install npm (only if host-side asset builds are needed): `sudo apt-get install -y npm`

## UID/GID normalization (roger:docker)
- [x] Verify roger UID: `id -u roger` (expect 1002 on wepp1; dev/test hosts expect 1000).
- [x] Verify docker GID: `getent group docker | cut -d: -f3` (expect 993 on dev/test; wepp1 uses 130 because 993 is `systemd-coredump`).
- [x] If docker GID is not 993 on wepp1, do not force-change it; set `GID=<docker gid>` in `docker/.env` and set `APP_GID=<docker gid>` for prod builds.
- [x] Run the docker GID fixer only on hosts that are supposed to be 993: `sudo ./scripts/ensure_docker_gid_993.sh fix` (see `scripts/README.docker_gid_993.md`).
- [x] Confirm roger is in docker group: `id -nG roger | rg -w docker`.
- [ ] After UID/GID updates, reset ownership: `sudo chown -R roger:docker /geodata`.
  - Dev/test hosts (`wc.bearhive.duckdns.org`, `wc-prod.bearhive.duckdns.org`) keep UID 1000 in `docker/.env`.
  - Prod (`wepp.cloud` / wepp1) should use UID 1002 and GID 130 (update `docker/docker-compose.prod.yml` build args or an override file before building).

## Backups
- [x] Postgres backup from bare metal to `/tmp/wepppy-YYYYMMDD.dump` (see `docs/dev-notes/docker_compose_plan.md`).
  - `pg_dump -h localhost -U wepppy -d wepppy -Fc -f /tmp/wepppy-YYYYMMDD.dump`
- [x] Archive repo: `rsync -a /workdir/wepppy /workdir/_wepppy_YYYYMMDD`.
- [x] Snapshot old systemd units: `sudo cp /etc/systemd/system/*wepp* /workdir/_wepppy_YYYYMMDD/systemd/`.

## Stop legacy services
- [x] `sudo systemctl disable --now <old weppcloud units>`.
- [x] Stop old redis/postgres systemd units if the compose stack will own those ports.
- [ ] Migrate Apache static sites from `/etc/apache2/sites-enabled/wsgi_sites.conf` into the Caddyfile.
- [x] Stop/disable Apache if it is still handling wepp.cloud (free 80/443 for Caddy).
- [x] Stop any old Docker containers (if present).

## Repos under /workdir
- [x] Clone `https://github.com/rogerlew/wepppy` -> `/workdir/wepppy`.
- [ ] `cap` assets are vendored in the prod image; clone `https://github.com/tiagozip/cap` -> `/workdir/cap` only if you want a host override.
- [x] Confirm which vendored deps should stay in the image (see `docker/Dockerfile`); host clones are optional unless you plan to mount overrides.
- [x] Install wctl: `cd /workdir/wepppy && ./wctl/install.sh wepp1` (optionally set `WCTL_SYMLINK_PATH`).
- [ ] Optional clones (only if you plan to override vendored deps from `docker/Dockerfile`):
  - [ ] `https://github.com/wepp-in-the-woods/wepppy2` -> `/workdir/wepppy2`.
  - [ ] `https://github.com/wepp-in-the-woods/weppcloud2` -> `/workdir/weppcloud2`.
  - [ ] `https://github.com/rogerlew/f-esri` -> `/workdir/f-esri`.
  - [ ] `https://github.com/rogerlew/weppcloud-wbt` -> `/workdir/weppcloud-wbt`.
  - [ ] `https://github.com/wepp-in-the-woods/wepppyo3` -> `/workdir/wepppyo3`.
  - [ ] `https://github.com/rogerlew/rosetta` -> `/workdir/rosetta`.
  - [ ] `/workdir/peridot`, `/workdir/wepp-forest`, `/workdir/wepp-forest-revegetation` (only if external tooling expects host paths).

## Compose env and config
- [x] Create `docker/.env` (keys + secrets + host config):
  - `UID`, `GID` (use host values; wepp1 uses UID 1002 and docker GID 130)
  - `SECRET_KEY`, `SECURITY_PASSWORD_SALT`
  - `POSTGRES_PASSWORD`, `DATABASE_URL` (example: `postgresql://wepppy:${POSTGRES_PASSWORD}@postgres:5432/wepppy`)
  - `WEPP_AUTH_JWT_SECRET`, `DTALE_INTERNAL_TOKEN`
  - `EXTERNAL_HOST`, `EXTERNAL_HOST_DESCRIPTION`
  - `OAUTH_REDIRECT_HOST=wepp.cloud` (optional; defaults to `EXTERNAL_HOST`)
  - OAuth keys: `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET`, `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`
  - CAP keys: `CAP_SITE_KEY`, `CAP_SECRET`, `CAP_CORS_ORIGIN`
  - `OPENTOPOGRAPHY_API_KEY` (if used)
- [x] Ensure `/wc1` and `/geodata` are mounted and readable (compose expects `/wc1` and `/wc1/geodata`).
- [x] Ensure `/geodata/extended_mods_data` exists and clone location bundles:
  - `https://github.com/rogerlew/wepppy-locations-laketahoe` -> `/geodata/extended_mods_data/wepppy-locations-laketahoe`
  - `https://github.com/rogerlew/wepppy-locations-portland` -> `/geodata/extended_mods_data/wepppy-locations-portland`
  - `https://github.com/rogerlew/wepppy-locations-seattle` -> `/geodata/extended_mods_data/wepppy-locations-seattle`
- [ ] Set `CADDY_FILE=/workdir/wepppy/docker/caddy/Caddyfile.weppcloud` (or similar) if using a custom Caddyfile.

## Caddy + TLS
- [x] Use Caddy for TLS termination on wepp.cloud (Lets Encrypt); Apache is retired.
- [x] Use `docker/caddy/Caddyfile.wepp1` for wepp.cloud (TLS termination + redirects).
- [x] Ensure HTTPS redirect is enforced (Caddy does this by default when TLS is enabled).
- [x] Use the override file `docker/docker-compose.prod.wepp1.yml` to expose 80/443 and persist `/data` + `/config`.
- [x] Ensure 80/443 are open to the host and DNS points to wepp1.

## Build + start stack
- [x] Build images (wepp1 override): `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml build`.
- [x] Start stack (wepp1 override): `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml up -d`.
- [x] Check health: `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml ps`.

## Restore database + migrate
- [x] Stop writers: `docker compose -f docker/docker-compose.prod.yml stop weppcloud rq-worker`.
- [x] Restore the backup into the `postgres` container (see `docs/dev-notes/docker_compose_plan.md`).
  - `docker compose -f docker/docker-compose.prod.yml cp /tmp/wepppy-20251224.dump postgres:/tmp/restore.dump`
  - `docker compose -f docker/docker-compose.prod.yml exec postgres pg_restore --clean --if-exists -U wepppy -d wepppy /tmp/restore.dump`
  - `docker compose -f docker/docker-compose.prod.yml exec postgres rm /tmp/restore.dump`
- [x] Run migrations: `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml run --rm -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db upgrade`.
- [x] Start services: `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml up -d`.

## Copy static vendor assets
- [x] Copy vendor assets from image to host (required because volume mount overrides built assets):
  - `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml cp weppcloud:/workdir/wepppy/wepppy/weppcloud/static/vendor /workdir/wepppy/wepppy/weppcloud/static/`
- [x] Verify vendor files exist: `ls -la /workdir/wepppy/wepppy/weppcloud/static/vendor/`

## Post-deploy validation
- [x] `curl -fsS https://wepp.cloud/health` (or `/weppcloud/health` via proxy).
- [x] Confirm login + OAuth, run creation, and a smoke run.
- [x] Verify status/preflight WebSockets, cap UI, dtale, and browse endpoints.
- [ ] Scan logs: `docker compose -f docker/docker-compose.prod.yml logs --tail=200`.

## Rollback
- [ ] Stop compose stack: `docker compose -f docker/docker-compose.prod.yml down`.
- [ ] Restore `/workdir/_wepppy_YYYYMMDD` and re-enable old systemd units.
- [ ] Restore Postgres from the pre-migration dump.
