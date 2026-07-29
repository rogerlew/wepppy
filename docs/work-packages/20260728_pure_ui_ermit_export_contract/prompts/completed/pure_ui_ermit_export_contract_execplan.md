# Verify the ERMiT export launcher and protected download

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized user can open the ERMiT export from WEPP results, watch one
run-scoped export job progress, download its protected artifact, and recover
from a transient failure with Retry. The visible lifecycle remains aligned
with canonical rq-engine response, session, CSRF, and authorization contracts.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-16 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced results link, launcher, session token, submit,
  status, download, worker, artifact, and existing tests.
- [x] (2026-07-28 UTC) Expanded actual-render and inline lifecycle/retry
  regressions.
- [x] (2026-07-28 UTC) Ran route/session/RQ/worker evidence and classified the
  rejected-token retry discrepancy.
- [x] (2026-07-28 UTC) Applied the one-line conformance repair that starts
  explicit retries with a fresh token request.
- [x] (2026-07-28 UTC) Completed validation, independent security review,
  records, commit preparation, and clean-closeout preparation.

## Surprises & Discoveries

- Observation: The launcher is an inline state machine rather than a bundled
  controller and currently has direct render/route tests but no executable
  browser lifecycle test.
  Evidence: Repository search finds no Jest ownership for
  `ermit_export_download.htm`.

- Observation: `tokenPromise` cached rejection as well as success, making the
  visible Retry action permanently reuse the first token error.
  Evidence: The new inline regression observed one token attempt after Retry
  until `startExport()` explicitly cleared the per-attempt cache.

## Decision Log

- Decision: Verify the inline script directly using the established template
  extraction pattern.
  Rationale: A rendered string assertion cannot prove token caching, polling,
  download, or retry behavior.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Preserve current export schemas, route paths, scopes, queue
  topology, and artifact format.
  Rationale: SURF-16 is a conformance audit, not a behavior redesign.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Reset the cached token only when an explicit export attempt starts.
  Rationale: This restores Retry without changing token issuance or sharing:
  submit, polling, and download still reuse one token within each attempt.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SURF-16 now has direct launcher rendering, executable token/submit/poll/
download/retry behavior, exact rq-engine authorization/run/job-state evidence,
and direct worker artifact metadata. A rejected token no longer makes Retry
permanently inert. Focused render/route tests passed 161; focused Jest passed 2;
frontend lint and the full 90-suite/673-test sweep passed. The combined focused
rq-engine/session/worker set passed 63 tests. Independent security review
passed with zero unresolved findings. The broad Python result is recorded
after completion: it stopped on the known unrelated GridMET `_FakeUnits.degC`
fixture failure after 2,455 passed and 40 skipped.

## Context and Orientation

`wepp_reports.htm` exposes the launcher only for eligible non-RHEM runs.
`wepp_bp.py::download_ermit_export` performs run authorization and CAP gating,
loads run context, and embeds the rq-engine URLs. The inline script mints a
run-scoped session token, submits `POST /export/ermit`, polls the returned
`status_url`, and bearer-downloads the returned artifact URL.
`export_routes.py` authorizes submit/download, enqueues
`run_ermit_export_rq`, and verifies job/run/finished state before delivery.

## Plan of Work

Expand the existing actual-template regression for every risk-bearing target
and initial state. Add a focused Jest suite that evaluates the production
inline script with controlled fetch, timers, blobs, and object URLs. Prove the
happy lifecycle and recovery after a failed token attempt. Run the existing
Flask, rq-engine, session-token, worker, and export tests after inspection.
If a regression exposes a mismatch, retain it and apply only the smallest
contract-compatible patch.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_wepp_bp.py --maxfail=1
    wctl run-npm test -- ermit_export
    wctl run-pytest tests/microservices/test_rq_engine_export_routes.py tests/microservices/test_rq_engine_session_routes.py tests/rq/test_ermit_export_rq.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_ermit_export_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run the controller build only if bundled controller source changes. Run the RQ
graph check only if queue wiring changes.

## Validation and Acceptance

Acceptance requires direct rendered evidence, executable happy/error/retry
client evidence, and retained authorization/session/route/queue/worker/artifact
evidence. All focused, frontend, documentation, and applicable broad gates
pass, except a proven unrelated pre-existing failure may be recorded exactly.

## Idempotence and Recovery

The render, Jest, pytest, lint, and docs commands are safe to rerun. Tests mock
queue, token, timer, and download side effects. Preserve unrelated work and do
not rebuild generated assets without a controller-source change.

## Interfaces and Dependencies

Preserve `ermit_export_*_url`, `job_id`, `status_url`, `download_url`,
`rq:export`, `rq:status`, run/config/pup scoping, the worker signature, relative
artifact metadata, canonical error envelopes, and existing CAP/auth rules.

## Revision Notes

2026-07-28: Created from explicit operator direction after SURF-11 closed.
2026-07-28: Closed after repairing rejected-token retry recovery and adding
direct lifecycle/security evidence.
