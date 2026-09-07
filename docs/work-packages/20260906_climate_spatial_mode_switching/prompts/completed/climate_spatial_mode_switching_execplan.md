# Restore climate spatial choices after dataset switching


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


A user can load Climate Options with Vanilla CLIGEN or stochastic PRISM, select
available observed Daymet or gridMET, and choose Multiple climates (Interpolated)
without reloading. Spatial mode 2 is the existing numeric interpolation option.

## Progress


- [x] (2026-09-07 03:13 UTC) Trace defect and record unchanged authority in package.md.
- [x] (2026-09-07 03:18 UTC) Add regression tests before patch.
- [x] (2026-09-07 03:18 UTC) Patch template and update guidance.
- [x] (2026-09-07 03:29 UTC) Validate, independently review, and record outcomes.

## Surprises & Discoveries


The backend catalog already supports both datasets. The controller caches the
radios present at initialization, while Jinja omits radios based solely on the
initial dataset. A render regression is necessary to catch this missing DOM state.

## Decision Log


2026-09-07 03:13 UTC, Codex: Restore contract conformance using the supplied
catalog union, not global options. No backend or capability expansion is needed.

## Outcomes & Retrospective


Completed locally: template union restored, 16 render matrix cases and two
controller regressions added, and guidance updated. Focused pytest: 212 passed;
full frontend: 835 passed. Independent review passed. Full pytest stopped after
5078 passes and 50 skips on an unrelated unchanged shape-converter Compose
assertion, reproduced in isolation. See tracker.md for gate disposition.
No live deployment or climate build was performed. Host Python lacks Jinja2;
rebuild succeeded with `wctl exec weppcloud python
wepppy/weppcloud/controllers_js/build_controllers_js.py` as one command.
The key lesson is to test initial rendered markup together with controller
switching: a controller cannot enable an option omitted from the DOM.

## Context and Orientation


`wepppy/weppcloud/templates/controls/climate_pure.htm` renders spatial radios.
`wepppy/weppcloud/controllers_js/climate.js` caches them and enables supported
modes when the dataset changes. `tests/weppcloud/routes/test_pure_controls_render.py`
exercises the real template. Controller Jest tests live in
`wepppy/weppcloud/controllers_js/__tests__/climate.test.js`.

## Plan of Work


Extend real-template coverage for each observed dataset, restricted catalogs,
and initial Vanilla/PRISM selections. Confirm failure before editing production.
Render the union from selectable supplied datasets, preserve exact-current
rendering, and disable modes outside the selected dataset. Correct DAYMET naming
in help. Add controller switching/submission coverage and update user/developer
documentation. Obtain independent correctness review per work-package policy.

## Concrete Steps


From `/home/workdir/wepppy`, run `wctl run-pytest
 tests/weppcloud/routes/test_pure_controls_render.py` (as one shell command).
Run `wctl run-npm lint`, `wctl run-npm test`, and
`wctl run-pytest tests --maxfail=1`. Rebuild using
`python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` if files under
controllers_js change. Lint changed docs with `wctl doc-lint --path <file>`.

## Validation and Acceptance


Mode 2 exists but is disabled on initial Vanilla/PRISM, becomes enabled when
either authorized observed dataset is selected, submits spatialmode 2, and is
disabled with a valid selection restored on switching back. Restricted catalogs
must not acquire mode 2. Preserve disabled stored modes and read-only behavior.
Record actual gate results and limitations in tracker.md; do not imply tests
exercised a live climate build.

## Idempotence and Recovery


Edits and tests can be repeated. Revert only this package's edits to undo the
fix. No run data, schema, external state, or deployment is mutated.

## Artifacts and Notes


Independent correctness review belongs in artifacts/20260906_correctness_review.md.

## Interfaces and Dependencies


Retain the catalog fields spatial_modes, disabled_spatial_modes, ui_exposed,
and current_selection_disabled, plus the existing climate_spatialmode radio
names and values. No new dependencies or public interfaces.

Revision 2026-09-07 03:13 UTC: initial plan and conformance scope.

Revision 2026-09-07 03:29 UTC: completed fix, validation and independent review;
recorded unrelated broad-test failure and runtime legacy-current limitation.
