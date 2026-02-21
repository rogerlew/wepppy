# Mini Work Package: Secrets Migration (Env Vars -> Secret Files)
Status: In Progress (forest + forest1 rollout complete; next: wepp1)
Last Updated: 2026-02-13
See also: `docs/infrastructure/secrets.md`, `docker/README.md`
Primary Areas: `docker/docker-compose.dev.yml`, `docker/docker-compose.prod.yml`, `docker/docker-compose.prod.worker.yml`, `docker/docker-compose.prod.wepp1.yml`, `wctl/*`, `tools/wctl2/*`, `wepppy/weppcloud/configuration.py`, `wepppy/weppcloud/utils/auth_tokens.py`, `wepppy/config/redis_settings.py`, `wepppy/microservices/browse/*`

## Objective
Migrate secrets from `.env`/Compose interpolation into file-mounted secrets (Docker Compose `secrets:` now; Kubernetes Secret volumes next) to reduce accidental exposure via:
- request/exception logging (notably browse microservice)
- `docker compose config` output
- container environment inspection (`docker inspect`, `/proc/*/environ`)

## Problem Summary (Current State)
- `env_file:` currently loads `docker/.env` into most containers, so secrets end up in process environments.
- Compose files interpolate secrets into env/commands (for example building URLs with `${REDIS_PASSWORD}`), so `docker compose config` can surface secret values.
- Several modules call `load_dotenv()` at import time, which makes configuration implicit and hard to audit.

## Scope
In-scope:
- Define and implement a single secret-file contract across services:
  - Docker Compose mounts to `/run/secrets/<secret_id>`
  - applications read secrets from `*_FILE` environment variables
- Remove non-doc `load_dotenv()` calls (exception: culvert-at-risk dev-package scripts).
- Update all Docker Compose stacks used in practice:
  - `forest` (dev): `docker/docker-compose.dev.yml`
  - `forest1` (test production): `docker/docker-compose.prod.yml`
  - `wepp1` (wepp.cloud): `docker/docker-compose.prod.wepp1.yml` (plus whatever base file `wctl` composes with)
  - `wepp2` (worker prod): `docker/docker-compose.prod.worker.yml` (+ override file if used)
- Add regression coverage for file-based secret reads and “no secret values in rendered compose” checks.
- Update operator tooling (`tools/wctl2/*`) so common commands (notably `wctl rq-info`) work with `*_FILE` secrets and do not place credentials in host argv/logs.

Out-of-scope (explicitly):
- Rotating secrets (keep values identical; migrate storage only).
- Re-architecting CAP/third-party services that do not support file-based secrets (track separately if needed).
- The Kubernetes worker migration itself (but ensure this secret contract is Kubernetes-ready).

## Target Contract (Authoritative)
1. Secrets live as files (not committed):
   - Compose: `docker/secrets/<secret_id>` -> `/run/secrets/<secret_id>`
   - Kubernetes: Secret volume -> `/run/secrets/<secret_id>`
2. Code reads secrets via `*_FILE` env vars, with a temporary compatibility fallback to direct env vars:
   - Prefer `<NAME>_FILE` if set
   - Else use `<NAME>` if set (transition only)
   - Else fail fast with a descriptive error (no silent defaults)
3. Non-secrets live in env files (committed defaults + per-host overrides):
   - `docker/defaults.env` (committed, non-secret)
   - `docker/.env` (gitignored, non-secret overrides only)

## Canonical Secret IDs (Initial Set)
Use stable IDs so Compose and Kubernetes mounts match.

This list reflects what the in-repo Compose files mount today. If a secret ID is listed in a service's `secrets:` block, the file must exist on the host (Compose will refuse to start otherwise).

- `flask_secret_key`
- `flask_security_password_salt`
- `wepp_auth_jwt_secrets` (comma-delimited list; first is active)
- `agent_jwt_secret`
- `wepp_mcp_jwt_secret` (Compose currently sets `WEPP_MCP_JWT_SECRET_FILE` for `query-engine`)
- `dtale_internal_token`
- `cap_secret`
- `postgres_password`
- `redis_password`
- `opentopography_api_key`
- `climate_engine_api_key`
- `admin_password` (used by `profile-playback`)
- `oauth_github_client_secret` (Compose mounts this by default)
- `oauth_google_client_secret` (Compose mounts this by default)
- `zoho_noreply_email_password` (Compose mounts this by default)

Notes:
- Some of the IDs above are feature-gated in application code, but *not* in Compose. If a `*_FILE` env var is set and the secret file is missing/empty, the service will fail fast.
- Full inventory (including optional integrations like `openet_api_key`, `wc_token`, etc.): `docs/infrastructure/secrets.md`.
## Implementation Plan (Multi-phase)

