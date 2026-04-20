# Agent Prompt: WP-02 (Client Diagnostics Engine: Core + Report)

Execute **WP-02** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Implement the diagnostics client core engine that runs non-auth/non-websocket checks and produces the canonical report model + copy-json action.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-02)
- `docs/ui-docs/diagnostics-page.spec.md` (Sections 2, 3.1 baseline subset, 3.3, 4)
- `docs/ui-docs/ui-style-guide.md`
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm`

## Scope

1. Implement diagnostics core checks:
   - JavaScript execution sentinel
   - Browser API baseline (`fetch`, `Promise`, `CustomEvent`, `URL`, `URLSearchParams`, `FormData`)
   - Cookie write/read/delete
   - `localStorage` write/read/delete
   - `AbortController` availability
2. Implement diagnostics report model and rollup:
   - overall: `ready`, `ready_with_degraded_realtime`, `not_ready`
   - per-check fields: `id`, `title`, `severity`, `status`, `evidence`, `fix_hint`
3. Implement deterministic rendering order and a `Copy JSON` action.
4. Wire template shell to run the core engine on load.

## Required Technical Contract

- Read `sitePrefix` from `document.body.dataset.sitePrefix` with fallback `""`.
- Do not include secrets in report payload.
- Keep UI within WEPPcloud conventions/macros/tokens.
- Keep auth checks and realtime checks out of this WP (those are WP-03/WP-04).

## Write Scope (Allowed Files)

- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm`
- `wepppy/weppcloud/static/js/diagnostics/*` (new core/report files)
- `tests/weppcloud/routes/test_diagnostics_page.py` (template/render assertions)
- Optional: targeted JS tests if existing harness supports these files

## Out of Scope

- `/api/auth/session-heartbeat` and `/api/auth/rq-engine-token` probes
- status/preflight websocket probes
- query-engine bandwidth endpoints/UI

## Acceptance Criteria

- Core checks execute and render deterministic statuses.
- Report model matches spec field names and severity semantics.
- Copy JSON emits redacted report.
- Page remains usable unauthenticated.

## Validation Commands

Run and report exact results:

- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl run-pytest tests/weppcloud/routes --maxfail=1 -k diagnostics`

If `wctl` runtime services are unavailable, run local equivalent and report blocker explicitly.

## Handoff Format

Report:

- files changed
- checks implemented
- tests run + results
- assumptions and residual risks

Do not commit or push.
