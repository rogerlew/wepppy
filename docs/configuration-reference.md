# Configuration Reference

Consolidated configuration surfaces discovered from:
`wepppy/config/redis_settings.py`, `wepppy/config/secrets.py`, `wepppy/weppcloud/configuration.py`,
`wepppy/microservices/rq_engine/**`, `wepppy/nodb/base.py`, `tests/conftest.py`,
`docker/defaults.env`, `docker/docker-compose.dev.yml`, and `docker/docker-compose.prod.yml`.

## Conventions

- Secrets: `NAME_FILE` (path) overrides `NAME` (value). Many secrets are only referenced via `*_FILE` in Docker Compose.
- Booleans (where applicable): `1/true/yes/on` → true, `0/false/no/off` → false; otherwise fall back to the default.
- Defaults: values shown as `python:` are in-code defaults; `compose(dev|prod):` are Docker Compose defaults.

## Redis

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `REDIS_URL` | `compose(dev|prod): redis://redis:6379/0` | `wepppy.config.redis_settings`; compose (many services) | Base Redis URL used to derive per-DB URLs. |
| `REDIS_HOST` | `python: localhost`; `compose(dev): redis`; `compose(prod): redis` | `wepppy.config.redis_settings` | Redis host when URL-based configuration is not used. |
| `REDIS_PORT` | `python: 6379`; `compose(prod): 6379` | `wepppy.config.redis_settings`; compose (host port mapping) | Redis port when URL-based configuration is not used. |
| `REDIS_PASSWORD` | — | `wepppy.config.redis_settings` | Redis password (secret; prefers `REDIS_PASSWORD_FILE`). |
| `REDIS_PASSWORD_FILE` | — | `wepppy.config.secrets`; compose (`redis`, app services) | Path to Redis password file (Docker secret). |
| `RQ_REDIS_URL` | — | `wepppy.config.redis_settings`; compose (`rq-worker*`) | Legacy alias for `REDIS_URL` (commonly points at the RQ DB). |
| `SESSION_REDIS_URL` | — | `wepppy.config.redis_settings` | Optional Redis URL override for Flask session storage. |
| `SESSION_REDIS_DB` | `python: 11` | `wepppy.config.redis_settings` | Optional DB index override for session storage when `SESSION_REDIS_URL` is used. |

## Database (PostgreSQL / SQLAlchemy)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `SQLALCHEMY_DATABASE_URI` | — | `wepppy.weppcloud.configuration` | Full SQLAlchemy DB URI (highest priority). |
| `DATABASE_URL` | — | `wepppy.weppcloud.configuration` | Alternate DB URI fallback. |
| `POSTGRES_HOST` | `python: postgres` | `wepppy.weppcloud.configuration` | PostgreSQL host for URI synthesis. |
| `POSTGRES_PORT` | `python: 5432`; `compose(prod): 5432` | `wepppy.weppcloud.configuration`; compose (host port mapping) | PostgreSQL port for URI synthesis / host port mapping. |
| `POSTGRES_DB` | `python: wepppy`; `compose(dev|prod): wepppy` | `wepppy.weppcloud.configuration`; compose (`postgres`) | PostgreSQL database name. |
| `POSTGRES_USER` | `python: wepppy`; `compose(dev|prod): wepppy` | `wepppy.weppcloud.configuration`; compose (`postgres`) | PostgreSQL user name. |
| `POSTGRES_PASSWORD` | — | `wepppy.weppcloud.configuration` | PostgreSQL password (secret; prefers `POSTGRES_PASSWORD_FILE`). |
| `POSTGRES_PASSWORD_FILE` | — | `wepppy.config.secrets`; compose (`postgres`, `weppcloud`, `rq-engine`) | Path to PostgreSQL password file (Docker secret). |
| `POSTGRES_IDLE_IN_TX_TIMEOUT` | — | `wepppy.weppcloud.configuration` | Optional `idle_in_transaction_session_timeout` (passed as a libpq `options` string). |
| `PGHOST` | `compose(dev|prod): postgres` | compose (`postgres-backup`) | Postgres backup target host. |
| `PGPORT` | `compose(dev|prod): 5432` | compose (`postgres-backup`) | Postgres backup target port. |
| `PGUSER` | `compose(dev|prod): wepppy` | compose (`postgres-backup`) | Postgres backup user. |
| `PGDATABASE` | `compose(dev|prod): wepppy` | compose (`postgres-backup`) | Postgres backup database name. |
| `BACKUP_DIR` | `compose(dev|prod): /backups` | compose (`postgres-backup`) | Backup output directory. |
| `BACKUP_KEEP_DAYS` | `compose(dev|prod): 7` | compose (`postgres-backup`) | Retention window (days) for backups. |
| `BACKUP_INTERVAL_SECONDS` | `compose(dev|prod): 86400` | compose (`postgres-backup`) | Backup interval (seconds). |

