# Verify the RQ job dashboard lifecycle

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

A CAP-verified user can open a job dashboard, see a safely rendered nested job
tree update until terminal state, understand rate limits and failures, and
cancel only with an authorized token. The surface remains usable under the
configured rq-engine polling-auth mode.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-07 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced Flask host, template state machine, token
  bridges, job routes, cancellation authorization, contracts, and tests.
- [x] (2026-07-28 UTC) Added direct-render and four real inline
  polling/tree/rate-limit/cancel regressions.
- [x] (2026-07-28 UTC) Passed 268 focused
  route/session/rq-engine/payload/render tests.
- [x] (2026-07-28 UTC) Repaired only the regression-proven required poll-auth
  mismatch with one authenticated fallback retry.
- [x] (2026-07-28 UTC) Completed broad validation, independent security review,
  records, commit, and clean closeout.

## Surprises & Discoveries

- Observation: Existing dashboard tests inspect source strings but never
  execute the 870-line inline state machine.
  Evidence: `test_rq_job_dashboard_template.py` has two source assertions and
  no DOM/poll/tree/cancel execution.

- Observation: Open-mode polling passed, but a required-mode 401 stopped the
  dashboard without using its existing authenticated token bridge.
  Evidence: The new real inline regression failed after one unauthenticated
  job-info request and passed after the bounded 401/403 retry repair.

## Decision Log

- Decision: Execute the real final inline script using the established
  template-extraction Jest pattern.
  Rationale: String checks cannot prove polling termination, backoff, escaping,
  token selection, or cancellation.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Preserve all server payloads, token scopes, polling policy, and
  cancellation authorization.
  Rationale: SURF-07 is a conformance audit rather than an API redesign.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Preserve the open-mode unauthenticated fast path and retry job-info
  exactly once with `fetchRqEngineToken()` only after 401 or 403.
  Rationale: This conforms to configured required mode without changing server
  policy, issuing tokens unnecessarily, or creating an unbounded retry loop.
  Date/Author: 2026-07-28 / Codex with operator authority.

## Outcomes & Retrospective

SURF-07 closed with one production repair: required poll-auth now falls back to
the existing authenticated `rq:status` token bridge for one retry. Four real
inline Jest tests cover safe terminal rendering, rate-limit backoff,
required-mode recovery, and session-token cancellation; 268 focused Python
tests cover rendering, routes, jobinfo, session/token bridges, cancellation,
and payloads. Frontend lint and the full Jest suite passed, the broad Python
suite reached 2,455 passed and 40 skipped before stopping at the permitted
unrelated GridMET `_FakeUnits.degC` fixture failure. Independent security review
passed with no unresolved findings.

## Context and Orientation

The CAP-gated Flask route renders `dashboard_pure.htm` with a job id.
The inline script polls `/rq-engine/api/jobinfo/{job_id}`, renders nested job
orders and child jobs, applies bounded rate-limit backoff, and stops polling
when the tree becomes terminal. Cancellation first tries a run-scoped session
token after jobinfo reveals `runid`, then falls back to the authenticated
rq-engine token bridge and posts to `/rq-engine/api/canceljob/{job_id}`.
`job_routes.py` owns polling modes, rate limiting, canonical errors, and
cancellation authorization.

## Plan of Work

Render the real template with a representative job id and assert every
risk-bearing target and asset. Add focused Jest that evaluates the production
inline script with mocked jobinfo, tokens, cancellation, timers, confirmation,
alerts, and QR generation. Retain existing Flask, rq-engine jobinfo/cancel,
session-token, token-bridge, and job-payload tests after inspecting and running
them. Patch only a regression-proven contradiction of the concise and canonical
contracts.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_rq_job_dashboard_template.py --maxfail=1
    wctl run-npm test -- rq_job_dashboard
    wctl run-pytest tests/microservices/test_rq_engine_jobinfo.py tests/microservices/test_rq_engine_session_routes.py tests/weppcloud/routes/test_rq_engine_token_api.py tests/rq/test_jobinfo_payloads.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_rq_job_dashboard_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run the controller build only if bundled controller source changes. Run the RQ
graph check only if queue wiring changes.

## Validation and Acceptance

Acceptance requires actual rendering, executable poll/tree/rate-limit/cancel
behavior, and retained server authorization/session/payload evidence. All
focused, frontend, documentation, and applicable broad gates pass, except a
proven unrelated pre-existing failure may be recorded exactly.

## Idempotence and Recovery

All tests mock timers, fetch, confirmation, QR, token, and cancellation side
effects and are safe to rerun. Preserve unrelated work and do not rebuild
generated assets without a controller-source change.

## Interfaces and Dependencies

Preserve the dashboard path, `job_id`, canonical jobinfo fields, terminal
status semantics, polling modes, `rq:status`, session/fallback token bridges,
cancel path and error envelope, CAP gate, and server authorization checks.

## Revision Notes

2026-07-28: Created from explicit operator direction after SURF-16 closed.
