# Verify the fork console contract

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized user can fork the exact source run with the selected copy options,
observe and cancel the one accepted job, reload without losing safe tracking,
and open the encoded destination after authoritative completion. Anonymous
public-run users must solve CAP before submission. Failures remain visible and
never become successful state.

## Progress

- [x] (2026-07-29 UTC) Scaffolded SURF-04 and ratified concise intent.
- [x] (2026-07-29 UTC) Traced the route, template/control, real client,
  shared transport/status consumers, API authorization, worker, and tests.
- [x] (2026-07-29 UTC) Reconciled the completed fork-copy predecessor.
- [x] (2026-07-29 UTC) Added actual-render and missing executable-client
  regressions.
- [x] (2026-07-29 UTC) Ran focused route, API, cancellation, worker, and
  terminal evidence.
- [x] (2026-07-29 UTC) Confirmed no production contradiction required a patch
  or bundle rebuild.
- [x] (2026-07-29 UTC) Completed broad gates, security review, records, and
  closure.

## Surprises & Discoveries

- Observation: The production fork client already has substantial direct Jest
  coverage in `console_smoke.test.js`, including storage restoration,
  authoritative completion, safe hostile identifiers, stale auth, and
  cancellation.
  Evidence: The suite imports `static/js/fork_console.js` directly.

- Observation: The completed 2026-05-06 copy-option package remained marked
  open with its ExecPlan active.
  Evidence: Its tracker records all deliverables, review disposition, 96
  passing focused tests, and only a deferred UI propagation regression.

- Observation: The RQ dependency checker reports existing static artifact
  drift even though SURF-04 changes no enqueue site or dependency edge.
  Evidence: `wctl check-rq-graph` names only the generated graph/catalog;
  neither appears in the SURF-04 diff.

## Decision Log

- Decision: Preserve existing fork behavior and treat SURF-04 as a conformance
  audit.
  Rationale: Current UI documentation, cross-cutting contracts, ADR-0021, and
  the registered concise intent agree; the operator requested execution, not a
  behavior change.
  Date/Author: 2026-07-29 / Codex with operator authority.

- Decision: Close the stale predecessor administratively and inherit its
  backend evidence while adding its deferred route-to-client regression.
  Rationale: Reopening already reviewed implementation would duplicate work,
  while leaving the package active obscures the actual dependency state.
  Date/Author: 2026-07-29 / Codex.

## Outcomes & Retrospective

SURF-04 closed without a production repair. Four route-context tests and three
actual-render variants prove exact authorization, CAP, token, and query-owned
option identity. Fifteen direct real-client tests prove payload propagation,
CAP block/solve/submit, repeat safety, storage confinement, renewable
authorization, cancellation, safe identifiers, and authoritative terminal
state. Existing API and RQ tests retain the downstream boundary. The
high-impact security review passed with no unresolved finding.
Frontend lint and all 101 suites/719 tests passed; repository Python passed
5,555 tests with 58 skips.

## Context and Orientation

`fork_console.py` authorizes and renders route/query defaults.
`fork_console_control.htm` emits the hidden config, options, CAP prompt, and
buttons. `static/js/fork_console.js` submits and tracks the job, uses SHR-02
transport/session behavior, and consumes SHR-03A polling/StatusStream behavior.
`fork_archive_routes.py` authorizes, verifies CAP where needed, validates, and
enqueues. `project_rq_fork.py` copies and normalizes the destination.

## Plan of Work

Render the actual route/template for authenticated, anonymous, selected-default,
and hostile values. Extend the direct production-client suite only at uncovered
seams: rendered default propagation, anonymous CAP submit, repeated
initialization/submit, invalid cross-scope storage, cancel target, and missing
runtime behavior. Retain the existing API and worker tests for authorization,
CAP, exact booleans, target allocation, enqueue, copy exclusions, identity
normalization, errors, and terminal triggers. Patch only a reproduced
contradiction.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- console_smoke
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/weppcloud/test_fork_console_template_contract.py \
      tests/microservices/test_rq_engine_fork_archive_routes.py \
      tests/rq/test_project_rq_fork.py --maxfail=1
    wctl check-rq-graph
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260729_pure_ui_fork_console_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Rebuild only if a bundled `controllers_js` source changes. The standalone
`static/js/fork_console.js` is not emitted by that builder.

## Validation and Acceptance

Acceptance requires actual-render evidence for route-owned defaults and
CAP/auth identity, direct execution of the real client at every uncovered
security/lifecycle seam, and retained API/RQ evidence through destination
state. Focused and broad applicable gates pass, or a proven unrelated failure
is recorded.

## Idempotence and Recovery

Rendering, Jest, pytest, graph, lint, and docs commands are safe to rerun.
Client tests use controlled browser storage and globals. Invalid storage is
removed; failed CAP/auth/submission leaves a visible retry path and does not
create successful terminal state.

## Interfaces and Dependencies

Preserve `data-fork-console-config`, encoded source/config storage keys,
`undisturbify`, `skip_wepp_runs_output`, optional `cap_token`, bearer/session
renewal, `job_id`, `new_runid`, `/api/canceljob/<job_id>`, channel `fork`,
authoritative polled terminal events, ADR-0021 thresholds, and safe destination
links. Add no dependency, route, queue edge, storage field, or default.

## Revision Notes

2026-07-29: Created from explicit operator direction to scaffold and execute
SURF-04.

2026-07-29: Completed with regression-only changes, predecessor reconciliation,
an evidence matrix, and a passing dedicated security review.
