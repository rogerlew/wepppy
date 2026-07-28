# Execute DOM-06 Outlet UI Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package proves users can select an outlet with either the map cursor or
manual longitude/latitude entry, submit the canonical coordinates to the
authenticated outlet job, and receive the persisted outlet after completion.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-06 and recorded the field/action matrix.
- [x] Added actual-render and manual-entry regressions; focused Python (167
  passed), lint, and Outlet Jest (5 passed) conform.
- [x] Ran full frontend validation; record the exact result below and archive
  this plan.

## Surprises & Discoveries

- Observation: Existing controller coverage proves cursor submission, while
  template-generated manual-entry identity/default state was not directly tested.

## Decision Log

- Decision: Add direct render/manual-entry assertions and reuse current
  route/RQ tests.
  Rationale: They cross the missing seams without broadening into outlet
  algorithms or queue refactoring.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-06 closed without a production repair. Direct tests protect both rendered
selection modes and the manual-entry coordinate payload; existing cursor,
route, RQ mutation, and reload evidence conformed. No helper was extracted and
no authenticated, queue, or worker implementation changed. Focused Python (167
tests), lint, focused Outlet Jest (5 tests), and the full frontend suite (88
suites, 663 tests) passed.

## Context and Orientation

`set_outlet_pure.htm` provides mode controls. `outlet_gl.js` posts numeric
`latitude` and `longitude` to the RQ-engine route. That route validates/enqueues
`set_outlet_rq`, which persists through `Watershed`; the controller refreshes
the displayed outlet after completion.

## Plan of Work

Add rendered-template assertions for both modes and lifecycle targets. Add a
manual-entry Jest assertion for its exact numeric payload. Reuse existing
route validation/enqueue and RQ mutation tests. If all conform, retain the
tests and make no production change.

## Concrete Steps

From `/home/workdir/wepppy`, run:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/microservices/test_rq_engine_watershed_routes.py tests/rq/test_project_rq_mutation_guards.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test -- outlet_gl
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_outlet_ui_contract

## Validation and Acceptance

Focused tests must prove both coordinate selection paths, route validation,
enqueue, worker mutation, and reload behavior. Rebuild controllers, run the RQ
graph check, and commission production reviews only if production source changes.

## Idempotence and Recovery

Tests and documentation are repeatable. Retain any regression before applying
a narrow compatible repair. Do not modify queue wiring, auth, CSRF, or outlet
algorithms absent a confirmed mismatch.
