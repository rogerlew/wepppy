# RQ-Engine Agent API Contract
> Canonical contract for agent clients using the WEPPcloud rq-engine.
> **Status:** Canonical path under `docs/schemas/` as of 2026-04-10 (moved from `docs/dev-notes/`).
> **Operator usability note (2026-04-11):** API-operator hardening for non-browser token bootstrap and smoke reliability shipped in `docs/work-packages/20260411_rq_operator_experience_hardening/`.
> **See also:** `docs/schemas/rq-response-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/schemas/weppcloud-csrf-contract.md`, `docs/dev-notes/correlation-id-debugging.md`, `docs/schemas/rq-controller-state-contract.md`, `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`, and user-facing `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md`.

## Purpose
This document defines how agents should call rq-engine safely and predictably.
It is the developer-facing contract for auth, scopes, response semantics, job
lifecycle polling, and route ownership.

## Canonical Surface
- Service: `wepppy/microservices/rq_engine/` (FastAPI).
- Direct app paths use `/api/...` (for example `/api/jobstatus/{job_id}`).
- Via WEPPcloud reverse proxy, endpoints are under `/rq-engine/api/...`.
- OpenAPI:
  - Direct service: `/openapi.json`
  - Proxied: `/rq-engine/openapi.json`
- Stable OpenAPI operation IDs use the `rq_engine_` prefix.