## Flask / WEPPcloud App

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `SITE_PREFIX` | `python: /weppcloud`; `compose(dev|prod): /weppcloud` | `wepppy.weppcloud.configuration`; `wepppy.microservices.rq_engine.*` | URL prefix where the app is mounted (also used for redirect/cookie paths). |
| `FLASK_DEBUG` | `python: false` | `wepppy.weppcloud.configuration` | Enables Flask debug mode. |
| `DEBUG` | `python: false` | `wepppy.weppcloud.configuration` | Fallback debug toggle when `FLASK_DEBUG` is unset. |
| `TEST_SUPPORT_ENABLED` | `python: false`; `compose(dev): false` | `wepppy.weppcloud.configuration`; compose (common env) | Enables test/support-only behaviors in WEPPcloud. |
| `ENABLE_LOCAL_LOGIN` | `python: true`; `compose(dev): true`; `compose(prod): false` | `wepppy.weppcloud.configuration`; compose (common env) | Enables local login flow. |
| `GL_DASHBOARD_BATCH_ENABLED` | `python: false`; `compose(dev|prod): false` | `wepppy.weppcloud.configuration`; compose (common env) | Enables GL dashboard batch features. |
| `SECRET_KEY` | required | `wepppy.weppcloud.configuration`; `wepppy.microservices.rq_engine.session_routes` | Flask `SECRET_KEY` (secret; prefers `SECRET_KEY_FILE`). |
| `SECRET_KEY_FILE` | — | `wepppy.config.secrets`; compose (`weppcloud`, `rq-engine`) | Path to Flask `SECRET_KEY` file (Docker secret). |
| `SECURITY_PASSWORD_SALT` | required | `wepppy.weppcloud.configuration` | Flask-Security password salt (secret; prefers `SECURITY_PASSWORD_SALT_FILE`). |
| `SECURITY_PASSWORD_SALT_FILE` | — | `wepppy.config.secrets`; compose (`weppcloud`, `rq-engine`) | Path to Flask-Security password salt file (Docker secret). |

## Sessions / Cookies

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `SESSION_COOKIE_PATH` | `python: /` | `wepppy.weppcloud.configuration` | Flask session cookie path. |
| `SESSION_COOKIE_SAMESITE` | `python: Lax` | `wepppy.weppcloud.configuration` | Flask session cookie SameSite policy. |
| `SESSION_REFRESH_EACH_REQUEST` | `python: true` | `wepppy.weppcloud.configuration` | Refreshes session on each request. |
| `REMEMBER_COOKIE_SAMESITE` | `python: (defaults to SESSION_COOKIE_SAMESITE)` | `wepppy.weppcloud.configuration` | Remember-me cookie SameSite policy. |
| `REMEMBER_COOKIE_DAYS` | `python: 30` | `wepppy.weppcloud.configuration` | Remember-me cookie duration in days (minimum 1). |
| `REMEMBER_COOKIE_SECURE` | `python: true` | `wepppy.weppcloud.configuration` | Remember-me cookie `Secure` attribute. |
| `REMEMBER_COOKIE_HTTPONLY` | `python: true` | `wepppy.weppcloud.configuration` | Remember-me cookie `HttpOnly` attribute. |
| `REMEMBER_COOKIE_REFRESH_EACH_REQUEST` | `python: false` | `wepppy.weppcloud.configuration` | Refresh remember-me cookie each request. |
| `SESSION_COOKIE_NAME` | `python: session` | `wepppy.microservices.rq_engine.session_routes` | Cookie name used to read the Flask session ID. |
| `SESSION_USE_SIGNER` | `python: true` | `wepppy.microservices.rq_engine.session_routes` | Whether to unsign the Flask session cookie (`itsdangerous` signer). |
| `SESSION_KEY_PREFIX` | `python: session:` | `wepppy.microservices.rq_engine.session_routes` | Redis key prefix for server-side Flask sessions. |
| `WEPP_BROWSE_JWT_COOKIE_NAME` | `python: wepp_browse_jwt` | `wepppy.microservices.rq_engine.session_routes` | Base name for per-run browse JWT cookies. |
| `WEPP_AUTH_SESSION_COOKIE_SAMESITE` | `python: lax` | `wepppy.microservices.rq_engine.session_routes` | SameSite policy for browse JWT cookies (`lax`, `strict`, `none`). |
| `WEPP_AUTH_SESSION_COOKIE_SECURE` | `python: (request-derived)` | `wepppy.microservices.rq_engine.session_routes` | Overrides whether browse JWT cookies are `Secure` (default inferred from forwarded headers / request scheme). |

