# Verify the Run Sync console contract

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An Admin can submit one exact remote-run import, optionally chain migrations,
monitor live and authoritative status, inspect safe provenance rows, and open
the imported local run. Private source tokens and downloaded files remain
confined to their intended boundaries.

## Progress

- [x] (2026-07-29 UTC) Scaffolded SURF-05 and ratified concise intent.
- [x] (2026-07-29 UTC) Traced route/template/config, source/generated client,
  shared runtime consumers, API authorization, worker, and existing tests.
- [x] (2026-07-29 UTC) Added actual-render and eight direct real-client
  regressions.
- [x] (2026-07-29 UTC) Repaired the reproduced duplicate-submission window.
- [x] (2026-07-29 UTC) Ran focused/frontend/graph validation and completed the
  security review.
- [x] (2026-07-29 UTC) Reconciled child/umbrella records and closed.

## Surprises & Discoveries

- Observation: Run Sync has focused API and worker tests but no direct
  controller suite.
  Evidence: repository search finds no Jest import of
  `run_sync_dashboard.js`.

- Observation: Run Sync is embedded in `controllers-gl.js`, not served as a
  standalone client.
  Evidence: the template loads the generated controller bundle.

- Observation: A second submit was accepted while the first request remained
  pending.
  Evidence: the pending-request Jest observed two `postJson` calls before the
  first promise resolved.

- Observation: The documented bare host build command lacks Jinja in this
  environment.
  Evidence: system `python3` raised `ModuleNotFoundError`; `.venv/bin/python`
  rebuilt the bundle successfully.

## Decision Log

- Decision: Preserve existing Run Sync behavior and treat SURF-05 as a
  conformance audit.
  Rationale: The registered scope, shared contracts, and current UI/API agree;
  the operator requested execution rather than new behavior.
  Date/Author: 2026-07-29 / Codex with operator authority.

- Decision: Limit submission exclusion to the initialized browser dashboard.
  Rationale: Cross-process duplicate exclusion would change backend
  orchestration behavior and queue topology beyond this package.
  Date/Author: 2026-07-29 / Codex.

- Decision: Use one synchronous client latch from request start through
  authoritative terminal state.
  Rationale: This is the smallest repair for the reproduced duplicate enqueue
  without changing backend queue topology or cross-process semantics.
  Date/Author: 2026-07-29 / Codex with operator authority.

## Outcomes & Retrospective

SURF-05 is verified and closed. One actual-render test, two route-context tests,
and eight direct real-controller tests now prove the fields/defaults, token
claims, exact payload, safe tables, validation/errors, terminal navigation,
repeat initialization, and submission exclusion. The only production repair is
the dashboard-local submission latch and missing-job-id rejection.

Focused client, render/route, API/RQ, and security evidence passed 8, 166, 10,
and 17 tests. Frontend lint and all 102 suites/735 tests passed. Repository
Python passed 5,559 tests with 58 skips. The generated bundle, RQ graph,
documentation, spelling, and diff gates pass. No unresolved security finding
remains.

## Context and Orientation

`run_sync_dashboard.py` authorizes Admin access and mints the rq-engine token.
`rq-run-sync-dashboard.htm` renders exact fields and hidden configuration.
`controllers_js/run_sync_dashboard.js` owns submit, tables, StatusStream, and
polling behavior and is embedded in generated `static/js/controllers-gl.js`.
`run_sync_routes.py` owns API authorization, source-token indirection, enqueue,
and status. `rq/run_sync_rq.py` owns download, verification, provenance, and
terminal events.

## Plan of Work

Render the actual dashboard with hostile token/default values and assert exact
fields, defaults, URLs, and bundle identity. Add a direct jsdom suite against
the real controller for safe empty/populated tables, exact payload booleans,
required-run validation, missing token, duplicate initialization, pending
submission exclusion, status errors, and terminal success/failure. Retain
existing API/worker evidence. Patch only a reproduced contradiction and rebuild
the generated controller bundle when source changes.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- run_sync_dashboard
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/microservices/test_rq_engine_run_sync_routes.py \
      tests/rq/test_run_sync_rq.py --maxfail=1
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path \
      docs/work-packages/20260729_pure_ui_run_sync_console_contract
    wctl doc-lint --path \
      docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

## Validation and Acceptance

Acceptance requires actual-render identity, direct execution of every
risk-bearing browser seam, retained API/RQ evidence through token consumption
and confined output, source/generated parity, and passing focused/broad gates.

## Idempotence and Recovery

Rendering, Jest, pytest, build, graph, lint, and documentation commands are
safe to rerun. Client timers and globals are controlled in jsdom. Generated
bundle changes must exactly reflect the controller-source repair.

## Interfaces and Dependencies

Preserve `#run_sync_config`, submit/status URLs, defaults, channel suffixes,
`source_host`, `runid`, optional `config`, `target_root`, `owner_email`,
`source_run_token`, `run_migrations`, `archive_before`, rq-engine user token,
source-token Redis indirection, `RUN_SYNC_COMPLETE`/failure lifecycle, and
dependent migration enqueue.

## Revision Notes

2026-07-29: Created from explicit operator direction to scaffold and execute
SURF-05.

2026-07-29: Added direct evidence, repaired duplicate submission, completed the
security review, reconciled parent records, and moved the plan to
`prompts/completed/`.
