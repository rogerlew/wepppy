# Secrets Management
> Authoritative guidance for handling secrets in WEPPpy / WEPPcloud deployments.

## Goals
- Reduce accidental secret exposure via:
  - request/exception logging (especially the browse microservice)
  - `docker compose config` output (rendered YAML interpolation)
  - container environment inspection (`docker inspect`, crash reports, `/proc/*/environ`)
- Keep one scheme that works for Docker Compose today and Kubernetes worker pools next.

## Threat Model (What This Does And Does Not Protect)
- Protects against accidental disclosure through logs, process environments, and operator tooling output.
- Does not protect against a host-root compromise. If an attacker has root on the node, they can read mounted secret files.

## Definitions
- **Secret**: any value that grants access, signs tokens, or enables impersonation.
  - Examples: Flask `SECRET_KEY`, password salts, JWT signing secrets, OAuth client secrets, API keys, SMTP passwords, internal service tokens.
- **Config (non-secret)**: values safe to appear in logs, `docker compose config`, and container env.
  - Examples: ports, feature flags, hostnames, `SITE_PREFIX`, run roots.

## Policy (Canonical Direction)
1. Secrets are mounted as files, not injected as environment variables.
2. Each service mounts only the secrets it needs (least privilege).
3. Secrets must never live under run trees (`/wc1/runs/...`) or any browseable/exportable directory.
4. Do not embed secrets inside URLs (for example `redis://:password@...`) unless there is no alternative.
5. Avoid passing secrets on process command lines (argv). Prefer config files or file-backed secret reads.

Implementation targets:
- Docker Compose: use Compose `secrets:` and mount to `/run/secrets/<secret_id>`.
- Kubernetes: use `Secret` volumes (or CSI secret stores) mounted to the same path scheme.

## Canonical Secret IDs (Recommended)
Use stable secret IDs so Compose and Kubernetes mount the same filenames:

| Secret ID | Used By | Notes |
| --- | --- | --- |
| `flask_secret_key` | `weppcloud`, `rq-engine` | Must match across services that mint/validate session cookies. |
| `flask_security_password_salt` | `weppcloud`, `rq-engine` | Must match where password hashing/session logic depends on it. |
| `wepp_auth_jwt_secrets` | API services that issue/validate JWTs | File contains either a single secret or a comma-delimited rotation list (first is active). |
| `wepp_mcp_jwt_secret` | `query-engine` | Enables MCP routes; can be the same value as `wepp_auth_jwt_secrets` but does not have to be. |
| `agent_jwt_secret` | agent auth paths | Keep distinct from Flask secret key. |
| `oauth_github_client_secret` | `weppcloud` | Optional, but treat as secret if enabled. |
| `oauth_google_client_secret` | `weppcloud` | Optional, but treat as secret if enabled. |
| `oauth_orcid_client_secret` | `weppcloud` | Optional, but treat as secret if enabled. |
| `dtale_internal_token` | `browse`, `dtale` | Internal service-to-service auth token. |
| `cap_secret` | `cap` | CAPTCHA secret; do not expose to browser clients. |
| `zoho_noreply_email_password` | `weppcloud` | SMTP auth secret when Zoho is enabled. |
| `postgres_password` | `postgres`, app services | Higher priority if connection strings can surface in logs. |
| `redis_password` | `redis`, app services | Lower priority if Redis is network-isolated, but still a secret. |
| `opentopography_api_key` | NoDb controllers / workers | OpenTopography API key used to download DEMs. |
| `climate_engine_api_key` | NoDb controllers / workers | ClimateEngine API key used by the OpenET Climate Engine integration. |
| `discord_bot_token` | `weppcloud`, `rq-worker`, `rq-worker-batch` | Mounted directly to `/opt/vendor/weppcloud2/weppcloud2/discord_bot/.bot_token` for vendorized Discord notifications. |
| `openet_api_key` | NoDb controllers / workers | OpenET API key used by the OpenET monthly time-series API. Not the same as ClimateEngine. |
| `wc_token` | dev tooling / integrations | Bearer token used by the `climatena_ca` helper (if used). |
| `admin_password` | test tooling | Automation credential for `profile_recorder` playback. Not needed for core runtime. |

Notes:
- A “one secret per file” rule holds naturally when each Secret key maps to one file.
- For rotation lists (for example JWT secrets), a single file may contain a comma-delimited list if the application expects a list.