## OAuth (WEPPcloud)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `OAUTH_REDIRECT_SCHEME` | `python: https` | `wepppy.weppcloud.configuration` | Redirect URI scheme used to build provider callback URLs. |
| `OAUTH_REDIRECT_HOST` | — | `wepppy.weppcloud.configuration` | Redirect host override; falls back to `EXTERNAL_HOST`. |
| `EXTERNAL_HOST` | — | `wepppy.weppcloud.configuration`; compose (common env) | Public host name used for OAuth redirect construction (and other external metadata). |
| `EXTERNAL_HOST_DESCRIPTION` | — | compose (common env) | Human-oriented host label (used by query-engine service env). |
| `OAUTH_GITHUB_CLIENT_ID` | — | `wepppy.weppcloud.configuration`; compose(prod): `weppcloud` | GitHub OAuth client id. |
| `GITHUB_OAUTH_CLIENT_ID` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GITHUB_CLIENT_ID`. |
| `GITHUB_OAUTH_CLIENTID` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GITHUB_CLIENT_ID`. |
| `OAUTH_GITHUB_CLIENT_SECRET` | — | `wepppy.weppcloud.configuration` | GitHub OAuth client secret (secret; prefers `OAUTH_GITHUB_CLIENT_SECRET_FILE`). |
| `OAUTH_GITHUB_CLIENT_SECRET_FILE` | — | `wepppy.config.secrets`; compose (`weppcloud`) | Path to GitHub OAuth client secret file (Docker secret). |
| `GITHUB_OAUTH_CLIENT_SECRET` | — | `wepppy.weppcloud.configuration` | Legacy GitHub OAuth secret alias (non-file form). |
| `GITHUB_OAUTH_SECRET_KEY` | — | `wepppy.weppcloud.configuration` | Legacy GitHub OAuth secret alias (non-file form). |
| `OAUTH_GITHUB_REDIRECT_URI` | — | `wepppy.weppcloud.configuration` | GitHub OAuth redirect override URI. |
| `GITHUB_OAUTH_REDIRECT_URI` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GITHUB_REDIRECT_URI`. |
| `GITHUB_OAUTH_CALLBACK_URL` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GITHUB_REDIRECT_URI`. |
| `OAUTH_GOOGLE_CLIENT_ID` | — | `wepppy.weppcloud.configuration`; compose(prod): `weppcloud` | Google OAuth client id. |
| `GOOGLE_OAUTH_CLIENT_ID` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GOOGLE_CLIENT_ID`. |
| `OAUTH_GOOGLE_CLIENT_SECRET` | — | `wepppy.weppcloud.configuration` | Google OAuth client secret (secret; prefers `OAUTH_GOOGLE_CLIENT_SECRET_FILE`). |
| `OAUTH_GOOGLE_CLIENT_SECRET_FILE` | — | `wepppy.config.secrets`; compose (`weppcloud`) | Path to Google OAuth client secret file (Docker secret). |
| `GOOGLE_OAUTH_CLIENT_SECRET` | — | `wepppy.weppcloud.configuration` | Legacy Google OAuth secret alias (non-file form). |
| `OAUTH_GOOGLE_REDIRECT_URI` | — | `wepppy.weppcloud.configuration` | Google OAuth redirect override URI. |
| `GOOGLE_OAUTH_REDIRECT_URI` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GOOGLE_REDIRECT_URI`. |
| `GOOGLE_OAUTH_CALLBACK_URL` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_GOOGLE_REDIRECT_URI`. |
| `OAUTH_ORCID_CLIENT_ID` | — | `wepppy.weppcloud.configuration` | ORCID OAuth client id. |
| `ORCID_OAUTH_CLIENT_ID` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_ORCID_CLIENT_ID`. |
| `ORCID_OAUTH_CLIENTID` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_ORCID_CLIENT_ID`. |
| `OAUTH_ORCID_CLIENT_SECRET` | — | `wepppy.weppcloud.configuration` | ORCID OAuth client secret (secret; prefers `OAUTH_ORCID_CLIENT_SECRET_FILE`). |
| `OAUTH_ORCID_CLIENT_SECRET_FILE` | — | `wepppy.config.secrets`; tests scrub env | Path to ORCID OAuth client secret file (Docker secret). |
| `ORCID_OAUTH_CLIENT_SECRET` | — | `wepppy.weppcloud.configuration` | Legacy ORCID OAuth secret alias (non-file form). |
| `ORCID_OAUTH_SECRET_KEY` | — | `wepppy.weppcloud.configuration` | Legacy ORCID OAuth secret alias (non-file form). |
| `OAUTH_ORCID_REDIRECT_URI` | — | `wepppy.weppcloud.configuration` | ORCID OAuth redirect override URI. |
| `ORCID_OAUTH_REDIRECT_URI` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_ORCID_REDIRECT_URI`. |
| `ORCID_OAUTH_CALLBACK_URL` | — | `wepppy.weppcloud.configuration` | Legacy alias for `OAUTH_ORCID_REDIRECT_URI`. |

