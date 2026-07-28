# Execute DOM-10 Soils UI Contract Audit

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Prove Soil form values survive rendering, browser serialization, persistence,
queued build work, and completion hydration.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-10 and added its field matrix.
- [x] Expanded actual-render evidence.
- [x] Validated; archive this plan.

## Surprises & Discoveries

- Observation: The register mentions uploads, but `soil_pure.htm` exposes no
  upload field; its actual risk boundary is modes, selections, build options,
  and queued build lifecycle.
  Evidence: rendered template and `soil.js`.

## Decision Log

- Decision: Audit only values actually produced by this controller.
  Rationale: An invented upload seam would not test a real consumer.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-10 closed without production repair. Expanded actual-render evidence and
existing controller/route/worker tests passed: 204 focused Python tests, lint,
7 focused Jest tests, and docs lint. The unchanged frontend tree's preceding
full sweep passed 88 suites/663 tests. No helper was added.

## Plan of Work

Extend real-template assertions, then reuse focused controller, Flask,
RQ-engine, and worker tests for the remaining path.

## Validation and Acceptance

Run focused Python, Soil Jest, frontend lint/full suite, scoped docs lint, and
`git diff --check`; expect all to pass without production changes.
