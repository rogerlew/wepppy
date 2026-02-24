# WEPPcloud Session Contract
> Authoritative contract for WEPPcloud browser sessions, session cookies, heartbeat refresh, and stale-tab UX.
> **See also:** `docs/schemas/weppcloud-csrf-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/schemas/rq-response-contract.md`, `docs/dev-notes/weppcloud-session-lifecycle.spec.md`

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
- Defers route-level CSRF policy and classification to `docs/schemas/weppcloud-csrf-contract.md`.
- Does not redefine JWT claim rules; those remain in `docs/dev-notes/auth-token.spec.md`.
- Does not redefine canonical error payloads; those remain in `docs/schemas/rq-response-contract.md`.

## Session Artifacts
| Artifact | Authority | Storage | Primary Purpose |
| --- | --- | --- | --- |
| Flask login session (`session` cookie by default) | Flask + Flask-Session | Redis DB 11 (`session:<sid>`), persisted by default in stacks that run Redis | Authenticated browse state and server session data |
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
- `SESSION_COOKIE_SAMESITE` MUST default to `Lax`; override via `SESSION_COOKIE_SAMESITE` is allowed.
- OAuth login MUST call `login_user(..., remember=True)` so remember-me restoration remains available.

Source-of-truth implementation:
- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/routes/_security/oauth.py`

## Session Durability Expectations (Redis)

- Deployments that include a Redis service MUST enable Redis persistence by default so Redis-backed sessions survive routine redeploys and host restarts (subject to normal TTL expiry).
- Deploy automation MAY intentionally clear RQ state, but MUST scope any flush to the RQ DB only (DB 9). Session storage (DB 11) MUST NOT be flushed as part of normal deploys.
- Changing the session DB index (default DB 11) invalidates all active sessions:
  - Existing session cookies will continue presenting the old session id, but the server will not find that id in the new DB index.
  - Result: users will be treated as logged out and must re-authenticate (remember-me may still rehydrate later depending on cookie state).
  - Any session DB index change MUST update this contract and MUST be coordinated across all session consumers (WEPPcloud + rq-engine marker paths).

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
- `POST /weppcloud/api/auth/session-heartbeat` and `POST /weppcloud/api/auth/rq-engine-token` MUST use same-origin checks (`Origin` or `Referer`), compared against the effective WEPPcloud origin (request host plus trusted forwarded/configured external host aliases).
- Requests missing both `Origin` and `Referer` headers MUST be rejected for these endpoints.
- `POST /rq-engine/api/runs/{runid}/{config}/session-token` (cookie-auth path) MUST ignore forwarded-origin aliases (`X-Forwarded-Proto`, `X-Forwarded-Host`) unless `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`.
- Deployments that need external-origin aliases for rq-engine cookie-path checks SHOULD prefer explicit host/scheme config (`OAUTH_REDIRECT_HOST`, `OAUTH_REDIRECT_SCHEME`, `EXTERNAL_HOST`, `EXTERNAL_SCHEME`) over forwarded-header trust.
- Anonymous or stale session-token claims MUST NOT bypass CAPTCHA/public-run gates in anonymous flows.
- Private-run session-token issuance via cookie-auth path MUST enforce run authorization from server-side owner/role state.

## Conformance Tests (Required)
The following suites MUST be updated when session contract behavior changes:
- `tests/weppcloud/test_configuration.py`
- `tests/weppcloud/routes/test_rq_engine_token_api.py`
- `tests/microservices/test_rq_engine_session_routes.py`
- `tests/microservices/test_rq_engine_fork_archive_routes.py`
- `wepppy/weppcloud/controllers_js/__tests__/session_heartbeat.test.js`
- `wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js`

## Change Management
- Any change to session TTLs, cookie defaults, heartbeat interval, stale-tab UX, or endpoint auth rules MUST update this contract and linked implementation docs in the same PR.
