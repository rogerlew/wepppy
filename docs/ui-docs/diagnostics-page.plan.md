# WEPPcloud Diagnostics Page Implementation Plan and Orchestration Board

> Plan companion to `docs/ui-docs/diagnostics-page.spec.md`.
> This document decomposes implementation into work-packages that can be executed end-to-end by agents and tracked as a live orchestration board.

## 1. Purpose

Deliver `/diagnostics/` as a first-class WEPPcloud page that verifies runtime prerequisites (JavaScript, cookie/session/auth, websocket realtime, and optional network quality) and reports results in a clear UI plus copyable JSON report.

This plan is intentionally execution-oriented: each work-package has a bounded scope, explicit dependencies, expected artifacts, validation commands, and completion gates.

## 2. Non-Negotiable Requirements

- Route and page contract must follow `docs/ui-docs/diagnostics-page.spec.md`.
- UI must follow existing WEPPcloud conventions from `docs/ui-docs/ui-style-guide.md` and reuse existing macros/tokens/patterns (`base_pure.htm`, control/card/status patterns, WC token classes).
- No speculative Flask wrappers for async diagnostics: bandwidth endpoints must live on query-engine (`/query-engine/*`), not `/weppcloud/*`, to avoid tying up Flask/Gunicorn workers.
- Diagnostics JSON report must redact secrets (no cookie values, no JWTs, no auth headers).
- Auth checks must stay same-origin and CSRF-compliant.

## 3. Exact `diagRunId` and WebSocket Requirements (Normative)

This section captures the exact currently enforced service constraints from code:

- Preflight2 run ID regex: `^[A-Za-z0-9_.;-]+$` (`services/preflight2/internal/server/server.go`).
- Status2 websocket path regex: `^[A-Za-z0-9_.;-]+:[A-Za-z0-9_.-]+$` (`services/status2/internal/server/server.go`).
- Diagnostics status channel name: `diagnostics` (fits `[A-Za-z0-9_.-]+`).
- Therefore `diagRunId` must satisfy:
  - allowed chars `[A-Za-z0-9_.;-]`
  - must not contain `:`
  - should be URI-encoded via `encodeURIComponent` before URL composition
- Recommended generated format:
  - `diag-<epochSeconds>-<randomBase36>`
  - example: `diag-1776723456-k8r3m1`

Normative websocket probe behavior:

- Status URL:
  - `${wsProtocol}//${location.host}/weppcloud-microservices/status/${encodeURIComponent(diagRunId)}:diagnostics`
- Preflight URL:
  - `${wsProtocol}//${location.host}/weppcloud-microservices/preflight/${encodeURIComponent(diagRunId)}`
- Client should send `{"type":"init"}` after open.
- Client should answer service `ping` frames with `{"type":"pong"}`.
- Probe window must be at least 20 seconds.
- First failure gets one reconnect retry before final degraded failure.

## 4. Orchestration Board

Status legend:

- `READY` not started.
- `ACTIVE` currently being implemented.
- `REVIEW` implementation complete, awaiting review/QA/security disposition.
- `DONE` accepted and merged.
- `BLOCKED` waiting on prerequisite or external dependency.

| WP | Status | Scope | Depends On | Suggested Agent Role | Primary Deliverables |
| --- | --- | --- | --- | --- | --- |
| WP-00 | DONE | Contract freeze and implementation map | None | `explorer` | Locked interfaces, endpoint contracts, acceptance matrix |
| WP-01 | DONE | WEPPcloud route + diagnostics page shell | WP-00 | `worker` | `/diagnostics/` route, template, no-store headers, `<noscript>` blocker |
| WP-02 | DONE | Client diagnostics engine (browser/storage/report) | WP-01 | `worker` | JS check runner, severity model, copy JSON |
| WP-03 | DONE | Auth/session checks (`session-heartbeat`, `rq-engine-token`) | WP-01 | `worker` | Auth probe module with CSRF + same-origin behaviors |
| WP-04 | DONE | Realtime probes (status/preflight websocket) | WP-01 | `worker` | `diagRunId` generation, status/preflight probe and retry logic |
| WP-05 | DONE | Query-engine async bandwidth endpoints | WP-00 | `query_engine_refactorer` | `GET/POST /query-engine/diagnostics/bandwidth/*` with guards |
| WP-06 | DONE | Bandwidth UI integration (informational only) | WP-02, WP-05 | `worker` | Client bandwidth runner + Save-Data skip + UI surfacing |
| WP-07 | DONE | Test, accessibility, docs, and rollout closeout | WP-02..WP-06 | `test_guardian` + `reviewer` + `security_reviewer` | Regression tests, lint/test evidence, final docs updates |

