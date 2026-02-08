# WeppCloud Bootstrap Specification

## Overview

Replace the external `wepppy-win-bootstrap` Windows tool with a server-side
git-based workflow integrated directly into the WeppCloud UI. Users can clone
a run's WEPP/SWAT+ input files, modify them locally, push changes back, and
re-run simulations against any committed state.

## Scope

### What Gets Tracked

Only simulation input directories:

- `wepp/runs/` — WEPP input files (`.slp`, `.sol`, `.cli`, `.man`, `.run`, etc.)
- `swat/TxtInOut/` — SWAT+ text input files

Everything else is `.gitignore`'d:

- DEM rasters, parquet files, output directories
- `.nodb` state files
- Logs, lock files, Redis state

### What Does NOT Apply

- **Batch runs** — Bootstrap is for canonical single runs only.
- **Omni scenarios** — No integration with `_pups/` or scenario/contrast system.
- **Child runs** — Only the top-level run directory.

## Architecture

### Server-Side Components

#### 1. Git Repository Initialization

When the user enables Bootstrap in the UI, the server:

1. Runs `git init` in the run's working directory
   (`/wc1/runs/<prefix>/<runid>/`, where `prefix` is the first two characters
   of the run ID).
2. Writes a `.gitignore` that excludes everything except `wepp/runs/` and
   `swat/TxtInOut/`, plus an explicit ignore for `wepp/runs/tc_out.txt`.
3. Creates an initial commit on `main` with the current input file state.
4. Sets `receive.denyCurrentBranch=updateInstead` so HTTP pushes update the
   checked-out working tree.
5. Sets `receive.denyNonFastForwards=true` (rejects force pushes) and
   `http.receivepack=true` (enables pushes over HTTP).
6. Installs the `pre-receive` validation hook.

#### 2. Git HTTP Backend via Caddy

Caddy reverse-proxies git HTTP requests to `git-http-backend`:

```
Client (git clone/push/pull)
    │
    ▼
Caddy (/git/<prefix>/<runid>/...)
    │
    ├── forward_auth → Flask /api/bootstrap/verify-token
    │                  (decodes JWT, checks signature, checks run eligibility)
    │                  Returns 200 or 401
    │
    ▼ (on 200)
git-http-backend (CGI)
    │
    ▼
work tree repo at /wc1/runs/<prefix>/<runid>/
```

**What is `git-http-backend`?** It is a CGI program that ships with git itself
(typically at `/usr/lib/git-core/git-http-backend`). It implements the smart HTTP
transport protocol. It is not a standalone server — it needs a CGI host.

**CGI host: `fcgiwrap`.** A lightweight FastCGI wrapper. It can run as a systemd
service on the host (Unix socket) or as a sidecar container over TCP
(`fcgiwrap:9000`). Caddy speaks FastCGI to it, and `fcgiwrap` invokes
`git-http-backend` per-request.

**Why Caddy:** Caddy's `forward_auth` directive handles the auth subrequest to
Flask cleanly, and its FastCGI transport proxies to `fcgiwrap` without additional
configuration. Automatic HTTPS via Let's Encrypt is a bonus.

**Why not Flask-proxied:** Streaming git pack data through Flask workers would
block them for the duration of clone/push operations. Caddy + fcgiwrap keeps
Flask workers free for application requests.

#### 3. Authentication (JWT)

**Stateless JWTs per user, per run.** No server-side token storage. Each user
mints a JWT from the UI, and the server validates it on every git operation by
checking the signature and ensuring the run is eligible (user opt-in is set in
nodb, the Postgres run record is not admin-disabled, and the run is
non-anonymous).

**JWT payload:**

```json
{
  "sub": "user@example.com",
  "runid": "feverish-lamp",
  "aud": "wepp.cloud",
  "iat": 1706900000,
  "exp": 1709492000
}
```

The `aud` (audience) claim is set to the `external_host` of the WeppCloud
instance (e.g., `wepp.cloud`, `forest.bearhive.duckdns.org`). This scopes the
JWT to a specific deployment — a token minted on one instance cannot be used on
another.

