# Verify Pure UI Unitizer preferences end to end

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

Users can select global SI/English units or override an individual measurement
category and see the selection applied, persisted for the active run, and
restored after reload. Success is observable through direct template,
browser-controller, route, NoDb, and generated-map tests without changing
conversion parameterization.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SHR-05 and ratified its concise intent.
- [x] (2026-07-28 UTC) Traced template, client, Project, route, NoDb, generated
  map, and existing test boundaries.
- [x] (2026-07-28 UTC) Added direct rendering and missing client regressions.
- [x] (2026-07-28 UTC) Extended Project, route, NoDb, and generated-map
  evidence; focused sets pass.
- [x] (2026-07-28 UTC) Repaired regression-proven global-state, selector, and
  event-ownership mismatches without changing parameterization.
- [x] (2026-07-28 UTC) Ran focused/broad validation, reconciled parent records,
  passed independent security review, and closed.

## Surprises & Discoveries

- Observation: Preference mutation has no RQ boundary.
  Evidence: Project posts synchronously to `unitizer_bp`, whose Unitizer locked
  context performs the NoDb dump before returning.

- Observation: Mixed category preferences returned `is_english=None`, but the
  template's broad falsy check marked global SI selected.
  Evidence: The new mixed-state render regression failed until the template
  required literal `false`.

- Observation: Source and generated controller state had drifted on the global
  radio selector.
  Evidence: `unitizer_client.js` used `uni_main_selector` while the producer and
  already-generated bundle used `unit_main_selector`.

- Observation: Correcting obsolete report-shell selectors would reactivate
  duplicate change handlers beside Project delegation.
  Evidence: Independent security review identified a redundant-write race; the
  shells now retain initial sync only and a Jest regression proves one POST.

## Decision Log

- Decision: Freeze all conversion and default parameterization.
  Rationale: The selected package is contract verification; changing formulas,
  precision, categories, tokens, or defaults would require a separate approved
  normative decision and ADR.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Use the actual rendered category inventory plus generated-map
  parity rather than duplicating conversion definitions in tests.
  Rationale: This proves every authoritative category while keeping one source
  of conversion truth.
  Date/Author: 2026-07-28 / Codex.

- Decision: Make Project the sole Unitizer change-event owner.
  Rationale: Delegated `data-project-unitizer` handlers already cover global
  and category changes; shell-local listeners duplicated asynchronous
  persistence and could race stale state.
  Date/Author: 2026-07-28 / Codex, confirmed by independent security review.

## Outcomes & Retrospective

SHR-05 closed with exact end-to-end preference evidence and four bounded
repairs: literal mixed-state rendering, the client selector typo, the run
bootstrap selector typo, and removal of duplicate shell event ownership.
Conversion formulas/defaults and backend authorization/persistence contracts
did not change. Focused render (114), Unitizer Python/Node (16), and Project
Jest (31) tests pass; full frontend lint/test passes with 89 suites and 670
tests. Independent security review passed with no unresolved findings.
The broad Python gate reached 2,452 passed and 40 skipped before reproducing
the known unrelated GridMET `_FakeUnits.degC` fixture failure; all SHR-05
focused Python evidence passes.

## Context and Orientation

`wepppy/nodb/unitizer.py` owns categories, conversion functions, preferences,
and NoDb persistence. `unitizer_map_builder.py` generates the browser map.
`unitizer_client.js` applies conversions and DOM state. `project.js` delegates
radio changes and posts the complete map to `unitizer_bp.py`. The modal and
radio producers live under `templates/controls/`.

## Plan of Work

Render the actual modal with metric, English, and mixed persisted states and
assert exact field identities, tokens, checked state, accessibility, and full
category coverage. Exercise UnitizerClient global/category selection, label and
numeric updates, event detail, absent inputs, and invalid tokens. Retain and
extend Project request/lifecycle, route filtering, NoDb persistence/reload, and
map-builder parity evidence. If a direct regression proves divergence from the
concise contract, apply only the smallest compatible repair and obtain
proportional correctness/security review.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_unitizer_bp.py tests/nodb/test_unitizer_preferences.py --maxfail=1
    wctl run-pytest tests/weppcloud/controllers_js/test_unitizer_map_builder.py tests/weppcloud/controllers_js/test_unitizer_client_js.py --maxfail=1
    wctl run-npm test -- project
    wctl run-npm lint
    wctl run-npm test
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_unitizer_preferences_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Build the controller bundle only if controller source changes. No RQ graph or
stub gate applies without corresponding implementation changes.

## Validation and Acceptance

Acceptance requires actual-render proof of all preference fields, browser proof
of global/category DOM conversion and complete persisted payloads, route/NoDb
proof of compatible validation and reload, and exact generated-map parity.
Focused Python/JavaScript and full frontend/documentation gates must pass.

## Idempotence and Recovery

All tests, lint, map generation, and documentation commands are safe to rerun.
The generated bundle must be rebuilt from source, never edited directly.
Preserve unrelated work and stop if an intended parameter/default change is
needed.

## Interfaces and Dependencies

Keep current `data-project-unitizer` hooks, `UnitizerClient` public methods,
Project lifecycle events, `/tasks/set_unit_preferences/` JSON response shape,
and NoDb keys. Add no dependency, queue path, schema, or fallback wrapper.

## Revision Notes

2026-07-28: Created from explicit operator direction after SURF-12 closed.
