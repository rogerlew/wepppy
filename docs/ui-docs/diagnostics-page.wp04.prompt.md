# Agent Prompt: WP-04 (Realtime Probe Module: Status + Preflight)

Execute **WP-04** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Implement diagnostics realtime websocket checks for status2 and preflight2 using one `diagRunId` per page load.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-04)
- `docs/ui-docs/diagnostics-page.spec.md` (Sections 5 and 6)
- `services/status2/internal/server/server.go`
- `services/preflight2/internal/server/server.go`

## Scope

1. Generate one `diagRunId` per page load and reuse for both probes.
2. Validate/run status websocket probe:
   - `/weppcloud-microservices/status/<diagRunId>:diagnostics`
3. Validate/run preflight websocket probe:
   - `/weppcloud-microservices/preflight/<diagRunId>`
4. Probe behavior:
   - send `{"type":"init"}`
   - respond `{"type":"pong"}` on ping
   - probe window >= 20000ms
   - one reconnect retry on first failure
5. Report checks as degraded capability checks (not blockers).

## `diagRunId` Contract

- Allowed characters must satisfy `[A-Za-z0-9_.;-]+`
- Must not contain `:`
- URL encode with `encodeURIComponent`
- Recommended format: `diag-<epochSeconds>-<randomBase36>`

## Write Scope (Allowed Files)

- `wepppy/weppcloud/static/js/diagnostics/*` (realtime module and registration)
- optional additive diagnostics template assertions only if required for new status indicators

## Out of Scope

- Core browser/storage checks (WP-02 ownership)
- Auth/session HTTP checks (WP-03 ownership)
- query-engine bandwidth work

## Integration Contract

- Plug into WP-02 diagnostics engine output model.
- Do not alter auth mapping semantics from WP-03.
- Keep report fields aligned to canonical model.

## Acceptance Criteria

- Status probe and preflight probe independently report pass/fail with evidence.
- Timeout/retry behavior is visible in evidence text.
- Overall rollup can produce `ready_with_degraded_realtime` when appropriate.

## Validation Commands

Run and report exact results:

- `wctl run-npm test`
- optional integration smoke against live status/preflight services if available

If runtime services are unavailable, document blocked integration checks explicitly.

## Handoff Format

Report:

- files changed
- `diagRunId` generator format and guardrails
- retry/timeout behavior implemented
- tests run + results
- residual risks

Do not commit or push.
