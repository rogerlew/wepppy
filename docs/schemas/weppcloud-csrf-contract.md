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
| WEPPcloud browser callers invoking rq-engine mutators via `requestWithSessionToken` | Session bootstrap -> bearer token -> rq-engine | CSRF applies to the token bridge endpoint, not the rq-engine mutator call itself. |
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

## Browser Same-Origin Guard Contract

This section governs only the three existing browser guards:

- Flask authentication/session mutations using `_is_same_origin_post`;
- rq-engine cookie-authenticated session-token issuance using
  `_is_same_origin_cookie_request`; and
- query-engine diagnostic bandwidth mutations using
  `_is_same_origin_request`.

Implementation conformance is pending REM-04.

An origin tuple is lowercase scheme and host plus an effective port: 443 for
HTTPS and 80 for HTTP when the URL omits a port. Invalid URLs, opaque
`Origin: null`, user information, and unsupported schemes do not produce an
origin tuple.

Each guard MUST apply this order:

1. `Sec-Fetch-Site: cross-site` MUST reject regardless of other headers.
   Unknown Fetch Metadata values do not authorize a request.
2. A present `Origin` MUST parse successfully. For the ordinary fallback it
   MUST exactly match an allowed scheme, host, and port.
3. `Sec-Fetch-Site: same-origin` MAY bridge only a trusted-proxy scheme
   mismatch: a present browser `Origin` is accepted when its host exactly
   matches the proxy-normalized or configured public host and its port is the
   effective public port for its declared scheme. A subdomain, different host,
   or explicit non-public port is conflicting and MUST reject. This exception
   exists so public HTTPS remains same-origin when the application sees the
   trusted proxy's internal HTTP hop; it is not general scheme or port
   coercion.
4. `Sec-Fetch-Site: same-origin` with no `Origin` MAY authorize the request.
   Fetch Metadata is a browser signal; protected Flask routes still require
   their existing CSRF token, and cookie-authenticated rq-engine routes still
   require their existing session authentication.
5. Without an authorizing same-origin Fetch Metadata signal, a present
   `Origin` MUST exactly match the allowed-origin set.
6. When `Origin` is absent, a present absolute `Referer` origin MUST exactly
   match the allowed-origin set.
7. Missing `Sec-Fetch-Site`, `Origin`, and `Referer` MUST reject.

Allowed origins MUST derive only from framework request properties after the
configured trusted-proxy middleware, the request's authoritative Host value,
or explicitly configured public origin values. Raw `X-Forwarded-Proto`,
`X-Forwarded-Host`, `X-Forwarded-Port`, and `X-Forwarded-Ssl` values MUST NOT
independently add allowed origins. rq-engine's legacy
`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` compatibility switch MUST no longer
expand this guard after REM-04.

The authoritative inputs and deployment preconditions are:

- Flask uses `request.scheme` and `request.host` after its one-hop `ProxyFix`,
  plus configured `OAUTH_REDIRECT_HOST`/`OAUTH_REDIRECT_SCHEME` or
  `EXTERNAL_HOST`. The service MUST be reachable only through the final trusted
  proxy, which MUST replace incoming forwarded headers. Direct client access to
  the ProxyFix-wrapped service is unsupported and unsafe.
- rq-engine and query-engine use the ASGI request URL scheme and authoritative
  Host plus configured public host/scheme values. They do not install
  forwarded-origin middleware in this contract and MUST ignore raw forwarded
  origin headers.
- If a required public origin is not available from those inputs, exact
  Origin/Referer fallback rejects. No raw-header recovery is allowed.

For the narrow upstream-TLS bridge, parse the browser Origin. Its host MUST
equal the authoritative request host or a configured public host. An exact
allowed tuple passes normally. Otherwise, bridging is available only with
`Sec-Fetch-Site: same-origin`, authoritative application scheme `http`,
application port 80, Origin scheme `https`, and Origin port 443. No other
scheme or port pair bridges. The browser Origin supplies the public scheme/port
only for this constrained Fetch Metadata case; raw forwarded headers are
irrelevant.

The shared regression vectors are:

| Fetch site | Origin / Referer condition | Expected |
| --- | --- | --- |
| `same-origin` | no Origin | allow, subject to existing CSRF/auth |
| `same-origin` | exact public Origin | allow |
| `same-origin` | public HTTPS Origin, trusted internal HTTP request, same host and effective public port | allow |
| `same-origin` | different host, subdomain, or explicit port | reject |
| `cross-site` | any | reject |
| absent or unknown | exact allowed Origin | allow |
| absent or unknown | exact allowed Referer with no Origin | allow |
| absent or unknown | `Origin: null`, malformed, scheme, host, subdomain, or port mismatch | reject |
| absent | no Origin and no Referer | reject |
| any non-authorizing value | raw forwarded host/proto only | reject |
| `same-origin` | HTTP:80 application tuple plus HTTPS:443 Origin on same authoritative host | allow |
| `same-origin` | any other scheme/port bridge | reject |

