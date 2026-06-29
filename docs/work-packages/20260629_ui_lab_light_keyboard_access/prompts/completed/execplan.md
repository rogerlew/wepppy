# Make the UI Lab Light Landing Page Keyboard Accessible

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` from the repository root. It is self-contained so a future contributor can continue from this file alone.

## Purpose / Big Picture

The WEPPcloud UI Lab light landing page is a public entry point for WEPPcloud. A keyboard-only user must be able to tab through it, reach links and controls in a predictable order, open map filters, and continue past the map section without needing a mouse. After this change, navigating to `/weppcloud/landing/light/` on the local WEPPcloud instance should load the React landing page, and pressing Tab should move through named, visible controls rather than staying on the document body.

## Progress

- [x] (2026-06-29 18:05 UTC) Read required repository and skill instructions for UI Lab, accessibility remediation, tests, docs, and ExecPlans.
- [x] (2026-06-29 18:05 UTC) Reproduced baseline `/weppcloud/landing/light/` failure: zero focusable elements because exported assets resolve to `/weppcloud/landing/light/assets/*` and 404.
- [x] (2026-06-29 18:05 UTC) Confirmed `/weppcloud/landing/` loads the light React app and currently exposes focusable controls.
- [x] (2026-06-29 18:14 UTC) Implemented narrow WEPPcloud route compatibility for `/landing/light/assets/*` and `/landing/dark/assets/*`.
- [x] (2026-06-29 18:14 UTC) Added light landing keyboard semantics: visible skip link, named map region, keyboard instructions, hidden filter panel focus guard, and focus-visible styling.
- [x] (2026-06-29 18:14 UTC) Added Playwright smoke test that tabs through `/weppcloud/landing/light/` and asserts stable focus sequence plus filter-panel behavior.
- [x] (2026-06-29 18:14 UTC) Rebuilt and installed UI Lab landing bundle with `npm --prefix weppcloud-ui-lab run export:landing`.
- [x] (2026-06-29 18:14 UTC) Ran focused tests and live-route verification.
- [x] (2026-06-29 18:14 UTC) Updated package/tracker/outcomes and closed the work package.
- [x] (2026-06-29 18:18 UTC) Recorded full frontend test gate after closure.
- [x] (2026-06-29 22:10 UTC) Follow-up remediation removed the map visual from tab order, strengthened focus indication, covered variant run-data loading, rebuilt/exported the bundle, and reran focused validation.
- [x] (2026-06-29 23:00 UTC) Follow-up hardening added explicit link tab stops, a first-Tab body fallback, no-store landing responses, cross-engine Playwright probes, and stricter smoke assertions.

## Surprises & Discoveries

- Observation: The most severe `/landing/light/` keyboard failure is not initially a React focus bug; the served route leaves `<div id="root"></div>` empty because relative Vite assets 404 under the variant path.
  Evidence: Playwright baseline reported `focusable count 0`; console/network events showed 404s for `/weppcloud/landing/light/assets/light-*.js`, `/weppcloud/landing/light/assets/utils-*.js`, and `/weppcloud/landing/light/assets/light-*.css`.

- Observation: `/weppcloud/landing/` loads the same light app successfully because `./assets/...` resolves to `/weppcloud/landing/assets/...`, which is already routed by Flask.
  Evidence: Playwright baseline reported `focusable 41` and body text beginning with `WEPPcloud`.

- Observation: The remediated `/weppcloud/landing/light/` route exposes a non-empty focus order and no longer emits variant asset 404s.
  Evidence: Live route smoke reported `focusable: 44` and `badAssets: []`; `wctl run-playwright --suite full --grep "light landing keyboard" --workers 1` passed.

- Observation: A focusable map visual is a poor keyboard stop because it is not an actionable link or control and can make traversal appear to jump to the map and stop.
  Evidence: User follow-up reported the behavior; follow-up smoke confirms focus now advances from about links directly to explicit map zoom/reset/filter buttons and then downstream page links.

## Decision Log

- Decision: Treat route asset compatibility and keyboard traversal as one end-to-end accessibility remediation.
  Rationale: A route that renders no interactive controls cannot be keyboard accessible, and fixing only the asset path would leave map/filter keyboard behavior untested.
  Date/Author: 2026-06-29 / Codex.

- Decision: Add a dedicated Playwright keyboard smoke spec instead of relying only on axe.
  Rationale: Axe can catch structural ARIA defects but does not prove that Tab reaches the expected controls in order or that hidden controls are excluded from the tab order.
  Date/Author: 2026-06-29 / Codex.

- Decision: Keep the Vite `base: './'` setting and add narrow Flask aliases for variant asset paths.
  Rationale: Relative assets keep the exported bundle deployable under both `/landing/` and local static previews. Route aliases fix `/landing/light/` and `/landing/dark/` without hard-coding `/weppcloud` into the generated bundle.
  Date/Author: 2026-06-29 / Codex.

- Decision: Keep the map visual out of sequential keyboard focus and expose keyboard operation through explicit buttons.
  Rationale: Keyboard traversal should advance link by link and control by control. The map canvas is not itself a useful keyboard target, so zoom/reset/filter buttons carry the operable map surface.
  Date/Author: 2026-06-29 / Codex.

- Decision: Normalize landing links with explicit `tabindex="0"` and add a first-Tab fallback from `document.body`.
  Rationale: Native link focus worked in Playwright engines, but the user still observed Tab doing nothing. Explicit link tab stops and a page-owned first-Tab fallback make the route robust to browser focus settings and stale body focus without replacing normal subsequent tab navigation.
  Date/Author: 2026-06-29 / Codex.

## Outcomes & Retrospective

The package completed in one focused session and same-day follow-up hardening passes. `/weppcloud/landing/light/` now loads the React light landing page, keyboard users can tab link by link through the page from body focus, the map visual is skipped as a non-actionable tab stop, the map section has explicit keyboard controls, and the year filter stays out of the tab order until the filter panel is opened. The UI Lab bundle was rebuilt and installed under `wepppy/weppcloud/static/ui-lab/`, and validation passed through source lint/build, full frontend test, Playwright keyboard smoke, route pytest, direct ESLint for the smoke spec, doc lint, and live-route smoke.

The main lesson is that keyboard accessibility defects on generated pages should be tested at the installed WEPPcloud route, not only in the source app, because route-relative asset loading can erase the entire interactive tree.

## Context and Orientation

The light landing page is a React application in `weppcloud-ui-lab/`, built by Vite. The source file for the light variant is `weppcloud-ui-lab/src/AppLight.tsx`, and its CSS is `weppcloud-ui-lab/src/index-light.css`. The build command `npm --prefix weppcloud-ui-lab run export:landing` compiles the Vite bundle and copies `weppcloud-ui-lab/dist/` to `wepppy/weppcloud/static/ui-lab/`, which is the static bundle served by WEPPcloud.

WEPPcloud serves the installed bundle from Flask routes in `wepppy/weppcloud/routes/weppcloud_site.py`. The route `/landing/` and `/landing/light/` both render the light variant. The route `/landing/assets/<asset_path>` serves generated JavaScript and CSS assets. Because Vite currently emits relative asset paths such as `./assets/light-....js`, `/landing/` works but `/landing/light/` tries to load `/landing/light/assets/...`, which is not currently routed.

The smoke-test harness is a Playwright test suite in `wepppy/weppcloud/static-src/tests/smoke/`, run with `wctl run-playwright --suite full ...` or with `npx playwright test --config=playwright.config.mjs` from `wepppy/weppcloud/static-src`. Playwright is appropriate here because the defect is browser focus behavior after scripts load.

## Plan of Work

First, make the installed `/landing/light/` route load its assets. The smallest route-compatible fix is to add Flask aliases for `/landing/light/assets/<asset_path>` and `/landing/dark/assets/<asset_path>` that delegate to the existing `landing_static_assets()` function. This preserves the current Vite `base: './'` behavior and avoids hard-coding `/weppcloud` into the bundle, while keeping the route narrow to existing UI Lab assets.

Second, update `weppcloud-ui-lab/src/AppLight.tsx` so keyboard users have a clear path through the page. Add a visually hidden skip link at the top that becomes visible on focus and jumps to the main content. Wrap page content in a `<main id="main-content">`. Give the map section an accessible name and description. Add a focusable map summary or region control with keyboard instructions so the map is represented in tab order without requiring Deck.GL pointer interactions. Ensure the filter panel has `hidden` and `aria-hidden` while closed so the select cannot receive focus until the panel opens. Add `aria-controls` and an explicit `aria-label` to the filter toggle. Add an `aria-live` status region for loading/error status text if needed.

Third, update `weppcloud-ui-lab/src/index-light.css` with visible focus styling for the light page and any skip-link or map-instruction helpers. The focus ring must be visible against white and light-gray backgrounds.

Fourth, add a Playwright smoke test under `wepppy/weppcloud/static-src/tests/smoke/`, for example `landing-keyboard.spec.js`. The test should visit `/weppcloud/landing/light/`, wait for the React app to render, assert that there are focusable controls, press Tab repeatedly, and verify the sequence includes the skip link, hero navigation links, map keyboard summary, filter toggle, help/resource links, contact mail links, data-source links, and footer accessibility statement. It should also assert that the year select is not focusable while the panel is closed, then open the filter panel and verify the year select can be focused.

Fifth, rebuild and install the UI Lab bundle with `npm --prefix weppcloud-ui-lab run export:landing`. After build, run lint/build/tests and a live route smoke against `https://wc.bearhive.duckdns.org/weppcloud/landing/light/`. If the running container does not pick up Python route changes automatically, restart the minimal required local container and verify again.

Finally, update this ExecPlan, `tracker.md`, `package.md`, and `PROJECT_TRACKER.md` with outcomes, validation results, and closure notes.

## Concrete Steps

Run commands from `/workdir/wepppy` unless otherwise noted.

1. Edit `wepppy/weppcloud/routes/weppcloud_site.py` to add light/dark variant asset aliases that call `landing_static_assets(asset_path)`.

2. Edit `weppcloud-ui-lab/src/AppLight.tsx` and `weppcloud-ui-lab/src/index-light.css` for keyboard semantics and focus styling.

3. Add `wepppy/weppcloud/static-src/tests/smoke/landing-keyboard.spec.js`.

4. Build and install:

    npm --prefix weppcloud-ui-lab run export:landing

5. Validate:

    npm --prefix weppcloud-ui-lab run lint
    npm --prefix weppcloud-ui-lab run build
    wctl run-playwright --suite full --grep "light landing keyboard" --workers 1
    wctl run-pytest tests/weppcloud/routes/test_landing_template.py --maxfail=1
    wctl doc-lint --path docs/work-packages/20260629_ui_lab_light_keyboard_access

6. Live route smoke:

    Use Playwright or curl to verify `/weppcloud/landing/light/` loads generated assets and contains focusable controls.

Completed validation transcript summary:

    npm --prefix weppcloud-ui-lab run lint
    passed

    npm --prefix weppcloud-ui-lab run build
    passed with existing Vite large-chunk warning

    npm --prefix weppcloud-ui-lab run export:landing
    passed; exported landing bundle to wepppy/weppcloud/static/ui-lab

    wctl run-pytest tests/weppcloud/routes/test_landing_template.py --maxfail=1
    1 passed

    wctl run-playwright --suite full --grep "light landing keyboard" --workers 1
    1 passed

    wctl run-npm test
    passed

    live route smoke
    {"title":"WEPPcloud","focusable":44,"badAssets":[]}

## Validation and Acceptance

Acceptance is met when:

- `/weppcloud/landing/light/` loads the React app and no longer logs 404s for `landing/light/assets/*`.
- A browser test pressing Tab reaches named, visible controls in expected order and can open the filter panel and focus the year select.
- The filter year select is absent from the tab order while the filter panel is closed.
- The generated bundle under `wepppy/weppcloud/static/ui-lab/` reflects the source changes.
- Targeted lint/build/Playwright/pytest/doc-lint checks pass, or any unavoidable environment limitation is recorded with evidence.

## Idempotence and Recovery

The Flask route alias is additive and can be rerun safely. The UI Lab export command deletes and recreates `wepppy/weppcloud/static/ui-lab/`, so rerun it after every source change and do not hand-edit generated files. If a build fails, fix source files and rerun the same command. If local Caddy or WEPPcloud serves stale route code, restart only the minimal affected service and re-run the live smoke.

## Artifacts and Notes

Baseline evidence:

    /weppcloud/landing/light/
    focusable count 0
    404 /weppcloud/landing/light/assets/light-CAvDTKdF.css
    404 /weppcloud/landing/light/assets/light-D8C95Rgl.js
    404 /weppcloud/landing/light/assets/utils-BaJH55ZX.js

    /weppcloud/landing/
    focusable 41
    body text begins with "WEPPcloud"

Closure evidence:

    /weppcloud/landing/light/
    focusable 44
    no failed /landing/light/assets/* responses
    Playwright keyboard smoke passed

## Interfaces and Dependencies

No new external dependencies are required. Use existing React, Vite, Deck.GL, MapLibre, and Playwright dependencies. The new Flask route aliases must remain under the existing `weppcloud_site_bp` blueprint and reuse `landing_static_assets(asset_path)` so MIME handling remains centralized.
