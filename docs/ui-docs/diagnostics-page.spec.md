# WEPPcloud Diagnostics Page Specification
> Defines the `/diagnostics/` page for validating browser/runtime prerequisites needed by WEPPcloud.
> See also: `docs/schemas/weppcloud-csrf-contract.md`, `docs/schemas/weppcloud-session-contract.md`, `services/status2/README.md`, `services/preflight2/README.md`.

## 1. Goals
- Provide a single operator/user-facing page that reports whether the current browser can run WEPPcloud reliably.
- Separate hard blockers (cannot proceed) from degraded capabilities (can proceed with limitations).
- Produce a structured JSON report that can be copied into bug reports.

## 2. Route and Rendering Contract
- Route: `GET /diagnostics/` on `weppcloud_site_bp`.
- External URL behind Caddy: `/weppcloud/diagnostics/`.
- Template base: `base_pure.htm` (inherits CSRF meta tag and site-prefix data attrs).
- `sitePrefix` for API calls must be read from `document.body.dataset.sitePrefix` (fallback `""`), matching existing WEPPcloud prefix handling.
- Must include `<noscript>` fallback that marks JavaScript support as a blocking failure.
- Response headers should disable caching (`Cache-Control: no-store`).

## 2.1 UI Conventions and Standards (Mandatory)
- The diagnostics page MUST follow existing WEPPcloud UI conventions and standards from `docs/ui-docs/ui-style-guide.md`.
- Layout and component composition SHOULD use established WEPPcloud patterns/macros (for example control shell, status/alert patterns, token-based spacing and typography) instead of ad-hoc markup.
- Styling MUST use existing design tokens/classes from the shared UI system (`ui-foundation.css`, theme tokens); avoid one-off inline visual styling except for narrowly scoped functional fallbacks.
- Accessibility and interaction semantics (headings, labels, status messaging, keyboard usability, ARIA where needed) MUST align with the style guide and current WEPPcloud component conventions.
- Diagnostic severity presentation (`blocker`, `degraded`, `info`) SHOULD reuse existing status/alert visual language so diagnostics remains visually consistent with the rest of WEPPcloud.

## 3. Required Checks

### 3.1 Blocking Checks
- JavaScript execution: page script loads and runs.
- Browser API baseline: `fetch`, `Promise`, `CustomEvent`, `URL`, `URLSearchParams`, `FormData`.
- Cookie write/read/delete probe (first-party cookie support).
- Authenticated-session heartbeat (only when authenticated):
  - `POST ${sitePrefix}/api/auth/session-heartbeat`
  - `credentials: same-origin`
  - send `X-CSRFToken` from `<meta name="csrf-token">`
  - pass on HTTP 200 with JSON payload `{"ok": true, ...}`
- RQ-engine token mint endpoint (only when authenticated):
  - `POST ${sitePrefix}/api/auth/rq-engine-token`
  - `credentials: same-origin`
  - send `X-CSRFToken` from `<meta name="csrf-token">`
  - same-origin policy enforced by server
  - pass on HTTP 200 with JSON containing `token` (token value must not be displayed)
  - expected explicit failure modes:
    - `400` for CSRF failures
    - `401` for unauthenticated session
    - `403` for same-origin enforcement failures

### 3.2 Degraded-Mode Checks
- `window.WebSocket` availability.
- Status websocket connectivity:
  - connect to `/weppcloud-microservices/status/<diagRunId>:diagnostics`
  - send `{"type":"init"}`
  - reply `{"type":"pong"}` to server `ping`
  - pass if socket opens and remains healthy for probe window
- Preflight websocket connectivity:
  - connect to `/weppcloud-microservices/preflight/<diagRunId>`
  - send `{"type":"init"}`
  - reply `{"type":"pong"}`
  - pass if socket opens and receives at least one `{"type":"preflight", ...}` payload
- Service health reachability:
  - `/weppcloud-microservices/status/health`
  - `/weppcloud-microservices/preflight/health`

### 3.3 Informational Checks
- `localStorage` write/read/delete.
- `AbortController` availability.
- User agent advisory (for example Safari websocket reliability notice).

## 4. Diagnostics Result Model
- Overall states:
  - `ready`
  - `ready_with_degraded_realtime`
  - `not_ready`
- Per-check fields:
  - `id`
  - `title`
  - `severity` (`blocker|degraded|info`)
  - `status` (`pass|fail|warn|skipped`)
  - `evidence` (short human-readable detail)
  - `fix_hint` (actionable remediation)
- Provide a `Copy JSON` action for the full report.
- Report must not include secrets (JWT values, cookie values, auth headers).

## 5. `diagRunId` Contract (Status + Preflight)

### 5.1 Exact Requirements
- `diagRunId` is used in both websocket probes and must satisfy both services:
  - preflight run id regex: `^[A-Za-z0-9_.;-]+$`
  - status `<runid>:<channel>` left side regex: `^[A-Za-z0-9_.;-]+$`
- `diagRunId` must **not** include `:` because status uses `:` as run/channel delimiter.
- `diagRunId` should be URI-encoded with `encodeURIComponent` before building URLs.

### 5.2 Recommended Format
- Recommended format:
  - `diag-<epochSeconds>-<randomBase36>`
  - example: `diag-1776723456-k8r3m1`