## 5. Parallelization and Execution Order

Execution waves:

- Wave A: `WP-00`.
- Wave B (parallel): `WP-01` and `WP-05` once WP-00 is done.
- Wave C (parallel): `WP-02`, `WP-03`, `WP-04` after WP-01.
- Wave D: `WP-06` after WP-02 and WP-05.
- Wave E: `WP-07` after all implementation WPs are complete.

Critical path is `WP-00 -> WP-01 -> (WP-02/WP-03/WP-04) -> WP-06 -> WP-07`.

## 6. Work-Packages

## WP-00: Contract Freeze and Implementation Map

Objective:

- Freeze all diagnostics interfaces before code edits to avoid churn across Flask, query-engine, and UI.

Scope:

- Confirm route-level contracts in `docs/ui-docs/diagnostics-page.spec.md`.
- Confirm exact status/preflight websocket constraints from service code.
- Confirm auth endpoint behavior for:
  - `POST /api/auth/session-heartbeat`
  - `POST /api/auth/rq-engine-token`
- Confirm query-engine integration boundary for async bandwidth endpoints.

Artifacts:

- Updated this plan with any discovered contract corrections.
- Contract matrix captured in this plan under "WP-00 Contract Matrix (Frozen 2026-04-20)".

Resolved WP-00 clarifications:

- `/diagnostics/` is currently a frozen contract target for `WP-01`; no route implementation exists yet.
- The acceptance contract matrix is maintained in this plan (not deferred to PR description text).

### WP-00 Contract Matrix (Frozen 2026-04-20)