Route ownership and freeze artifacts:
- Frozen endpoint inventory:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- Route contract checklist:
  `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- Drift guards:
  - `tools/check_endpoint_inventory.py`
  - `tools/check_route_contract_checklist.py`

## Auth Model
Accepted token classes follow `docs/dev-notes/auth-token.spec.md`:
- `user`
- `session`
- `service`
- `mcp` (where route scope/claims allow)

Run-scoped routes enforce run access in addition to scope checks:
- User tokens: owner/public-run checks.
- Session tokens: Redis session marker validation for run scope.
- Service/MCP tokens: run claims must permit the target run.

### Polling Auth Modes
Polling routes:
- `GET /api/jobstatus/{job_id}`
- `GET /api/jobinfo/{job_id}`
- `POST /api/jobinfo`

Mode switch via `RQ_ENGINE_POLL_AUTH_MODE`:
- `open` (default) - no token required.
- `token_optional` - validate JWT when bearer token is sent.
- `required` - bearer token required; must include `rq:status`.

Polling hardening:
- The optional `jobstatus.queue` snapshot follows whichever polling auth result
  the endpoint already produced. It does not require a token in `open` mode,
  does not vary by token class, and does not add scope requirements. The
  long-lived Culvert service JWT with `rq:status` remains sufficient for
  authenticated polling. The short-lived returned Culvert `browse_token` is a
  separate batch-scoped artifact token for browse/download only and does not
  gain `rq:status`.
- In-memory rate limiter (`endpoint + caller + ip`).
- Default limit: `400` requests per `60` seconds.
- Env vars:
  - `RQ_ENGINE_POLL_RATE_LIMIT_COUNT`
  - `RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS`

## Scope Contract
Core scopes used by agent-facing routes:

| Scope | Used for |
|---|---|
| `rq:status` | Job polling (`jobstatus`, `jobinfo`) and `canceljob`; also bearer path for session-token issuance and setup-discovery compatibility (`/api/configs`, `/api/endpoints*`). |
| `rq:read` | Read-only setup/controller-state metadata surfaces (`/api/configs`, `/api/endpoints*`, `/api/runs/{runid}/{config}/pipeline`, `/api/runs/{runid}/{config}/readiness`, `/api/runs/{runid}/{config}/controllers*`, `/api/runs/{runid}/{config}/endpoints*`, `/api/runs/{runid}/{config}/geospatial-metadata`, `/api/runs/{runid}/{config}/outputs`). |
| `rq:enqueue` | Most run mutations that enqueue background jobs or perform run mutations under rq-engine routes. |
| `rq:export` | Export artifact endpoints under `/runs/{runid}/{config}/export/*`. |
| `bootstrap:enable` | Bootstrap enable endpoint. |
| `bootstrap:token:mint` | Bootstrap token mint endpoint. |
| `bootstrap:read` | Bootstrap read endpoints (`commits`, `current-ref`). |
| `bootstrap:checkout` | Bootstrap checkout endpoint. |
| `culvert:batch:submit` | Culvert batch submit endpoint; also accepted for `/api/canceljob/{job_id}`. |
| `culvert:batch:retry` | Culvert batch retry endpoint. |

Bootstrap routes do not accept `rq:enqueue` as a substitute for `bootstrap:*`.

### Project Config Builder description

The authenticated Builder description response reports
`builder_description_schema_version = 2`. Its singular `capability_graph` and
top-level `components` retain the frozen historical Continental-US schema-v2
response shape for read-only parsing compatibility. They are not a WP12C
creation contract. The authoritative `capability_graphs_by_locale` object is
keyed by `continental-us`, `europe`, `canada`, `australia`, and `global-earth`;
every value is one complete project-owned config schema-v3 capability graph.
`components_by_locale` contains each matching complete component population.
Clients select the graph using the locale stable ID and MUST NOT union graph
axes. The server performs the same locale-keyed selection during validation and
creation. The registry revision covers both complete mappings.

Validation and creation requests MUST submit
`builder_description_schema_version = 2` and a schema-v3
`climate_station_database` selection. A client that omits either field or sends
an unsupported description version receives `409 unsupported_builder_schema`
before directory creation or NoDb mutation. Therefore legacy clients may parse
the singular compatibility members but cannot create a WP12C run.

Schema-v3 Builder selections include `climate_station_database`. Its value is a
stable component ID from the selected locale graph, separate from the climate
dataset ID. The server revalidates it and materializes the component's exact
`climate.cligen_db` value. Cross-locale or unknown station-database IDs return a
field-addressable 4xx before creation.

### Project Config Update and Capability Refresh

The run-scoped update routes are:

- `GET /api/runs/{runid}/{config}/project-config/update-availability`;
- `GET /api/runs/{runid}/{config}/project-config/update-preview`; and
- `POST /api/runs/{runid}/{config}/project-config/update-apply`.

Availability requires run-read access and is non-mutating. Preview/apply require
owner/Admin/Root mutation authority, and the worker reauthorizes. Availability
returns `current_digest`, nullable `last_update`, nullable `update_kind`, and
`acknowledgment_required` but no graph delta. Preview returns complete additions,
deterministic `resulting_digest`, exact update kind, preserved project
selections, and the complete capability delta when applicable.

Disabled/unavailable state and `last_update` disclosure MUST match the project-
owned config contract: null update kind, false acknowledgment requirement,
read-only digest/reconciliation fields, and no actor identity or warning text.

Preview `capability_refresh` is null for `additive`; otherwise it MUST reproduce
the complete typed schema in project-owned config contract section 13.1:
`locale_profile`, unchanged ordered `locales`,
`preserved_project_selections`, exact `acknowledgment`, typed `prior` and
`resulting` identity objects, and deterministically sorted typed `changes`.
Clients MUST preserve JSON nulls, list order, lexicographic ID order, and
`changes` order; they MUST NOT treat this object as an extensible untyped delta.

Apply always sends `preview_id`. It sends `{section, option}` trigger only when
additions exist and exact `{accepted: true, revision:
"PC-24-capability-refresh-v1"}` capability acknowledgment only when the preview
has a capability delta. Missing acknowledgment is `400
capability_refresh_acknowledgment_required`; drift is `409
stale_config_preview`; unavailable refresh is `409 config_update_unavailable`.
These fail before reservation.

Ordinary accepted apply returns HTTP 202 `job_id`. If the latest committed
amendment has the same non-null preview ID and matching resulting digest, apply
returns HTTP 200 without enqueue and exactly `{applied: true, recovered: true,
sequence, prior_digest, resulting_digest}`. Historical latest amendments
without kind/preview are reported as `additive`/JSON `null` and cannot match an
idempotent replay.

The endpoint's schema/defaults, operation document, OpenAPI representation, and
runtime response MUST expose the same required members and types. A generic
object placeholder is not contract-conformant.
- Controller-state cutover package
  `20260410_rq_controller_state_contract_cutover` closed on 2026-04-11 with
  auth-scope parity evidence and keeps `rq:status` + `rq:read` compatibility
  for read-only controller-state routes in the frozen baseline.
- `rq:status` compatibility is bounded to read-only controller-state endpoints
  and MUST NOT broaden access to mutation/export/admin/bootstrap-control
  endpoint families.
- Explicit cutover policy decision: session-token minting continues to accept
  bearer `rq:status` and mint broader run-scoped session scopes for
  compatibility. Treat this as an accepted residual/design risk until a
  follow-on policy package updates route + descriptor + contract together.

## Landuse First-Class Route Contract (2026-04-24)

Phase 1 + Phase 2 + Phase 3 migration adds canonical rq-engine landuse interfaces:

- `POST /api/runs/{runid}/{config}/set-landuse-mode`
- `POST /api/runs/{runid}/{config}/set-landuse-db`
- `POST /api/runs/{runid}/{config}/modify-landuse-coverage`
- `GET /api/runs/{runid}/{config}/controllers/landuse/state`
- `GET /api/runs/{runid}/{config}/landuse-user-defined/catalog`
- `POST /api/runs/{runid}/{config}/landuse-user-defined/upload`
- `POST /api/runs/{runid}/{config}/landuse-user-defined/delete`
- `POST /api/runs/{runid}/{config}/landuse-user-defined/update-description`
- `GET /api/runs/{runid}/{config}/landuse-map/snapshot`
- `POST /api/runs/{runid}/{config}/landuse-map/save`
- `POST /api/runs/{runid}/{config}/landuse-map/clear-override`
- `POST /api/runs/{runid}/{config}/modify-landuse`

Auth and scope requirements:
- Landuse mutators require `rq:enqueue`, run access, and token class in
  `{user, session, service, mcp}`.
- Landuse read state requires run access plus one of `{rq:read, rq:status}`.
- Phase 3 read routes (`landuse-user-defined/catalog`, `landuse-map/snapshot`)
  require run access plus one of `{rq:read, rq:status}` and token class in
  `{user, session, service, mcp}`.

Request contract clarifications:
- `set-landuse-mode` requires `mode`; `landuse_single_selection` remains an
  optional field.
- `landuse-map/save` requires `rows` and an optimistic-concurrency precondition
  hash supplied in either:
  - `X-If-Match-Sha256` request header, or
  - `if_match_sha256` request body field.
  Each row requires `key` and `management_file`; optional `description`
  persists a custom summary/report label for that key.
  Missing precondition hash returns `428 PRECONDITION_REQUIRED`.
- `build-landuse` `landuse_management_mapping_selection` must be a supported
  mapping key; path-like or unknown selections are rejected with
  `invalid_mapping_selection`.

Run-root targeting policy for migrated landuse routes:
- Optional query parameter `pup` is supported for non-composite runids.
- `pup` resolves only under run `_pups/` with containment checks.
- Composite runids (`;;`) ignore `pup` and use runid-encoded context.

`landuse-user-defined/upload` archive policy:
- Real management payload files MUST be `.man` members at archive root.
- Known macOS metadata sidecars (`__MACOSX/*`, `.DS_Store`, `._*`) are ignored.
- Nested non-sidecar members are rejected with canonical `invalid_archive` errors.

Browser transport policy for moved UI callers:
- Browser callers use `requestWithSessionToken` to invoke `/rq-engine/api/...`.
- No cookie-mutation fallback is introduced for migrated rq-engine mutators.
- WEPPcloud render routes remain in WEPPcloud and only their machine/state APIs
  moved:
  - `/runs/{runid}/{config}/report/landuse`
  - `/runs/{runid}/{config}/landuse-user-defined`
  - `/runs/{runid}/{config}/landuse-map`

Compatibility/deprecation policy:
- Legacy Flask landuse compatibility machine/state routes were removed on
  **2026-04-24** via package
  `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/`.
- Removed Flask compatibility endpoints:
  - `/runs/{runid}/{config}/tasks/set_landuse_mode/`
  - `/runs/{runid}/{config}/tasks/set_landuse_db/`
  - `/runs/{runid}/{config}/tasks/modify_landuse_coverage[/]`
  - `/runs/{runid}/{config}/tasks/modify_landuse_mapping/`
  - `/runs/{runid}/{config}/api/landuse/user_defined/catalog`
  - `/runs/{runid}/{config}/tasks/landuse/user_defined/upload|delete|update-description`
  - `/runs/{runid}/{config}/api/landuse/map_snapshot`
  - `/runs/{runid}/{config}/tasks/landuse/map/save|clear-override`
  - `/runs/{runid}/{config}/tasks/modify_landuse/`
- Agents and browser callers MUST use rq-engine routes for these operations;
  removed Flask endpoints now return routing-level not-found behavior.

## Response Contract
rq-engine responses must follow `docs/schemas/rq-response-contract.md`.

Submission/command responses:
- Async submit commonly returns `job_id` and `status_url`.
- Async status codes vary by endpoint contract (`200` or `202`); treat
  `job_id`/`job_ids` as the canonical async signal.
- Previously shipped named-child `job_ids` objects remain endpoint-specific
  compatibility surfaces. For AgFields Run All, `job_id` is the suite root and
  the object values are its three routing children.
- Sync operations return `message` and optional `result`.
- Keys use `lower_snake_case`.

Polling responses:
- `jobstatus`:
  `{job_id, runid, status, started_at, ended_at, progress?, queue?,
  conditioning_diagnostics?, error?, error_id?}`. `progress` is the existing
  aggregate job-count object; its runtime semantics are unchanged.
  When present, `queue` is exactly:
  ```json
  {
    "name": "batch",
    "rank": 17,
    "jobs_ahead": 16,
    "position_job_id": "next-queued-member-job-id",
    "basis": "next_queued_job_in_tree",
    "observed_at": "2026-08-07T18:42:11Z"
  }
  ```
  `name` is a non-empty RQ queue origin. `rank` is a positive one-based
  position in the current ordered Redis queue list. `jobs_ahead` is the
  non-negative zero-based offset of the selected job and must satisfy
  `rank == jobs_ahead + 1`. `position_job_id` is the requested root or a
  registered descendant reached exclusively through `job.meta` keys beginning
  with `jobs:`. `basis` is exactly `next_queued_job_in_tree`; `observed_at` is a
  UTC RFC 3339/ISO-8601 timestamp ending in `Z`.
  The object is present only when a normalized `queued` member exists, every
  queued candidate has a non-empty resolvable origin, all candidates share one
  origin, and a candidate remains in that origin's ordered queue list at the
  read. The minimum zero-based offset wins. Omit the entire object for no
  queued member, started/terminal/deferred-only/scheduled-only trees,
  missing/invalid origin, mixed origins, a dequeue race with no remaining
  candidate, or any expected RQ/Redis race that prevents a reliable snapshot.
  Never return null, partial/guessed data, rank zero/negative values, queue
  depth, unrelated job IDs or metadata, or a cross-queue global rank. For
  multiple same-origin candidates use one ordered queue snapshot or equivalent
  bounded operation, not one scan/position call per child. The snapshot is
  advisory, not an ETA, reservation, fairness guarantee, capacity estimate, or
  stable promise.
  The optional field is present only for successful WBT channel delineation
  and follows `docs/schemas/wbt-conditioning-diagnostics-contract.md`; a
  terminal WBT tree cannot report success with missing or invalid diagnostics.
- `jobinfo`: `{job_id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children, auth_actor?, culvert_batch_uuid?}`
- Canonical `status` values in successful polling payloads:
  - non-terminal: `queued`, `started`, `deferred`, `scheduled`
  - terminal success: `finished`
  - terminal failure: `failed`, `stopped`, `canceled`
- `not_found` is surfaced as HTTP `404` with canonical error payload (not a
  successful polling status value).

Errors:
- Status-code-first semantics (4xx input/auth/access; 5xx server failures).
- Canonical shape:

```json
{
  "error": {
    "message": "Human-readable summary",
    "code": "optional_code",
    "details": "error detail or traceback"
  },
  "error_id": "required-for-5xx"
}
```
- 5xx responses must include `error_id` for response/log correlation.
- 5xx observability requirement: return traceback details in `error.details`, or
  return a stable `error_id` that maps to server-side traceback/error logs.

Common route-level status requirements are enforced by
`tests/microservices/test_rq_engine_openapi_contract.py`.

Climate-parse validation contract:
- `POST /api/runs/{runid}/{config}/build-climate` returns canonical
  `validation_error` payloads for invalid/missing climate fields.
- Missing-field failures SHOULD surface machine-actionable field entries under
  top-level `errors` (for example `future_start_year`, `future_end_year`)
  instead of traceback text in `error.details`.

## Agent Workflow (Recommended)
1. Acquire a token:
   - User/service token (pre-issued), or
   - Run-scoped session token from `POST /api/runs/{runid}/{config}/session-token`.
2. Submit work to an agent-facing endpoint under `/api/...`.
3. If response includes `job_id`, poll `GET /api/jobstatus/{job_id}`.
4. On failure/debug needs, fetch `GET /api/jobinfo/{job_id}`.
5. Optionally cancel with `POST /api/canceljob/{job_id}`.
   Cancellation requires access to the run resolved from job metadata for user,
   session, service, and MCP tokens. The legacy `culvert:batch:submit` scope is
   accepted only when job info carries verified `culvert_batch_uuid` metadata.
   For `fork-archive` origin jobs, non-Admin/Root callers may cancel only while
   the job remains queued; dispatch handoff or started state returns `403`.

For runs with project capability schema v2 or v3, run-scoped controller schemas,
templates/defaults, aggregated operation documents, pipeline, and readiness
metadata expose only the authority stored in that run's flattened config.
Clients MUST treat these run-scoped enums and model tuples as authoritative;
the current global provider catalog cannot broaden an existing run. Flattened
no-capability and non-Builder/overlay/Turkey/RHEM compatibility modes retain
their existing discovery behavior. Schema-v1 does too except when an exact-
digest, active filename/parent-chain-congruent preset manifest with current
parent hashes, byte-exact canonical rematerialization, and one congruent
recognized Builder base without locale overlay select current locale authority
for only climate and land cover. The recognized non-flattened
legacy-base exception is defined below.
The climate, landuse, and soils build endpoints and the WEPP run endpoint MUST
return `409 capability_authority_invalid` with diagnostic `error.details`
before mutation or enqueue when stored schema-v2/schema-v3 authority is malformed,
partial, contradictory, or unsupported.

For any run with resolved graph authority, `POST
/api/runs/{runid}/{config}/tasks/upload-cli/` MUST require
`user_defined_cli` in that graph before reading or saving multipart content,
removing a timestamp, reserving, or enqueueing. Upload is a content replacement,
not an exact-current rebuild, so an outside-authority current value does not
authorize it. No-graph compatibility modes retain established upload behavior.

For non-flattened legacy runs, effective `.cfg` locale `us`, `eu`, `canada`,
`au`, or `earth` selects the matching current Builder graph for landuse, soil,
and climate discovery and mutation. Other legacy compositions retain localized
catalogs. The exact climate datasets are US Vanilla/PRISM/Daymet/gridMET/DEP
NEXRAD/Future CMIP5/User-Defined, Europe Vanilla/E-OBS/User-Defined, Canada
Vanilla/Daymet/User-Defined, Australia Vanilla/AGDC/User-Defined, and Earth
Vanilla/User-Defined. Builder Land-cover selection is a default only; discovery
and mutation expose the complete locale land-cover envelope. `409
locale_authority_invalid` and `503 builder_registry_error` with
`Retry-After: 5` are explicit diagnostic planning failures; agents MUST NOT
substitute a global catalog. Unavailable, malformed, or inconsistent canonical
preset policy also uses the diagnostic 503 after auth/run access and is never
treated as an inactive-preset compatibility fallback. After a terminal config-update job failure, agents
MUST compare the original preview digests with availability `current_digest`
and `last_update` to classify not-applied versus committed/recovered state.

A locale-bearing legacy query/config-token creation override returns HTTP 400
`project_config_validation_failed` before publication or controller
initialization. Config Builder's typed locale selection is not such an override.

## Climate Build Ordering (Operator Replication)
For API-only replication flows, climate setup is order-sensitive:
1. Run discovery first and read operation docs from
   `GET /api/runs/{runid}/{config}/endpoints?include_operation_docs=true`.
2. Resolve `climate_catalog_id` and its derived `climate_mode` explicitly before
   `build-climate`.
   - For schema-v2/schema-v3 runs, send the stable catalog ID advertised by run-scoped
     discovery. A numeric mode alone cannot authorize a new selection.
   - Send the catalog's integer mode for compatibility and mode/catalog
     agreement validation.
   - Do not blindly replay `resolved_defaults` when it reports `-1`
     (`ClimateMode.Undefined`).
3. Set station and spatial behavior atomically in `build-climate` using the
   run-scoped discovery fields `climate_station_method` and
   `climate_spatial_method`. Send their numeric compatibility fields
   `climatestation_mode` and `climate_spatialmode` when an older caller requires
   them; if both stable and numeric forms are present, they MUST agree. Legacy
   pre-build station mutation routes remain compatibility paths, not a
   requirement for new clients.
4. Send years and scaling parameters in the `build-climate` request payload
   (not as separate pre-build mutations):
   - years: `observed_start_year`, `observed_end_year`,
     `future_start_year`, `future_end_year`
   - scaling: `precip_scaling_mode`, `precip_scale_factor`,
     `precip_monthly_scale_factors_0..11`, `precip_scale_reference`,
     `precip_scale_factor_map`
5. Submit `POST /api/runs/{runid}/{config}/build-climate` and poll
   `GET /api/jobstatus/{job_id}` to terminal state.

Notes:
- Stable station/spatial method fields are authoritative for a new schema-v2/schema-v3
  selection. Numeric compatibility fields are accepted atomically and must map
  to the same stable IDs when both forms are sent.
- `climate_mode` in rq-engine `build-climate` payloads is parsed as an integer
  code (string aliases are not part of this route contract). Schema-v2 and
  schema-v3 runs additionally require `climate_catalog_id` for a new selection;
  omission is
  accepted only for an ordinary rebuild of the exact persisted current dataset
  and mode.
- Advanced climate toggles such as `use_gridmet_wind_when_applicable` and
  `adjust_mx_pt5` are also pre-build task mutations.

## Dev-Agent Local Workflow
- Canonical local account + credential-file convention:
  - `wepppy/weppcloud/static-src/tests/smoke/AGENTS.md`
- Preferred local secret file:
  - `docker/secrets/dev-agent.env`
- Typical setup:
  1. Sign in as `dev-agent@example.com`.
  2. Mint a bearer token from `POST /weppcloud/profile/mint-token` (session + CSRF).
  3. Use that token for `/rq-engine/api/*` calls.
- Admin sanity endpoint for role/scope verification:
  - `GET /rq-engine/api/admin/recently-completed-jobs`

## API Operator Bootstrap Contract (No `wctl`)

For non-developer API operators, auth bootstrap MUST be executable with standard
HTTP clients (`curl`, `python requests`, or equivalent) and MUST NOT require
`wctl`.

Target-profile requirements (owned by `20260411_rq_operator_experience_hardening`):
- Token bootstrap for API operators MUST have at least one documented machine
  path that does not depend on browser DOM/HTML scraping.
- Runbooks and schema docs MUST include a fully API-only bootstrap example with
  redaction guidance for secrets/tokens.
- Operator bootstrap MUST support least-privilege scope selection for the
  target action family (`rq:read`, `rq:status`, `rq:enqueue`, `rq:export`) and
  MUST document required scopes per flow.
- Machine-safe bootstrap MUST require a strong authenticated caller boundary
  (authenticated user principal, trusted service principal, or equivalent);
  anonymous token minting is prohibited.
- Cookie-auth bootstrap paths MUST enforce same-origin/CSRF rules per
  `docs/schemas/weppcloud-csrf-contract.md`.
- Machine-safe bootstrap endpoints MUST be `POST`-only, rate-limited, and
  audited.
- Machine-safe bootstrap tokens SHOULD default to short TTL unless an explicit
  longer-lived policy is documented for that flow.
- If a route remains browser/session-bound (for example CSRF-gated same-origin
  flows), docs MUST label it explicitly as browser-oriented and MUST provide
  the machine-safe alternative.
- Scope grant contract for machine-safe bootstrap:
  - `granted_scopes = requested_scopes ∩ authorized_scopes`;
  - mint routes MUST NOT silently add scopes not present in `requested_scopes`;
  - unknown or unauthorized requested scopes MUST return canonical `4xx`
    errors;
  - read-oriented operator flows SHOULD default to `rq:read` (and include
    `rq:status` only when polling compatibility is required and documented).

Shipped machine-safe bootstrap surface:
- `POST /weppcloud/api/auth/rq-engine-operator-token`
  - bearer-auth only (`Authorization: Bearer <token>`, audience `rq-engine`);
  - source bearer token MUST include a `jti` claim (missing `jti` returns `401`);
  - source bearer token revocation is checked against the JWT denylist
    (`revoked` returns `403`);
  - accepted caller token classes: `user`, `service`;
  - allowed operator scopes: `rq:read`, `rq:status`, `rq:enqueue`, `rq:export`;
  - request body (optional): `{"requested_scopes":[...]}`.
- Scope grant semantics are strict:
  - `granted_scopes = requested_scopes ∩ authorized_scopes`;
  - no silent scope expansion;
  - unknown requested scopes return `400`;
  - unauthorized requested scopes return `403`.
  - example: if caller bearer has only `rq:status`, then
    `{"requested_scopes":["rq:read"]}` returns `403`; request
    `{"requested_scopes":["rq:status"]}` instead.
- Defaults and guardrails:
  - defaults to read-oriented scope when request body omits `requested_scopes`;
  - callers SHOULD send explicit `requested_scopes` that are a subset of source
    bearer scopes to avoid avoidable `403` responses;
  - short-lived token default (`900s`, env-tunable);
  - rate limited and audit logged;
  - revocation backend unavailability returns `503` with retry guidance (`Retry-After`);
  - response uses `Cache-Control: no-store`.
- Run-scoped passthrough:
  - when caller token includes `runid`/`config`/`runs`, minted token preserves
    those claims to maintain rq-engine run authorization behavior.

Browser/session compatibility surface (still supported):
- `POST /weppcloud/profile/mint-token` remains valid for browser-oriented
  session + CSRF flows.
- Browser renewal bridge (`/weppcloud/api/auth/rq-engine-token`) remains for UI
  compatibility and should be treated as browser/session-bound.

## Correlation ID Debugging

- Send `X-Correlation-ID` on submission requests to make cross-service tracing deterministic.
- Confirm `X-Correlation-ID` is echoed on rq-engine responses.
- Use `GET /api/jobinfo/{job_id}` together with worker logs to validate enqueue metadata continuity.
- For end-to-end commands and troubleshooting patterns, use `docs/dev-notes/correlation-id-debugging.md`.

## Browser Renewal Contract (UI clients)
For WEPPcloud browser traffic using `WCHttp.requestWithSessionToken(...)`, token
acquisition is resilient by contract:

1. Attempt run-scoped session token:
   - `POST /api/runs/{runid}/{config}/session-token` (proxied as `/rq-engine/api/...`).
2. If token issuance returns `401` or `403`, transparently fall back to:
   - `POST /weppcloud/api/auth/rq-engine-token` (same-origin Flask endpoint).
3. Retry the original rq-engine request with the fallback bearer token.

Notes:
- This renewal path is intended for authenticated WEPPcloud browser sessions.
- Anonymous/CAPTCHA flows (for example public fork) remain route-specific and do
  not use `/api/auth/rq-engine-token`.
- Fallback token scopes are `rq:enqueue`, `rq:status`, `rq:export`.
- Client-side fallback token cache is short-lived; callers should still treat
  401/403 responses as authoritative when both primary and fallback paths fail.
- CSRF/same-origin behavior for this bridge is governed by
  `docs/schemas/weppcloud-csrf-contract.md`.

## Endpoint Families (Agent-Facing)
For the exact frozen route list (currently 114 routes), use the contract
checklist artifact. The
table below is the practical family map used by agent clients.

| Family | Paths | Typical Execution | Primary Scope |
|---|---|---|---|
| Job control | `/api/jobstatus/{job_id}`, `/api/jobinfo/{job_id}`, `/api/jobinfo`, `/api/canceljob/{job_id}` | Polling is sync/read-only; cancel is sync mutation and enforces access to the job's run | `rq:status` (cancel also accepts `culvert:batch:submit`) |
| Setup discovery | `/api/configs`, `/api/configs/{config}`, `/api/endpoints`, `/api/endpoints/{operation_id}/{schema\\|defaults\\|errors}`, `/api/runs/{runid}/{config}/endpoints?include_operation_docs=true` | Sync read-only discovery | `rq:status` or `rq:read` |
| Bootstrap | `/api/runs/{runid}/{config}/bootstrap/*` plus `run-*-noprep` endpoints | Mix of sync no-queue (`checkout`, reads, mint) and async (`enable`, no-prep runs) | `bootstrap:*` and `rq:enqueue` |
| Build/prep | `/api/runs/{runid}/{config}/build-*`, `fetch-dem-and-build-channels`, `set-outlet` | Mostly async enqueue | `rq:enqueue` |
| Model runs | `/api/runs/{runid}/{config}/run-*` (`wepp`, `wepp-watershed`, `swat`, `rhem`, `ash`, `debris-flow`, `omni`) | Mostly async enqueue; some sync dry-run paths | `rq:enqueue` |
| AgFields | `/api/runs/{runid}/{config}/agfields/*` | Read-only state plus synchronous setup/clear and asynchronous sub-field/integrated watershed jobs; the watershed run accepts one fixed routing scheme or the serial `all` suite | `rq:status` for reads; `rq:enqueue` for mutations |
| Upload tasks | `/api/runs/{runid}/{config}/tasks/upload-*` | Sync for upload/validation or async enqueue depending on route | `rq:enqueue` |
| Export | `/api/runs/{runid}/{config}/export/*` | Sync read-only file delivery | `rq:export` |
| Archive/fork | `/api/runs/{runid}/{config}/archive`, `/restore-archive`, `/delete-archive`, `/fork` | Mostly async enqueue; some sync mutation paths | `rq:enqueue` |
| External TS | `/api/runs/{runid}/{config}/acquire-openet-ts`, `/acquire-rap-ts` | Async enqueue | `rq:enqueue` |
| Culvert batch | `/api/culverts-wepp-batch/`, `/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | Async enqueue | `culvert:batch:*` |
| Project create | `/create/` (alias `/api/create/`) | Sync redirect (`303`) plus resource creation | `rq:enqueue` token path or CAPTCHA |

Watershed map-input normalization (`fetch-dem-and-build-channels`):
- For `set_extent_mode` `0`/`1`, agents may submit `map_bounds` without
  `map_center`/`map_zoom`.
- The backend derives missing `map_center` (bbox midpoint) and missing
  `map_zoom` (fit zoom from bounds).
- Explicitly supplied `map_center`/`map_zoom` still override derived values.

## Internal Admin Debug Endpoints
These routes are intentionally **internal/admin** and are not part of the
frozen 114-route agent-facing checklist.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/admin/recently-completed-jobs` | Recently completed jobs across `default`, `batch`, and `fork-archive` queues (lookback/filter support). | JWT Bearer, `rq:status`, `Admin`/`Root` role |
| `GET` | `/api/admin/jobs-detail` | Complete started + queued jobs across `default`, `batch`, and `fork-archive` queues. | JWT Bearer, `rq:status`, `Admin`/`Root` role |

Inventory source of truth for these internal routes remains:
`docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`.

## Bootstrap + Flask Exceptions
Agent-facing Bootstrap operations are canonically owned by rq-engine. Two
Bootstrap endpoints remain intentionally Flask-owned for infrastructure/UI
reasons:
- `/api/bootstrap/verify-token` (Caddy `forward_auth`)
- `/runs/<runid>/<config>/bootstrap/disable` (admin UI control)

## Stability and Change Control
- Route inventory and checklist artifacts are the frozen baseline.
- OpenAPI guard coverage includes:
  - metadata completeness
  - operation ID convention
  - required response code documentation
  - size budgets to prevent OpenAPI bloat
- Any contract change must update:
  - route implementation/OpenAPI metadata
  - freeze/checklist artifacts
  - guard tests
  - this document when behavior changes for clients

The global canonical OpenAPI size budget is 138,000 bytes as of 2026-07-13.
The AgFields backend contributes 15 frozen run-scoped operations. The existing
watershed-run operation accepts exact `concept_1`, `concept_2`, `hybrid`, and
`all` request values; omitted scheme remains `concept_2`. A single-scheme submit
may omit `max_workers` for automatic sizing or provide an integer from 1 through
16; values outside that range return the canonical 400 error rather than being
clamped. It returns `job_id` plus a one-entry `job_ids` mapping. `all` returns one
suite parent as `job_id`, a scheme-to-child `job_ids` mapping for the three serial
routing jobs, and the additive `finalizer_job_id`. The parent registers those
children plus a finalizer that depends on every scheme with
`allow_failure=true`, so finalization waits for every terminal scheme and is not
stranded by child failure. Every failure-tolerant dependent receives the same
already-terminal release guard used by Batch Runner. The complete four-child
tree and audit metadata are stored atomically on the parent before dispatch;
dispatch and cancellation share a lock so cancellation cannot observe a partial
tree. Suite-owned scheme children do not emit the suite completion trigger; the
finalizer is its single publisher. The isolated-clear operation accepts the same
selection contract, preserves legacy unscoped Concept 2 evidence, and never
creates an `all` artifact tree. The canonical OpenAPI size budget remains
138,000 bytes.

## Controller-State Contract Status
- Controller-state/schema/orchestration contract for agent clients is tracked in
  `docs/schemas/rq-controller-state-contract.md`.
- Roadmap cutover row 8 (`20260410_rq_controller_state_contract_cutover`)
  completed on 2026-04-11 with freeze/checklist/OpenAPI/doc parity evidence.
- Implemented additive subset includes:
  - setup discovery: `/api/configs`, `/api/endpoints*`
  - orchestration reads: `/api/runs/{runid}/{config}/pipeline`,
    `/api/runs/{runid}/{config}/readiness`
  - schema/default discovery:
    `/api/runs/{runid}/{config}/controllers*`,
    `/api/runs/{runid}/{config}/endpoints*`
  - geospatial/output metadata:
    `/api/runs/{runid}/{config}/geospatial-metadata`,
    `/api/runs/{runid}/{config}/outputs`
- Remaining additive scope stays planned in
  `docs/schemas/rq-controller-state-contract.md` and must follow the same
  freeze/checklist/OpenAPI guard workflow.

## End-to-End Smoke Runbook
- Canonical smoke runbook for the row-8 frozen baseline:
  `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`
- Use this runbook for:
  - deterministic pre-smoke contract/guard regression checks,
  - manual end-to-end API surface smoke sequence (`/api/configs` through
    run-scoped controller-state endpoints and outputs).
- Smoke-runbook contract requirements:
  - pass/fail assertions MUST be based on command exit status and contract-shape
    checks, not hard-coded historical pass counts;
  - expected test-count strings MAY be reported as examples but MUST NOT be the
    correctness gate;
  - endpoint-call evidence MUST record method/path/status with UTC timestamps.