- Character set recommendation:
  - `[A-Za-z0-9_.-]` (subset of allowed set; avoids edge cases)
- Length recommendation:
  - <= 64 chars

### 5.3 Lifecycle and Semantics
- Generate one `diagRunId` per page load.
- Reuse that same value for both status and preflight probes in that run.
- No existing WEPP run directory or NoDb state is required:
  - status2 accepts any valid `<runid>:<channel>` and can still ping/pong without published status messages.
  - preflight2 calls `HGETALL <runid>`; missing hash yields an empty/default checklist payload (still valid for connectivity testing).

## 6. Status and Preflight Probe Details

### 6.1 Status Probe (`status2`)
- URL:
  - `${wsProtocol}//${location.host}/weppcloud-microservices/status/${encodeURIComponent(diagRunId)}:diagnostics`
- `wsProtocol` must follow page protocol:
  - `wss:` when page is `https:`
  - `ws:` when page is `http:`
- Probe pass criteria:
  - connection opens
  - at least one server `ping` is observed and replied to with `pong`
  - no immediate close/error during probe interval
- Normative timing:
  - probe window MUST be at least `20000 ms`
  - on first failure, perform one reconnect retry before marking degraded
- Notes:
  - this validates transport and keepalive.
  - it does not prove Redis publish fan-out unless a test message is injected.

### 6.2 Preflight Probe (`preflight2`)
- URL:
  - `${wsProtocol}//${location.host}/weppcloud-microservices/preflight/${encodeURIComponent(diagRunId)}`
- Probe pass criteria:
  - connection opens
  - server `ping` handled via `pong`
  - at least one `type=preflight` frame is received
- Normative timing:
  - probe window MUST be at least `20000 ms`
  - on first failure, perform one reconnect retry before marking degraded
- Expected payload for non-existent run id:
  - checklist map with mostly `false` values and optional empty `lock_statuses`.

## 7. Optional Data-Path Validation (Recommended Phase 2)
- Add a server-side diagnostics helper endpoint that publishes one known status message to Redis DB 2 for `${diagRunId}:diagnostics`.
- Browser waits for that exact message on the status websocket.
- This validates end-to-end Redis pub/sub relay, not just websocket transport.

## 8. Bandwidth Test Feasibility

### 8.1 Can we implement one?
- Yes, but it should be an informational network-quality probe, not a blocker.

### 8.2 Async Endpoint Requirement (Mandatory)
- Bandwidth probes must hit an async service endpoint, not Flask `weppcloud` routes.
- Rationale: avoid tying up Gunicorn/Flask worker threads with large request/response bodies.
- Preferred host surface: `query-engine` (`/query-engine/*`) because it is already an async Starlette service behind Caddy.

### 8.3 Recommended Endpoint Shape
- Implement same-origin download/upload throughput probes on `query-engine`:
  - `GET /query-engine/diagnostics/bandwidth/download?bytes=<n>`
  - `POST /query-engine/diagnostics/bandwidth/upload`
- Endpoint behavior:
  - download route returns deterministic bytes with explicit `Content-Length`.
  - upload route accepts raw bytes and returns JSON containing received byte count.
  - both routes should set `Cache-Control: no-store`.
- Measure:
  - transfer size
  - elapsed time
  - estimated Mbps
  - RTT estimate from a tiny request

### 8.4 Guardrails
- Keep payload sizes bounded (for example 256 KiB, 1 MiB, optional 4 MiB max).
- Run once per page load; no continuous load generation.
- Skip automatically when `Save-Data` is enabled.
- Clearly label as approximate and environment-dependent (VPN, Wi-Fi, browser throttling, proxy effects).
- Apply IP/session rate limits to prevent abuse.
- Enforce per-request timeouts and bounded concurrent probe requests.

### 8.5 Websocket-Specific Throughput
- A websocket bandwidth test is possible only with a server-assisted publisher/echo path.
- Without that backend helper, diagnostics can only verify websocket connect/keepalive behavior.

## 9. Security and Privacy
- Do not render secrets in UI or JSON report.
- Keep mutating checks same-origin and CSRF-compliant.
- Avoid cross-origin probes and third-party network calls from diagnostics.

## 10. Acceptance Criteria
- `/diagnostics/` loads without authentication.
- JS-disabled browser shows explicit blocker state.
- Authenticated session performs heartbeat and token checks with clear pass/fail.
- Unauthenticated users receive `status=skipped` for auth-only checks (`session-heartbeat`, `rq-engine-token`) and are evaluated only on non-auth checks.
- Websocket probes report degraded state when status/preflight backends are unavailable.
- Websocket probes use a normative probe window and one reconnect retry before failing.
- Bandwidth test endpoints exist only on async service routes under `/query-engine/diagnostics/bandwidth/*` and do not exist under `/weppcloud/*`.
- Bandwidth endpoints enforce payload caps, timeouts, rate limits, and bounded concurrency.
- Bandwidth endpoint implementation is streaming/non-buffering for large payloads and does not consume Flask/Gunicorn worker capacity.
- Diagnostics UI uses existing WEPPcloud UI conventions from `docs/ui-docs/ui-style-guide.md` and does not introduce a conflicting visual system.
- JSON report is copyable and redacted for sensitive values.
