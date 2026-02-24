# WEPPcloud CSRF Contract
> Authoritative contract for CSRF protections across WEPPcloud Flask routes and related microservice token bridges.
> **See also:** `docs/schemas/weppcloud-session-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/schemas/rq-response-contract.md`

## Normative Status
- This document is normative and authoritative for CSRF behavior.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.
- If implementation and this contract diverge, either:
  - implementation MUST be corrected, or
  - this contract MUST be updated in the same change set.

## Scope
- Covers CSRF policy for WEPPcloud browser-facing routes and token bridge endpoints.
- Defines which auth paths require CSRF protection and which do not.
- Covers migration requirements for enabling global Flask CSRF enforcement safely.
- Does not replace authentication/authorization requirements.
- Does not redefine canonical error payloads (see `docs/schemas/rq-response-contract.md`).

## Threat Model and Boundary
- CSRF risk exists when browsers automatically attach ambient credentials (for example, Flask session cookies).
- CSRF risk is not the primary concern for bearer-token API calls where clients send `Authorization: Bearer ...` headers.
- Microservice endpoints that support cookie-auth fallback are treated as CSRF-relevant and MUST enforce same-origin constraints.

## Endpoint Policy Matrix
| Endpoint Class | Primary Auth Path | CSRF Requirement |
| --- | --- | --- |
| Flask mutating routes (`POST`, `PUT`, `PATCH`, `DELETE`) using browser session cookies | Flask session cookie | MUST require CSRF protection (token validation or explicit same-origin gate for approved boundary endpoints). |
| Flask safe routes (`GET`, `HEAD`, `OPTIONS`) | Any | CSRF token not required. |
| rq-engine run APIs called with bearer token | `Authorization: Bearer` | CSRF token MUST NOT be required. |
| rq-engine session-token endpoint via cookie path | Flask session cookie fallback | MUST enforce same-origin checks and reject requests with no `Origin` and no `Referer`. |
| browse/query-engine API calls using bearer token | `Authorization: Bearer` | CSRF token MUST NOT be required. |

## Flask Route Requirements
- For cookie-authenticated mutating routes, protection MUST be satisfied by one of:
  - validated CSRF token (`X-CSRFToken`, `X-CSRF-Token`, or form `csrf_token`), or
  - explicit same-origin gate for narrowly scoped boundary endpoints.
- Broad exemptions (`@csrf.exempt`) MUST be rare, documented inline, and accompanied by tests for abuse scenarios.
- Any endpoint that mints tokens or mutates session state from cookie auth MUST enforce same-origin checks.
- Same-origin checks MUST:
  - compare normalized origin tuples (scheme, host, port),
  - honor trusted proxy/external host aliases,
  - reject missing `Origin` and missing `Referer`.

## Browser Client Requirements
- Browser mutation requests SHOULD use `WCHttp.request(...)` or its helpers so CSRF headers are attached consistently.
- Raw `fetch(...)` mutation calls MUST attach `X-CSRFToken` when they target CSRF-protected Flask routes.
- Templates that rely on JS mutations SHOULD expose a discoverable token source (for example, `<meta name="csrf-token" ...>` or hidden form field).

## rq-engine and 3rd-Party API Requirements
- 3rd-party and agent clients MUST use bearer-token auth for rq-engine API routes.
- Bearer-token routes MUST remain CSRF-agnostic so non-browser clients are not coupled to CSRF tokens.
- Cookie-auth support on `POST /rq-engine/api/runs/{runid}/{config}/session-token` is a browser bridge and MUST remain same-origin guarded.
- Forwarded-origin aliases (`X-Forwarded-Proto`, `X-Forwarded-Host`) for rq-engine cookie-path same-origin checks MUST remain opt-in via `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`.

## Current Baseline Controls (Do Not Regress)
- Global Flask CSRF middleware is enabled in WEPPcloud (`flask_wtf.csrf.CSRFProtect`).
- `POST /weppcloud/api/auth/rq-engine-token` enforces authenticated session + same-origin checks.
- `POST /weppcloud/api/auth/session-heartbeat` enforces authenticated session + same-origin checks.
- OAuth provider disconnect is protected by global CSRF middleware.
- `WCHttp` auto-attaches `X-CSRFToken` for non-safe methods when token discovery succeeds.
- `templates/base_pure.htm` exposes `<meta name="csrf-token" ...>` and provides browser CSRF propagation for same-origin form/fetch mutation requests.
- `POST /weppcloud/api/bootstrap/verify-token` is CSRF-exempt by design as a forward-auth infrastructure boundary endpoint.

## Migration Completion Criteria (Global Flask CSRF)
Before enabling blanket global CSRF middleware enforcement, the following MUST be true:
1. Base templates expose a shared token source usable by JS mutation paths.
2. Known raw `fetch(...)` mutating calls targeting Flask routes are migrated to `WCHttp` or manually attach CSRF headers.
3. CSRF failure UX is standardized (form + JSON/AJAX paths) so failures are observable and actionable.
4. Exempt boundary endpoints are explicitly documented with rationale and regression tests.

## Required Test Coverage
- Missing/invalid CSRF token on protected Flask mutation routes MUST fail.
- Valid CSRF token on protected Flask mutation routes MUST succeed.
- Same-origin gate endpoints MUST reject cross-origin and missing-origin submissions.
- rq-engine bearer-token routes MUST remain callable without CSRF token headers.
- rq-engine cookie-path session-token issuance MUST enforce same-origin behavior.

## Change Management
- Any change to CSRF rules, same-origin behavior, or route classification MUST update this contract in the same PR.
- Related contract docs MUST stay aligned:
  - `docs/schemas/weppcloud-session-contract.md`
  - `docs/dev-notes/auth-token.spec.md`
  - `docs/dev-notes/rq-engine-agent-api.md`

## Implementation References
- `wepppy/weppcloud/app.py`
- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/templates/base_pure.htm`
- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/routes/_security/oauth.py`
- `wepppy/weppcloud/routes/bootstrap.py`
- `wepppy/weppcloud/controllers_js/http.js`
- `wepppy/weppcloud/controllers_js/forms.js`
- `wepppy/microservices/rq_engine/session_routes.py`
- `wepppy/microservices/rq_engine/auth.py`