### Phase 0: Inventory + Design Lock (No Behavior Change)
- [x] Inventory all secret consumers and current env var names.
- [x] Confirm which services actually require each secret (especially browse).
- [ ] Confirm Docker Compose version supports `secrets:` with non-root runtime users on all target hosts.
- [x] Write the “secret map” table (secret id -> env var(s) -> consuming services) into `docs/infrastructure/secrets.md` (append-only update).
- [x] Decide on exact `*_FILE` names (prefer `FOO_FILE` where `FOO` already exists).

Review gate:
- [x] Diff review: no secret values added to docs/examples.

### Phase 1: Code Support For File-Based Secrets (Keep Existing Env Working)
- [x] Add a small shared helper (for example `wepppy/config/secrets.py`) to:
  - read secret bytes/text from `<NAME>_FILE` (strip trailing newline/whitespace)
  - fall back to `<NAME>` (transition only)
  - raise clear errors when required secrets are missing
- [x] Update `wepppy/weppcloud/configuration.py` to load:
  - `SECRET_KEY` via `SECRET_KEY_FILE`
  - `SECURITY_PASSWORD_SALT` via `SECURITY_PASSWORD_SALT_FILE`
  - OAuth client secrets via `*_FILE` variants
- [x] Update `wepppy/weppcloud/utils/auth_tokens.py` to support:
  - `WEPP_AUTH_JWT_SECRETS_FILE` (preferred)
  - `WEPP_AUTH_JWT_SECRET_FILE` (fallback if a single secret is used)
- [x] Update Redis resolution to support `REDIS_PASSWORD_FILE` (even if Redis is low priority, it is used in browse auth + revocation).
- [x] Remove import-time `load_dotenv()` usage everywhere except:
  - `docs/culvert-at-risk-integration/dev-package/scripts/*`
- [x] Lock down browse exception paths so stack traces are not returned/written by default (debug opt-in env vars only).
- [x] Sanitize OpenTopography error handling so API keys do not leak via exception/log strings.
- [x] Add pytest coverage:
  - file-based secret read
  - missing file error shape (explicit)
  - precedence when both `<NAME>` and `<NAME>_FILE` are set

Review gates:
- [x] `wctl run-pytest tests --maxfail=1`
- [x] `rg -n \"load_dotenv\\(\" wepppy | wc -l` equals expected post-change baseline.

### Phase 2: Docker Compose Secrets Wiring (Dev + Prod UI Stacks)
- [x] Create `docker/defaults.env` (committed) containing only non-secrets.
- [x] Update `docker/.env` guidance: non-secret overrides only (keep file mode `0600` on hosts anyway).
- [x] Add `docker/secrets/` directory to `.gitignore` (if not already present).
- [x] Update `docker/docker-compose.dev.yml`:
  - add top-level `secrets:` definitions (file sources under `docker/secrets/`)
  - mount only required secrets per service
  - replace secret env vars with `*_FILE` env vars
  - remove secret interpolation from URLs/commands where feasible
- [x] Update `docker/docker-compose.prod.yml` similarly.
- [x] Update `docker/README.md` and any deploy docs that instruct creating secrets in `docker/.env`.

Review gates:
- [x] `wctl docker compose config` does not contain secret values (spot-check by searching for known secret keys without values; validate that only `*_FILE` paths remain).
- [x] `docker inspect <container>` shows no secret values in `.Config.Env` (only `*_FILE` vars).

### Phase 3: Worker Stack + wepp1 Overlay
- [x] Update `docker/docker-compose.prod.worker.yml`:
  - remove `${REDIS_PASSWORD}` interpolation in URLs/commands (prefer `REDIS_PASSWORD_FILE` + code reading)
  - mount only worker-required secrets (likely JWT + agent auth + redis password if needed)
- [x] Update `docker/docker-compose.prod.wepp1.yml` (and any `wctl` compose composition rules) so wepp1’s rendered config still uses secrets-as-files.
- [x] Ensure dev/prod websocket services can read bind-mounted secret files (`status`, `preflight` run as `${UID}:${GID}`).
- [ ] Ensure per-host UID/GID and secret file readability is correct for images built with `APP_UID`/`APP_GID` (notably `wepp1`/`worker` with `APP_UID=1002`, `APP_GID=130`). Compose `secrets:` are bind-mounts; validate with `docker compose exec <service> sh -lc 'id; ls -l /run/secrets; for f in /run/secrets/*; do test -r "$f" || echo "not readable: $f"; done'` and document the required host ownership/mode.

