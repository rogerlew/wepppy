# Execute DOM-07 Subcatchment UI Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package proves rendered WBT/MOFE options retain their identities through
the GL request, route update, ordered subcatchment-build/abstraction jobs, and
completion reload.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-07 and recorded the field/action matrix.
- [x] Added actual-render, exact payload, and ordered-worker-chain regressions.
- [x] Ran focused and full applicable validations; archive this plan.

## Surprises & Discoveries

- Observation: Route tests covered option coercion and parent enqueue, but not
  the parent worker's build-before-abstraction dependency edge.

## Decision Log

- Decision: Add only the missing template/payload/worker-edge assertions.
  Rationale: They cover the exact user-facing data path without a registry,
  controller helper, route refactor, or queue change.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-07 closed without a production repair. It added direct regressions at the
render, controller payload, and worker ordering seams; existing route coercion,
update, and reload coverage conformed. No helper was extracted. Focused Python
(169 tests), frontend lint, focused Subcatchment Jest (12 tests), and the full
frontend suite (88 suites, 663 tests) passed.

## Plan of Work

Render actual WBT/MOFE options; assert the controller sends that serialized
payload unchanged; reuse route coercion tests; prove the parent worker enqueues
build before its dependent abstraction child. Retain the tests if all conform.

## Validation and Acceptance

Run focused Python, frontend lint, focused and full frontend tests, docs lint,
and `git diff --check`. Rebuild controllers, check the RQ graph, and require
production/security review only after a production change.
