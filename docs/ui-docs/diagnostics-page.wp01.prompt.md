# Agent Prompt: WP-01 (Diagnostics Route + Page Shell)

Execute **WP-01** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Implement the WEPPcloud diagnostics route and baseline page shell only.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-01)
- `docs/ui-docs/diagnostics-page.spec.md`
- `docs/ui-docs/ui-style-guide.md`
- `wepppy/weppcloud/AGENTS.md`
- `wepppy/weppcloud/routes/weppcloud_site.py`

## Scope

1. Add `GET /diagnostics/` on `weppcloud_site_bp`.
2. Return a diagnostics template that extends `base_pure.htm`.
3. Build page shell using existing WEPPcloud UI conventions/macros/tokens (no new design system).
4. Include explicit `<noscript>` blocker content.
5. Set no-store caching headers for this route response.
6. Add route/template tests under `tests/weppcloud/routes/`.

## Hard Constraints

- Do not implement WP-02+ logic (no check engine, no websocket probes, no bandwidth test logic).
- Keep this work limited to route + template shell + tests.
- Do not modify query-engine files.
- Keep changes additive and minimal.

## Write Scope (Allowed Files)

- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/templates/**` (new diagnostics template)
- `tests/weppcloud/routes/**` (new diagnostics route/template tests)

## Out of Scope

- Any query-engine endpoint work.
- Any diagnostics check execution logic.
- Any docs/spec/plan editing.

## Acceptance Criteria

- `/diagnostics/` is routed and renders successfully for unauthenticated users.
- Template extends `base_pure.htm` and follows style guide conventions.
- `<noscript>` blocker is present and clear.
- Response includes `Cache-Control: no-store`.
- Tests pass and cover route render + no-store header.

## Validation Commands

Run and report exact results:

- `wctl run-pytest tests/weppcloud/routes --maxfail=1 -k diagnostics`

## Handoff Format

Report:

- files changed
- tests run + results
- any assumptions
- residual risks

Do not commit or push.
