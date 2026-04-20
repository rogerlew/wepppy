# Agent Prompt: WP-05 (Query-Engine Async Bandwidth Endpoints)

Execute **WP-05** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Implement async, bounded query-engine bandwidth probe endpoints for diagnostics.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-05)
- `docs/ui-docs/diagnostics-page.spec.md` (Section 8)
- `wepppy/query_engine/app/server.py`
- `tests/query_engine/test_server_routes.py`

## Scope

Implement these query-engine endpoints:

- `GET /diagnostics/bandwidth/download?bytes=<n>`
- `POST /diagnostics/bandwidth/upload`

(Served under Caddy as `/query-engine/diagnostics/bandwidth/*`.)

## Required Behavior

- Async handlers only (no Flask route wrappers).
- Download route returns deterministic bytes and explicit `Content-Length`.
- Upload route accepts raw bytes and returns JSON at least including received byte count.
- Set `Cache-Control: no-store` on both endpoints.
- Enforce bounded payload sizes (max cap).
- Enforce bounded concurrency (service-level guard).
- Add abuse/time guardrails (size validation + timeout-aware behavior).
- Return clear 4xx errors for invalid/out-of-bounds requests.

## Hard Constraints

- Do not modify WEPPcloud Flask routes/templates/controllers.
- Do not add endpoints under `/weppcloud/*`.
- Keep scope to query-engine endpoints + tests.

## Write Scope (Allowed Files)

- `wepppy/query_engine/app/server.py` (or extracted query-engine app module if needed)
- `wepppy/query_engine/app/server.pyi` (if signatures/public helpers require)
- `tests/query_engine/**` (add/extend tests)

## Out of Scope

- Diagnostics page UI work.
- Docs/spec/plan edits.

## Acceptance Criteria

- Endpoints are mounted in query-engine app and reachable via query-engine pathing.
- Out-of-range byte requests fail with 4xx and structured JSON errors.
- Success responses include expected headers/body contract.
- No-store headers present.
- Targeted and broader query-engine tests pass.

## Validation Commands

Run and report exact results:

- `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`
- `wctl run-pytest tests/query_engine --maxfail=1`

## Handoff Format

Report:

- files changed
- tests run + results
- endpoint contract summary (status codes, headers, body)
- residual risks

Do not commit or push.
