# Verify the archive console contract

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized user can list, create, restore, download, and delete archives for
the exact project; observe the one active archive/restore job; and recover
visibly from conflicts or failures. Archive names and contents remain confined
to the run, and terminal actions refresh the authoritative list.

## Progress

- [x] (2026-07-29 UTC) Scaffolded SURF-03 and ratified concise intent.
- [x] (2026-07-29 UTC) Traced route/template/config, source/built client,
  shared transport/status consumers, API authorization, workers, and tests.
- [x] (2026-07-29 UTC) Added actual-render and eight missing executable-client
  regressions.
- [x] (2026-07-29 UTC) Ran focused route, API, worker, and security evidence.
- [x] (2026-07-29 UTC) Repaired the confirmed sibling-mutation request-window
  race while preserving all API and worker contracts.
- [x] (2026-07-29 UTC) Completed broad gates, security review, records, and
  closure.

## Surprises & Discoveries

- Observation: Source and built archive clients are byte-identical.
  Evidence: `cmp` succeeds for `static-src/js/archive_console.js` and
  `static/js/archive_console.js`.

- Observation: The real-client suite exercises archive creation only.
  Evidence: `console_smoke.test.js` has one archive test; restore/delete/list
  rows and terminal archive transitions are not directly executed.

- Observation: Restore and delete left sibling mutation controls enabled while
  their requests were pending.
  Evidence: The new pending-delete client test failed because create and
  restore remained enabled; the same gap was present in restore submission.

## Decision Log

- Decision: Preserve existing archive behavior and treat SURF-03 as a
  conformance audit.
  Rationale: Current UI documentation, cross-cutting contracts, and registered
  scope agree; the operator requested execution rather than a behavior change.
  Date/Author: 2026-07-29 / Codex with operator authority.

- Decision: Keep the pending generated RQ graph line-number update outside the
  package.
  Rationale: It predates SURF-03 and changes no archive edge; preserving it
  avoids misattributing evidence or scope.
  Date/Author: 2026-07-29 / Codex.

- Decision: Disable all three archive mutation controls synchronously for
  restore and delete, then restore them only when no active job exists.
  Rationale: This is the smallest repair for the reproduced request-window race
  and aligns the client with the existing shared backend active-job slot.
  Date/Author: 2026-07-29 / Codex with operator authority.

## Outcomes & Retrospective

SURF-03 is verified and closed. One actual-render test and eight new direct
client tests now cover exact identity, hostile metadata, restore/delete,
confirmation cancellation, repeat initialization, request mutual exclusion,
terminal refresh, and visible submission failure. The only production repair
mutually disables create/restore/delete during restore or delete submission;
source and served assets remain byte-identical.

Focused console, route/render, archive API/RQ, and security evidence passed 23,
166, 32, and 17 tests respectively. Frontend lint and all 101 suites/727 tests
passed. Repository Python passed 5,556 tests with 58 skips. Documentation,
spelling, graph, parity, and diff closeout gates passed. No unresolved security
finding remains.

## Context and Orientation

`archive_dashboard.py` authorizes and renders the dashboard and supplies the
archive list. `archive_console_control.htm` emits the hidden run-scoped URLs.
`static-src/js/archive_console.js` lists rows and submits create/restore/delete
actions through renewable session authorization, while controlBase and
StatusStream present job state. `fork_archive_routes.py` owns mutation
authorization and enqueue. `project_rq_archive.py` owns archive creation and
restore safeguards.

## Plan of Work

Render the actual route template with authorized and hostile context. Extend
the direct real-client suite for empty/populated rows, safe metadata,
create/comment truncation, refresh, restore, delete, confirmation cancellation,
repeat initialization, active exclusion, terminal success/failure, and errors.
Retain existing route/API/worker evidence for authorization, stale jobs,
conflicts, path/integrity/disk/lock/cache handling, and triggers. Patch only a
reproduced contradiction and keep source/built parity if a client patch is
required.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- console_smoke
    wctl run-pytest tests/weppcloud/routes/test_archive_dashboard_route.py \
      tests/weppcloud/routes/test_pure_controls_render.py \
      tests/microservices/test_rq_engine_fork_archive_routes.py \
      tests/rq/test_project_rq_archive.py \
      tests/rq/test_project_rq_archive_helpers.py --maxfail=1
    wctl check-rq-graph
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260729_pure_ui_archive_console_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

If production client source changes, copy/rebuild the built archive client and
prove byte parity. No full controller-bundle rebuild is needed for this
standalone static-src asset.

## Validation and Acceptance

Acceptance requires actual-render evidence for exact server-owned URLs and
authorization identity, direct execution of the real client at each uncovered
mutation/lifecycle seam, and retained API/RQ evidence through filesystem and
terminal state. Focused and broad applicable gates pass, or a proven unrelated
failure is recorded.

## Idempotence and Recovery

Rendering, Jest, pytest, graph, lint, and docs commands are safe to rerun.
Client tests use controlled browser globals. Restore/delete confirmation can be
declined without mutation; failed submissions retain visible retry state.

## Interfaces and Dependencies

Preserve `data-archive-dashboard-config`, run/config/list/create/restore/delete/
project URLs, `comment`, `archive_name`, 40-character limit, renewable session
token, one active archive job id, channel `archive`, `ARCHIVE_*`/`RESTORE_*`
events, confined download URLs, and safe project navigation. Add no dependency,
route, queue edge, archive format, field, or default.

## Revision Notes

2026-07-29: Created from explicit operator direction to scaffold and execute
SURF-03.

2026-07-29: Added direct evidence, repaired sibling-mutation exclusion,
completed security review, reconciled parent records, and moved the plan to
`prompts/completed/`.