## Mail (WEPPcloud)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `ZOHO_NOREPLY_EMAIL` | — | `wepppy.weppcloud.configuration` | Enables Zoho SMTP if set (pairs with `ZOHO_NOREPLY_EMAIL_PASSWORD`). |
| `ZOHO_NOREPLY_EMAIL_PASSWORD` | — | `wepppy.weppcloud.configuration` | Zoho SMTP password (secret; prefers `ZOHO_NOREPLY_EMAIL_PASSWORD_FILE`). |
| `ZOHO_NOREPLY_EMAIL_PASSWORD_FILE` | — | `wepppy.config.secrets`; compose (`weppcloud`) | Path to Zoho SMTP password file (Docker secret). |

## CAPTCHA (CAP service)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `CAP_BASE_URL` | `compose(prod): /cap` | `wepppy.microservices.rq_engine.project_routes`; compose (`weppcloud`, `rq-engine`) | CAPTCHA base URL (path or absolute URL used for siteverify). |
| `CAP_ASSET_BASE_URL` | `compose(prod): /cap/assets` | compose (`weppcloud`) | Public base URL for CAPTCHA assets. |
| `CAP_SITE_KEY` | required | `wepppy.microservices.rq_engine.project_routes`; compose (`cap`, `weppcloud`, `rq-engine`) | CAPTCHA site key. |
| `CAP_SECRET` | required | `wepppy.microservices.rq_engine.project_routes`; `wepppy.microservices.rq_engine.fork_archive_routes` | CAPTCHA secret (secret; prefers `CAP_SECRET_FILE`). |
| `CAP_SECRET_FILE` | — | `wepppy.config.secrets`; compose (`cap`, `weppcloud`, `rq-engine`) | Path to CAPTCHA secret file (Docker secret). |
| `CAP_CORS_ORIGIN` | `compose(dev|prod): *` | compose (`cap`) | Allowed CORS origin(s) for CAP service. |
| `CAP_ASSET_ROOT` | `compose(dev|prod): /opt/cap` | compose (`cap`) | CAP asset root directory inside the CAP container. |
| `CAP_DATA_DIR` | `compose(dev|prod): /var/lib/cap` | compose (`cap`) | CAP writable data directory inside the CAP container. |
| `CAP_REPO` | `compose(dev|prod): https://github.com/tiagozip/cap` | compose (build arg; `cap`) | CAP build source repo. |
| `CAP_REF` | `compose(dev|prod): main` | compose (build arg; `cap`) | CAP build ref (branch/tag/sha). |
| `CAP_IMAGE` | `compose(prod): wepppy-cap:latest` | compose (image selection; `cap`) | CAP image tag override. |

