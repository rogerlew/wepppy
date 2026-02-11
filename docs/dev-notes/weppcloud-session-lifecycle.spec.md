# WEPPcloud Session Lifecycle Specification
> Implementation specification for how WEPPcloud sessions behave across Flask pages, rq-engine-only activity, and stale-tab recovery.
> **Normative contract:** `docs/schemas/weppcloud-session-contract.md`

## Purpose
- Describe the concrete lifecycle behind the normative session contract.
- Provide operational flow references for debugging and future refactors.
- Keep expected behavior explicit for stale-tab and long-running WEPP workflows.

## Components
- Flask session store: Redis DB 11 (`session:<sid>`) via Flask-Session.
- Flask-Security remember-me cookie for login restoration.
- rq-engine session-token issuer: `POST /rq-engine/api/runs/{runid}/{config}/session-token`.
- Flask heartbeat endpoint: `POST /weppcloud/api/auth/session-heartbeat`.
- Global heartbeat client: `wepppy/weppcloud/static/js/session_heartbeat.js`.
- CAP guard marker (`cap_verified_at`) for anonymous gating windows.

## Core Flows

### 1) Authenticated interactive browsing
1. User signs in (or is restored via remember-me).
2. Flask page response includes `base_pure.htm` and loads `session_heartbeat.js`.
3. Heartbeat writes `_heartbeat_ts` into Flask session on init and every 5 minutes.
4. Session key TTL in Redis is kept warm while Flask heartbeat continues succeeding.

### 2) Long-running rq-engine activity
1. User starts job(s); browser begins rq-engine polling/status checks.
2. Without heartbeat, Flask session TTL would continue counting down.
3. With heartbeat active, Flask session remains refreshed during rq-engine-only periods.
4. User returns later and remains authorized without opening a new tab for manual refresh.

### 3) Expired/stale tab recovery
1. Heartbeat receives `401` or `403` (expired or unauthorized server session).
2. Heartbeat client stops its interval, emits `wepp:session-heartbeat-expired`, and renders a persistent banner.
3. Banner offers:
   - `Sign in` (navigates to login with `next=<current URL>`), and
   - `Reload` (refreshes current page state).
4. Page-specific request handlers (for example fork console) treat explicit auth failures as stale-session events and prompt reload/sign-in.

### 4) Session-token mint path
1. Client requests `POST /rq-engine/api/runs/{runid}/{config}/session-token`.
2. rq-engine resolves auth either from bearer claims or Flask session cookie.
3. For cookie path:
   - validates session cookie signature and Redis session existence,
   - extracts `user_id`/`roles` from session payload when present,
   - enforces private-run authorization from owner/role state.
4. rq-engine issues run-scoped session JWT and sets HttpOnly browse cookie.

## State and TTL Model
| State Item | TTL/Refresh Behavior | Notes |
| --- | --- | --- |
| Flask session key (`session:<sid>`) | 12h target lifetime; refreshed by Flask session writes | heartbeat enforces writes during idle-tab periods |
| Heartbeat timestamp (`_heartbeat_ts`) | updated each successful heartbeat | used as write marker |
| Session run marker (`auth:session:run:<runid>:<session_id>`) | 4 days | tied to rq-engine session-token issuance |
| CAP marker (`cap_verified_at`) | default 20 minutes (`CAP_SESSION_TTL_SECONDS`) | anonymous users only |

## Failure Modes and Expected Behavior
- Missing/anonymous auth on heartbeat endpoint:
  - expected: `401` canonical error payload.
- Cross-origin heartbeat or token-refresh POST:
  - expected: `403` canonical error payload.
- Missing both `Origin` and `Referer` on heartbeat or token-refresh POST:
  - expected: `403` canonical error payload.
- Same-origin checks normalize default ports and honor trusted forwarded/configured external host aliases so proxied HTTPS origins are accepted.
- Heartbeat network failures:
  - client tolerates transient failures and keeps retrying on the interval; only auth failures (`401`/`403`) trigger session-expired UX.
- Stale authenticated UI shell:
  - must transition to explicit re-auth prompt state, not silent gray/disabled controls.

## Operational Checks
- Validate config:
  - `SESSION_COOKIE_SAMESITE` default `Lax`.
  - `SESSION_COOKIE_SECURE=true`.
  - `PERMANENT_SESSION_LIFETIME=12h`.
- Validate endpoints:
  - `POST /weppcloud/api/auth/session-heartbeat` from authenticated tab should return `{ok:true,...}`.
  - Same endpoint from cross-origin should return `403`.
- Validate UX:
  - Forcibly expire session key, then observe stale-tab banner on next heartbeat/failing action.

## Implementation References
- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/templates/base_pure.htm`
- `wepppy/weppcloud/static/js/session_heartbeat.js`
- `wepppy/microservices/rq_engine/session_routes.py`
- `wepppy/weppcloud/utils/cap_guard.py`