## Phase 0 Inventory (Current Consumers + Env Names)
This section is the Phase 0 “inventory” deliverable for the secrets migration work package.

### Secret Map
| Secret ID | Current env var(s) | Proposed `*_FILE` env var(s) | Primary consumers | Notes |
| --- | --- | --- | --- | --- |
| `flask_secret_key` | `SECRET_KEY` | `SECRET_KEY_FILE` | Flask `weppcloud`; FastAPI `rq-engine` session validation | Signs Flask session cookies via `itsdangerous.Signer`. Must be identical between `weppcloud` and `rq-engine` for `/rq-engine/api/.../session-token` flows. |
| `flask_security_password_salt` | `SECURITY_PASSWORD_SALT` | `SECURITY_PASSWORD_SALT_FILE` | Flask `weppcloud` | Flask-Security password hashing salt/pepper input. Treat as auth-critical and stable. |
| `wepp_auth_jwt_secrets` | `WEPP_AUTH_JWT_SECRETS`, `WEPP_AUTH_JWT_SECRET` | `WEPP_AUTH_JWT_SECRETS_FILE`, `WEPP_AUTH_JWT_SECRET_FILE` | `weppcloud` token issuance; `rq-engine`/`browse` token validation | Prefer `WEPP_AUTH_JWT_SECRETS` (comma-delimited rotation list; first is active). |
| `wepp_mcp_jwt_secret` | `WEPP_MCP_JWT_SECRET` | `WEPP_MCP_JWT_SECRET_FILE` | `query-engine` MCP mount | Enables `/mcp` routes when configured. Compose mounts `/run/secrets/wepp_mcp_jwt_secret` and sets `WEPP_MCP_JWT_SECRET_FILE`. |
| `agent_jwt_secret` | `AGENT_JWT_SECRET` (dev `.env` also uses `AGENT_JWT_SECRET_KEY`) | `AGENT_JWT_SECRET_FILE` | `weppcloud` agent JWT issuance; `wepppy/mcp/*` tool auth | Code expects `AGENT_JWT_SECRET`. `AGENT_JWT_SECRET_KEY` is a legacy/dev key name; do not treat it as a runtime env var. |
| `agent_jwt_token` | `AGENT_JWT_TOKEN` | *(runtime; not file-backed)* | agent session bootstrap (`wepppy/rq/agent_rq.py`, `wepppy/mcp/base.py`) | Short-lived bearer token granted to the agent session. Treat as secret; never log or persist. |
| `oauth_github_client_secret` | `OAUTH_GITHUB_CLIENT_SECRET`, `GITHUB_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_SECRET_KEY` | `OAUTH_GITHUB_CLIENT_SECRET_FILE` | `weppcloud` OAuth | Optional; keep ID/secret pairs aligned with the correct host redirect URI. |
| `oauth_google_client_secret` | `OAUTH_GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_CLIENT_SECRET` | `OAUTH_GOOGLE_CLIENT_SECRET_FILE` | `weppcloud` OAuth | Optional. |
| `oauth_orcid_client_secret` | `OAUTH_ORCID_CLIENT_SECRET`, `ORCID_OAUTH_CLIENT_SECRET`, `ORCID_OAUTH_SECRET_KEY` | `OAUTH_ORCID_CLIENT_SECRET_FILE` | `weppcloud` OAuth | Optional. |
| `dtale_internal_token` | `DTALE_INTERNAL_TOKEN` | `DTALE_INTERNAL_TOKEN_FILE` | `browse` -> `dtale` loader bridge | Shared secret used as `X-DTALE-TOKEN` for `/internal/load`. |
| `cap_secret` | `CAP_SECRET` | `CAP_SECRET_FILE` | `cap` service; server-side CAPTCHA verification (`weppcloud`, `rq-engine`) | `CAP_SITE_KEY` is public; `CAP_SECRET` is the server-side verify secret. |
| `zoho_noreply_email_password` | `ZOHO_NOREPLY_EMAIL_PASSWORD` | `ZOHO_NOREPLY_EMAIL_PASSWORD_FILE` | `weppcloud` mail | Optional; only used when `ZOHO_NOREPLY_EMAIL` is also set. |
| `postgres_password` | `POSTGRES_PASSWORD` | `POSTGRES_PASSWORD_FILE` | `postgres` container; app DB URLs | `DATABASE_URL`/`SQLALCHEMY_DATABASE_URI` currently embed the password (treat those as secret-bearing config). |
| `redis_password` | `REDIS_PASSWORD` | `REDIS_PASSWORD_FILE` | `redis` container; Python + Go clients | Many services accept `*_REDIS_URL` and inject `REDIS_PASSWORD` if the URL lacks auth. |
| `opentopography_api_key` | `OPENTOPOGRAPHY_API_KEY` | `OPENTOPOGRAPHY_API_KEY_FILE` | DEM downloads (`wepppy/locales/earth/opentopography`) | Used as a query parameter when calling OpenTopography. |
| `climate_engine_api_key` | `CLIMATE_ENGINE_API_KEY` | `CLIMATE_ENGINE_API_KEY_FILE` | OpenET Climate Engine integration (`wepppy/nodb/mods/openet`) | Legacy `docker/.env` scanning has been removed; configure `CLIMATE_ENGINE_API_KEY(_FILE)` explicitly. |
| `discord_bot_token` | *(none; vendor reads file path directly)* | *(none; mounted at fixed vendor path)* | Discord notifications (`weppcloud2.discord_bot.discord_client`) | Compose mounts this secret at `/opt/vendor/weppcloud2/weppcloud2/discord_bot/.bot_token` to satisfy vendor import-time token loading. |
| `openet_api_key` | `OPENET_API_KEY` | `OPENET_API_KEY_FILE` | OpenET time-series API (`wepppy/locales/conus/openet`) | Different API than ClimateEngine; not interchangeable with `CLIMATE_ENGINE_API_KEY`. |
| `wc_token` | `WC_TOKEN` | `WC_TOKEN_FILE` | ClimateNA-CA helper (`wepppy/climates/climatena_ca`) | Used as an `Authorization: Bearer ...` token for the external helper service. |
| `admin_password` | `ADMIN_PASSWORD` | `ADMIN_PASSWORD_FILE` | `wepppy/profile_recorder` | Automation-only credential used by playback harness to log into a WEPPcloud instance. |

