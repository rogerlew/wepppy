# Mini Work Package: Browse JWT Auth and Session Cookie Bridge
Status: Completed
Last Updated: 2026-02-09
Primary Areas: `wepppy/microservices/rq_engine/session_routes.py`, `wepppy/microservices/browse/browse.py`, `wepppy/microservices/browse/dtale.py`, `wepppy/microservices/browse/files_api.py`, `wepppy/microservices/browse/_download.py`, `wepppy/microservices/_gdalinfo.py`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`, `wepppy/weppcloud/routes/_security/logging.py`, `docs/dev-notes/auth-token.spec.md`

## Objective
Add JWT-based authorization to the Starlette browse service family and align token issuance so browser navigation can recover from missing/expired tokens through a lightweight `runs0_nocfg` bridge and HttpOnly cookies.

## Cursory Observations
- `rq-engine` already mints run-scoped session tokens, but browse currently has no JWT auth gate.
- Browse serves multiple file-access surfaces (`browse`, `files`, `download`, `gdalinfo`, `aria2c.spec`, `dtale`) from one app.
- Existing frontend helpers still support bearer tokens and should remain compatible.
- Current session-token cookie flow checks session existence but does not fully enforce private-run ownership on cookie auth path.

## Decisions Locked (2026-02-09)
1. Unauthorized browse navigation will redirect through the config resolver route:
   - `/weppcloud/runs/{runid}/?next={encoded_target}`
   - When `next` is present, `runs0_nocfg` mints/refreshes the run-scoped cookie and redirects directly to `next` without loading `/runs/{runid}/{config}/`.
   - `runs0_nocfg` validates `next` as a safe same-origin relative path and constrains it to the current run scope.
2. Auth is required across browse-adjacent endpoints, not only `/browse`.
3. `include_hidden=1` is out of scope and should not be added.
4. Session token `roles` claim will be a list of role names (`list[str]`), not a bitmask.
5. Browse auth must accept cookie JWT first and fall back to bearer header for services/automation.

## Scope
- Extend `POST /rq-engine/api/runs/{runid}/{config}/session-token` to include authenticated identity claims:
  - `user_id` (int) when Flask session is authenticated.
  - `roles` (`list[str]`) from Flask session role cache.
- Add Flask-Security signal handling to cache role data in session at login time (database-free use by `rq-engine`).
- Set the session JWT as an HttpOnly cookie scoped to `/weppcloud/runs/{runid}/{config}/` while preserving the current JSON response contract.
- Enforce JWT auth and policy checks across browse service endpoints (see matrix below).
- Add runid claim checks and token-class checks in browse authorization.
- Add 401 redirect behavior for browser navigation paths with `next` support.
- Keep bearer compatibility for non-browser/service callers.

## Non-goals
- Reintroducing hidden-file query behavior.
- Refactoring browse rendering templates or directory listing UX.
- Changing queue wiring or RQ dependency edges.

## Endpoint Auth Matrix
| Route Family | Token Classes | Anonymous Public Run | Anonymous Private Run |
| --- | --- | --- | --- |
| `/runs/{runid}/{config}/browse/**` | `session`, `user`, `service` | Allow basic access | Redirect to `/weppcloud/runs/{runid}/?next=...` |
| `/runs/{runid}/{config}/dtale/**` | `session`, `user`, `service` | Deny (auth required) | Redirect to `/weppcloud/runs/{runid}/?next=...` |
| `/runs/{runid}/{config}/download/**` | `session`, `user`, `service` | Allow | Redirect to `/weppcloud/runs/{runid}/?next=...` for browser GET; `401` for non-HTML clients |
| `/runs/{runid}/{config}/gdalinfo/**` | `session`, `user`, `service` | Allow | `401` (JSON/plain error), no forced HTML redirect |
| `/runs/{runid}/{config}/aria2c.spec` | `session`, `user`, `service` | Allow | `401` (plain error), no forced HTML redirect |
| `/runs/{runid}/{config}/files/**` | `user`, `service` | Deny (auth required) | `401` (canonical JSON error) |
| `/culverts/{uuid}/browse|download|gdalinfo|dtale/**` | `user`, `service` | N/A | `401/403` per token validity and claim scope |
| `/batch/{batch_name}/browse|download|gdalinfo|dtale/**` | `user`, `service` | N/A | `401/403` per token validity and claim scope |

Notes:
- Culvert/batch endpoints are service-facing; session tokens are not required there.
- Service tokens must carry explicit run scope claims that match route identifiers.

## Authorization Rules
### Token extraction order
1. Browse cookie JWT (new HttpOnly session token cookie).
2. `Authorization: Bearer <token>` header fallback.

### Claim checks
- Validate signature/audience with shared JWT config (`aud=rq-engine` unless overridden).
- Enforce run scope:
  - `session` token: `runid` claim must match route run id.
  - `service` token: `runid` or `runs` claims must include route identifier.
  - `user` token: owner/public-run authorization checks (same policy as Flask `authorize()` semantics).

### Path policy checks
- `_logs/`, `exceptions.log`, `exception_factory.log` are Root-only.
- `dtale` requires authenticated token even for public runs.
- `/files/**` does not allow anonymous access.

## Session Claim Source (Database-Free)
- Add a Flask-Security `user_authenticated` signal handler that writes session keys:
  - `_user_id` as int.
  - `_roles` as `list[str]`.
- Optional `user_unauthenticated` cleanup should clear these keys.
- `rq-engine/session_routes.py` reads those session values from Redis-backed Flask session payload to enrich issued session JWTs.

## Redirect and Next Flow
1. Unauthorized browser request to private browse path returns `302` to:
   - `/weppcloud/runs/{runid}/?next={urlencoded_original_path_and_query}`
2. `runs0_nocfg` resolves canonical config and validates `next`:
   - reject absolute/external URLs,
   - reject cross-run targets,
   - normalize to `/weppcloud/runs/{runid}/{config}/...`.
3. `runs0_nocfg` executes session-token mint logic (shared helper) and sets/refreshes the HttpOnly browse cookie.
4. `runs0_nocfg` redirects directly to validated `next` target.
5. When `next` is absent, `runs0_nocfg` keeps its existing behavior and redirects to `/weppcloud/runs/{runid}/{config}/`.

## Implementation Plan
1. Add session role cache signal hooks in Flask security logging module (or a dedicated auth-session module), keeping scope minimal.
2. Extend `session-token` issuance:
   - Enforce private-run auth for cookie-based issuance.
   - Add `user_id` and `roles` claims when session indicates authenticated user.
   - Set HttpOnly cookie with path `/weppcloud/runs/{runid}/{config}/`.
3. Add browse auth utility layer:
   - Token extraction (cookie then bearer).
   - Shared claim validation and run-scope checks.
   - Helper for browser-redirect vs API-401 behavior.
4. Wire auth enforcement into:
   - `browse.py` handlers,
   - `dtale.py`,
   - `_download.py`,
   - `_gdalinfo.py`,
   - `files_api.py`.
5. Add Root-only path restrictions for log artifacts in browse path checks.
6. Add `next` bridge support in `runs0_nocfg`:
   - safe `next` validation/normalization,
   - direct cookie mint + redirect handoff to browse target,
   - no required intermediate render of `/runs/{runid}/{config}/` for this flow.
7. Update auth contract docs to reflect session token claim additions and cookie behavior.

## Test Plan
- `tests/microservices/test_rq_engine_session_routes.py`
  - session-token JSON unchanged fields still present.
  - cookie is set with expected attributes/path.
  - `user_id` and `roles` claims present for authenticated session.
  - private-run cookie issuance denied without ownership/auth.
- New/expanded browse auth tests (`tests/microservices/test_browse_routes.py`, `tests/microservices/test_browse_security.py`)
  - anonymous public browse allowed.
  - anonymous private browse redirects with correct `next`.
  - `/files/**` rejects anonymous requests.
  - service token accepted on culvert endpoints.
  - runid claim mismatch returns `403`.
  - `_logs/`, `exceptions.log`, `exception_factory.log` require Root.
  - dtale requires authenticated token.
- Route behavior tests for `runs0_nocfg` mint-and-handoff flow:
  - valid `next` mints cookie and redirects directly to browse target.
  - invalid `next` values are rejected or normalized safely.
  - no-`next` path preserves existing config redirect behavior.

## Risks and Mitigations
- Risk: breaking existing JS bearer flows.
  - Mitigation: keep bearer fallback and existing JSON token response.
- Risk: over-redirecting API clients.
  - Mitigation: only redirect when request is browser navigation (`Accept: text/html`); return 401/JSON for API routes.
- Risk: stale session role cache.
  - Mitigation: populate on login and clear on logout; roles are advisory for browse policy, not sole source for ownership checks.

## Acceptance Criteria
- All targeted browse-family endpoints enforce JWT policy per matrix.
- Anonymous access to private run browse paths redirects through `/runs/{runid}/?next=...`.
- Session token endpoint emits role/user claims for authenticated users and sets HttpOnly path-scoped cookie.
- `runs0_nocfg` supports direct mint-and-handoff to validated `next` browse targets without intermediate run-page load.
- `include_hidden` logic is not reintroduced.
- Tests cover anonymous, session, user, and service token paths, including culvert service access.

## Deferred Follow-up (2026-02-09)
- Deferred by decision: user-token identifier scoping for group routes (`/culverts/{uuid}/...`, `/batch/{batch_name}/...`).
- Current behavior: route-identifier claim checks are enforced for `service` and `session` tokens; `user` tokens are authorized by user identity and run/group ownership policy.
- Planned hardening: introduce identifier-scoped group tokens, starting with `batch_uuid`-specific tokens, and require claim-to-route identifier matching for group endpoints.
- Release note: this work package intentionally ships without that tightening and tracks it as follow-up security hardening.
