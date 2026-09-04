# WEPPcloud Session Contract
> Authoritative contract for WEPPcloud browser sessions, session cookies, heartbeat refresh, and stale-tab UX.
> **See also:** `docs/schemas/weppcloud-csrf-contract.md`, `docs/schemas/weppcloud-browse-auth-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/schemas/rq-response-contract.md`, `docs/dev-notes/weppcloud-session-lifecycle.spec.md`

## Normative Status
- This document is normative and authoritative for WEPPcloud session behavior.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.
- If code and this contract diverge, the change is incomplete until either:
  - code is corrected to match this contract, or
  - this contract is updated in the same change set.

## Scope
- Covers browser-facing WEPPcloud session lifecycle and cookies.
- Covers Flask-side session refresh APIs and client heartbeat behavior.
- Covers rq-engine session-token minting when sourced from Flask session cookies.
- Defers browse-route auth and grouped-route policy to `docs/schemas/weppcloud-browse-auth-contract.md`.
- Defers route-level CSRF policy and classification to `docs/schemas/weppcloud-csrf-contract.md`.
- Does not redefine JWT claim rules; those remain in `docs/dev-notes/auth-token.spec.md`.
- Does not redefine canonical error payloads; those remain in `docs/schemas/rq-response-contract.md`.

## Product and UX Priority

- WEPPcloud authentication architecture MUST minimize repeated authentication
  and unnecessary user interaction during ordinary use.
- Security controls MUST be proportionate to the documented threat model and
  SHOULD NOT add user-visible friction unless they address a demonstrated
  material risk.
- Direct user feedback is authoritative product evidence when selecting
  authentication defaults. Security review constrains how an accepted
  experience is implemented; it does not silently replace the accepted product
  objective with a lower-friction-independent objective.
- Ordinary users SHOULD remain signed in across browser restarts and active use
  without reentering credentials or completing another CAPTCHA.
- Shared-device users MUST retain a clear opt-out at login and a reliable
  explicit logout.

## Session Artifacts
| Artifact | Authority | Storage | Primary Purpose |
| --- | --- | --- | --- |
| Flask login session (`__Host-weppcloud_session` on secure production; migration-aware) | Flask + Flask-Session | Redis DB 11 (`session:<sid>`), persisted by default in stacks that run Redis | Authenticated browse state and server session data |
| Flask-Security remember-me token (`remember_token`) | Flask-Security | Browser cookie | Rehydrate login after Flask session expiry |
| rq-engine browse JWT (`wepp_browse_jwt` by default) | rq-engine session endpoint | Browser HttpOnly cookie | Run-scoped JWT for browse/rq-engine interactions |
| CAP verification marker (`cap_verified_at`) | WEPPcloud CAP guard | Flask session payload | Anonymous CAPTCHA gate cooldown window |
| Session run marker (`auth:session:run:<runid>:<session_id>`) | rq-engine session endpoint | Redis DB 11 | Server-side marker tying session ID to run scope |

## Flask Session Contract
- `SESSION_TYPE` MUST be `redis`.
- `SESSION_USE_SIGNER` MUST be enabled.
- `SESSION_KEY_PREFIX` MUST default to `session:`.
- `PERMANENT_SESSION_LIFETIME` MUST be `12 hours`.
- `SESSION_PERMANENT` MUST remain `False` unless this contract is revised.
- `SESSION_COOKIE_SECURE` MUST be `True`.
- The secure-host cookie name MUST default to `__Host-weppcloud_session`, with
  Path `/`, no Domain, `HttpOnly`, and signing enabled. Startup MUST reject a
  secure-host profile that violates those invariants. Explicit local HTTP
  profiles MAY use `weppcloud_session`.
- `SESSION_COOKIE_SAMESITE` MUST default to `Lax`; override via `SESSION_COOKIE_SAMESITE` is allowed.
- OAuth login MUST call `login_user(..., remember=True)` so remember-me restoration remains available.
- Password-login pages MUST render "Remember me on this device" selected by
  default while preserving an explicit user opt-out.
