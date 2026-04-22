# Agent Prompt: WP-06 (Bandwidth UI Integration, Informational)

Execute **WP-06** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Implement client-side bandwidth diagnostics checks on `/diagnostics/` using the existing query-engine bandwidth endpoints from WP-05.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-06)
- `docs/ui-docs/diagnostics-page.spec.md` (Sections 4, 8, 10)
- `docs/ui-docs/ui-style-guide.md`
- `wepppy/query_engine/app/server.py` (existing bandwidth endpoint contract)

## Scope

Add informational bandwidth checks to the diagnostics report pipeline:

1. RTT probe (lightweight request)
2. Download probe (bounded bytes)
3. Upload probe (bounded bytes)

These checks must integrate into the existing diagnostics check model and UI/report rendering.

## Endpoint Contract (Use As-Is)

- `GET /query-engine/diagnostics/bandwidth/download?bytes=<n>`
- `POST /query-engine/diagnostics/bandwidth/upload`

Do not change endpoint behavior in this WP; consume the current contract.

## Required Behavior

- Run probes once per page load.
- Use bounded defaults (recommended: `256 KiB` download and `256 KiB` upload max test payload).
- Compute approximate Mbps using transferred bytes and elapsed time.
- Include reproducibility details in evidence (bytes, elapsed ms, derived Mbps).
- Respect Save-Data:
  - if `navigator.connection.saveData === true`, mark bandwidth checks `status=skipped` with explicit evidence.
- Mark bandwidth checks as `info` (or `warn` where appropriate), never `blocker`.
- Non-2xx responses from bandwidth endpoints must degrade only these checks, not global blocker readiness.
- Keep evidence text redaction-safe (no secrets, no auth headers, no token/cookie values).
- Use client-side timeout bounds so probes cannot hang diagnostics indefinitely.

## UI/UX Constraints

- Follow `docs/ui-docs/ui-style-guide.md` conventions.
- Reuse existing diagnostics UI patterns (cards/status chips/check list/report preview).
- Label bandwidth metrics as approximate/environment-dependent.

## Write Scope (Allowed Files)

- `wepppy/weppcloud/static/js/diagnostics/*` (new/updated bandwidth probe module and registration)
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm` (only if script wiring/additional UI hints are required)
- `wepppy/weppcloud/controllers_js/__tests__/diagnostics_*.test.js` (new/updated diagnostics JS tests)
- `tests/weppcloud/routes/test_diagnostics_page.py` (template wiring assertions only)

## Out of Scope

- Query-engine endpoint implementation changes (WP-05 already owns that).
- Realtime websocket/auth behavior changes from WP-03/WP-04.
- Non-diagnostics route/template refactors.
- Docs/spec/plan edits unless a contract contradiction is discovered.

## Acceptance Criteria

- Diagnostics report includes bandwidth checks with deterministic IDs/order.
- Save-Data skip path works and emits valid `skipped` results.
- Successful probes show bytes, elapsed time, and approximate Mbps.
- Failure paths show actionable hints and remain informational.
- Overall diagnostics rollup behavior remains contract-compliant (`ready`, `ready_with_degraded_realtime`, `not_ready`).

## Validation Commands

Run and report exact results:

- `wctl run-npm lint`
- `wctl run-npm test -- diagnostics`
- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py --maxfail=1`
- `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`

## Handoff Format

Report:

- files changed
- check IDs added and ordering behavior
- probe defaults (sizes/timeouts) and Save-Data behavior
- tests run + results
- residual risks

Do not commit or push.