| Endpoint / Check | Expected Behavior (Frozen Contract) | Source Evidence | Decision |
| --- | --- | --- | --- |
| `/diagnostics/` route contract | Add `GET /diagnostics/` on `weppcloud_site_bp`; external URL remains `/weppcloud/diagnostics/` via Caddy prefix handling. | `weppcloud_site_bp` blueprint exists in `wepppy/weppcloud/routes/weppcloud_site.py` (`24`); Caddy strips `/weppcloud` then proxies to Flask (`docker/caddy/Caddyfile:218`, `230`, `267`). No current diagnostics route declaration found in `wepppy/weppcloud/routes/*.py` (code search during WP-00). | Contract accepted as target for `WP-01` (implementation still pending). |
| `POST /api/auth/session-heartbeat` | Requires authenticated session; blocks cross-origin requests; updates session heartbeat and returns `{"ok": true, "heartbeat_at": <int>}` on success. | Route logic and statuses in `wepppy/weppcloud/routes/weppcloud_site.py:724`, `726`, `730`, `735`, `738`; same-origin helper in `wepppy/weppcloud/routes/weppcloud_site.py:351`; CSRF globally enabled in `wepppy/weppcloud/app.py:70` with JSON `400` CSRF error contract in `wepppy/weppcloud/app.py:125`; route is not CSRF-exempt (`wepppy/weppcloud/routes/weppcloud_site.py:1177`, `1179`; exemption wiring in `wepppy/weppcloud/app.py:505`). | Contract confirmed; no spec change needed. |
| `POST /api/auth/rq-engine-token` | Requires authenticated session; blocks cross-origin requests; returns `{"token": "<jwt>"}` on `200`; expected explicit failures include `400` (CSRF), `401` (auth), `403` (same-origin). | Route logic and statuses in `wepppy/weppcloud/routes/weppcloud_site.py:376`, `378`, `382`, `400`; same-origin helper in `wepppy/weppcloud/routes/weppcloud_site.py:351`; CSRF enable/error wiring in `wepppy/weppcloud/app.py:70`, `125`; only operator-token route is exempt (`wepppy/weppcloud/routes/weppcloud_site.py:1179`). | Contract confirmed; no spec change needed. |
| Status websocket path + regex constraints | Browser path remains `/weppcloud-microservices/status/<runid>:<channel>`; service accepts only `GET`; path must match `^[A-Za-z0-9_.;-]+:[A-Za-z0-9_.-]+$`. | Caddy status proxy path in `docker/caddy/Caddyfile:36`; regex and method checks in `services/status2/internal/server/server.go:25`, `90`, `95`, `101`; `init`/`pong` handling in `services/status2/internal/server/server.go:188`. | Contract confirmed and frozen. |
| Preflight websocket path + regex constraints | Browser path remains `/weppcloud-microservices/preflight/<runid>`; service accepts only `GET`; run id must match `^[A-Za-z0-9_.;-]+$`. | Caddy preflight proxy path in `docker/caddy/Caddyfile:40`; regex and method checks in `services/preflight2/internal/server/server.go:25`, `94`, `98`, `104`; `init`/`pong` handling in `services/preflight2/internal/server/server.go:231`. | Contract confirmed and frozen. |
| `diagRunId` rules + channel shape | `diagRunId` must satisfy `[A-Za-z0-9_.;-]+` and exclude `:`; status channel token must satisfy `[A-Za-z0-9_.-]+`; `diagnostics` is valid channel name. | Preflight run-id regex in `services/preflight2/internal/server/server.go:25`; status path regex in `services/status2/internal/server/server.go:25`. | Contract confirmed and frozen. |
| Query-engine-only boundary for async bandwidth probes | New diagnostics bandwidth endpoints must be implemented on query-engine routes under `/query-engine/*`, not Flask `/weppcloud/*`. | Caddy query-engine proxy in `docker/caddy/Caddyfile:104`; query-engine route list in `wepppy/query_engine/app/server.py:599`; Flask fallback path remains `/weppcloud/*` to weppcloud app in `docker/caddy/Caddyfile:218`, `267`. | Boundary confirmed and frozen for `WP-05`; no Flask/query-engine runtime changes in `WP-00`. |

Validation gate:

- No code changes required; this is complete when all downstream WPs can cite stable contracts.

## WP-01: WEPPcloud Route and Diagnostics Shell

Objective:

- Add the diagnostics page route and baseline UI shell with WEPPcloud visual/interaction conventions.

Implementation targets:

- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/templates/...` (new diagnostics template)
- `tests/weppcloud/routes/` (new/updated route-template tests)

Requirements:

- Route: `GET /diagnostics/` on `weppcloud_site_bp`.
- External URL via Caddy path handling: `/weppcloud/diagnostics/`.
- Template extends `base_pure.htm`.
- Reuse existing WC component patterns/macros (`control_shell` or `card_shell`, status/alert conventions).
- Include `<noscript>` content that explicitly reports JS as a blocker.
- Response must include `Cache-Control: no-store`.

Acceptance criteria:

- Unauthenticated user can load the diagnostics page.
- Page visually matches existing WEPPcloud style language.
- Route and template tests pass.

Validation commands:

- `wctl run-pytest tests/weppcloud/routes --maxfail=1 -k diagnostics`

## WP-02: Client Diagnostics Engine (Browser/Storage/Report)

Objective:

- Implement deterministic client-side checks for browser primitives and stateful storage, and aggregate into a structured report.

Implementation targets:

- `wepppy/weppcloud/static/js/...` or `wepppy/weppcloud/controllers_js/...` (choose one approach and keep consistent)
- diagnostics template script wiring
- JS unit tests under existing frontend test conventions

Checks in scope:

- JS execution sentinel.
- Browser API baseline: `fetch`, `Promise`, `CustomEvent`, `URL`, `URLSearchParams`, `FormData`.
- Cookie write/read/delete probe.
- `localStorage` write/read/delete probe.
- `AbortController` availability.

Result model (required):

- Overall status: `ready`, `ready_with_degraded_realtime`, `not_ready`.
- Per-check fields: `id`, `title`, `severity`, `status`, `evidence`, `fix_hint`.
- `Copy JSON` action that emits fully redacted diagnostics report.

Acceptance criteria:

- Checks render in deterministic order.
- Severity and overall rollup logic match spec.
- Copy JSON output excludes secrets.

Validation commands:

- `wctl run-npm lint`
- `wctl run-npm test`

## WP-03: Auth/Session Probe Module

Objective:

- Add auth-aware checks that validate active session and token mint path without leaking secrets.

Implementation targets:

- Diagnostics client probe module + tests.
- Any minor route-template data plumbing for CSRF token/site prefix.

Checks in scope:

- `POST ${sitePrefix}/api/auth/session-heartbeat`
- `POST ${sitePrefix}/api/auth/rq-engine-token`

Required behavior:

- Include `credentials: "same-origin"`.
- Send `X-CSRFToken` from `<meta name="csrf-token">`.
- Treat unauthenticated runs as `skipped` (not hard fail) per spec.
- Do not render token value in UI/report.
- Surface explicit status mapping for expected error classes (`400`, `401`, `403`).

Acceptance criteria:

- Authenticated session returns pass/fail with clear evidence.
- Anonymous session produces `skipped` for auth-only checks.
- CSRF or origin failures are surfaced with actionable hints.

Validation commands:

- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py --maxfail=1`
- `wctl run-npm test`

## WP-04: Realtime Probe Module (Status + Preflight)

Objective:

- Validate websocket realtime path health against status2 and preflight2 using one generated `diagRunId`.

Implementation targets:

- Diagnostics client probe module + tests.

Required implementation:

- Generate one `diagRunId` per page load and reuse for both probes.
- Status probe channel: `${diagRunId}:diagnostics`.
- Preflight probe run ID: `${diagRunId}`.
- Send `init`, handle `ping` with `pong`.
- Enforce 20-second probe windows.
- Retry once on first failure before final degraded result.
- Mark checks as `degraded` severity failures, not blockers.

Pass criteria:

- Status probe passes when socket opens and remains healthy through probe window.
- Preflight probe passes when socket opens and at least one `type=preflight` frame is received.

Acceptance criteria:

- Probe output clearly differentiates transport failure vs timeout vs missing frames.
- `diagRunId` is spec-compliant and URL-safe.

Validation commands:

- `wctl run-npm test`
- Optional integration confirmation against live dev stack websocket services.

## WP-05: Query-Engine Async Bandwidth Endpoints

Objective:

- Implement bounded, async network-quality probes in query-engine so bandwidth tests do not consume Flask worker capacity.

Implementation targets:

- `wepppy/query_engine/app/server.py` (or extracted diagnostics route module mounted there)
- `wepppy/query_engine/app/server.pyi` if signatures change
- `tests/query_engine/test_server_routes.py` (or new dedicated test module)

Required endpoints:

- `GET /query-engine/diagnostics/bandwidth/download?bytes=<n>`
- `POST /query-engine/diagnostics/bandwidth/upload`

Required controls:

- Hard payload caps (for example max 4 MiB).
- Deterministic `Content-Length` for download probe.
- `Cache-Control: no-store`.
- Per-request timeout behavior.
- Bounded concurrency (service-level semaphore) and simple abuse guard (IP/session scoped limiter).
- JSON response for upload probe with received byte count and timing metadata.

Acceptance criteria:

- Endpoints are reachable via query-engine path only.
- Endpoints reject out-of-bounds payload sizes with clear 4xx responses.
- Endpoint handlers are async/non-blocking and keep memory bounded.

