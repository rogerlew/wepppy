# Execute DOM-09 Landuse Modifier UI Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package proves map-selected Topaz IDs and the chosen landuse code retain
their values through authenticated browser submission and run-scoped mutation.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-09 and recorded its field/action matrix.
- [x] Added actual-render evidence.
- [x] Ran applicable validation; archive this plan.

## Surprises & Discoveries

- Observation: The RQ-engine `modify-landuse` endpoint mutates Landuse
  synchronously; it does not enqueue the build RQ named by register shorthand.
  Evidence: `landuse_routes.modify_landuse` and its focused route test.

## Decision Log

- Decision: Verify the actual synchronous consumer and leave build lifecycle to
  DOM-08A.
  Rationale: Tests must follow the real value path and must not create
  speculative queue infrastructure.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-09 closed without production repair. The actual partial now has direct
render evidence for selection, values, submit, and lifecycle targets. Existing
Jest and RQ-engine tests proved map selection, exact `{topaz_ids, landuse}`
submission, authorization, validation, and synchronous mutation. Focused Python
(138 tests), lint, focused Jest (3 tests), and documentation lint passed; the
unchanged frontend tree's immediately preceding full sweep passed 88 suites and
663 tests. No helper was added.

## Plan of Work

Render the modifier partial and assert all risk-bearing identities. Reuse the
existing controller tests for map selection and exact native payload, and the
RQ-engine route tests for authorization, validation, and mutation.

## Validation and Acceptance

Run focused render, modifier Jest, RQ-engine Landuse tests, frontend lint/full
tests, documentation lint, and `git diff --check`. Production-only gates are
not applicable unless a production source changes.