## RQ Engine (FastAPI microservice)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `RQ_ENGINE_RQ_TIMEOUT` | `python: 216000` | `wepppy.microservices.rq_engine.*` | Default enqueue timeout (seconds) used by many routes. |
| `RQ_ENGINE_RUN_SYNC_TIMEOUT` | `python: 86400` | `wepppy.microservices.rq_engine.run_sync_routes` | Run-sync job timeout (seconds). |
| `RQ_ENGINE_MIGRATIONS_TIMEOUT` | `python: 7200` | `wepppy.microservices.rq_engine.run_sync_routes` | Migrations job timeout (seconds). |
| `RQ_ENGINE_JWT_AUDIENCE` | `python: rq-engine` | `wepppy.microservices.rq_engine.auth`; `project_routes`; `culvert_routes` | Audience used when decoding/minting rq-engine tokens. |
| `RQ_ENGINE_POLL_AUTH_MODE` | `python: open` | `wepppy.microservices.rq_engine.job_routes` | Poll auth mode (`open`, `token_optional`, `required`). |
| `RQ_ENGINE_POLL_RATE_LIMIT_COUNT` | `python: 400` | `wepppy.microservices.rq_engine.job_routes` | In-memory poll rate limit count (minimum 1). |
| `RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS` | `python: 60` | `wepppy.microservices.rq_engine.job_routes` | In-memory poll rate limit window (seconds; minimum 1). |
| `CULVERTS_ROOT` | `python: /wc1/culverts` | `wepppy.microservices.rq_engine.culvert_routes` | Filesystem root for culvert batch artifacts. |

## JWT / Tokens / Internal Auth

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `WEPP_AUTH_JWT_SECRET` | — | tests (`tests/conftest.py`) | Test-only dummy JWT secret injected for routes that decode tokens. |
| `WEPP_AUTH_JWT_SECRETS_FILE` | — | compose (`weppcloud`, `browse`, `rq-engine`) | Path to JWT secret bundle file (Docker secret). |
| `WEPP_AUTH_JWT_SECRET_FILE` | — | tests scrub env | Path to a single JWT secret file (legacy name). |
| `AGENT_JWT_SECRET_FILE` | — | compose (`weppcloud`) | Path to agent JWT secret file (Docker secret). |
| `WEPP_MCP_JWT_SECRET_FILE` | — | compose (`query-engine`) | Path to MCP JWT secret file (Docker secret). |
| `DTALE_INTERNAL_TOKEN_FILE` | — | compose (`browse`, `dtale`) | Path to internal Dtale token file (Docker secret). |
| `WC_TOKEN_FILE` | — | tests scrub env | Path to WC token file (Docker secret / host env hygiene). |
| `OPENET_API_KEY_FILE` | — | tests scrub env | Path to OpenET API key file (Docker secret / host env hygiene). |
| `OPENTOPOGRAPHY_API_KEY_FILE` | — | compose (`weppcloud`, `rq-worker*`) | Path to OpenTopography API key file (Docker secret). |
| `CLIMATE_ENGINE_API_KEY_FILE` | — | compose (`weppcloud`, `rq-worker*`) | Path to Climate Engine API key file (Docker secret). |
| `ADMIN_PASSWORD_FILE` | — | compose (`profile-playback`) | Path to admin password file (Docker secret). |

## Proxy / HTTP Headers (rq-engine)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `Authorization` | — | `wepppy.microservices.rq_engine.auth` | Bearer token header used for JWT auth. |
| `X-Forwarded-Prefix` | — | `wepppy.microservices.rq_engine.__init__` | Reverse-proxy mount prefix (sets FastAPI `root_path`). |
| `X-Forwarded-Proto` | — | `wepppy.microservices.rq_engine.session_routes` | Used to infer whether requests are secure for cookie defaults. |
| `X-Forwarded-Ssl` | — | `wepppy.microservices.rq_engine.session_routes` | Used to infer whether requests are secure for cookie defaults. |
| `X-Forwarded-For` | — | `wepppy.microservices.rq_engine.job_routes` | Used for poll audit/rate-limit caller IP attribution. |

## NoDb