Validation commands:

- `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`
- `wctl run-pytest tests/query_engine --maxfail=1`

## WP-06: Bandwidth UI Integration (Informational)

Objective:

- Add optional bandwidth/latency diagnostics to the UI using WP-05 endpoints.

Implementation targets:

- Diagnostics client module + template rows for bandwidth checks.

Required behavior:

- Run lightweight RTT + download/upload probes once per page load.
- Compute approximate Mbps from bytes and elapsed time.
- Respect `Save-Data` and auto-skip when enabled.
- Mark as `info` or `warn`, never blocker.
- Clearly label metrics as approximate/environment-dependent.

WP-06 frozen endpoint contract (from current query-engine implementation):

- Download probe endpoint:
  - `GET /query-engine/diagnostics/bandwidth/download?bytes=<n>`
  - default size: `262144` bytes when `bytes` omitted
  - maximum size: `4194304` bytes
  - success: `200` streaming octet response with explicit `Content-Length` and `Cache-Control: no-store`
  - expected failures: `400` invalid bytes, `413` probe too large, `429` rate-limited, `503` busy
- Upload probe endpoint:
  - `POST /query-engine/diagnostics/bandwidth/upload`
  - success JSON includes `ok`, `bytes_received`, `elapsed_ms`, `max_bytes`
  - expected failures: `403` cross-origin blocked, `408` upload timeout, `413` upload too large, `429` rate-limited, `503` busy
- Both endpoints enforce same-origin and anti-abuse controls server-side; client must treat non-2xx as informational degradation, not blocker.

WP-06 implementation constraints (client):

- Probe calls should be same-origin and root-relative under `/query-engine/...`.
- Do not surface secrets/tokens/cookies in evidence text.
- Time-bound UI probe execution (client timeout) so diagnostics page does not hang on network stalls.
- Keep probe sizes lightweight by default (for example: RTT tiny request, download `256 KiB`, upload `256 KiB`).
- Skip bandwidth probes when `navigator.connection.saveData === true` with explicit `status=skipped` evidence.

Acceptance criteria:

- Bandwidth section can be skipped gracefully and still produces valid report.
- Results include probe sizes and elapsed times for reproducibility.
- Overall diagnostics rollup remains governed by blocker/degraded checks; bandwidth checks must not force `not_ready`.
- UI output follows existing WEPPcloud status chip + card conventions from `ui-style-guide.md`.

Validation commands:

- `wctl run-npm lint`
- `wctl run-npm test -- diagnostics`
- `wctl run-npm test`
- `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`

## WP-07: Validation, Accessibility, Security Review, and Closeout

Objective:

- Run full quality gates, disposition findings, and close implementation with documentation updates.

Scope:

- Route/tests and frontend lint/test.
- Accessibility and UI convention compliance pass against `ui-style-guide.md`.
- Security review of new endpoints and redaction rules.
- Final documentation touch-ups in spec/plan if implementation details changed.

WP-07 execution packet (must deliver all):

- Validation evidence bundle:
  - command log with exact commands and pass/fail outcomes
  - failed-command diagnosis and disposition (if any)
- Accessibility review notes for diagnostics page:
  - heading/landmark structure
  - status/alert semantics
  - keyboard and focus behavior for Copy JSON/report preview interactions
  - concise remediation list if any violations are found
- Security review notes:
  - diagnostics report redaction verification
  - same-origin enforcement expectations for auth and bandwidth probes
  - timeout/bounded-resource checks for realtime/bandwidth diagnostics
- Documentation closeout:
  - update WP statuses in this plan to final dispositions
  - if behavior changed from spec, update `docs/ui-docs/diagnostics-page.spec.md` in same change set

Required checks:

- `wctl run-pytest tests/weppcloud --maxfail=1`
- `wctl run-pytest tests/query_engine --maxfail=1`
- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl doc-lint --path docs/ui-docs/diagnostics-page.spec.md --path docs/ui-docs/diagnostics-page.plan.md`

Recommended targeted confidence checks (run before full sweeps):

- `wctl run-npm test -- diagnostics`
- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py --maxfail=1`
- `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`

