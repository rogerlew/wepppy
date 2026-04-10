# WCAG 2.1 AA Remediation for WEPPcloud Frontend Findings 1-6

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work lands, the specific accessibility weak points identified in findings 1-6 are no longer present in the targeted WEPPcloud surfaces. Users who navigate with keyboards and assistive technology can operate copy controls, interact with named dialogs, see clear focus indicators, use explicitly labeled fields, and access standalone pages with correct document semantics. Success is visible when targeted templates/controllers pass new accessibility checks plus existing test gates without functional regressions.

## Progress

- [x] (2026-03-31 22:47Z) Created work-package scaffold and authored `package.md`.
- [x] (2026-03-31 22:47Z) Authored initial tracker and active ExecPlan.
- [x] (2026-03-31 23:49Z) Milestone 1: Remediated finding 1 (legacy copy icon anchors) in scoped report templates.
- [x] (2026-03-31 23:52Z) Milestone 2: Remediated finding 2 (dialog accessible names) for dynamic modal surfaces.
- [x] (2026-03-31 23:53Z) Milestone 3: Remediated finding 3 (focus indicator regressions), including `wc-unitizer__summary`.
- [x] (2026-03-31 23:55Z) Milestone 4: Remediated finding 4 (placeholder-only controls) in command bar and browse templates.
- [x] (2026-03-31 23:56Z) Milestone 5: Resolved finding 5 by removing `role="application"` from scoped map canvas templates.
- [x] (2026-03-31 23:58Z) Milestone 6: Remediated finding 6 standalone document semantics (`lang`, `iframe title`, and missing document title).
- [x] (2026-04-01 00:17Z) Milestone 7: Added accessibility-focused automated regression coverage and ran targeted validation.
- [x] (2026-04-01 00:44Z) Milestone 8: Closed package docs (`package.md`, `tracker.md`, `PROJECT_TRACKER.md`) with outcomes and evidence links.

## Surprises & Discoveries

- Observation: Existing automation already enforces theme contrast AA thresholds, but no structural a11y gate (for semantics/focus/labels) is present.
  Evidence: `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js` plus no `axe`/`jest-axe` usage across frontend tests.

- Observation: Several newer UI modules already have strong accessibility patterns (modal focus trap, status logs, aria-live helpers), so remediation can reuse these conventions instead of introducing a new pattern set.
  Evidence: `wepppy/weppcloud/controllers_js/modal.js`, `wepppy/weppcloud/templates/controls/_pure_macros.html` (`status_panel`, `job_hint`).

- Observation: Broad validation gates currently surface unrelated baseline failures that predate this package, so targeted WCAG checks were used for package-level acceptance evidence.
  Evidence: `tests/weppcloud/routes/test_pure_controls_render.py::test_disturbed_modal_renders_requested_controls` and `wctl run-npm lint` failure in `controllers_js/__tests__/disturbed.test.js` (`jest/prefer-to-be`).

- Observation: Independent regression review identified a copytable heading extraction compatibility gap when controls are button-based instead of anchor-based.
  Evidence: `wepppy/weppcloud/static/js/copytext.js` legacy title extraction heuristic and reviewer findings.

## Decision Log

- Decision: Execute remediation in finding order (1 through 6), then add regression automation as a dedicated milestone.
  Rationale: This keeps implementation traceable to the original assessment while reducing blended-risk edits.
  Date/Author: 2026-03-31 / Codex.

- Decision: Keep this package scoped to targeted remediations and one practical automation increment rather than full-system AA certification.
  Rationale: User request is specific; this keeps scope bounded and shippable.
  Date/Author: 2026-03-31 / Codex.

- Decision: Update `copytext.js` title extraction to be control-agnostic (strip both button and anchor copy controls via DOM clone) and add a Jest regression test.
  Rationale: Prevents copy payload regressions as templates migrate to semantic buttons.
  Date/Author: 2026-03-31 / Codex.

## Outcomes & Retrospective

Implemented findings 1-6 end-to-end across templates, controller JS, and shared CSS, with explicit accessibility regression assertions added to pytest and Jest suites.

Validated outcomes:
- `wctl run-npm test -- map_gl` passed (includes new modal accessible-name test).
- New targeted pytest checks for copy controls, map-role semantics, placeholder-labeling, and standalone metadata passed.
- Bundle rebuild completed via `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`.

Residual validation caveat:
- Broad lint/full-suite pass is currently blocked by unrelated existing failures outside this package scope. These are documented in package tracker artifacts.

Independent review outcome:
- Reviewer-flagged regression risk in copy payload headings was confirmed and fixed.
- Added `controllers_js/__tests__/copytext.test.js` to lock the button-based heading behavior.

## Context and Orientation

This package addresses six code-level findings identified in a repository audit.

Finding 1: Legacy copy controls in report templates are implemented as image-only anchors with `onclick`, which can degrade keyboard/accessibility semantics.

Key paths:
- `wepppy/weppcloud/templates/reports/wepp/prep_details.htm`
- `wepppy/weppcloud/templates/reports/wepp/frq_flood.htm`
- `wepppy/weppcloud/templates/reports/rhem/return_periods.htm`
- `wepppy/weppcloud/templates/reports/rhem/avg_annual_summary.htm`
- `wepppy/weppcloud/templates/reports/wepp/_return_period_simple_table.htm`
- `wepppy/weppcloud/templates/reports/wepp/_return_period_extraneous_table.htm`

Finding 2: One dynamic map feature modal has dialog role semantics but no explicit accessible name.

