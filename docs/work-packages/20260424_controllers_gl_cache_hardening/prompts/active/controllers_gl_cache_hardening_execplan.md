# Controllers-GL Cache Hardening Rollout ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference process: `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users should never stay on a stale `controllers-gl.js` silently. After this package, every WEPPcloud template that loads `controllers-gl.js` will use `static_url(...)` cache-busted links and will also load `controllers_gl_stale_check.js` so users get a clear reload prompt if HTML and JS bundle versions drift.

## Progress

- [x] (2026-04-24 17:03 UTC) Work-package scaffold created.
- [x] (2026-04-24 17:03 UTC) Active ExecPlan created with required review milestones.
- [x] (2026-04-24 18:05 UTC) Built definitive template inventory and froze edit list (19 WEPPcloud templates include `controllers-gl.js`).
- [x] (2026-04-24 18:12 UTC) Implemented include remediation (`controllers-gl.js` via `static_url`) and stale-check include coverage.
- [x] (2026-04-24 18:17 UTC) Added regression coverage for include invariants in `tests/weppcloud/test_stale_controllers_gl_template_wiring.py`.
- [x] (2026-04-24 18:26 UTC) Ran targeted validation commands and captured evidence.
- [x] (2026-04-24 18:30 UTC) Completed independent code review and dispositioned findings.
- [x] (2026-04-24 18:32 UTC) Completed independent QA review and dispositioned findings.
- [x] (2026-04-24 18:33 UTC) Finalized package docs/tracker and closed lifecycle state updates.

## Surprises & Discoveries

- Observation: `wepppy/weppcloud/routes/batch_runner/templates/layout.j2` still used `{{ site_prefix }}/static/js/controllers-gl.js` instead of helper-based asset URLs.
  Evidence: Inventory grep hit in `layout.j2:19`; patched to `static_url` + stale-check include.

- Observation: The required npm command emits npm CLI warnings (`--runTestsByPath` treated as argument) but still runs the intended Jest path via wrapper.
  Evidence: `wctl run-npm test -- --runTestsByPath ...controllers_gl_stale_check.test.js` output shows warnings followed by `PASS` for the expected suite.

- Observation: Existing stale-check wiring test covered only a subset of templates and required `defer`, which would not catch non-deferred include regressions.
  Evidence: Updated `tests/weppcloud/test_stale_controllers_gl_template_wiring.py` with inventory-driven assertions across all templates containing `controllers-gl.js`.

## Decision Log

- Decision: Keep this package scoped to include-hygiene only (`static_url` + stale-check include coverage).
  Rationale: Fast, low-risk hardening directly addresses incident vector.
  Date/Author: 2026-04-24 / Codex.

- Decision: Preserve per-template script-loading behavior (`defer` preserved where present; not added where previously absent).
  Rationale: Requirement was include hardening with stable behavior and script order, not execution-mode changes.
  Date/Author: 2026-04-24 / Codex.

- Decision: Use an inventory-based regression test over all WEPPcloud templates containing `controllers-gl.js`.
  Rationale: This prevents future drift in either include style (`static_url`) or stale-check pairing across route/template families.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

Implemented the full package scope end-to-end:
- All 19 WEPPcloud templates that include `controllers-gl.js` now use `static_url('js/controllers-gl.js')`.
- All 19 now load `controllers_gl_stale_check.js` immediately after `controllers-gl.js`.
- Regression coverage now enforces this invariant repository-wide for template files.
- Required validation commands and additional targeted tests passed.
- Code review and QA review gates completed with no unresolved medium/high findings.

No residual blockers were discovered for this package scope.

## Context and Orientation

`controllers-gl.js` build identity and stale-checking already exist:
- Build id is exposed from the generated bundle (`window.__weppControllersGlBuildId`) via `wepppy/weppcloud/controllers_js/templates/controllers.js.j2`.
- Expected build id and cache-busted static helper come from `wepppy/weppcloud/_context_processors.py` (`static_url`, `controllers_gl_expected_build_id`).
- Stale banner behavior is implemented in `wepppy/weppcloud/static/js/controllers_gl_stale_check.js`.

The drift was adoption consistency: some templates still included `controllers-gl.js` through `url_for('static', ...)` or raw `/static/...` paths, and some templates loaded `controllers-gl.js` without loading `controllers_gl_stale_check.js` immediately after.

## Plan of Work

Milestone 1 (Inventory): enumerate all templates in `wepppy/weppcloud/**` that include `controllers-gl.js`; freeze the exact file list and classify each include as compliant/non-compliant for:
1) `static_url('js/controllers-gl.js')` usage and
2) adjacent stale-check include presence.

Milestone 2 (Implementation): patch only the non-compliant files. Preserve existing script order and defer behavior changes beyond include method and stale-check coverage.

Milestone 3 (Regression + Validation): run targeted render and JS tests, and add regression tests to fail if templates regress to non-compliant include patterns.

Milestone 4 (Code Review): run independent correctness-focused review over changed files; record findings and disposition in `artifacts/2026-04-24_code_review.md`; resolve all medium/high findings.

Milestone 5 (QA Review): run independent QA/test-quality review; record findings and disposition in `artifacts/2026-04-24_qa_review.md`; resolve all medium/high findings and validate final test matrix.

Milestone 6 (Closure): update tracker, package deliverables, and `PROJECT_TRACKER.md` lifecycle state.

## Concrete Steps

Working directory: `/home/workdir/wepppy`

1. Inventory templates:
   `rg -n "controllers-gl.js" wepppy/weppcloud/templates wepppy/weppcloud/routes -S`

2. Find non-compliant include style:
   `rg -n "url_for\('static', filename='js/controllers-gl.js'\)|/static/js/controllers-gl.js" wepppy/weppcloud/templates wepppy/weppcloud/routes -S`

3. Patch template include tags.

4. Run validation commands:
   `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
   `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/controllers_gl_stale_check.test.js`
   `wctl run-pytest tests/weppcloud/test_stale_controllers_gl_template_wiring.py --maxfail=1`

5. Execute code review and QA review milestones; record and disposition findings.

## Validation and Acceptance

Acceptance requires all of the following:
- Every WEPPcloud template loading `controllers-gl.js` uses `static_url('js/controllers-gl.js')`.
- Every WEPPcloud template loading `controllers-gl.js` also loads `controllers_gl_stale_check.js` after it.
- Required targeted tests pass.
- No unresolved medium/high findings remain after code + QA reviews.

Status: complete; all acceptance criteria met.

## Idempotence and Recovery

Edits are idempotent: re-running inventory commands shows zero remaining non-compliant includes.

## Artifacts and Notes

- Code review artifact: `docs/work-packages/20260424_controllers_gl_cache_hardening/artifacts/2026-04-24_code_review.md`
- QA review artifact: `docs/work-packages/20260424_controllers_gl_cache_hardening/artifacts/2026-04-24_qa_review.md`

## Interfaces and Dependencies

Use existing WEPPcloud template helpers and stale-check implementation. No new client-side stale detection protocols were introduced in this package.

## Plan Revision Log

- 2026-04-24 / Codex: Initial ExecPlan created to operationalize package scope and mandatory review milestones.
- 2026-04-24 / Codex: Completed full execution cycle (inventory, implementation, regression coverage, validation, review gates, closure updates).
