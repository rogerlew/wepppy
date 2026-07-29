# Verify the Pure Runs catalog contract

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authenticated user can search, sort, page, map, open, and selectively delete
their own runs. Admin and Root users can deliberately scope the same surface to
another account. Ownership, stored run/config identity, readonly state,
deletion enqueue, job polling, and terminal UI state agree end to end.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-06 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced template, inline client, catalog/users/map
  routes, ownership queries, delete route, TTL state, RQ worker, and tests.
- [x] (2026-07-28 UTC) Added actual render and real-inline-client evidence.
- [x] (2026-07-28 UTC) Retained focused route/ownership/delete/RQ/worker evidence.
- [x] (2026-07-28 UTC) Repaired only confirmed conformance mismatches.
- [x] (2026-07-28 UTC) Completed security review, broad gates, records, commit,
  and clean
  closeout.

## Surprises & Discoveries

- Observation: `buildRunRow` opens the catalog's stored configuration, but
  `deleteRun` hardcodes configuration `0`.
  Evidence: `templates/user/runs2.html` uses `run.config` for Open and `0` for
  `/tasks/delete/`.

- Observation: The template constructs run paths from raw server values rather
  than encoded path segments.
  Evidence: Open and delete URL interpolation in `runs2.html`.

- Observation: The readonly route returned a failure payload with HTTP 200.
  Evidence: the direct blueprint regression observed success status before the
  route was aligned to the existing error contract.

- Observation: The full frontend sweep caught an older extracted-function test
  that did not load the new URL helper.
  Evidence: `runs_lifecycle_template.test.js` failed with `buildRunUrl is not
  defined`; extracting both real functions restored isolated evidence.

## Decision Log

- Decision: Preserve the exact stored `(runid, config)` identity in both Open
  and Delete actions.
  Rationale: Authorization and run-context loading are configuration-aware;
  substituting `0` can target the wrong or nonexistent context.
  Date/Author: 2026-07-28 / Codex applying the existing catalog/route identity.

- Decision: Encode each server-provided path segment at the browser boundary.
  Rationale: Text rendering is already escaped; action URLs require equivalent
  path-component containment.
  Date/Author: 2026-07-28 / Codex applying safe-output and exact-route intent.

- Decision: Keep deletion failures in the page summary and avoid logging run
  identifiers to the browser console.
  Rationale: Visible bounded feedback is sufficient and avoids unnecessary
  operational identifier disclosure.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SURF-06 closed with three actual-render/CSRF tests, four real-inline-client
tests, retained ownership/catalog/map/delete/RQ evidence, and a passed
high-impact security review. The focused Python set passed 65 tests, focused
Jest passed four tests, frontend lint passed, the full frontend sweep passed 98
suites/703 tests, and broad Python passed 5,540 tests with 58 skips. Compared
with the initial plan, production repair was
required only at confirmed action-identity, path-containment, credential,
readonly-status, and safe-feedback seams; no endpoint, role, queue, ownership
rule, retention behavior, or dependency was added.

## Context and Orientation

`wepppy/weppcloud/templates/user/runs2.html` contains the dashboard shell and
its inline catalog, scope, map, deletion, and polling client.
`wepppy/weppcloud/routes/user.py` supplies the page, protected user directory,
catalog, and map JSON. `_resolve_runs_user_id` confines ordinary users to their
own ID and resolves Admin/Root aliases. The project blueprint's `delete_run`
reauthorizes and enqueues `wepppy.rq.project_rq.delete_run_rq`.

## Plan of Work

Render the actual template for ordinary and privileged viewers. Execute the
actual inline script under Jest for catalog rows, hostile values, search,
pagination, Admin scoping, map states, readonly behavior, exact deletion,
enqueue failures, polling terminals, and retry exhaustion. Retain real Flask
database evidence for ownership and aliases plus project/RQ delete evidence.
Write failing regressions before the smallest contract-compatible repair.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_runs_catalog_contract.py \
      tests/weppcloud/routes/test_user_runs_admin_scope.py \
      tests/weppcloud/routes/test_project_bp.py \
      tests/rq/test_project_rq_delete_run.py --maxfail=1
    wctl run-npm test -- runs_catalog_inline
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_runs_catalog_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

No controller build is expected because the client is inline. Run
`wctl check-rq-graph` only if queue wiring changes.

## Validation and Acceptance

Acceptance requires exact ordinary/Admin rendering, owned/scoped JSON, safe
metadata, readonly state, encoded run/config actions, CSRF, delete
authorization/enqueue, bounded polling, terminal row removal, and persistent
worker evidence. No unresolved security finding may remain.

## Idempotence and Recovery

Tests use in-memory databases, temporary run directories, mocked fetch/deck
APIs, fake queues, and fake timers. They do not delete production runs or
contact map providers. Repeated execution is safe. The child commit is the
restore point.

## Artifacts and Notes

The field matrix is `artifacts/field_matrix.md`. The required security review
is `artifacts/2026-07-28_security_review.md`.

## Interfaces and Dependencies

Retain existing page/catalog/users/map/delete endpoints, ownership joins,
Admin/Root role set, TTL delete-state contract, RQ default queue, response
envelopes, and terminal status vocabulary. Add no dependency, endpoint, queue,
ownership rule, or retention behavior.

Revision note: created 2026-07-28 for the registered SURF-06 audit.
