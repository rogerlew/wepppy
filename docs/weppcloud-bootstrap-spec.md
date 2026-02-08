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
5. Installs the `pre-receive` validation hook.

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

**CGI host: `fcgiwrap`.** A lightweight FastCGI wrapper (`apt install fcgiwrap`)
that runs as a systemd service and listens on a Unix socket. Caddy speaks
FastCGI to it, and `fcgiwrap` invokes `git-http-backend` per-request.

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
   and the runid. Tokens expire after 30 days (`exp` claim).
3. Clone URL is displayed with the JWT as the Basic auth password.

```
git clone https://<user_id>:<jwt>@wepp.cloud/git/<prefix>/<runid>
```

The `<user_id>` is a URL-safe identifier (username or numeric ID, not raw email)
to avoid `@` encoding issues in URLs. The server resolves it to the full user
record.

**Verification flow** (`/api/bootstrap/verify-token`):

1. Decode and verify JWT signature against server secret.
2. Check `aud` claim matches the current `external_host`.
3. Extract `runid` claim from the JWT.
4. Check URL path is `/git/<prefix>/<runid>` (derive `prefix` from `runid`).
5. Check the run is eligible: nodb `_bootstrap_enabled = true`, Postgres run
   record has `bootstrap_disabled = false`, and `is_anonymous = false`.
6. Check `sub` is a valid user with access to the run.
7. Return 200 with `X-Auth-User` header (user email) for server-side audit
   logging only. Commit attribution is based on the JWT audit trail (git
   author fields are not enforced).

**Revocation — admin blacklist flag:**

- **No per-user revocation.** Revocation is per-run only.
- When bootstrap is disabled for a run, `bootstrap_disabled` is set to true in
  Postgres. All JWTs for that run become invalid immediately.
- Re-enabling bootstrap for the same run sets `bootstrap_disabled = false`.
  Users should mint a new JWT. Prior tokens still expire within 30 days. The
  nodb user opt-in remains set.
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
- Do not enforce git author/committer emails; rely on JWT audit logs instead.
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
    Returns the clone URL with embedded JWT.
    """

def get_bootstrap_commits(self) -> list[dict]:
    """
    Return list of commits on main branch.
    Each entry: {sha, short_sha, message, author, date}
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
    Admin-only. Sets runs.bootstrap_disabled = True (invalidates all JWTs).
    Leaves working files and git history in place.
    """
```

### Pipeline Auto-Commit

When Bootstrap is enabled and the normal WeppCloud pipeline runs (e.g., user
changes landuse, rebuilds soils, regenerates climate), the pipeline should
ensure `main` is checked out at the beginning. This applies to the standard
run endpoints (non-bootstrap). Bootstrap no-prep routes do not switch branches
and do not auto-commit.

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
│  Clone URL: https://<user_id>:<jwt>@wepp.cloud/     │
│             git/<prefix>/<runid>             [Copy] │
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
│  [Disable Bootstrap (Admin)]                        │
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
3. User clicks **Mint Token** — server signs a JWT, UI shows clone URL.
4. User clones locally:
   ```
   git clone https://<user_id>:<jwt>@wepp.cloud/git/<prefix>/<runid>
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

    handle_path /git/* {
        forward_auth localhost:5000 {
            uri /api/bootstrap/verify-token
            copy_headers {
                Authorization
            }
        }
        reverse_proxy unix//run/fcgiwrap.socket {
            transport fastcgi {
                env GIT_PROJECT_ROOT /wc1/runs
                env GIT_HTTP_EXPORT_ALL ""
                env SCRIPT_FILENAME /usr/lib/git-core/git-http-backend
            }
        }
    }
}
```

### Server Dependencies

```
git                    # Provides git-http-backend at /usr/lib/git-core/git-http-backend
fcgiwrap               # FastCGI wrapper for CGI programs (apt install fcgiwrap)
caddy                  # Reverse proxy with forward_auth and FastCGI transport
```

`fcgiwrap` runs as a systemd service (`systemctl enable --now fcgiwrap.socket`)
and listens on a Unix socket (typically `/run/fcgiwrap.socket`). Caddy's FastCGI
transport connects to this socket to invoke `git-http-backend` per-request.

The `forward_auth` block ensures every git operation hits the Flask token
verification endpoint before reaching `git-http-backend`.

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
   `(external_host, runid, user_email)` triple and expires after 30 days. The
   verify endpoint confirms the `aud` matches the current host and the `runid`
   matches the URL path. No cross-run or cross-deployment access.

4. **Push validation:** Server-side `pre-receive` hook is the security boundary.
   Even if a user crafts a malicious push, the hook rejects it before files land
   on disk.

5. **`.run` file lockdown:** These files execute via `subprocess`. No user
   modifications permitted. Hook enforces this by diffing against the protected
   baseline.

6. **Path traversal:** Hook rejects any paths containing `..`, symlinks, or
   paths outside the allowed directories.

7. **No shell in commit messages:** Commit messages are never interpolated into
   shell commands.

## Implementation Plan

- [ ] Add `runs.bootstrap_disabled` (admin blacklist) and enforce
  `is_anonymous = false` gating in enable and verify flows.
- [ ] Update nodb `Wepp` to set `_bootstrap_enabled` as a one-way user opt-in.
- [ ] Implement JWT signing with 30-day expiry and `/api/bootstrap/verify-token`
  eligibility checks (nodb opt-in + Postgres not disabled).
- [ ] Initialize git repo with `.gitignore` (including `wepp/runs/tc_out.txt`),
  set `receive.denyCurrentBranch=updateInstead`, and install `pre-receive`.
- [ ] Implement `pre-receive` hook: path allowlist, `.run` protection, symlink
  rejection, binary rejection, 50 MB per-file cap, and parser validation via a
  process pool with fail-fast behavior.
- [ ] Add rq-engine `bootstrap_routes.py` with no-prep endpoints:
  `/runs/{runid}/{config}/run-wepp-npprep`,
  `/runs/{runid}/{config}/run-swat-noprep`,
  `/runs/{runid}/{config}/run-wepp-watershed-no-prep`.
- [ ] Update standard pipeline entrypoints to `git checkout main` when
  Bootstrap is enabled; keep no-prep bootstrap routes on the current checkout.
- [ ] Build the Bootstrap UI panel (enable, mint token, clone URL, commit list,
  checkout, run buttons) and mark disable as admin-only.
- [ ] Add tests for auth gating, JWT expiry, hook rejection cases, and parser
  validation errors.
- [ ] Deprecate `wepppy-win-bootstrap` docs in favor of this workflow.
