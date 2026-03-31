# WCAG 2.1 AA Frontend Accessibility Remediation (Findings 1-6)

**Status**: Implemented (2026-03-31)

## Overview
This package remediates six high-confidence WCAG 2.1 AA weak points identified in the WEPPcloud frontend codebase: legacy non-semantic copy controls, modal accessible-name gaps, missing/weak focus indicators, placeholder-only input labeling, `role="application"` map semantics, and missing document/iframe baseline attributes in standalone templates. The goal is to remove known accessibility debt in core UI paths while preserving existing runtime behavior and contracts.

## Objectives
- Replace or harden legacy non-semantic copy controls so they are keyboard-operable, named, and screen-reader friendly.
- Ensure all dialog surfaces have explicit accessible names and preserve modal focus management.
- Restore or add visible, keyboard-discernible focus styling where currently removed or ambiguous.
- Eliminate placeholder-only form controls by adding explicit labels or equivalent accessible naming.
- Reassess `role="application"` usage on map canvases and migrate to safer semantics where appropriate.
- Add missing `lang`/`title` and related baseline semantics for standalone HTML surfaces.
- Add automated accessibility checks to prevent regression on the addressed patterns.

## Scope
This package covers targeted frontend template, CSS, and controller changes in WEPPcloud and associated tests/documentation needed to lock in the six remediation categories.

### Included
- WEPPcloud templates under `wepppy/weppcloud/templates/**` and route-local templates under `wepppy/weppcloud/routes/**/templates/**` tied to findings 1-6.
- Relevant controller/static JS in `wepppy/weppcloud/controllers_js/**` and `wepppy/weppcloud/static/js/**` for modal semantics and map role behavior.
- Shared style fixes in `wepppy/weppcloud/static/css/ui-foundation.css` and focused template-local style blocks where needed.
- Targeted pytest/Jest/Playwright updates and new a11y checks for modified surfaces.
- Package-local and canonical docs updates reflecting final accessibility contract changes.

### Explicitly Out of Scope
- Full product-wide WCAG certification or third-party audit attestation.
- Complete redesign of map interaction UX beyond semantics/keyboard and focus requirements needed for AA conformance targets in scope.
- Broad visual refresh unrelated to accessibility failures.
- Unrelated legacy refactors outside the six confirmed finding categories.

## Stakeholders
- **Primary**: WEPPcloud end users (keyboard and assistive-technology users), frontend maintainers.
- **Reviewers**: WEPPcloud templates/controllers maintainers; QA maintainers for smoke and route test coverage.
- **Informed**: Docs maintainers and release owners.

## Success Criteria
- [x] All finding-1 copy controls use semantic interactive elements and have accessible names in affected report templates.
- [x] All finding-2 dialog surfaces have explicit accessible names (`aria-labelledby` or `aria-label`) and pass keyboard trap/escape checks.
- [x] All finding-3 focus-regression targets show a visible keyboard focus indicator.
- [x] All finding-4 placeholder-only controls in scoped files have explicit labels or equivalent robust accessible naming.
- [x] Finding-5 map semantic decision is implemented and documented (role retained with justification and tests, or replaced).
- [x] Finding-6 standalone HTML semantic gaps (`lang`, iframe `title`, etc.) are remediated in scoped templates.
- [x] Automated regression coverage includes at least one accessibility-focused gate beyond contrast checks.
- [ ] Full validation matrix passes (`pytest`, `npm lint/test`, smoke/a11y checks, doc lint).

Validation caveat (2026-03-31): broad suite/lint gates currently fail due pre-existing unrelated failures in
`tests/weppcloud/routes/test_pure_controls_render.py::test_disturbed_modal_renders_requested_controls` and
`wepppy/weppcloud/controllers_js/__tests__/disturbed.test.js` (`jest/prefer-to-be`), while all new scoped WCAG checks pass.

## Dependencies

### Prerequisites
- Existing WCAG risk assessment baseline (code references collected on 2026-03-31).
- Existing modal infrastructure in `wepppy/weppcloud/controllers_js/modal.js`.
- Existing theme contrast smoke harness (`wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js`).

### Blocks
- Follow-on package for broader AA hardening outside findings 1-6.
- Future accessibility governance and policy documentation updates dependent on remediation outcomes.

## Related Packages
- **Related**: [20260330_disturbed_panel_modal](../20260330_disturbed_panel_modal/package.md)
- **Related**: [20251027_ui_style_guide_refresh](../20251027_ui_style_guide_refresh/package.md)
- **Follow-up**: Potential package for full keyboard/screen-reader journey audits across run/report screens.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/weppcloud/templates/reports/wepp/prep_details.htm` - legacy copy icon anchor pattern.
- `wepppy/weppcloud/templates/reports/wepp/_return_period_simple_table.htm` - legacy copy icon macro usage.
- `wepppy/weppcloud/controllers_js/map_gl_feature_ui.js` - modal creation semantics.
- `wepppy/weppcloud/static/css/ui-foundation.css` - shared focus styles and regressions.
- `wepppy/weppcloud/routes/command_bar/templates/command-bar.htm` - placeholder-only control candidates.
- `wepppy/weppcloud/templates/controls/map_pure_gl.htm` - map role semantics.
- `wepppy/weppcloud/templates/huc-fire/index.html` - missing standalone `lang`.
- `wepppy/weppcloud/templates/locations/joh/index.htm` - iframe `title` gaps.
- `docs/work-packages/20260331_wcag21aa_frontend_accessibility/prompts/active/wcag21aa_frontend_accessibility_execplan.md` - active execution plan.

## Deliverables
- Active ExecPlan with milestone-level remediation and validation steps.
- Targeted frontend/template/controller fixes for findings 1-6.
- Regression tests and accessibility-focused automation updates.
- Updated tracker, package notes, and closure summary with evidence links.

## Follow-up Work
- Full-route accessibility crawl (maps, command surfaces, report tables) with prioritized backlog.
- Additional checks for accessible table names/headers and dynamic announcement consistency.
- Optional adoption of broader a11y test tooling across smoke suites.
