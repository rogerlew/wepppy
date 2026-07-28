# Verify Pure UI report shell and readonly contracts

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

WEPPcloud reports share one Pure shell and one older report shell. After
SURF-12, direct tests will prove these producers display the correct run and
readonly state, preserve report content, and load their common navigation,
modal, unit, command-bar, and script hooks. A developer can observe success by
running the focused render suite and seeing both producers and their finite
consumers pass.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-12 and activated it in the parent.
- [x] (2026-07-28 UTC) Inventoried 14 Pure-shell and 5 legacy-shell consumers.
- [x] (2026-07-28 UTC) Recorded the concise presentation/readonly contract.
- [x] (2026-07-28 UTC) Added direct producer and finite-consumer render
  regressions; the render suite passes 113 tests.
- [x] (2026-07-28 UTC) Ran applicable Project and report-route evidence; 28
  Jest tests and 124 route tests pass.
- [x] (2026-07-28 UTC) Confirmed canonical conformance; no production repair
  was required.
- [x] (2026-07-28 UTC) Completed focused/broad validation and closed parent
  records.

## Surprises & Discoveries

- Observation: Five current RHEM/WEPP reports still inherit the standalone
  Bootstrap-era `_page_container.htm`.
  Evidence: Direct inheritance search found two RHEM and three WEPP consumers;
  migration is not required to verify their current presentation contract.

- Observation: The global theme class also contains `wc-run-header`, so an
  absence test must target the exact run-header element rather than an
  incidental class token.
  Evidence: The first absent-run regression was narrowed to exact header
  markup and then passed.

- Observation: The legacy producer expects the application `static_url`
  context helper.
  Evidence: Supplying that real context boundary in the direct fixture made
  the render test representative without changing production.

## Decision Log

- Decision: Treat SURF-12 as faithful verification, not shell modernization.
  Rationale: The operator selected the registered producer contract; redesign
  would broaden scope and risk without a canonical intent decision.
  Date/Author: 2026-07-28 / Codex.

- Decision: The shell reflects readonly state but does not own persistence.
  Rationale: `data-project-toggle` and `disable-readonly` are consumed by the
  Project controller, whose mutation path is already owned by DOM-02.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Retain all domain report bodies under their existing DOM/SURF
  owners and verify only direct inheritance/content participation here.
  Rationale: This proves finite shell fan-out without duplicating domain
  calculation or interaction ownership.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SURF-12 closed with no production mismatch or repair. Five direct regressions
prove both producers, persisted readonly/public projection, PUP scoping,
absent-run fallback, shared runtime targets, and all 19 direct consumers.
The focused evidence passed with 113 render tests, 124 route tests, and 28
Project Jest tests; full frontend lint/test and documentation/diff gates also
passed. Domain report calculations and interactions remain intentionally owned
by their existing DOM/SURF packages.

## Context and Orientation

`wepppy/weppcloud/templates/reports/_base_report.htm` extends `base_pure.htm`
and renders the modern full-width report header and shared controls.
`wepppy/weppcloud/templates/reports/_page_container.htm` is a standalone legacy
shell retained by five reports. `tests/weppcloud/routes/test_pure_controls_render.py`
provides a production Jinja loader. Focused route suites under
`tests/weppcloud/routes/` prove Ash, Debris Flow, Geneva, RHEM, Observed, Storm
Event Analyzer, and WEPP route context.

## Plan of Work

First render the Pure shell with explicit mutable and readonly states and assert
exact identities, values, checked state, absent PUP links, shared components,
and script/runtime hooks. Render the legacy shell and assert its supported
content and stale-build contract. Inventory every direct consumer and render
representatives only where domain fixtures are practical; retain existing
domain route/render evidence after inspection. If a shell contradicts the
concise intent contract, retain the failing regression and apply only the
smallest compatible repair. Then reconcile all child and parent records.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_project_bp.py tests/weppcloud/routes/test_rhem_bp.py tests/weppcloud/routes/test_debris_flow_bp.py --maxfail=1
    wctl run-npm test -- project
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_report_shell_readonly_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

No controller build is required unless controller source changes. No RQ graph
or stub gate is required without corresponding implementation changes.

## Validation and Acceptance

Acceptance requires direct proof of the two shell producers, persisted readonly
and public rendering, Project-compatible hooks, PUP-sensitive navigation,
shared UI/script targets, all direct consumer ownership, and existing route
context. Full frontend and scoped Python/documentation suites must pass.

## Idempotence and Recovery

Jinja, Jest, lint, and documentation commands are safe to rerun. Preserve
unrelated work and keep repairs inside the shell producer whose regression
proves the mismatch. Do not migrate legacy consumers or alter domain outputs.

## Interfaces and Dependencies

Use existing Jinja blocks and globals, `data-project-*` hooks, Project
controller behavior, modal/theme primitives, and route context objects. Add no
dependency, registry, generated index, or new persistence path.

## Revision Notes

2026-07-28: Created from explicit operator direction after SHR-04A/04B closed.
