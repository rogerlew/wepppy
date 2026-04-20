# Agent Prompt: WP-03 (Auth + Session Probe Module)

Execute **WP-03** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Implement diagnostics auth/session checks and integrate them into the diagnostics check registry without leaking secrets.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-03)
- `docs/ui-docs/diagnostics-page.spec.md` (Section 3.1 auth checks)
- `wepppy/weppcloud/routes/weppcloud_site.py` (auth endpoint contracts)

## Scope

Implement auth-aware checks for:

- `POST ${sitePrefix}/api/auth/session-heartbeat`
- `POST ${sitePrefix}/api/auth/rq-engine-token`

Required behavior:

- `credentials: "same-origin"`
- send `X-CSRFToken` from `<meta name="csrf-token">`
- map unauthenticated sessions to `status=skipped` for auth-only checks
- map explicit failure classes (`400`, `401`, `403`) with actionable `fix_hint`
- never render token value in UI or report JSON

## Write Scope (Allowed Files)

- `wepppy/weppcloud/static/js/diagnostics/*` (auth probe module and registration)
- `tests/weppcloud/routes/test_rq_engine_token_api.py` only if contract tests need additive coverage
- optional diagnostics route/template assertion updates if strictly required for wiring

## Out of Scope

- Core browser/storage checks (WP-02 ownership)
- WebSocket status/preflight checks (WP-04 ownership)
- query-engine bandwidth work

## Integration Contract

- Treat this WP as a plugin/module into the WP-02 diagnostics engine.
- Avoid changing WP-02-owned core check implementations.
- Keep output shape identical to diagnostics report model.

## Acceptance Criteria

- Authenticated runs produce pass/fail for heartbeat/token checks.
- Anonymous runs report these checks as `skipped`.
- No token/secret leakage to DOM or copy JSON.

## Validation Commands

Run and report exact results:

- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py --maxfail=1`
- `wctl run-npm test`

If `wctl` runtime services are unavailable, run local equivalent and report blocker explicitly.

## Handoff Format

Report:

- files changed
- status mapping table for `200/400/401/403`
- tests run + results
- residual risks

Do not commit or push.