Review gates:
- [x] `wctl docker compose config` on each host profile (`dev`, `prod`, `wepp1`, `worker`) contains no secret values.
### Phase 3.5: Operator Tooling (wctl2)
- [x] Patch `wctl rq-info` to resolve the Redis URL inside the container (supports `REDIS_PASSWORD_FILE`).
- [x] Ensure `wctl rq-info` does not place Redis credentials into host-side argv/logging.
- [x] Add unit coverage under `tools/wctl2/tests/*` and update `tools/wctl2/docs/*`.

### Phase 4: Environment Rollouts (Forest/Fleet)
Roll out in this order: `forest` -> `forest1` -> `wepp1` -> `wepp2`.

#### forest (dev instance)
- [x] Create `docker/secrets/` locally and populate from the current `docker/.env` values (do not regenerate).
- [x] Move any remaining secret values out of `docker/.env`.
- [x] `wctl down && wctl up -d`
- [x] Validate:
  - `GET /health`
  - login/session cookie flow
  - browse endpoints for a known run (include a forced error path to ensure stack traces do not include env dumps)
  - rq-engine session-token flow (if applicable)
  - `wctl rq-info` works (no Redis `Authentication required.` errors)

Rollback:
- [ ] Restore previous compose + `docker/.env` and recreate containers.

#### forest1 (test production)
Preflight:
- [x] Snapshot current `docker/.env` (secure location; do not commit).
- [x] Confirm `wctl` profile/compose files in use.
- [x] Confirm no active migrations require stable worker pools.

Deploy:
- [x] Create `docker/secrets/` and populate from existing values (no rotation).
- [x] Deploy updated compose stack.
- [x] Verify:
  - `/health` (weppcloud)
  - websocket bridges (status/preflight)
  - CAP health
  - rq-worker connectivity (`wctl rq-info`)

Notes:
- If `cap`, `status`, or `preflight` were not rebuilt during deploy, they may fail with missing secret env or Redis `NOAUTH`. Fix by rebuilding and recreating those services (`wctl build --no-cache cap status preflight && wctl up -d --no-deps --force-recreate cap status preflight`).

Rollback:
- [ ] Re-deploy prior compose config and restore env-based secrets.

#### wepp1 (wepp.cloud)
Preflight:
- [ ] Confirm active compose topology (`wctl docker compose config`).
- [ ] Confirm run storage mounts (`/geodata/wc1` vs `/wc1`) and that secrets directory is not under a browseable mount.
- [ ] Confirm session/JWT invariants required across services (do not change raw values).

Deploy:
- [ ] Create secret files with existing values.
- [ ] Deploy compose changes (prefer staged restart: start new containers before stopping old if topology allows).
- [ ] Verify:
  - auth flows (login, session persistence)
  - browse microservice access control (JWT validation + revocation checks)
  - rq-engine endpoints
  - CAP integration (if enabled)

Rollback:
- [ ] Revert to the prior compose config without regenerating secrets.

#### wepp2 (worker prod)
Preflight:
- [ ] Confirm worker host uses `docker/docker-compose.prod.worker.yml` (and whether `weppcloudr` profile is enabled).
- [ ] Confirm RQ queue state and acceptable restart window.

Deploy:
- [ ] Create worker-required secret files (minimize scope; do not mount UI-only secrets).
- [ ] Restart worker services using compose.
- [ ] Validate:
  - workers register with RQ dashboard / redis
  - enqueue/execute a known lightweight job

Rollback:
- [ ] Restore env-based secrets and restart.

## Test Plan (Automated + Manual)
Automated:
- [x] `wctl run-pytest tests --maxfail=1`
- [x] `wctl run-npm test`
- [x] `wctl doc-lint --path docs/infrastructure/secrets.md --path docs/mini-work-packages/20260213_secrets_migration.md`

Manual:
- [x] `wctl docker compose config | rg -n \"SECRET_KEY=|WEPP_AUTH_JWT_SECRET=|OAUTH_.*_SECRET=\"` returns no matches.
- [x] `docker inspect <browse_container>` does not show secret values in env.
- [ ] Induce a controlled browse exception and confirm logs do not include environment dumps.

## Acceptance Criteria
- No secret values appear in `docker compose config` output for the dev/prod/worker/wepp1 profiles.
- No secret values are injected via `env_file:` into browse (or any) services; only `*_FILE` paths remain.
- Login/session/JWT auth continues to work unchanged (no secret rotation).
- Non-doc `load_dotenv()` usage is eliminated.

## Follow-ups
- Kubernetes worker pool manifests (Deployments, Secrets, rolling restarts) can use the same `/run/secrets/<secret_id>` contract.
- If third-party images cannot read secrets from files, track a dedicated package for “file-to-env wrapper entrypoints” (or upstream patches) with explicit risk acceptance.