**Token lifecycle:**

1. User clicks **Enable Bootstrap** (or **Mint Token** if already enabled).
2. Server signs a JWT with a server-wide secret key containing the user's email
   and the runid. Tokens expire after 6 months (`exp` claim).
3. UI displays the Clone Command and Set Remote Origin Command with the JWT as
   the Basic auth password.

```
git clone https://<user_id>:<jwt>@wepp.cloud/git/<prefix>/<runid>/.git
```

The `<user_id>` is a URL-safe identifier (username or numeric ID, not raw email)
to avoid `@` encoding issues in URLs. Authorization is based on JWT claims
(`sub`, `runid`, `aud`); the Basic-auth username is not used for access checks.

**Verification flow** (`/api/bootstrap/verify-token`):

1. Decode and verify JWT signature against server secret.
2. Check `aud` claim matches the current `external_host`.
3. Extract `runid` claim from the JWT.
4. Check URL path is `/git/<prefix>/<runid>/.git/...` after URL-decoding and
   normalization (reject traversal segments and malformed paths).
5. Check the run is eligible: nodb `_bootstrap_enabled = true`, Postgres run
   record has `bootstrap_disabled = false`, and `is_anonymous = false`.
6. Check `sub` is a valid user with access to the run.
7. Return 200 with `X-Auth-User` header (user email). The `pre-receive` hook
   requires this header and records commit attribution based on the JWT (git
   author fields are not enforced).

**Revocation — admin blacklist flag:**

- **No per-user revocation.** Revocation is per-run only.
- When bootstrap is disabled for a run, `bootstrap_disabled` is set to true in
  Postgres. Git HTTP push/pull and token minting for that run are blocked
  immediately.
- Re-enabling bootstrap for the same run sets `bootstrap_disabled = false`.
  Users should mint a new JWT. Prior tokens still expire within 6 months. The
  nodb user opt-in remains set.
- Read-only commit/history checkout flows in the UI and bootstrap no-prep run
  buttons remain available for existing commit states while disabled.
- Only non-anonymous runs can enable bootstrap.

**Benefits:**

- **No token storage** — only a run-level admin blacklist flag in Postgres and
  a nodb opt-in flag are required.
- **Audit trail** — `sub` claim identifies the user on every request.
- **Stateless verification** — just signature check + run eligibility lookup.
- **Users can self-serve** — mint a new JWT anytime from the UI without
  admin intervention.

#### 4. Push Validation Hook (`pre-receive`)

A server-side `pre-receive` hook runs on every push and validates all ref
updates atomically:

**File type validation:**
- `.cli` files — verify climate file header/structure
- `.sol` files — verify soil file format
- `.man` files — verify management file format
- `.slp` files — verify slope file format
- Other recognized WEPP/SWAT+ input types — basic structural checks
  - Use the existing parsers for each file type; surface parser errors
    directly so users see the exact validation failure.
  - Run parser validations in a process pool for speed; reject on the first
    failure to keep hook latency low.

**`.run` file protection:**
- `.run` files are **tracked** (so users can clone and run WEPP locally) but
  **modifications are rejected**. The hook compares `.run` files against the
  `main` baseline and rejects the push if any differ.
- Rationale: `.run` files are passed to `subprocess`. Allowing user
  modifications is a command injection surface.

**General safety:**
- Reject files outside `wepp/runs/` and `swat/TxtInOut/` paths.
- Reject symlinks.
- Reject files exceeding 50 MB per file.
- Reject binary files (all tracked content should be text).
- Require an authenticated user header and write a JWT-based push log for
  commit attribution; git author/committer fields are not enforced.
- Persist the push log at `.git/bootstrap/push-log.ndjson` for UI lookup.
- Do not enforce commit message formats; the hook ignores message content.
- Concurrency relies on git fast-forward rules; a second push is rejected until
  the user pulls.

On validation failure, the hook prints a descriptive error message that the user
sees in their `git push` output.

#### 5. RQ Engine Bootstrap Routes (No-Prep)