| Variable / Surface | Default | Used by | Description |
|---|---:|---|---|
| `WEPPPY_LOCK_TTL_SECONDS` | `python: 21600` | `wepppy.nodb.base` | Default distributed lock TTL in seconds (applies to NoDb locking). |
| `wepppy/nodb/configs/*.cfg` | — | `wepppy.nodb.base` | NoDb controller configuration basenames (`get_configs()`). |
| `wepppy/nodb/configs/_defaults.toml` | — | `wepppy.nodb.base` | Default configuration seed path (`get_default_config_path()`). |
| `wepppy/nodb/configs/legacy/*.toml` | — | `wepppy.nodb.base` | Legacy configuration basenames (`get_legacy_configs()`). |

## Docker / Infra (Compose)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `WEPPPY_ENV_FILE` | `compose(dev|prod): defaults.env` | compose | Selects the `env_file` loaded by many services. |
| `UID` | `defaults.env: 1000` | compose(dev): container user | Container user id for dev stack. |
| `GID` | `defaults.env: 993` | compose(dev): container group | Container group id for dev stack. |
| `WC1_DIR` | `defaults.env: /wc1` | compose(dev): bind mounts | Host mount path for `/wc1`. |
| `GEODATA_DIR` | `defaults.env: /wc1/geodata` | compose(dev): bind mounts | Host mount path for `/geodata`. |
| `CADDY_FILE` | `defaults.env: ./caddy/Caddyfile` | compose | Caddy config file path (relative to `docker/`). |
| `CADDY_PORT` | `compose(prod): 8080` | compose(prod): `caddy` | Host port for Caddy in prod stack. |
| `WEPPCLOUD_IMAGE` | `compose(prod): wepppy:latest` | compose(prod) | Base image tag for prod services. |
| `WEPPCLOUD_PORT` | `compose(prod): 8000` | compose(prod): `weppcloud` | Host port mapping for WEPPcloud. |
| `BROWSE_PORT` | `compose(prod): 9009` | compose(prod): `browse` | Host port mapping for browse service. |
| `BROWSE_REDIS_URL` | `compose(prod): redis://redis:6379/0` | compose(prod): `browse` | Browse service `REDIS_URL` override. |
| `STATUS_PORT` | `compose(prod): 9002` | compose(prod): `status` | Host port mapping for status service. |
| `PREFLIGHT_PORT` | `compose(prod): 9001` | compose(prod): `preflight` | Host port mapping for preflight service. |
| `ELEVATIONQUERY_PORT` | `compose(prod): 8002` | compose(prod): `elevationquery` | Host port mapping for elevationquery service. |
| `METQUERY_PORT` | `compose(prod): 8004` | compose(prod): `metquery` | Host port mapping for metquery service. |
| `WMESQUE_PORT` | `compose(prod): 8003` | compose(prod): `wmesque` | Host port mapping for wmesque service. |
| `WMESQUE2_PORT` | `compose(prod): 8030` | compose(prod): `wmesque2` | Host port mapping for wmesque2 service. |
| `F_ESRI_IMAGE` | `compose(prod): wepppy-f-esri:latest` | compose (image selection; `f-esri`) | f-esri image tag override. |
| `WEPPCLOUD_STATUS_IMAGE` | `compose(prod): wepppy-status:latest` | compose(prod): `status` | status service image tag override. |
| `WEPPCLOUD_PREFLIGHT_IMAGE` | `compose(prod): wepppy-preflight:latest` | compose(prod): `preflight` | preflight service image tag override. |
| `WEPPCLOUDR_IMAGE` | `compose(prod): weppcloudr:latest` | compose(prod): `weppcloudr` | weppcloudr image tag override. |
| `WEPPCLOUDR_PORT` | `compose(prod): 8050` | compose(prod): `weppcloudr` | weppcloudr port env / mapping. |
| `WEPPCLOUDR_CONTAINER` | `compose(prod): weppcloudr` | compose(prod): `rq-worker*` | Docker container name used by RQ workers when they need weppcloudr. |
| `PROFILE_PLAYBACK_BASE_URL` | `compose(dev|prod): http://weppcloud:8000/weppcloud` | compose (`profile-playback`) | WEPPcloud base URL consumed by profile-playback service. |
| `PROFILE_PLAYBACK_ROOT` | `compose(dev|prod): /workdir/wepppy-test-engine-data/profiles` | compose (`profile-playback`) | Root directory for stored profiles. |
| `PROFILE_PLAYBACK_DATA_DIR` | `compose(prod): /workdir/wepppy-test-engine-data` | compose(prod): `profile-playback` | Host bind for profile-playback data directory. |
| `PROFILE_PLAYBACK_RUN_ROOT` | `compose(dev|prod): /workdir/wepppy-test-engine-data/playback/runs` | compose (common env) | Profile playback runs root. |
| `PROFILE_PLAYBACK_FORK_ROOT` | `compose(dev|prod): /workdir/wepppy-test-engine-data/playback/fork` | compose (common env) | Profile playback fork root. |
| `PROFILE_PLAYBACK_ARCHIVE_ROOT` | `compose(dev|prod): /workdir/wepppy-test-engine-data/playback/archive` | compose (common env) | Profile playback archive root. |
| `PROFILE_PLAYBACK_USE_CLONE` | `compose(dev|prod): true` | compose (common env) | Prefer clone semantics for profile playback. |
| `WEPPPY_SOURCE_ROOT` | `compose(dev|prod): /workdir/wepppy` | compose (common env) | Source root path inside containers. |
| `MPLCONFIGDIR` | `compose(dev|prod): /tmp/matplotlib` | compose (common env; `rq-worker*`) | Matplotlib config/cache dir (avoids writing to `$HOME`). |
| `PYTHONUNBUFFERED` | `compose(dev|prod): 1` | compose (common env) | Unbuffered Python output (better logs). |
| `DTALE_SERVICE_URL` | `compose(dev|prod): http://dtale:9010` | compose (common env) | Internal Dtale base URL used by app services. |
| `DTALE_BASE_URL` | `compose(dev|prod): http://dtale:9010` | compose (`dtale`) | Dtale service self base URL. |
| `CAO_BASE_URL` | `compose(dev): http://host.docker.internal:9889` | compose(dev): app services | CAO service base URL in dev stack. |
| `DEV_MODE` | `compose(dev): false` | compose(dev): common env | Dev-mode toggle passed through container environment. |
| `ENABLE_PROFILE_COVERAGE` | `compose(dev): false` | compose(dev): common env | Profile coverage toggle passed through container environment. |
| `PLAYWRIGHT_BROWSERS_PATH` | `compose(dev): /workdir/wepppy/weppcloud/static-src/.playwright-browsers` | compose(dev): `weppcloud` | Playwright browser cache location. |
| `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS` | `compose(dev): 1` | compose(dev): `weppcloud` | Disables Playwright host requirements validation. |
| `CONTROLLERS_JS_EXTRA_OUTPUTS` | `compose(prod): /srv/weppcloud/static/js/controllers-gl.js` | compose(prod): `weppcloud` | Extra controllers JS output path (prod). |
| `STATIC_ASSET_SYNC_DIR` | `compose(prod): /srv/weppcloud/static` | compose(prod): `weppcloud` | Static asset sync directory (prod). |
| `PORT` | `compose(dev|prod): 8050` | compose (`weppcloudr`) | weppcloudr listen port env. |
| `TEMPLATE_ROOT` | `compose(dev|prod): /srv/weppcloudr/templates/scripts/users/chinmay` | compose (`weppcloudr`) | weppcloudr template root. |
| `DEVAL_TEMPLATE` | `compose(dev|prod): /srv/weppcloudr/templates/scripts/users/chinmay/new_report.Rmd` | compose (`weppcloudr`) | weppcloudr report template entrypoint. |
| `SCHEDULE_CONFIG` | `compose(dev|prod): /workdir/wepppy/docker/scheduled-tasks.yml` | compose (`scheduler`) | Scheduled task config file path. |
| `SCHEDULE_SLEEP_SECONDS` | `compose(dev|prod): 30` | compose (`scheduler`) | Scheduler poll interval (seconds). |
| `SCHEDULE_LOG_LEVEL` | `compose(dev|prod): INFO` | compose (`scheduler`) | Scheduler log level. |
| `RQ_DASHBOARD_URL_PREFIX` | `compose(dev): /rq-dashboard` | compose(dev): `rq-dashboard` | URL prefix for rq-dashboard behind a proxy. |
| `PIP_DISABLE_PIP_VERSION_CHECK` | `compose(dev): 1` | compose(dev): `rq-dashboard` | Disables pip version check noise. |
| `WEPPPY_NCPU` | `compose(dev|prod): 6` | compose (`rq-worker-batch`) | Worker concurrency / CPU hint used by rq-worker-batch. |
| `PERIDOT_CPU` | `compose(dev): 4`; `compose(prod): 12` | compose (`rq-worker-batch`) | Peridot CPU allocation hint used by rq-worker-batch. |
| `LOGLEVEL` | `compose(dev): DEBUG`; `compose(prod): INFO` | compose (`rq-worker*`) | Worker log level. |
| `RQ_LOGGING_LEVEL` | `compose(dev): DEBUG`; `compose(prod): INFO` | compose (`rq-worker*`) | RQ worker logging level. |