Key path:
- `wepppy/weppcloud/controllers_js/map_gl_feature_ui.js`

Finding 3: Focus visibility regression exists where an interactive summary removes outlines without replacement.

Key path:
- `wepppy/weppcloud/static/css/ui-foundation.css` (`.wc-unitizer__summary`)

Finding 4: Some controls rely on placeholder text without explicit labeling.

Key paths:
- `wepppy/weppcloud/routes/command_bar/templates/command-bar.htm`
- `wepppy/weppcloud/routes/browse/templates/browse/directory.htm`
- `wepppy/weppcloud/routes/browse/templates/browse/not_found.htm`

Finding 5: Map canvases use `role="application"`; this requires explicit decision and validation because it can override standard virtual-cursor navigation.

Key paths:
- `wepppy/weppcloud/templates/controls/map_pure_gl.htm`
- `wepppy/weppcloud/templates/user/runs2.html`

Finding 6: Standalone templates miss baseline semantics such as document language and iframe titles.

Key paths:
- `wepppy/weppcloud/templates/huc-fire/index.html`
- `wepppy/weppcloud/templates/controls/edit_csv.htm`
- `wepppy/weppcloud/templates/locations/joh/index.htm`

## Plan of Work

Milestone 1 remediates finding-1 templates by replacing non-semantic image anchors with semantic button controls and explicit text/accessible naming, preserving copy-to-clipboard behavior.

Milestone 2 updates modal naming contracts. All dialogs in scope must have accessible names via `aria-labelledby` or `aria-label`, including dynamically created modal markup in map feature UI code.

Milestone 3 restores visible keyboard focus indicators in affected styles. Keep the existing theme system and avoid introducing style drift by reusing established focus tokens (`--wc-color-accent-soft`, etc.).

Milestone 4 addresses placeholder-only inputs by adding explicit labels or robust equivalent naming attributes that are not placeholder-dependent.

Milestone 5 evaluates and resolves `role="application"` map semantics. Either remove it in favor of less intrusive semantics (preferred unless strong rationale exists) or retain it with explicit justification and focused keyboard/screen-reader checks.

Milestone 6 adds missing standalone document semantics (`<html lang>`, iframe `title`) in identified templates.

Milestone 7 adds accessibility-focused automated checks and runs the complete validation matrix.

Milestone 8 closes documentation and tracker artifacts with final status and references.

## Concrete Steps

All commands run from `/workdir/wepppy`.

1. Baseline targeted locations before edits.

    rg -n "<a onclick=|copytable\(|role=\"application\"|<html>|<iframe" wepppy/weppcloud/templates wepppy/weppcloud/routes --glob "**/*.htm" --glob "**/*.html"
    rg -n "wc-unitizer__summary|aria-modal|role=\"dialog\"" wepppy/weppcloud/static/css/ui-foundation.css wepppy/weppcloud/controllers_js/map_gl_feature_ui.js

2. Implement finding 1 and finding 2 changes in templates/controllers.

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-pytest tests/weppcloud/test_jinja_filters.py --maxfail=1
    wctl run-npm test -- disturbed map

3. Implement finding 3 and finding 4 changes (focus + labels).

    wctl run-npm lint
    wctl run-npm test

4. Implement finding 5 and finding 6 changes (map semantics + standalone metadata).

    wctl run-pytest tests/weppcloud --maxfail=1

5. Add and run accessibility-focused regression checks.

    cd wepppy/weppcloud/static-src
    npm run smoke -- tests/smoke/run-page-smoke.spec.js
    npm run smoke -- tests/smoke/map-gl.spec.js
    cd /workdir/wepppy

6. Run full final validation and doc lint.

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260331_wcag21aa_frontend_accessibility
    wctl doc-lint --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance requires all of the following:

- Finding 1 controls are semantic interactive elements and expose an accessible name.
- Finding 2 dialogs (including dynamic map feature modal) expose accessible names.
- Finding 3 focus targets show visible keyboard focus styles.
- Finding 4 placeholder-only controls in scope have explicit labels/names.
- Finding 5 map role decision is implemented and documented with validation evidence.
- Finding 6 standalone template semantics are corrected (`lang`, iframe `title`).
- Existing theme contrast smoke checks still pass.
- New accessibility-focused regression checks pass.
- Full Python and frontend test gates pass.

## Idempotence and Recovery

- Template and CSS changes are additive and can be re-run safely.
- If a specific remediation causes UX regression, revert that file-level change and re-run targeted tests before continuing.
- Keep map-semantics edits isolated to designated templates to allow low-risk rollback.
- Preserve existing runtime route/controller contracts unless explicitly required for accessibility semantics.

## Artifacts and Notes

At closure, add these artifacts under this package directory (or link to existing generated artifacts if retained elsewhere):

- Accessibility remediation summary by finding (1-6) with before/after references.
- Validation command log excerpt (pass/fail summary).
- Any smoke/a11y report outputs generated during Milestone 7.

## Interfaces and Dependencies

- Modal behavior depends on `wepppy/weppcloud/controllers_js/modal.js`; naming changes must remain compatible with existing focus trap and dismiss semantics.
- Shared focus styling must stay compatible with `wepppy/weppcloud/static/css/themes/all-themes.css` token overrides.
- Existing contrast automation in `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js` remains part of regression gates.

---

Revision note (2026-04-01 00:44Z): Independent regression review completed; copytable compatibility fix + test added; package docs closed with validation evidence.