Bootstrap run buttons use no-prep endpoints that skip any prep steps which would
overwrite WEPP/SWAT+ inputs. Add a dedicated `bootstrap_routes.py` to the
rq-engine with:

```
@router.post("/runs/{runid}/{config}/run-wepp-npprep")
@router.post("/runs/{runid}/{config}/run-swat-noprep")
@router.post("/runs/{runid}/{config}/run-wepp-watershed-no-prep")
```

These routes run against the currently checked-out commit and must not switch
branches or regenerate input files.

### Integration Point: Wepp NoDb Controller

Bootstrap is **not a separate mod**. It is integrated directly into the existing
`Wepp` nodb controller.

Bootstrap uses two flags:

1. **User opt-in (nodb):** `_bootstrap_enabled` is set by the user when they
   enable Bootstrap and is a one-way switch (no user-facing disable).
2. **Admin blacklist (Postgres):** `runs.bootstrap_disabled` blocks all git
   access for the run regardless of user opt-in.

Only non-anonymous runs can enable bootstrap.

#### New Properties

```python
_bootstrap_enabled: bool    # User opt-in (one-way)
```

#### New Methods

```python
def init_bootstrap(self) -> None:
    """
    Initialize git repo, write .gitignore, create initial commit,
    install pre-receive hook. Sets _bootstrap_enabled = True.
    """

def mint_bootstrap_jwt(self, user_email: str, user_id: str) -> str:
    """
    Sign and return a JWT for the given user and this run.
    Does not store anything server-side.
    Returns the clone URL with embedded JWT (UI builds commands from it).
    """

def get_bootstrap_commits(self) -> list[dict]:
    """
    Return list of commits on main branch.
    Each entry: {sha, short_sha, message, author, date, pusher, git_author?}
    `author` is derived from the JWT push log (defaults to `\"unknown\"` if
    missing); use `git_author` for diagnostic context only.
    """

def checkout_bootstrap_commit(self, sha: str) -> bool:
    """
    Checkout a specific commit (detached HEAD or reset main).
    Returns success/failure.
    """

def get_bootstrap_current_ref(self) -> str:
    """
    Return current HEAD — either branch name or short SHA if detached.
    """

def disable_bootstrap(self) -> None:
    """
    Admin/Root only. Sets runs.bootstrap_disabled = True (invalidates all JWTs).
    Leaves working files and git history in place.
    """
```

### Pipeline Auto-Commit

When Bootstrap is enabled and the normal WeppCloud pipeline runs (e.g., user
changes landuse, rebuilds soils, regenerates climate), the pipeline should
ensure `main` is checked out at the beginning. This applies to the standard
run endpoints (non-bootstrap), and those paths auto-commit rebuilt inputs.
Bootstrap no-prep routes do not switch branches and do not auto-commit.

```python
# At start of pipeline (non-bootstrap endpoints only):
if wepp.bootstrap_enabled:
    # git checkout main

# At end of pipeline stage (after writing input files):
if wepp.bootstrap_enabled:
    # git add wepp/runs/ swat/TxtInOut/
    # git commit -m "Pipeline: rebuilt {stage_name}"
```

This keeps pipeline-generated commits on `main` while still allowing bootstrap
no-prep runs to execute against detached commits.

## UI Design

### Placement

Third collapsible section in the existing WEPP/SWAT+ execution panel:

```
▸ WEPP Advanced Options
▸ SWAT+ Advanced Options
▾ Bootstrap
```

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Bootstrap                                       [▾] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Current: main (a1b2c3d)                            │
│                                                     │
│  [Mint Token]                                       │
│                                                     │
│  Clone Command:                                     │
│  ┌────────────────────────────────────────────┐     │
│  │ git clone https://<user_id>:<jwt>@...      │     │
│  └────────────────────────────────────────────┘     │
│                                             [Copy]  │
│                                                     │
│  Set Remote Origin Command:                         │
│  ┌────────────────────────────────────────────┐     │
│  │ git remote set-url origin https://<...>    │     │
│  └────────────────────────────────────────────┘     │
│                                             [Copy]  │
│                                                     │
│  Commit:                                            │
│  ┌────────────────────────────────────────────┐     │
│  │ a1b2c3d — Pipeline: rebuilt climate     ▼  │     │
│  │ f4e5d6c — User: adjusted soil K values     │     │
│  │ 8g7h6i5 — Pipeline: initial commit         │     │
│  └────────────────────────────────────────────┘     │
│                                                     │
│  [Checkout]                                         │
│                                                     │
│  [Run WEPP Hillslopes and Watershed]                │
│  [Run WEPP Watershed]                               │
│  [Run SWAT+ Channel Routing]                        │
│                                                     │
│  [Disable Bootstrap (Admin/Root)]                   │
└─────────────────────────────────────────────────────┘
```

Before Bootstrap is enabled, the collapsible shows a single:

```
┌─────────────────────────────────────────────────────┐
│ Bootstrap                                       [▾] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Enable git-based input file management.            │
│  Clone the run's WEPP and SWAT+ input files,        │
│  modify them locally, and push changes back.        │
│                                                     │
│  [Enable Bootstrap]                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Workflow

1. User clicks **Enable Bootstrap**.
2. Server `git init`s (if not already initialized), commits current state.
3. User clicks **Mint Token** — server signs a JWT, UI shows Clone Command and
   Set Remote Origin Command.
4. User runs the Clone Command (or runs Set Remote Origin inside an existing
   clone):
```
git clone https://<user_id>:<jwt>@wepp.cloud/git/<prefix>/<runid>/.git
```
```
git remote set-url origin https://<user_id>:<jwt>@wepp.cloud/git/<prefix>/<runid>/.git
```
5. User edits input files, commits, pushes.
6. Push hook validates files. Rejects if `.run` modified or formats invalid.
7. User returns to UI, refreshes commit list (or it auto-refreshes).
8. User selects a commit from the dropdown.
9. User clicks **Checkout**, server checks out that commit.
10. User clicks **Run WEPP Hillslopes and Watershed** (or other run button);
    the UI calls the no-prep bootstrap routes.
11. WEPP runs against the checked-out input files.

## Caddy Configuration

Example Caddyfile snippet:

```caddyfile
wepp.cloud {
    # ... existing routes ...

    handle /git/* {
        forward_auth weppcloud:8000 {
            uri /api/bootstrap/verify-token
            copy_headers X-Auth-User
            header_up Authorization {http.request.header.Authorization}
            header_up X-Forwarded-Uri {uri}
            header_up X-Forwarded-Host {host}
            header_up X-Forwarded-Proto {scheme}
        }
        uri strip_prefix /git
        reverse_proxy fcgiwrap:9000 {
            transport fastcgi {
                env GIT_PROJECT_ROOT /wc1/runs
                env GIT_HTTP_EXPORT_ALL ""
                env SCRIPT_FILENAME /usr/lib/git-core/git-http-backend
            }
        }
    }
}
```

`forward_auth` should see the unstripped `/git/...` path (so the verify endpoint
can validate it). `uri strip_prefix /git` ensures `git-http-backend` receives
`/<prefix>/<runid>/.git/...` relative to `GIT_PROJECT_ROOT`.

For Docker-based deployments, run `fcgiwrap` as a sidecar container (exposed on
`fcgiwrap:9000`) or bind-mount the host socket into the Caddy container and
replace the upstream with `unix//run/fcgiwrap.socket`. The sidecar should use
the same Python environment as WEPPcloud (or otherwise have the WEPPcloud
dependencies available), because the `pre-receive` hook imports WEPPcloud
parsers for validation.

### Server Dependencies

```
git                    # Provides git-http-backend at /usr/lib/git-core/git-http-backend
fcgiwrap               # FastCGI wrapper for CGI programs (apt install fcgiwrap)
caddy                  # Reverse proxy with forward_auth and FastCGI transport
```

`fcgiwrap` can run as a systemd service (`systemctl enable --now fcgiwrap.socket`)
and listen on a Unix socket (typically `/run/fcgiwrap.socket`), or it can run in
a sidecar container and listen on TCP (for example `fcgiwrap:9000`). Caddy's
FastCGI transport should target whichever endpoint you deploy.

If the `fcgiwrap` process runs as a different user than the repo owner, Git may
refuse to serve the repo (`fatal: detected dubious ownership`). Set
`safe.directory` (for example `git config --system --add safe.directory '*'`) or
run `fcgiwrap` under the same user/group as the run directories.

The `forward_auth` block ensures every git operation hits the Flask token
verification endpoint before reaching `git-http-backend`.

`forward_auth` passes response headers upstream, so `X-Auth-User` from the
verify endpoint becomes `HTTP_X_AUTH_USER` for `git-http-backend` and hooks.

If you have an upstream proxy (HAProxy, nginx, etc.) in front of Caddy, ensure
it preserves the `Authorization` header. Basic auth credentials are required
for every git HTTP request.

## Deployment & Operations

### Deploy Checklist

- Set `EXTERNAL_HOST` to the public hostname (used as the JWT `aud` claim).
- Set `WEPP_AUTH_JWT_SECRET` (and `WEPP_AUTH_JWT_SECRETS` if rotating).
- Set `DTALE_INTERNAL_TOKEN` to a non-default secret value for production.
- Apply the Postgres migration that adds `runs.bootstrap_disabled`.
- Update the Caddy `/git/*` route (forward auth + header forwarding + FastCGI).
- Run `fcgiwrap` as a sidecar using the WEPPcloud image so the `pre-receive`
  hook can import the WEPP parsers.
- Keep `ENABLE_LOCAL_LOGIN=false` in production unless explicitly needed for a
  controlled break-glass workflow.
- Rebuild the controller bundle after UI changes:
  `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.

**Sidecar example (compose):**

```yaml
services:
  fcgiwrap:
    build:
      context: ..
      dockerfile: docker/Dockerfile.fcgiwrap
      args:
        BASE_IMAGE: ${WEPPCLOUD_IMAGE:-wepppy:latest}
    volumes:
      - /wc1:/wc1
      - /wc1/geodata:/geodata
    expose:
      - "9000"
```

### Integration Notes

- The UI provides a **Clone Command** (new clone) and **Set Remote Origin
  Command** (existing clone). The username should be a URL-safe ID (numeric
  user ID preferred), not raw email.
- Tokens expire after 6 months. Mint a new token and update `origin` when
  necessary.
- Use the no-prep endpoints for bootstrap runs:
  `/runs/{runid}/{config}/run-wepp-npprep`,
  `/runs/{runid}/{config}/run-swat-noprep`,
  `/runs/{runid}/{config}/run-wepp-watershed-no-prep`.
- Automated pipelines that are not using bootstrap should `git checkout main`
  before prep so they operate on canonical inputs.
- If `fcgiwrap` runs as a different user than the run directories, configure
  `git config --system --add safe.directory '*'` (or run as the same user).

### Troubleshooting

- **401 missing authorization** — upstream proxy stripped `Authorization`. Ensure
  it is preserved and Caddy forwards it to `/api/bootstrap/verify-token`.
- **401 invalid git path** — missing/stripped `X-Forwarded-Uri`. Ensure Caddy
  passes the original path and only strips `/git` after `forward_auth`.
- **401 invalid token / expired** — mint a new token; verify `EXTERNAL_HOST`
  matches the public hostname (JWT `aud`).
- **502/503 from Caddy** — `fcgiwrap` unavailable or misconfigured upstream.
- **500 with "dubious ownership"** — set `safe.directory` or align user/group.
- **pre-receive: python3 not found / import error** — run `fcgiwrap` with the
  WEPPcloud image. If your code is mounted outside the image path, set
  `WEPPPY_SOURCE_ROOT` in the service environment so the hook can extend
  `PYTHONPATH`.
- **pre-receive validation failed** — fix file format, remove `.run` changes,
  or reduce file size below 50 MB.

## File Validation Details

### `.cli` (Climate) Files

- Must start with expected header line(s).
- Numeric fields must parse as numbers.
- Date fields must be valid.

### `.sol` (Soil) Files

- Must match WEPP soil file structure (header + horizon blocks).
- Numeric parameters within plausible ranges.

### `.slp` (Slope) Files

- Must match WEPP slope profile format.
- Non-negative distances, valid gradients.

### `.man` (Management) Files

- Must match WEPP management file structure.
- Section counts consistent with declared values.

### `.run` Files

- **Read-only.** Any diff from the baseline `main` commit rejects the push.

### SWAT+ `TxtInOut/` Files

- Basic text format validation (non-binary, reasonable size).
- Specific format checks can be added incrementally as needed.

## Security Considerations

1. **JWT signing secret:** A single server-wide secret key used to sign all
   bootstrap JWTs. Stored in the application config (e.g., environment variable
   or config file), not in nodb. Rotating this secret invalidates all JWTs
   across all runs.

2. **Run eligibility (Postgres + nodb):** Only non-anonymous runs can enable
   bootstrap. The verify endpoint checks `runs.bootstrap_disabled = false`,
   `is_anonymous = false`, and nodb `_bootstrap_enabled = true` for every git
   operation.

3. **JWT scope + expiry:** Each JWT is bound to a specific
   `(external_host, runid, user_email)` triple and expires after 6 months. The
   verify endpoint confirms the `aud` matches the current host and the `runid`
   matches the URL path. No cross-run or cross-deployment access.

4. **Commit attribution:** The `pre-receive` hook requires an authenticated
   user header (`X-Auth-User` → `HTTP_X_AUTH_USER`) and logs commit SHAs with
   that JWT identity. The UI should display this log instead of git author
   fields.

5. **Push validation:** Server-side `pre-receive` hook is the security boundary.
   Even if a user crafts a malicious push, the hook rejects it before files land
   on disk.

6. **`.run` file lockdown:** These files execute via `subprocess`. No user
   modifications permitted. Hook enforces this by diffing against the protected
   baseline.

7. **Path traversal:** Hook rejects any paths containing `..`, symlinks, or
   paths outside the allowed directories.

8. **No shell in commit messages:** Commit messages are never interpolated into
   shell commands.

## Implementation Plan
- [x] Add `runs.bootstrap_disabled` (admin blacklist) and enforce
  `is_anonymous = false` gating in enable and verify flows.
- [x] Update nodb `Wepp` to set `_bootstrap_enabled` as a one-way user opt-in.
- [x] Implement JWT signing with 6-month expiry and `/api/bootstrap/verify-token`
  eligibility checks (nodb opt-in + Postgres not disabled).
- [x] Initialize git repo with `.gitignore` (including `wepp/runs/tc_out.txt`),
  set `receive.denyCurrentBranch=updateInstead`,
  `receive.denyNonFastForwards=true`, `http.receivepack=true`, and install
  `pre-receive`.
- [x] Implement `pre-receive` hook: path allowlist, `.run` protection, symlink
  rejection, binary rejection, 50 MB per-file cap, and parser validation via a
  process pool with fail-fast behavior. Record JWT-based commit attribution to
  `.git/bootstrap/push-log.ndjson`.
- [x] Add rq-engine `bootstrap_routes.py` with no-prep endpoints:
  `/runs/{runid}/{config}/run-wepp-npprep`,
  `/runs/{runid}/{config}/run-swat-noprep`,
  `/runs/{runid}/{config}/run-wepp-watershed-no-prep`.
- [x] Update standard pipeline entrypoints to `git checkout main` when
  Bootstrap is enabled and auto-commit rebuilt inputs; keep no-prep bootstrap
  routes on the current checkout.
- [x] Build the Bootstrap UI panel (enable, mint token, clone + remote commands,
  commit list, checkout, run buttons) and mark disable as Admin/Root-only. Display
  JWT-based `pusher` and optionally `git_author` for commit attribution.
- [x] Add tests for auth gating (Flask-Security integration), JWT expiry/invalid
  tokens for `/api/bootstrap/verify-token`, hook rejection cases, parser
  validation errors, push-log parsing, and bootstrap route coverage.
- [ ] Deprecate `wepppy-win-bootstrap` docs in favor of this workflow.

## Phase 2 Implementation Plan (RQ Engine + Agent API)

### Goals

- Move Bootstrap API operations to rq-engine so they are available in OpenAPI
  for agent and external API clients.
- Move expensive bootstrap initialization (`git init` + initial commit) off
  Flask request threads and into an RQ job.
- Add explicit concurrency control for git mutations at run scope.
- Keep existing WeppCloud routes as compatibility wrappers during migration.

### Status (February 8, 2026)

- [x] Added first-class rq-engine Bootstrap endpoints for enable/mint/read/checkout.
- [x] Moved Bootstrap enable initialization into async RQ job `bootstrap_enable_rq`.
- [x] Added Redis lock key `bootstrap:git-lock:<runid>` for enable/checkout mutations.
- [x] Added dedupe key `bootstrap:enable:job:<runid>` to suppress duplicate enable jobs.
- [x] Updated Flask `/runs/.../bootstrap/enable` route to enqueue the same async job.
- [x] Added route/unit tests for rq-engine Bootstrap endpoints, lock contention, and job enqueue logic.

### Redis Git Lock Design

Use Redis DB 0 (`RedisDB.LOCK`) as the authoritative lock backend.

- **Lock key:** `bootstrap:git-lock:<runid>`
- **Lock value (JSON):**
  - `token` (uuid)
  - `owner` (`hostname:pid`)
  - `operation` (`enable|checkout|auto_commit`)
  - `actor` (user/session/service id)
  - `acquired_at` (unix seconds)
  - `ttl_seconds`
- **Acquire:** `SET <key> <value> NX EX <ttl_seconds>`
- **Default TTL:** 900 seconds for short operations (`checkout`, `auto_commit`)
- **Enable lock TTL:** `max(BOOTSTRAP_GIT_LOCK_TTL_SECONDS, RQ_ENGINE_RQ_TIMEOUT + 300)`
- **Enable dedupe TTL:** `max(BOOTSTRAP_ENABLE_JOB_TTL_SECONDS, RQ_ENGINE_RQ_TIMEOUT + 300)`
- **Renewal:** not currently implemented; long enable operations use the computed
  timeout-aligned TTL values above.
- **Release:** compare-and-delete Lua script (delete only if token matches)
- **Contention behavior:** return HTTP 409 (`bootstrap lock busy`) for
  mutation endpoints when another mutation lock is active.
- **Crash safety:** lock expires via TTL if owner dies.

This lock is for git mutations only and is separate from `.nodb` file locks.

### New rq-engine Bootstrap Endpoints

Add first-class endpoints in `wepppy/microservices/rq_engine/bootstrap_routes.py`
under `/rq-engine/api`:

- `POST /runs/{runid}/{config}/bootstrap/enable`
- `POST /runs/{runid}/{config}/bootstrap/mint-token`
- `GET /runs/{runid}/{config}/bootstrap/commits`
- `GET /runs/{runid}/{config}/bootstrap/current-ref`
- `POST /runs/{runid}/{config}/bootstrap/checkout`

Authentication/authorization model:

- Require JWT auth (`require_jwt`) and run authorization (`authorize_run_access`).
- Enforce non-anonymous run requirements for `enable` and `mint-token`.
- Enforce explicit Bootstrap scopes:
  - `bootstrap:enable`
  - `bootstrap:token:mint`
  - `bootstrap:read`
  - `bootstrap:checkout`
- Bootstrap routes require the explicit `bootstrap:*` scopes above; `rq:enqueue`
  is not accepted as a substitute.

### Async Bootstrap Enable Flow

`POST /bootstrap/enable` should enqueue an RQ job instead of running in-request.

1. Validate JWT + run access + eligibility.
2. Acquire per-run bootstrap git lock (or fail with 409 if busy).
3. Enqueue `bootstrap_enable_rq(runid, actor)` with dedupe guard.
4. Return `202 Accepted` with `job_id` and polling URL.
5. Worker performs idempotent `wepp.init_bootstrap()` and records status.
6. Worker releases git lock.

Recommended dedupe key:

- `bootstrap:enable:job:<runid>` → active job id (short TTL) to prevent
  duplicate initialize jobs.

### Compatibility and Migration

Phase 2 keeps existing Flask routes in place as wrappers while clients migrate.

- WeppCloud `bootstrap.py` wrapper handlers now call shared operations in
  `wepppy/weppcloud/bootstrap/api_shared.py`, which are also used by rq-engine.
  This keeps status/payload behavior deterministic during migration.
- UI can switch incrementally to `/rq-engine/api/...` endpoints.
- Flask exceptions that remain intentionally Flask-owned:
  - `/api/bootstrap/verify-token` (Caddy `forward_auth` contract).
  - `/runs/<runid>/<config>/bootstrap/disable` (Admin/Root UI action).
- Wrapper deprecation plan:
  1. Move UI callers to rq-engine endpoints.
  2. Keep wrappers as pass-through aliases for one release cycle.
  3. Remove duplicate Flask wrappers after telemetry confirms no active usage.

### Data and Response Contracts

- Keep success/error payloads aligned with `docs/schemas/rq-response-contract.md`.
- Ensure rq-engine OpenAPI documents Bootstrap request/response models.
- Include lock contention (`409`), auth errors (`401/403`), and run eligibility
  errors (`400`) explicitly in endpoint docs.

### Testing Plan

Add/expand tests in `tests/microservices/` and `tests/weppcloud/routes/`:

- rq-engine auth + scope coverage for all Bootstrap endpoints, including missing
  scope, expired token, audience mismatch, and revoked `jti`.
- Enable route returns `202` and enqueues exactly one job per run while dedupe key exists.
- Redis lock behavior:
  - lock acquisition success
  - lock contention returns `409`
  - token-checked release
  - TTL expiry recovery
- Flask bootstrap route status-code regressions (`400/404/409/500`) and
  canonical run-path resolution (`get_wd(..., prefer_active=False)`).
- Functional checks for mint/commits/current-ref/checkout in rq-engine.
- Pre-receive policy edge coverage: symlink/submodule rejection, rename/copy
  rejection, and delete rejection inside allowed input roots.
- Backward-compatibility wrapper tests for existing Flask Bootstrap routes.

### Phase 2 Closure Snapshot (February 8, 2026)

Implemented remediations from the production-readiness review:

- Canonical run-path resolution for bootstrap mutations via
  `get_wd(..., prefer_active=False)` in Flask + rq-engine paths.
- Explicit status-code handling for Flask bootstrap endpoints (`400/404/409/500`)
  and generic internal error responses.
- Admin/Root authorization parity in both web and rq-engine helpers.
- Sanitized unexpected rq-engine bootstrap exceptions (no traceback payload leaks).
- `bootstrap_disabled` enforcement for mutation/token-mint operations while
  keeping read/checkout available.
- Enable lock and dedupe TTLs aligned with RQ timeout
  (`max(configured_ttl, RQ timeout + 300)`).
- Git lock coverage for WEPP/SWAT auto-commit mutation paths.
- Production compose defaults hardened for JWT and D-Tale secrets.

Verification snapshot:

- Targeted Bootstrap suite run on 2026-02-08:
  - `tests/weppcloud/routes/test_bootstrap_bp.py`
  - `tests/weppcloud/routes/test_bootstrap_auth_integration.py`
  - `tests/microservices/test_rq_engine_bootstrap_routes.py`
  - `tests/rq/test_bootstrap_enable_rq.py`
  - `tests/weppcloud/bootstrap/test_enable_jobs.py`
  - `tests/rq/test_bootstrap_autocommit_rq.py`
  - `tests/weppcloud/bootstrap/test_pre_receive.py`
- Result: `60 passed`

Known measurement limitation:

- `/wc1/runs/fa/fast-paced-blastoff` exists but currently lacks `.git` and
  `wepp/runs` content, so destructive bootstrap-init timing tests were not run
  there.
