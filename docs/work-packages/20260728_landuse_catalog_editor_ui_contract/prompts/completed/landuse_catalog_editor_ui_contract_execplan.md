# Execute DOM-08B Landuse Catalog and Map Editor UI Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package proves the rendered catalog and map-editor pages send their
run-scoped file and mapping mutations through the authenticated RQ-engine
contracts and return refreshed persisted state.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-08B and recorded the field/action matrix.
- [x] Added actual-render catalog and map-editor contract evidence.
- [x] Ran focused and broad applicable validation; archive this plan.

## Surprises & Discoveries

- Observation: Mature inline-script and RQ-engine suites already cover upload,
  catalog mutation, optimistic concurrency, atomic mapping persistence, and
  authorization; the missing seam was actual rendered endpoint/control data.
  Evidence: `landuse_*_inline.test.js` and
  `test_rq_engine_landuse_routes.py`.

## Decision Log

- Decision: Add direct render assertions and reuse existing downstream tests.
  Rationale: This closes the observed seam without a helper, production patch,
  or duplicate route cases.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-08B closed without a production repair. Actual rendering now proves catalog
endpoint/upload identities and map endpoint/mutation/precondition state.
Existing browser and RQ-engine tests cover authenticated upload, edit, delete,
save, conflict, clear, atomic persistence, and refresh behavior. Focused Python
(169 tests), frontend lint, focused inline Jest (4 tests), full frontend (88
suites, 663 tests), and documentation lint passed. No helper was extracted.

## Plan of Work

Render both standalone templates with risk-bearing seed state and endpoint
URLs. Assert upload identities, mutation controls, and snapshot precondition
data. Run the existing inline browser and RQ-engine route suites, then retain
tests and close if behavior conforms.

## Validation and Acceptance

Run focused render, Flask route, RQ-engine Landuse, and inline Jest tests,
frontend lint and full frontend tests, scoped documentation lint, and
`git diff --check`. RQ graph and generated-bundle checks are not applicable
unless production queue/controller sources change.
