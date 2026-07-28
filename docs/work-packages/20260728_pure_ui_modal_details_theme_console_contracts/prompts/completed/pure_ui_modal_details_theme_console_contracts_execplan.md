# Verify modal, details, theme, and console contracts

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

Pure UI pages share modal focus management, dismissible details menus, theme
selection, and console configuration/rendering. After SHR-04B, direct tests
will prove that these behaviors remain accessible and deterministic, including
when a script executes more than once. A developer can observe success by
running the focused Jest and Jinja suites and seeing the shared producers and
representative consumers pass.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SHR-04B and activated it in the parent.
- [x] (2026-07-28 UTC) Inventoried shared sources, generated theme output,
  macros, and representative hosts.
- [x] (2026-07-28 UTC) Added four direct Jest tests for the JavaScript
  producers.
- [x] (2026-07-28 UTC) Added actual-render assertions for console/table macros
  and modal/theme producers.
- [x] (2026-07-28 UTC) Repaired three duplicate-initialization mismatches and
  one nested-caller rendering mismatch.
- [x] (2026-07-28 UTC) Completed focused/broad validation and closed parent
  records.

## Surprises & Discoveries

- Observation: Modal, details, and theme behavior is bundled from controller
  sources, while console configuration is a standalone static script.
  Evidence: `build_controllers_js.py` includes the first three in generated
  outputs; console hosts load `static/js/console_utils.js` directly.

- Observation: Run pages can execute theme behavior from both the standalone
  theme asset and the controller bundle.
  Evidence: Before repair, a second module execution emitted a second initial
  `wc-theme:change` event and installed another change listener.

- Observation: Nested Jinja call blocks shadowed `table_page`'s outer caller.
  Evidence: The direct render contained the table-page header but omitted
  `table_panel` and its table until caller output was captured first.

- Observation: Independent correctness review found no production defect and
  two low-severity evidence gaps.
  Evidence: Modal public/dismiss paths and the source/generated theme
  cross-load seam were added; focused Jest and render suites remained green.

- Observation: The broad Python suite reproduced the known unrelated GridMET
  fixture failure.
  Evidence: 2,452 passed and 40 skipped before `_FakeUnits.degC` failed in
  `test_gridmet_interpolation_propagates_unpublished_suffix_to_parquet_and_prn`.

## Decision Log

- Decision: Use direct Jest imports, module-cache resets, and production markup
  rather than a new helper framework.
  Rationale: Existing jsdom tests already provide the exact browser seam and a
  second import after reset reproduces duplicate script execution.
  Date/Author: 2026-07-28 / Codex.

- Decision: Keep domain console transport and mutations outside SHR-04B.
  Rationale: SHR-04B owns shared producers; registered SURF packages own the
  stateful workflows that consume them.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Add producer-local global guards without changing public APIs.
  Rationale: The canonical controller contract requires singleton/idempotent
  behavior, and early return is the smallest compatible duplicate-load repair.
  Date/Author: 2026-07-28 / Codex.

- Decision: Capture `table_page` caller output before nested macro calls.
  Rationale: It restores the macro's existing content contract without changing
  its signature, styling, or consumers.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SHR-04B closed with four direct Jest tests and 108 passing rendered-template
tests.
Duplicate module execution now preserves one modal manager, one details-menu
listener set, and one theme initializer/listener. `table_page` again renders
its caller content through the nested console shell. The standalone generated
theme asset was rebuilt from `controllers_js/theme.js`; the ignored local
controller bundle was also rebuilt for runtime verification. Console config,
console macros, and accessible modal/theme markup required no repair. Unit
preferences and stateful console workflows remain with SHR-05 and their SURF
owners. Full frontend validation passed 89 suites and 667 tests. The broad
Python sweep stopped only at the plan-known unrelated GridMET fixture failure
after 2,452 passes and 40 skips.

## Context and Orientation

`wepppy/weppcloud/controllers_js/modal.js` manages modal state and focus.
`details_menu.js` closes run/navigation details menus. `theme.js` persists and
applies the selected theme and generates `wepppy/weppcloud/static/js/theme.js`.
`wepppy/weppcloud/static/js/console_utils.js` merges console configuration.
`wepppy/weppcloud/templates/shared/console_macros.htm` renders common console
shells and buttons. The shared idempotence rule is in
`docs/ui-docs/controller-contract.md`.

## Plan of Work

First add direct Jest coverage for normal behavior, failure-tolerant storage,
and duplicate execution of each JavaScript producer. Add direct Jinja coverage
for shared macro identities/actions and representative modal/theme markup.
When a test proves conflict with the canonical singleton/idempotence rule,
retain it and apply the smallest producer-local repair. Rebuild generated
controller/theme outputs after controller-source edits. Then reconcile the
child and parent records and archive this plan.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- shared_ui_contracts
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_modal_details_theme_console_contracts
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

The controller build is required if any bundled source changes. RQ graph,
stub, and backend security gates are not required without corresponding file
changes.

## Validation and Acceptance

Acceptance requires direct proof of modal keyboard/focus/state, details-menu
dismissal, theme persistence/synchronization/events, console configuration,
duplicate execution, and rendered producer hooks. Generated theme and
controller bundles must match their sources. Full frontend lint/test and the
existing rendered-template suite must pass.

## Idempotence and Recovery

Jest, Jinja, build, lint, and documentation commands are safe to rerun. Never
edit generated bundles directly. Preserve unrelated work and keep any repair
inside the producer whose direct regression proves the mismatch.

## Interfaces and Dependencies

Use the existing globals `ModalManager`, `WCDetailsMenu`, and
`WCConsoleConfig`, the `wc-theme:change` event, and current Jinja macros. Add no
dependency, registry, generator, or new public API unless a canonical contract
decision explicitly requires it.

## Revision Notes

2026-07-28: Created from explicit operator direction after SHR-04A closed.

2026-07-28: Completed with four minimal conformance repairs and direct
producer/consumer regression evidence.
