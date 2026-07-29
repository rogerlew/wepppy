# Harden fork destination readiness before exposing success

This ExecPlan is maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

A user who sees the fork console’s “Load project” action can open it without a
transient not-found response. RQ job completion remains authoritative for
worker success, while a separate WEPPcloud check proves the destination is
visible enough for the run page before the action appears.

## Progress

- [x] (2026-07-29 21:16 UTC) Captured the production incident and scaffolded
  the hardening package.
- [x] (2026-07-29 21:16 UTC) Reviewed the closed SURF-04 contract, trigger
  precedent, route, client, worker, and existing tests.
- [x] (2026-07-29 21:27 UTC) Implemented an authorized, job-bound readiness
  route and bounded client
  reconciliation.
- [x] (2026-07-29 21:32 UTC) Added exact route and executable-client
  regressions.
- [x] (2026-07-29 21:35 UTC) Ran targeted and broad validation.
- [x] (2026-07-29 21:36 UTC) Completed independent code and QA reviews and
  dispositioned all findings.
- [x] (2026-07-29 21:36 UTC) Closed locally without deployment.

## Surprises & Discoveries

- Observation: SURF-04 confirms the client waits for authoritative polled RQ
  status, yet it immediately converts `finished` into a destination link.
  Evidence: `markCompleted()` calls `handleForkComplete()` directly in
  `wepppy/weppcloud/static/js/fork_console.js`.

- Observation: `get_wd` caches only paths that exist and validates positive
  cache entries, so there is no application-level negative path cache to clear.
  Evidence: `wepppy/weppcloud/utils/helpers.py:get_wd`.

- Observation: the original submission and restoration messages contained
  destination anchors before the terminal success action.
  Evidence: independent review and the former `appendNewRunLink` call sites.

- Observation: a destination-only readiness URL would expose an unbound
  existence oracle.
  Evidence: independent security-oriented code review.

## Decision Log

- Decision: Add readiness after RQ completion, not inside worker completion.
  Rationale: the failure occurs across the worker-to-web visibility boundary;
  checking only from the worker would repeat the same assumption.
  Date/Author: 2026-07-29 / Codex.

- Decision: Bind the readiness request to the exact finished `fork_rq` job and
  run IDs, authorize both source and destination, and require the destination
  directory plus core root NoDb files.
  Rationale: the check executes in the web service whose page previously
  returned 404 without creating an unbound destination-existence oracle.
  Date/Author: 2026-07-29 / Codex.

- Decision: Render destination identifiers as plain text until readiness and
  disable cancellation once RQ success begins finalization.
  Rationale: all UI paths must obey the same readiness boundary and a
  successfully finished fork is no longer cancellable.
  Date/Author: 2026-07-29 / Codex, from independent review.

## Outcomes & Retrospective

The console now distinguishes RQ success from web-visible destination
readiness. Its sole load link is created only after a source-and-destination
authorized, exact-job-bound readiness response succeeds. Thirty automatic
checks are followed by visible manual recovery without discarding tracked
state.

Focused route and client tests, full frontend tests and lint, full repository
pytest, documentation lint, changed-file broad-exception enforcement, and diff
checks passed. Independent code and QA reviews found no unresolved medium/high
issues after fixes. Nothing was deployed. The operator owns local integration
testing and may reopen the package.

## Context and Orientation

`wepppy/rq/project_rq.py:fork_rq` copies and finalizes the destination, then
publishes completion. `wepppy/weppcloud/static/js/fork_console.js` reconciles
stream events with authoritative job polling and currently exposes the link as
soon as polling reports `finished`. The fork blueprint in
`wepppy/weppcloud/routes/fork_console/fork_console.py` runs inside WEPPcloud and
already authorizes access to the source run.

“Readiness” here means only that WEPPcloud resolves the canonical destination
directory and sees the root NoDb files required to initialize the run page. It
does not mean model outputs are complete or valid.

## Plan of Work

Add a GET route to the fork blueprint that authorizes both runs, binds the
request to the exact finished `fork_rq` job, validates the destination
identifier through `get_wd`, and returns an explicit JSON ready/not-ready
result without mutation. Extend the fork client so an
authoritative RQ success begins a bounded readiness loop, retains browser
tracking during that loop, and shows the success link only after readiness.
Treat authorization errors as stale-session failures and transport/exhaustion
as visible retryable failures.

Add route tests for ready and absent/incomplete destinations and direct Jest
tests proving immediate readiness, delayed readiness, bounded exhaustion,
duplicate trigger safety, and restored-job reconciliation.

Update `docs/ui-docs/weppcloud-project-forking.md` so job success and
destination readiness are explicit separate contracts.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- console_smoke
    wctl run-pytest tests/weppcloud/routes/test_fork_console_route.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260729_fork_destination_readiness_hardening
    wctl doc-lint --path docs/ui-docs/weppcloud-project-forking.md
    git diff --check

## Validation and Acceptance

The new delayed-readiness client test must demonstrate that no load link exists
after RQ completion while the route reports not ready, and that exactly one
link appears after readiness. The exhaustion test must prove polling is finite
and produces a visible retry path. All targeted tests and applicable broad
gates pass. Independent code and QA reviews have no unresolved medium/high
findings.

## Idempotence and Recovery

The route is read-only and safe to repeat. Client reconciliation is guarded by
one completion state and one readiness loop. Reload recovery retains the
existing source/config/job/destination record until readiness succeeds. Revert
the bounded readiness layer and route to restore prior behavior; no data
migration or cleanup is required.

## Interfaces and Dependencies

Preserve existing fork submission payloads, job IDs, StatusStream triggers,
poll-authoritative status, session storage fields, authorization, CAP, and
destination URL. Add no dependency, queue edge, parameter default, or run-data
field.

## Revision Notes

2026-07-29: Created from the operator-reported production 404 after confirmed
fork completion.

2026-07-29: Closed after local validation and dual review; moved from active to
completed. Deployment remains deferred.
