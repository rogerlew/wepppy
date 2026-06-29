# Tracker – UI Lab Light Landing Keyboard Access

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-29 18:05 UTC
**Current phase**: Closed
**Last updated**: 2026-06-29 18:18 UTC
**Next milestone**: N/A
**Security impact**: low
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Package scaffold created with package brief, tracker, and active ExecPlan. (2026-06-29 18:05 UTC)
- [x] Baseline reproduced: `/weppcloud/landing/light/` loaded zero focusable elements because Vite assets 404 under `/landing/light/assets/`. (2026-06-29 18:05 UTC)
- [x] Baseline checked: `/weppcloud/landing/` loads the React app and exposes focusable controls. (2026-06-29 18:05 UTC)
- [x] Implemented WEPPcloud route compatibility for `/landing/light/` and `/landing/dark/` asset paths. (2026-06-29 18:14 UTC)
- [x] Implemented light landing keyboard semantics and focus visibility. (2026-06-29 18:14 UTC)
- [x] Added Playwright keyboard accessibility regression coverage. (2026-06-29 18:14 UTC)
- [x] Rebuilt/exported UI Lab landing bundle into WEPPcloud static assets. (2026-06-29 18:14 UTC)
- [x] Ran targeted validation and live-route smoke verification. (2026-06-29 18:14 UTC)
- [x] Closed work package and updated root tracker. (2026-06-29 18:14 UTC)

## Timeline

- **2026-06-29 18:05 UTC** – Package created, initial scoping completed, baseline route/load failure reproduced.
- **2026-06-29 18:14 UTC** – Route compatibility, keyboard remediation, Playwright regression, rebuild/install, and live-route verification completed.
- **2026-06-29 18:18 UTC** – Full frontend test gate recorded after package closure.

## Decisions Log

### 2026-06-29 18:05 UTC: Treat route loading and keyboard traversal as one package

**Context**: The user reported that it is not possible to tab through the UI Lab light landing page. Browser reproduction found that `/weppcloud/landing/light/` currently has no focusable elements because the React bundle does not load, while `/weppcloud/landing/` does load and needs keyboard-specific coverage.

**Options considered**:
1. Fix only React focus semantics - would leave `/landing/light/` broken.
2. Fix only route asset loading - would restore focusable links but leave no regression for map/filter keyboard behavior.
3. Fix both and validate the installed route - addresses the user-visible failure end to end.

**Decision**: Fix both route asset compatibility and keyboard traversal in one scoped package.

**Impact**: Acceptance requires a live `/weppcloud/landing/light/` Playwright check after rebuilding/installing the bundle.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Generated UI Lab assets drift from source | Medium | Medium | Run `npm --prefix weppcloud-ui-lab run export:landing` and commit generated static outputs with source changes | Mitigated |
| Map library internals may add unexpected focus targets | Medium | Medium | Mark wrapper semantics explicitly and test a stable named focus sequence around the map controls | Mitigated |
| Browser route uses different asset base for `/landing/` and `/landing/light/` | Medium | High | Add route alias or generated asset path handling and test `/landing/light/` directly | Closed |

## Hardening Signal Log

- **Baseline health signals**: `/weppcloud/landing/light/` returned HTML but asset requests under `/weppcloud/landing/light/assets/*` returned 404; focusable element count was `0`.
- **Post-change health signals**: `/weppcloud/landing/light/` live smoke reported `focusable: 44` and `badAssets: []`; Playwright keyboard smoke passed.
- **Danger signals observed**: None in targeted validation.
- **Temporary callus register**: None.
- **Softening experiments**: N/A.

## Verification Checklist

### Code Quality

- [x] Frontend UI Lab lint/build clean.
- [x] Playwright keyboard regression passes.
- [x] WEPPcloud route/template tests pass where affected.
- [x] Docs lint clean for package/tracker.

### Security

- [x] Security impact triage recorded as low with rationale.
- [x] Dedicated security artifact not required.
- [x] No attack-surface change beyond public static route compatibility.

### Documentation

- [x] Work package scaffold complete.
- [x] Active ExecPlan updated through completion.
- [x] Work package closure notes complete.
- [x] Root `PROJECT_TRACKER.md` updated.