## Docker Build Args (Compose)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `APP_USER` | `compose(prod): roger` | compose(prod): `x-wepppy-image` build | Image build user name. |
| `APP_GROUP` | `compose(prod): docker` | compose(prod): `x-wepppy-image` build | Image build group name. |
| `APP_UID` | `compose(prod): 1000` | compose(prod): `x-wepppy-image` build | Image build user id. |
| `APP_GID` | `compose(prod): 993` | compose(prod): `x-wepppy-image` build | Image build group id. |
| `BASE_IMAGE` | `compose(prod): (defaults to WEPPCLOUD_IMAGE)` | compose(prod): `fcgiwrap` build | Base image for fcgiwrap build. |

## Status / Preflight Services (Compose)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `STATUS_REDIS_URL` | `compose(dev|prod): redis://redis:6379/2` | compose (`status`) | Status service Redis URL. |
| `STATUS_REDIS_PASSWORD_FILE` | — | compose (`status`) | Status service Redis password file (Docker secret). |
| `STATUS_LISTEN_ADDR` | `compose(dev|prod): 0.0.0.0:9002` | compose (`status`) | Status service listen address. |
| `STATUS_LOG_LEVEL` | `compose(dev|prod): info` | compose (`status`) | Status service log level. |
| `STATUS_METRICS_ENABLED` | `compose(dev|prod): true` | compose (`status`) | Enables status service metrics. |
| `PREFLIGHT_REDIS_URL` | `compose(dev|prod): redis://redis:6379/0` | compose (`preflight`) | Preflight service Redis URL. |
| `PREFLIGHT_REDIS_PASSWORD_FILE` | — | compose (`preflight`) | Preflight service Redis password file (Docker secret). |
| `PREFLIGHT_LISTEN_ADDR` | `compose(dev|prod): 0.0.0.0:9001` | compose (`preflight`) | Preflight service listen address. |
| `PREFLIGHT_LOG_LEVEL` | `compose(dev|prod): info` | compose (`preflight`) | Preflight service log level. |
| `PREFLIGHT_METRICS_ENABLED` | `compose(dev|prod): true` | compose (`preflight`) | Enables preflight service metrics. |

