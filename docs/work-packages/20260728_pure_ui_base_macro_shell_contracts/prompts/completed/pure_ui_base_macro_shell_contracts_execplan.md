# Verify Pure UI base and macro shell contracts

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

Pure UI controllers depend on one base document and a shared Jinja macro
library. After this package, direct tests will prove that these producers render
stable field identities, submitted names, values, state, lifecycle regions, and
accessibility hooks. A user can observe success by running the focused render
suite and seeing both producer tests and all completed-DOM consumer tests pass.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SHR-04A and activated it in the parent.
- [x] (2026-07-28 UTC) Inventoried 66 macro importers and 28 base extenders.
- [x] (2026-07-28 UTC) Added direct producer regressions for every material
  macro family.
- [x] (2026-07-28 UTC) Ran all representative completed-DOM consumer
  regressions in the same 105-test suite.
- [x] (2026-07-28 UTC) Confirmed conformance; no production patch was needed.
- [x] (2026-07-28 UTC) Completed focused/broad validation and closed parent
  records.

## Surprises & Discoveries

- Observation: The 1,227-line macro file has broad consumer reach but no
  dedicated producer-level test module.
  Evidence: Existing evidence is distributed across the completed DOM render
  suite.

- Observation: Direct producer tests covered the shared rendering contract
  without exposing a new production mismatch.
  Evidence: All 105 producer and consumer render tests pass without a template
  edit.

## Decision Log

- Decision: Add direct Jinja assertions to the existing render suite.
  Rationale: It already supplies the production loader/globals and keeps exact
  rendered values visible without introducing a helper or registry.
  Date/Author: 2026-07-28 / Codex.

- Decision: Preserve current macro APIs and defaults unless a direct test proves
  conflict with the canonical controller contract.
  Rationale: This is a conformance audit, not a redesign.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Close SHR-04A as a test/documentation-only verification.
  Rationale: Exact rendered identity, state, ARIA, lifecycle, and empty-state
  assertions all pass; changing a conforming producer would broaden risk
  without evidence.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SHR-04A closed with direct coverage for the base document and all material
macro families plus the full completed-DOM consumer render suite. No production
producer changed and no mismatch was found. The focused suite passed 105 tests;
frontend lint/test, scoped documentation lint, and the clean-diff gate also
passed. Transport/session, JavaScript lifecycle, modal/theme/console, and unit
conversion remain independently owned by SHR-02, SHR-03A, SHR-04B, and SHR-05.

## Context and Orientation

`wepppy/weppcloud/templates/base_pure.htm` owns the Pure HTML document shell.
`wepppy/weppcloud/templates/controls/_pure_macros.html` owns form/control
producers. `tests/weppcloud/routes/test_pure_controls_render.py` renders real
templates with a deterministic Jinja environment. The canonical shared
invariants are in `docs/ui-docs/controller-contract.md`.

SHR-04A owns rendering only. SHR-02 owns transport/session behavior, SHR-03A
owns job lifecycle, SHR-04B owns modal/theme/console behavior, and SHR-05 owns
unit conversion/preferences.

## Plan of Work

First render each material producer family with explicit values and assert the
exact HTML identity and state. Then run the existing completed-DOM render suite
as consumer evidence. If a producer conflicts with the canonical contract,
retain the failing regression, re-triage risk, and apply only the smallest
compatible template repair. Finally update the package and parent records and
archive this plan under `prompts/completed/`.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_base_macro_shell_contracts
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

No controller build is required unless controller JavaScript changes. No RQ
graph gate is required unless queue wiring changes.

## Validation and Acceptance

Acceptance requires direct producer coverage for shells/panels, field/choice
state, and structural/ARIA macros; passing representative real consumers; full
frontend lint/test; scoped documentation lint; and a clean diff. A production
repair requires proportional correctness review and security review only if it
changes an attack surface.

## Idempotence and Recovery

Jinja, Jest, lint, and documentation commands are safe to rerun. Preserve
unrelated work and never reset the repository. Keep any repair limited to the
confirmed producer and its direct consumers.

## Interfaces and Dependencies

Use the existing Jinja `Environment` and production templates. Do not add a
dependency, schema, generated index, registry, or new CI workflow.

## Revision Notes

2026-07-28: Created from explicit operator direction after all DOM packages
closed and DOM-12 supplied measured shared-macro evidence.

2026-07-28: Completed as a conformance audit with direct producer coverage and
no production repair.