### Testing

- [x] Keyboard regression test added.
- [x] Generated bundle installed and live route verified.
- [x] Edge cases documented and tested.

### Deployment

- [x] Built and installed in local WEPPcloud static bundle.
- [x] Local Caddy/WEPPcloud route verified at `wc.bearhive.duckdns.org`.

## Progress Notes

### 2026-06-29 18:05 UTC: Scoping and baseline reproduction

**Agent/Contributor**: Codex

**Work completed**:
- Read `weppcloud-a11y-remediator`, `docs-maintainer`, `wepppy-tester`, ExecPlan, UI Lab, tests, Playwright smoke, and work-package guidance.
- Located source and routes: `weppcloud-ui-lab/src/AppLight.tsx`, `weppcloud-ui-lab/src/index-light.css`, `wepppy/weppcloud/routes/weppcloud_site.py`, and `wepppy/weppcloud/static-src/tests/smoke/`.
- Reproduced `/weppcloud/landing/light/` empty focusable state with Playwright.

**Blockers encountered**:
- None.

**Next steps**:
- Implement route compatibility and keyboard semantics.
- Add Playwright keyboard test.
- Rebuild/export and verify live route.

**Test results**:
- Baseline reproduction script found `focusable count 0` on `/weppcloud/landing/light/`.

### 2026-06-29 18:14 UTC: Remediation, rebuild, and validation

**Agent/Contributor**: Codex

**Work completed**:
- Added Flask landing asset aliases in `wepppy/weppcloud/routes/weppcloud_site.py`.
- Updated `weppcloud-ui-lab/src/AppLight.tsx` with a skip link, main landmark, named map region, keyboard map controls, hidden filter-panel focus guard, and status semantics.
- Updated `weppcloud-ui-lab/src/index-light.css` with visible focus styling, skip-link styling, and map control styling.
- Added `wepppy/weppcloud/static-src/tests/smoke/landing-keyboard.spec.js`.
- Ran `npm --prefix weppcloud-ui-lab run export:landing` to install rebuilt static assets in `wepppy/weppcloud/static/ui-lab/`.
- Restarted the local `weppcloud` container so Flask route aliases loaded.

**Blockers encountered**:
- `wctl run-playwright` initially timed out during stack settling after restart; rerun executed normally.
- Initial Playwright assertion used a non-exact heading locator and matched multiple headings; tightened to exact `WEPPcloud`.
- Direct ESLint of the new smoke spec needed `/* global process */` for the existing config.

**Next steps**:
- None for this package.

**Test results**:
- `npm --prefix weppcloud-ui-lab run lint` passed.
- `npm --prefix weppcloud-ui-lab run build` passed with existing Vite large-chunk warning.
- `npm --prefix weppcloud-ui-lab run export:landing` passed and installed the bundle.
- `wctl run-pytest tests/weppcloud/routes/test_landing_template.py --maxfail=1` passed: `1 passed`.
- `wctl run-playwright --suite full --grep "light landing keyboard" --workers 1` passed: `1 passed`.
- `wctl run-npm lint` passed.
- `wctl run-npm test` passed.
- `cd wepppy/weppcloud/static-src && npx eslint --config .eslintrc.cjs tests/smoke/landing-keyboard.spec.js` passed.
- `python -m py_compile wepppy/weppcloud/routes/weppcloud_site.py` passed.
- Live route smoke against `https://wc.bearhive.duckdns.org/weppcloud/landing/light/` reported `focusable: 44` and no bad light-asset responses.
- `wctl doc-lint --path docs/work-packages/20260629_ui_lab_light_keyboard_access` passed: `3 files validated, 0 errors, 0 warnings`.

## Watch List

- **Generated asset churn**: Vite hashed filenames will change after build; keep source and installed assets together.
- **Route alias scope**: Asset alias should be narrow to landing static assets, not a broad catch-all.

## Communication Log

### 2026-06-29 18:05 UTC: User request

**Participants**: User, Codex
**Question/Topic**: Scaffold and execute a work-package to make the `weppcloud-ui-lab` light landing page keyboard accessible, with tests, build, and install in WEPPcloud.
**Outcome**: Package opened and execution started.