## Tests (env hygiene)

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `ADMIN_PASSWORD_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `AGENT_JWT_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `CAP_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `CLIMATE_ENGINE_API_KEY_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `DTALE_INTERNAL_TOKEN_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `OAUTH_GITHUB_CLIENT_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `OAUTH_GOOGLE_CLIENT_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `OAUTH_ORCID_CLIENT_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `OPENET_API_KEY_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `OPENTOPOGRAPHY_API_KEY_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `POSTGRES_PASSWORD_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `REDIS_PASSWORD_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `SECRET_KEY_FILE` | — | tests set / scrub env | Tests install deterministic Flask secrets via temp files. |
| `SECURITY_PASSWORD_SALT_FILE` | — | tests set / scrub env | Tests install deterministic Flask secrets via temp files. |
| `WC_TOKEN_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `WEPP_AUTH_JWT_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `WEPP_AUTH_JWT_SECRETS_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `WEPP_MCP_JWT_SECRET_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |
| `ZOHO_NOREPLY_EMAIL_PASSWORD_FILE` | — | tests scrub env | Prevents host `*_FILE` secrets from leaking into tests. |

## Legacy / Deprecated

| Variable | Default | Used by | Description |
|---|---:|---|---|
| `SESSION_REDIS_HOST` | `python: localhost` | legacy (dead code in `wepppy.weppcloud.configuration`) | Legacy session Redis host override (superseded by `SESSION_REDIS_URL`). |
| `SESSION_REDIS_PORT` | `python: 6379` | legacy (dead code in `wepppy.weppcloud.configuration`) | Legacy session Redis port override (superseded by `SESSION_REDIS_URL`). |
