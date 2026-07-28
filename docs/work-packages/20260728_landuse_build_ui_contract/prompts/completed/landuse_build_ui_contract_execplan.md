# Execute DOM-08A Landuse Build UI Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package proves Landuse build controls retain their field identities through
browser multipart transport, route parsing, persisted state, RQ build work, and
completion reload.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-08A and recorded the field/action matrix.
- [x] Added actual-render, exact FormData, and multipart-normalization regressions.
- [x] Ran focused and full frontend validation; archive this plan.

## Surprises & Discoveries

- Observation: The build action uses browser `FormData`; prior controller
  coverage proved only that a form object was sent, not its risk-bearing entries.

## Decision Log

- Decision: Add only direct render, FormData, and multipart parser assertions.
  Rationale: Existing mode, upload, worker, and reload tests already cover the
  remaining build path, so another abstraction would add no value.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-08A closed without a production repair. It added render, exact multipart,
and route-normalization evidence while retaining the existing mode, upload,
worker, and reload tests. No helper was extracted. Focused Python (190 tests),
frontend lint, focused Landuse Jest (29 tests), and the full frontend suite
(88 suites, 663 tests) passed.

## Plan of Work

Render upload mode with disturbance options; assert actual multipart entries;
assert multipart boolean normalization at the route; reuse existing persistence,
worker, and completion evidence. Retain tests if all conform.

## Validation and Acceptance

Run focused Python, frontend lint, focused and full frontend tests, docs lint,
and `git diff --check`. Rebuild controllers, check the RQ graph, and require
production/security review only after a production change.