### Ambiguous Secrets (Clarifications)
- `SECRET_KEY` vs `WEPP_AUTH_JWT_SECRET(S)`:
  - `SECRET_KEY` is the Flask session signing secret (also used by `rq-engine` to unsign/validate session cookies).
  - `WEPP_AUTH_JWT_SECRET`/`WEPP_AUTH_JWT_SECRETS` is the HMAC secret used for application JWTs (`auth_tokens.*`), including browse/rq-engine bearer tokens.
- `WEPP_AUTH_JWT_SECRET(S)` vs `WEPP_MCP_JWT_SECRET`:
  - `WEPP_MCP_JWT_SECRET` gates the query-engine MCP mount and validates MCP tokens (`WEPP_MCP_JWT_*` env prefix).
  - It can be the same underlying bytes as `WEPP_AUTH_JWT_SECRETS[0]` for simplicity, but treat it as a separate “secret slot” in inventory.
- `AGENT_JWT_SECRET_KEY`:
  - Not a runtime env var consumed by code; it is a dev `.env` key name that Compose maps into `AGENT_JWT_SECRET` in containers.
- `CLIMATE_ENGINE_API_KEY` vs `OPENET_API_KEY`:
  - `CLIMATE_ENGINE_API_KEY` authenticates requests to `api.climateengine.org` (OpenET integration via ClimateEngine).
  - `OPENET_API_KEY` authenticates requests to `openet-api.org` (OpenET monthly time-series API).
- `CAP_SITE_KEY`:
  - Public “site key” used by browser clients. Do not store it as a secret file, but keep it adjacent to `CAP_SECRET` in deployment docs because operators often rotate them together.
- `DATABASE_URL` / `SQLALCHEMY_DATABASE_URI`:
  - Treated as secret-bearing because they typically embed the DB password. Prefer composing them at runtime from non-secrets + `postgres_password` rather than storing them in env long-term.

