# UI Lab Light Landing Keyboard Access

**Status**: Closed (2026-06-29)
**Timezone**: UTC

## Overview

The WEPPcloud UI Lab light landing page must be usable without a mouse. The current deployed light variant at `/weppcloud/landing/light/` can render as an empty React root because its exported assets resolve under the wrong route, and the map/filter surface needs explicit keyboard semantics so users can tab through the page predictably.

This package fixes the installed light landing page, adds automated keyboard accessibility coverage, rebuilds the exported UI Lab bundle, and verifies the result in the local WEPPcloud deployment.

## Objectives

- Restore the `/weppcloud/landing/light/` variant so the React app and focusable controls load from WEPPcloud.
- Make the light landing page's map/filter controls reachable, named, and operable by keyboard.
- Add Playwright regression coverage that validates tab traversal on the installed WEPPcloud route.
- Rebuild and install the UI Lab landing bundle under `wepppy/weppcloud/static/ui-lab/`.
- Record validation evidence in this work package and keep root package tracking current.

## Scope

### Included

- `weppcloud-ui-lab/src/AppLight.tsx` keyboard and semantic accessibility fixes.
- `weppcloud-ui-lab/src/index-light.css` focus visibility and map accessibility styling.
- WEPPcloud landing asset route compatibility for `/landing/light/`.
- Playwright smoke coverage under `wepppy/weppcloud/static-src/tests/smoke/`.
- Exported/generated UI Lab bundle installed under `wepppy/weppcloud/static/ui-lab/`.
- Work-package documentation, tracker updates, and root `PROJECT_TRACKER.md` entry.

### Explicitly Out of Scope

- Dark landing page redesign beyond any incidental shared route compatibility.
- Full VPAT/ACR refresh; this is a focused remediation with local evidence.
- Replacing the Deck.GL/MapLibre map implementation.
- Login/authentication accessibility flows unrelated to the anonymous landing page.

## Implementation Fidelity and Evidence

- **Fidelity target**: targeted remediation.
- **Authoritative source path(s)**: `weppcloud-ui-lab/src/AppLight.tsx`, `weppcloud-ui-lab/src/index-light.css`, and `wepppy/weppcloud/routes/weppcloud_site.py`.
- **Cutover proof required**: `npm --prefix weppcloud-ui-lab run export:landing` updates `wepppy/weppcloud/static/ui-lab/`, and Playwright verifies `/weppcloud/landing/light/` in the running local stack.
- **Acceptance evidence type**: both generated-output and live-route browser evidence.

## Stakeholders

- **Primary**: WEPPcloud users relying on keyboard-only navigation.
- **Reviewers**: WEPPcloud frontend/accessibility maintainers.
- **Security Reviewer**: Not required for this focused public-static route and keyboard remediation.
- **Informed**: Operators deploying WEPPcloud landing assets.

## Success Criteria

- [x] `/weppcloud/landing/light/` loads the light landing React app with non-empty focusable controls.
- [x] Keyboard traversal reaches hero navigation, map controls, help/resource links, contact mail links, attribution links, and footer accessibility link without trapping focus.
- [x] The map section exposes a named focusable region and keyboard instructions.
- [x] The filter toggle and year select are not focusable while hidden and become focusable when opened.
- [x] New Playwright keyboard accessibility test passes against the installed route.
- [x] UI Lab landing bundle is rebuilt and installed in `wepppy/weppcloud/static/ui-lab/`.
- [x] Targeted lint/tests/build checks pass or any residual gap is documented.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes

## Dependencies

### Prerequisites

- Local WEPPcloud dev stack available at `wc.bearhive.duckdns.org`.
- Existing UI Lab Vite build and export workflow.
- Existing Playwright smoke harness under `wepppy/weppcloud/static-src`.

### Blocks

- None.

## Related Packages

- **Depends on**: N/A
- **Related**: `docs/ui-docs/accessiblity.md` accessibility strategy and existing manual AT evidence.
- **Follow-up**: Full VPAT/current evidence refresh only if maintainers decide this focused remediation materially changes buyer-facing conformance artifacts.

## Timeline Estimate

- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Low-Medium

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: The package changes a public landing page, static asset route compatibility, and browser-side keyboard behavior. It does not change authentication, authorization, uploads/downloads, secrets, queue execution, or user-submitted input handling.
- **Security review artifact**: N/A

## Hardening and Callus Softening

- **Failure signature(s)**: `/weppcloud/landing/light/` serves an HTML shell whose Vite asset URLs resolve to `/weppcloud/landing/light/assets/*` and return 404, leaving zero focusable elements. Working `/weppcloud/landing/` route needs explicit keyboard coverage for map/filter traversal.
- **Related prior hardening efforts**: N/A
- **Health signals**: Browser route has focusable controls; Playwright tab sequence reaches expected named controls; generated bundle is installed.
- **Danger signals**: Focusable hidden controls, focus traps around the map, or generated bundle drift from source.
- **Observation window**: Local validation during package execution.
- **Temporary calluses introduced**: None.
- **Callus softening hypothesis**: N/A.

## References

- `weppcloud-ui-lab/AGENTS.md` - UI Lab build/export workflow and host context.
- `weppcloud-ui-lab/src/AppLight.tsx` - canonical light landing React source.
- `weppcloud-ui-lab/src/index-light.css` - light landing CSS.
- `wepppy/weppcloud/routes/weppcloud_site.py` - WEPPcloud landing route and static asset routing.
- `wepppy/weppcloud/static-src/tests/smoke/` - Playwright smoke test harness.
- `docs/ui-docs/accessiblity.md` - accessibility strategy and test map.

## Deliverables

- Additive Flask asset aliases for `/landing/light/assets/<asset_path>` and `/landing/dark/assets/<asset_path>`.
- UI Lab light landing source updates for skip link, focus-visible styling, named map region, keyboard map zoom/reset controls, hidden filter-panel focus guard, and status announcements.
- New Playwright keyboard accessibility smoke test at `wepppy/weppcloud/static-src/tests/smoke/landing-keyboard.spec.js`.
- Rebuilt and installed UI Lab static bundle under `wepppy/weppcloud/static/ui-lab/`.
- Accessibility strategy documentation updated to include the new keyboard traversal smoke.

## Follow-up Work

- No required follow-up for the scoped defect.
- A future VPAT/current evidence refresh can include this package if maintainers decide the landing-page remediation materially changes buyer-facing conformance evidence.

## Closure Notes

**Closed**: 2026-06-29

**Summary**: The UI Lab light landing variant now loads correctly from `/weppcloud/landing/light/` and exposes a keyboard-accessible tab sequence. The map section has a named focusable representation and keyboard zoom/reset controls, the filter panel no longer leaks its select into the tab order while hidden, the rebuilt bundle is installed in WEPPcloud static assets, and targeted plus frontend validation passed.

**Lessons Learned**: The user-visible keyboard failure had two layers: the variant route first failed to load generated assets, leaving no focusable content, and the working `/landing/` route lacked a focused regression for map/filter keyboard behavior. Testing the installed route rather than only the Vite source caught both issues.

**Archive Status**: Package brief, tracker, completed ExecPlan, and validation evidence remain under `docs/work-packages/20260629_ui_lab_light_keyboard_access/`.