Disposition criteria:

- All blockers fixed.
- Degraded/info known limitations documented.
- Security review confirms no sensitive leakage and bounded resource usage.
- Accessibility review confirms diagnostics UI aligns with existing WEPPcloud conventions or includes explicit accepted follow-ups.

### WP-07 Closeout Snapshot (2026-04-21)

Final disposition: `DONE`.

Validation summary:

- ✅ `wctl run-npm test -- diagnostics`
- ✅ `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py --maxfail=1`
- ✅ `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`
- ✅ `wctl run-pytest tests/weppcloud --maxfail=1`
- ✅ `wctl run-pytest tests/query_engine --maxfail=1`
- ✅ `wctl run-npm lint`
- ✅ `wctl run-npm test`
- ✅ `wctl doc-lint --path docs/ui-docs/diagnostics-page.spec.md --path docs/ui-docs/diagnostics-page.plan.md`

Accessibility disposition:

- Added a screen-reader heading (`<h1 class="wc-sr-only">`) for page-level heading hierarchy.
- Added live-region semantics (`role="status"`, `aria-live="polite"`, `aria-atomic="true"`) for copy feedback updates.
- `<noscript>` blocker copy, keyboard behavior for `Copy JSON`, and native keyboard support for `<details>/<summary>` report preview were verified as conformant.

Security disposition:

- Report redaction verified in `report.js` for authorization/token/cookie markers and JWT-like payloads.
- Auth probes remain same-origin + CSRF aligned (`credentials: "same-origin"` + `X-CSRFToken`; server enforces same-origin and CSRF contract).
- Realtime probes are time-bounded (minimum 20s windows) with a single reconnect retry and degraded classification on failure.
- Bandwidth probes remain informational-only client-side and server-side bounded by request caps, per-request timeout, semaphore concurrency guard, and rate limiting.

## 7. Handoff Contract Per Work-Package

Each WP completion handoff must include:

- files changed
- tests run (exact commands)
- observed results
- residual risks
- explicit disposition (`accepted`, `accepted-with-followup`, `rejected`)

## 8. Risks and Mitigations

- Websocket probes may fail intermittently in hostile networks.
  - Mitigation: 20-second window + one retry + explicit degraded classification.
- Bandwidth probes can be abused for traffic amplification.
  - Mitigation: strict payload caps, rate/concurrency guardrails, request timeouts.
- Styling drift from WEPPcloud conventions.
  - Mitigation: macro/token reuse and dedicated UI conformance review in WP-07.
- Auth endpoint checks may produce noisy failures for anonymous users.
  - Mitigation: auth-aware `skipped` semantics and concise remediation text.

## 9. Execution Notes for Agent Orchestration

- Keep a single active owner per WP; do not overlap write scopes.
- Use review agents only after implementation WP reaches `REVIEW` state.
- Do not start `WP-06` before both `WP-02` and `WP-05` are accepted.
- If implementation deviates from this plan/spec, update both docs in the same change set before handoff.

## 10. Dispatch Artifacts

- Wave 1 prompts:
  - `docs/ui-docs/diagnostics-page.wp01.prompt.md`
  - `docs/ui-docs/diagnostics-page.wp05.prompt.md`
  - `docs/ui-docs/diagnostics-page.wave1.board.md`
- Wave C prompts:
  - `docs/ui-docs/diagnostics-page.wp02.prompt.md`
  - `docs/ui-docs/diagnostics-page.wp03.prompt.md`
  - `docs/ui-docs/diagnostics-page.wp04.prompt.md`
  - `docs/ui-docs/diagnostics-page.wavec.board.md`
- Wave D prompts:
  - `docs/ui-docs/diagnostics-page.wp06.prompt.md`
- Wave E prompts:
  - `docs/ui-docs/diagnostics-page.wp07.prompt.md`