### Non-canonical Secret Sources (Should Be Removed In Migration)
These are inventory items because they can load secrets implicitly and widen exposure:
- `wepppy/nodb/base.py` / `wepppy/nodb/status_messenger.py` / `wepppy/rq/project_rq.py` / `wepp_runner/status_messenger.py`: `load_dotenv(.../.env)` import-time loads (files are not present in repo; legacy behavior). Removed in Phase 1 (2026-02-13).
- `wepppy/rq/cancel_job.py`, `wepppy/webservices/wmesque2.py`, `wepppy/climates/climatena_ca/__init__.py`: `load_dotenv()` with implicit search. Removed in Phase 1 (2026-02-13).
- `wepppy/nodb/mods/openet/openet_ts.py`: scans for `docker/.env` to resolve `CLIMATE_ENGINE_API_KEY`. Removed in Phase 1 (2026-02-13).
- `wepppy/locales/conus/openet/openet_client.py`: reads `wepppy/locales/conus/openet/.env` if `OPENET_API_KEY` is unset. Removed in Phase 1 (2026-02-13).

Allowed exception (do not remove):
- `docs/culvert-at-risk-integration/dev-package/scripts/*` (dev-package tooling explicitly keeps `load_dotenv`).

## Docker Compose: Secrets As Files (Recommended)

### File Layout
Recommended structure (secret files are not committed):

```text
docker/
  defaults.env                 # committed, non-secret defaults
  overrides.env                # optional per-host non-secret overrides (gitignored)
  secrets/                     # gitignored; one file per secret ID
    flask_secret_key
    flask_security_password_salt
    wepp_auth_jwt_secrets
    dtale_internal_token
    ...
```

### Compose Pattern
Use Compose secrets so `docker compose config` does not render secret values.

Minimal example:

```yaml
secrets:
  flask_secret_key:
    file: ./secrets/flask_secret_key

services:
  weppcloud:
    secrets:
      - flask_secret_key
    environment:
      SECRET_KEY_FILE: /run/secrets/flask_secret_key
```

Key rules:
- Do not reference secret values in `environment:` (for example `SECRET_KEY: ${SECRET_KEY}`).
- Do not bake secrets into `command:` args.
- Prefer `*_FILE` environment variables that point to `/run/secrets/<secret_id>`.
  - This keeps code paths consistent across Compose and Kubernetes.
  - `*_FILE` values are not secrets; they are paths.
- Treat setting `*_FILE` as an explicit contract: the file must exist and be non-empty (the app fails fast when a configured secret file is unreadable/empty).

### Non-Secrets: Keep Using env files
Continue using `env_file:` for non-secrets (defaults, paths, ports, feature flags).
If a value is a secret, it does not belong in `env_file:`.

### Local Development Workflow (Manual)
Generate secrets as files (example; choose your own generation policy):

```bash
cd /workdir/wepppy/docker
mkdir -p secrets
chmod 700 secrets

python -c 'import secrets; print(secrets.token_urlsafe(64))' > secrets/flask_secret_key
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/flask_security_password_salt
chmod 600 secrets/*
```

Operational check:
- `docker compose config` must not contain secret values.
- `docker inspect <container>` env must not contain secret values (only `*_FILE` paths).

## Kubernetes: Worker Pools (Forward-Compatible)
For `rq-worker` and `rq-worker-batch` running in Kubernetes:
- Store the same secret IDs in a Kubernetes `Secret`.
- Mount them as a volume to `/run/secrets/` (or `/run/secrets/wepppy/`).
- Set only `*_FILE` environment variables to point at those mounted paths.

This keeps the container contract aligned across:
- Docker Compose (UI + microservices)
- Kubernetes (worker pools with rolling restarts/scale)

## Migration Checklist (Docs-First)
1. Inventory secrets currently flowing via `.env`/`env_file:` and Compose interpolation.
2. Define the secret ID set and canonical file names (table above).
3. Move secrets into file mounts (Compose secrets / Kubernetes Secret volumes).
4. Update runtime configuration to read secrets from files (prefer `*_FILE`).
5. Remove non-doc `load_dotenv()` usage so configuration is explicit and auditable.
6. Verify:
   - `docker compose config` contains no secret values.
   - browse service error paths do not surface secrets in stack traces or exception logs.
   - rotating a secret requires only updating the secret file + restarting affected services.

## Operational Notes (Logging Risk)
- Treat the browse microservice as a high-exposure surface:
  - it handles untrusted paths and returns detailed error payloads in some flows.
  - secrets should not be present in its environment, argv, or exception messages.
- Never accept secrets via query parameters. Use headers/cookies and redact them in logs.
- Operator guidance: do not pass secrets on command lines (for example credential-bearing URLs). `wctl`/`wctl2` logs `docker compose` invocations; `compose exec` redaction is best-effort and passthrough commands may log args verbatim.