- Remembered-login cookies MUST default to a rolling 90-day browser inactivity
  lifetime. An authenticated request carrying a valid remember cookie MUST
  refresh its browser expiration. An ordinary authenticated session without a
  remember cookie MUST NOT create one merely because a request occurred.
- A password-login submission that opts out MUST neither issue nor retain a
  remember cookie. If the browser already carries one, the response MUST expire
  it using the configured name, path, and domain.
- The duration MAY be changed by an explicit operator override. Configuration
  documentation MUST identify the effective value and its security/UX tradeoff.
- Explicit logout MUST clear both session and remember cookies using their
  configured names, paths, domains, and security attributes.
- During the legacy migration window, Flask and rq-engine MUST use identical,
  bounded raw-Cookie selection semantics. Presence of any primary-name cookie
  blocks fallback to legacy `session`. Within one name, invalid signatures MAY
  be skipped; the first correctly signed SID is the only candidate that may be
  authorized. Later signed, live payloads are inspected only for conflict
  detection. Adoption is allowed only when all live candidates represent the
  same authenticated principal. An authenticated/anonymous conflict, different
  principals, multiple live anonymous sessions, corrupt payload, Redis error,
  or missing Redis record for the authoritative SID MUST fail closed and MUST
  NOT authorize a later candidate.
- Reader precedence and writer name MUST be independently configurable during
  staged rollout. Reader-first deployment MUST prefer
  `__Host-weppcloud_session` while continuing to write `session`; activation
  changes only the writer to `__Host-weppcloud_session`. Flask and rq-engine
  MUST retain identical primary/legacy reader configuration in both phases.
- A migrated session MUST retain its SID and complete Redis payload. A signed
  SID whose Redis record is absent MUST be discarded and MUST NOT seed a new
  session; any recovery receives a fresh unpredictable SID.
- When an anonymous session becomes authenticated, the server MUST atomically
  rotate its SID while preserving the session payload. If logout/reset has
  already revoked the old SID, the promotion MUST fail closed, persist no new
  session, and expire both the owned session and remember cookies.
- Explicit logout and browser-state reset during migration MUST invalidate all
  bounded, correctly signed primary and legacy SIDs presented by that request.
  Revocation fencing MUST prevent late concurrent responses from recreating a
  revoked SID. SID tombstones MUST outlive every derivative session credential
  (currently four days), and every `token_class=session` authorization check
  MUST reject a tombstoned SID. Generic legacy browser cookies MUST NOT be
  broadly deleted.
- Cookie parsing and migration telemetry MUST be bounded and value-free.
  Rejection MUST occur rather than truncation. Logs and metrics MUST NOT contain
  raw cookies, SIDs, principals, CSRF values, or remember tokens.
- Server-side Redis sessions MUST retain the rolling 12-hour inactivity window.
  Remembered login restores identity after that session expires or the browser
  session cookie is discarded.

### Remember-Token Threat Boundary

- The Flask-Login remember token is a signed bearer credential. In the pinned
  implementation it contains no server-validated issuance timestamp.
- The 90-day duration is therefore a browser-enforced inactivity policy, not a
  cryptographic or server-side maximum for a copied raw token.
- This residual replay risk is accepted for the ordinary WEPPcloud threat model
  because remembered login materially reduces user friction and no production
  evidence currently demonstrates a need for per-device server-side token
  state.
- Secure, HttpOnly, SameSite=Lax, TLS, secret redaction, and explicit logout
  remain mandatory exposure controls.
- Ordinary logout clears the requesting browser but does not revoke a copied
  token. Suspected token theft MUST be contained by rotating the affected
  user's `fs_uniquifier`; responders MUST understand that this also invalidates
  that user's other active Flask-Security sessions.