## Browser-State Reset Cookie Ownership

Implementation conformance is pending REM-04. Browser-state reset owns only:

- the configured `SESSION_COOKIE_NAME` at `SESSION_COOKIE_PATH` and
  `SESSION_COOKIE_DOMAIN`; and
- the configured `REMEMBER_COOKIE_NAME` at `REMEMBER_COOKIE_PATH` and the
  resolved `REMEMBER_COOKIE_DOMAIN`.

An unset domain means a host-only deletion. Paths normalize to `/` when unset.
Reset MUST NOT synthesize parent-domain or path variants and MUST NOT delete
generic `csrf_token` or `csrftoken` cookies. Flask-WTF stores its CSRF value in
the WEPPcloud session, so deletion of the owned session cookie clears that
browser CSRF state without claiming ownership of generic CSRF cookie names.
The reset helper MUST read Flask/Flask-Login's resolved configuration values
directly; it MUST NOT invent a session-domain fallback for an unset remember
domain. Tests MUST cover both unset domains and distinct session/remember
domains.

During the session-cookie migration window, reset MUST also invalidate every
bounded, correctly signed WEPPcloud primary or legacy SID presented by the
request in Redis and install the canonical revocation fence. This is
server-side invalidation, not ownership of the generic browser cookie. Reset
MUST NOT synthesize or emit deletion headers for legacy `session` domain/path
variants. A late response MUST NOT recreate a fenced SID.

## Browser Client Requirements
- Browser mutation requests SHOULD use `WCHttp.request(...)` or its helpers so CSRF headers are attached consistently.
- Raw `fetch(...)` mutation calls MUST attach `X-CSRFToken` when they target CSRF-protected Flask routes.
- Templates that rely on JS mutations SHOULD expose a discoverable token source (for example, `<meta name="csrf-token" ...>` or hidden form field).

## rq-engine and 3rd-Party API Requirements
- 3rd-party and agent clients MUST use bearer-token auth for rq-engine API routes.
- Bearer-token routes MUST remain CSRF-agnostic so non-browser clients are not coupled to CSRF tokens.
- Cookie-auth support on `POST /rq-engine/api/runs/{runid}/{config}/session-token` is a browser bridge and MUST remain same-origin guarded.
- Raw forwarded-origin aliases (`X-Forwarded-Proto`, `X-Forwarded-Host`) MUST
  NOT authorize the rq-engine cookie path. The legacy
  `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` variable is accepted but inert;
  deployments MUST use explicit external host/scheme configuration instead.
- Landuse Phase 1 moved browser mutators (`set-landuse-mode`, `set-landuse-db`,
  `modify-landuse-coverage`) MUST use bearer transport via
  `requestWithSessionToken` and MUST NOT introduce cookie-mutation fallback on
  rq-engine route handlers.
- Landuse Phase 3 moved browser surfaces (`landuse-user-defined/*`,
  `landuse-map/*`, `modify-landuse`) MUST use the same session-token bridge
  bearer pattern from WEPPcloud render pages and MUST NOT reintroduce direct
  cookie mutation handling on rq-engine mutators.
- Legacy Flask landuse compatibility machine/state endpoints were removed on
  `2026-04-24`; browser callers MUST NOT regress to direct Flask mutation paths
  for these operations.

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
- All three existing guards MUST consume the shared Browser Same-Origin Guard
  vectors, including the upstream-TLS scheme bridge and conflicting-Origin
  rejection.
- CSRF-enabled Flask tests MUST prove that same-origin evidence does not bypass
  a missing or invalid CSRF token.
- Browser-state reset tests MUST assert the complete owned cookie deletion tuple
  set and absence of generic CSRF or synthesized parent-domain targets.
- rq-engine tests MUST prove
  `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true` is inert for authorization.

## Change Management
- Any change to CSRF rules, same-origin behavior, or route classification MUST update this contract in the same PR.
- Related contract docs MUST stay aligned:
  - `docs/schemas/weppcloud-session-contract.md`
  - `docs/dev-notes/auth-token.spec.md`
  - `docs/schemas/rq-engine-agent-api-contract.md`

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
