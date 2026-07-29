# Verify and separate the privileged RQ active-job view

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An Admin or Root operator can open RQ Info Details and distinguish active
default work from active batch work immediately. The page remains a static,
read-only privileged snapshot. The result is observable through direct
rendering and route tests that show ordered, isolated queue panels and preserve
the existing completed and failed tables.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-17 and recorded operator approval.
- [ ] Complete two independent contract reviews and commit the checkpoint.
- [ ] Trace authorization, Redis/RQ listing, hydration, rendering, navigation,
  and existing tests.
- [ ] Add direct render, authorization, grouping, filtering, failure, and
  retained-producer evidence.
- [ ] Implement the ratified server-owned active queue grouping.
- [ ] Complete security review, focused/broad validation, records, commits, and
  clean closeout.

## Surprises & Discoveries

- Observation: The existing route already accepts an ordered `queues` query and
  the listing payload already labels every active job with its queue.
  Evidence: `_parse_queues`, `list_active_jobs`, and the current Queue column.

## Decision Log

- Decision: Render one active panel per requested queue, in request order.
  Rationale: this separates default and batch operations while preserving
  custom queue filtering and avoiding a hard-coded presentation exception.
  Date/Author: 2026-07-28 / operator and Codex.

- Decision: Keep completed and failed tables combined.
  Rationale: the operator requested active-list separation only.
  Date/Author: 2026-07-28 / operator and Codex.

## Outcomes & Retrospective

Pending execution.

## Context and Orientation

`wepppy/weppcloud/routes/rq/info_details/routes.py` owns the Admin/Root Flask
route. It requests completed and active job payloads from
`wepppy/rq/job_listings.py`, adds submitter display information, and renders
`templates/info_details.htm`. An active job is either started or waiting in an
RQ queue. The current template combines all active queues in one table.

## Plan of Work

First commit the contract-decision checkpoint after two independent reviews.
Then add a small route helper that produces an ordered sequence containing each
first-occurrence requested queue name and only jobs whose stripped producer
queue equals that name case-sensitively. Render one existing active-table shape
per sequence entry. Add hermetic route and actual-template tests for
authorization, default/custom ordering, whitespace, case differences,
duplicates, unknown/unrequested values, queue isolation, empty states, hostile
values, links, combined terminal tables, and failures. Do not change
`job_listings.py` unless a direct regression proves its retained payload
contract is wrong. Create `tests/rq/test_job_listings.py` to exercise the real
read-only producer's queue labels, ordering, started/queued states, and absence
of mutation calls; current admin-route tests mock this boundary and are not
sufficient retained-producer evidence.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_rq_info_details.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-pytest tests/rq/test_job_listings.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_rq_info_details_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run `wctl check-rq-graph` only if queue wiring changes; the ratified plan does
not authorize such a change.

## Validation and Acceptance

Acceptance requires Admin/Root-only route evidence, a read-only snapshot, exact
default and custom queue panel order, no cross-queue job leakage, an empty state
per queue, safe metadata rendering, retained job/run navigation, unchanged
combined terminal tables, and no unresolved high or medium security findings.
Focused and broad gates pass except a proven unrelated baseline failure
recorded exactly.

## Idempotence and Recovery

Tests use fake Redis/listing results and Flask request contexts. Repeated runs
do not touch a live queue. The checkpoint and implementation are separate
commits, so contract ancestry remains auditable without destructive recovery.

## Artifacts and Notes

The contract decision is
`artifacts/2026-07-28_contract_decision.md`; the field matrix is
`artifacts/field_matrix.md`. Record both pre-implementation reviews and the
final security review under `artifacts/`.

## Interfaces and Dependencies

Retain Flask-Security `login_required` plus `roles_accepted("Admin", "Root")`,
`wepppy.rq.job_listings`, the RQ Redis database, Pure CSS table markup, and
`url_for_run`. Add no dependency, endpoint, queue edge, polling loop, or
mutation.

Revision note: created 2026-07-28 to execute the operator-approved active queue
separation within SURF-17.