- A future server-side issuance, device, or revocation mechanism requires new
  user evidence or a demonstrated material threat, its own compatibility and
  UX analysis, an ADR, and an amended checkpoint. It MUST NOT be introduced as
  an undocumented review preference.

Source-of-truth implementation:
- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/session_migration.py`
- `wepppy/weppcloud/routes/_security/oauth.py`

## Authentication Logging Contract

- Authentication logs MUST NOT include passwords, CSRF tokens, CAPTCHA tokens,
  remember-cookie values, session-cookie values, OAuth tokens, or bearer tokens.
- Authentication diagnostics MAY record whether Flask-Login scheduled a
  remember-cookie set or clear action, but MUST NOT record the cookie value.
- Production security logs MUST use a writable, persistent path. The canonical
  container path is `/wc1/logs/weppcloud/security.log`.
- Application workers MUST append without performing in-process rotation;
  rotation and retention MUST be coordinated by the host. The directory and
  file MUST be restricted to the WEPPcloud runtime account (`0700` directory,
  `0600` file), and the directory MUST NOT be exposed by run-file routes.
- Logging failures MUST remain visible in the main service log and MUST NOT
  silently disable authentication event observability.

Source-of-truth implementation:
- `wepppy/weppcloud/routes/_security/logging.py`

## Session Durability Expectations (Redis)

- Deployments that include a Redis service MUST enable Redis persistence by default so Redis-backed sessions survive routine redeploys and host restarts (subject to normal TTL expiry).
- Deploy automation MAY intentionally clear RQ state, but MUST scope any flush to the RQ DB only (DB 9). Session storage (DB 11) MUST NOT be flushed as part of normal deploys.
- Changing the session DB index (default DB 11) invalidates all active sessions:
  - Existing session cookies will continue presenting the old session id, but the server will not find that id in the new DB index.
  - Result: users will be treated as logged out and must re-authenticate (remember-me may still rehydrate later depending on cookie state).
  - Any session DB index change MUST update this contract and MUST be coordinated across all session consumers (WEPPcloud + rq-engine marker paths).
- Migration deployment on `wepp.cloud` MUST be reader-first: all web and
  rq-engine consumers understand primary and legacy names while writers still
  emit `session`; only then may all production web writers activate the primary
  name without overlap with legacy-only workers. Rollback after activation MUST
  use a pinned migration-aware image and MUST NOT dual-write `session`.
- Bearhive origins are development/test rehearsal environments and are not
  production cookie-continuity targets.

## rq-engine Session JWT Cookie Contract
- Endpoint `POST /rq-engine/api/runs/{runid}/{config}/session-token` MUST:
  - issue `token_class=session` JWT with run-scoped claims,
  - return a JSON payload containing `token`, `token_class`, `runid`, `config`, `session_id`, `expires_at`, `scopes`, and `audience`,
  - set an HttpOnly cookie containing the same token.
- Browse JWT cookie defaults:
  - name: `wepp_browse_jwt` (override `WEPP_BROWSE_JWT_COOKIE_NAME`),
  - path: `{SITE_PREFIX}/runs/{runid}/{config}/`,
  - max age: `345600` seconds (4 days),
  - `HttpOnly=true`,
  - `SameSite=lax` by default (override `WEPP_AUTH_SESSION_COOKIE_SAMESITE`),
  - `Secure` derived from request/proxy scheme unless `WEPP_AUTH_SESSION_COOKIE_SECURE` overrides.

Source-of-truth implementation:
- `wepppy/microservices/rq_engine/session_routes.py`

## Session Refresh Contract
- Authenticated pages rendered from `templates/base_pure.htm` MUST load `static/js/session_heartbeat.js`.
- Heartbeat client behavior MUST be:
  - immediate POST on init,
  - periodic POST every 5 minutes,
  - extra POST when tab visibility changes to `visible`.
- Heartbeat request:
  - endpoint: `POST /weppcloud/api/auth/session-heartbeat`,
  - credentials: same-origin cookie auth,
  - no anonymous mode.
- Heartbeat endpoint MUST:
  - require authenticated user (`401` canonical error when anonymous),
  - enforce same-origin POST (`403` canonical error when blocked),
  - mark the Flask session modified (`session.modified = True`) and persist heartbeat timestamp.

Source-of-truth implementation:
- `wepppy/weppcloud/templates/base_pure.htm`
- `wepppy/weppcloud/static/js/session_heartbeat.js`
- `wepppy/weppcloud/routes/weppcloud_site.py`

## Stale-Tab UX Contract
- On heartbeat `401` or `403`, client MUST:
  - stop further heartbeat scheduling,
  - emit `wepp:session-heartbeat-expired`,
  - display a persistent session-expired banner with `Sign in` and `Reload` actions.
- A page MUST NOT continue presenting stale authenticated affordances without a re-auth prompt once server auth failure is detected.
- Page-specific workflows that submit to rq-engine (fork, archive, reports, readme actions, other ancillary run pages) SHOULD treat explicit auth failures (`401`, `403`, `unauthorized`, `forbidden`) as stale-session signals and prompt reload/sign-in.

## Same-Origin and Security Contract
- The normative decision order and origin normalization for
  `POST /weppcloud/api/auth/session-heartbeat`,
  `POST /weppcloud/api/auth/rq-engine-token`, and the cookie-auth path of
  `POST /rq-engine/api/runs/{runid}/{config}/session-token` are defined by
  `docs/schemas/weppcloud-csrf-contract.md` section "Browser Same-Origin Guard
  Contract."
- Requests missing Fetch Metadata, `Origin`, and `Referer` MUST reject.
- `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` is retained as an accepted legacy
  environment variable for deployment compatibility but is inert for
  same-origin authorization after REM-04. Raw forwarded headers MUST NOT add an
  allowed origin even when it is `true`.
- Deployments that need an external rq-engine origin MUST configure
  `OAUTH_REDIRECT_HOST`/`OAUTH_REDIRECT_SCHEME` or
  `EXTERNAL_HOST`/`EXTERNAL_SCHEME`. Operators previously relying on the legacy
  forwarded-origin switch MUST set those values before deploying REM-04.
- Anonymous or stale session-token claims MUST NOT bypass CAPTCHA/public-run gates in anonymous flows.
- Private-run session-token issuance via the cookie-auth path MUST enforce run
  authorization from server-side owner/role state. The authenticated user id
  MAY be recovered from the signed server-side session, but Admin/Root roles
  MUST be loaded from the current user record rather than trusted from optional
  session-cached role fields. This keeps the bridge consistent with WEPPcloud
  page authorization and prevents stale role grants or denials.

## Conformance Tests (Required)
The following suites MUST be updated when session contract behavior changes:
- password-login form rendering and submitted opt-out tests;
- successful login, remembered-request refresh, and logout cookie-boundary
  tests;
- rq-engine same-origin tests proving the legacy forwarded-origin environment
  switch cannot authorize raw `X-Forwarded-Proto` or `X-Forwarded-Host`;
- authentication diagnostic redaction and persistence tests;
- `tests/weppcloud/test_configuration.py`
- `tests/weppcloud/routes/test_rq_engine_token_api.py`
- `tests/microservices/test_rq_engine_session_routes.py`
- `tests/microservices/test_rq_engine_fork_archive_routes.py`
- duplicate raw-cookie, migration, logout/reset fencing, first-request POST,
  and corrupt/missing Redis session tests;
- `wepppy/weppcloud/controllers_js/__tests__/session_heartbeat.test.js`
- `wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js`

When a listed suite is unaffected, the work package MUST record a reviewed
`N/A` rationale and run the suite as a regression gate rather than silently
omitting it.

## Change Management
- Any change to session TTLs, cookie defaults, heartbeat interval, stale-tab UX, or endpoint auth rules MUST update this contract and linked implementation docs in the same PR.
