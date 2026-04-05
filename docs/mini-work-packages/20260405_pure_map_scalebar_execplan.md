# Pure Run Map Scalebar

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows the repository guidance in `docs/prompt_templates/codex_exec_plans.md`. It must remain self-contained so a future contributor can resume the work from this file alone.

## Purpose / Big Picture

The pure run page should show a visual map scalebar inside the deck.gl map so users can judge map distance without estimating from coordinates or zoom level. The scalebar must follow the project unitizer's global `distance` preference as a system selector: when the preferred `distance` unit is `km`, the map is in SI mode and the bar should label short ranges in metres and longer ranges in kilometres; when the preferred `distance` unit is `mi`, the map is in English mode and the bar should label short ranges in feet and longer ranges in miles. The result should be visible on `runs0_pure.htm` without introducing a dependency on `react-map-gl` or changing backend routes.

## Progress

- [x] (2026-04-05 19:08Z) Read the root and controller-specific `AGENTS.md` guidance, the pure run page template, the pure map partial, the map controller, the unitizer event surface, and the map CSS.
- [x] (2026-04-05 19:12Z) Resolved the unit preference model: use unitizer `distance` as the SI-versus-English selector instead of binding the scalebar directly to `km` or `mi` labels.
- [x] (2026-04-05 19:18Z) Implemented a map-owned scalebar overlay in the deck.gl controller path with no backend changes.
- [x] (2026-04-05 19:20Z) Added Jest coverage for initial render, zoom-driven updates, and unitizer preference switching.
- [x] (2026-04-05 19:25Z) Rebuilt the controller bundle, ran targeted validation, and recorded outcomes here.
- [x] (2026-04-05 19:28Z) Ran independent code-review and QA-review subagents, fixed the antimeridian/low-zoom scalebar math, removed the decorative `aria-label`, added async hydration and narrow/zoom-0 coverage, and updated this plan with the final state.

## Surprises & Discoveries

- Observation: the pure page already loads `@deck.gl/widgets`, but the map controller only uses `ZoomWidget`.
  Evidence: `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm` loads the widgets CDN assets, while `wepppy/weppcloud/controllers_js/map_gl.js` only constructs `new deckApi.ZoomWidget(...)`.

- Observation: current WEPPcloud map CSS styles deck widget button groups, but there is no existing scale-widget-specific styling.
  Evidence: `wepppy/weppcloud/static/css/ui-foundation.css` has selectors for `.deck-widget-button-group` and `.deck-widget-icon-button`, but no scale widget selectors.

- Observation: the `.wc-map` shell is already `position: relative`, so the scalebar can be mounted as a simple absolute overlay without touching the template layout.
  Evidence: `wepppy/weppcloud/static/css/ui-foundation.css` defines `.wc-map { position: relative; }`.

- Observation: measuring the scalebar from the full west-to-east viewport span is incorrect once the deck view repeats the world or the visible bounds approach global scale.
  Evidence: the independent reviewer noted that `MapView({ repeat: true })` plus `zoom = 0` can make a full-span haversine measurement choose the shortest arc instead of the actual on-screen span. The fix was to measure a local segment between two nearby screen points via `deckgl.unproject(...)`.

## Decision Log

- Decision: implement the scalebar as a house-owned DOM overlay instead of adopting deck.gl's experimental `ScaleWidget`.
  Rationale: the existing codebase already owns the map shell and overlay controls, the current widget styling only covers zoom buttons, and a custom overlay gives stable control over unitizer-driven SI versus English behavior with lower regression risk than relying on deck widget internals or CDN version details.
  Date/Author: 2026-04-05 / Codex

- Decision: treat unitizer `distance` as a system selector only.
  Rationale: `distance` preferences are `km` or `mi`, which are suitable for deciding SI versus English mode but are not suitable as the only display units for a practical scalebar at small scales. This preserves user intent while still producing readable labels in `m/km` or `ft/mi`.
  Date/Author: 2026-04-05 / Codex

- Decision: prefer controller-side updates triggered from existing view-state refresh paths and unitizer preference events.
  Rationale: the map controller already centralizes viewport updates in `updateMapStatus()`, and the project/unitizer flow already dispatches `unitizer:preferences-changed`. Reusing those hooks avoids new polling or template-specific glue.
  Date/Author: 2026-04-05 / Codex

- Decision: compute metres-per-pixel from a local screen-space sample instead of the full viewport width.
  Rationale: the map enables world repeat and supports zooming to 0, so a full west-to-east bounds measurement can under-report or collapse around the antimeridian. Sampling a nearby horizontal segment with `deckgl.unproject(...)` keeps the scale local to the rendered screen span and survives wraparound.
  Date/Author: 2026-04-05 / Codex

- Decision: keep the scalebar decorative for assistive technology in this iteration.
  Rationale: the control currently has no keyboard interaction and updates frequently during map movement, so exposing it as an accessibility surface would need a more deliberate non-live announcement design. Removing the redundant `aria-label` while leaving `aria-hidden="true"` keeps the current intent internally consistent.
  Date/Author: 2026-04-05 / Codex

## Outcomes & Retrospective

The feature is complete. The pure-page map now shows a bottom-left scalebar owned by the map controller. It follows the unitizer `distance` preference as a system selector, switching between `m/km` and `ft/mi` without page reloads or backend changes. The implementation fits the existing controller split by isolating scale DOM and formatting logic in `map_gl_scale_control.js` while keeping orchestration in `map_gl.js`.

The two requested subagent reviews materially improved the result. The QA reviewer pointed out an accessibility inconsistency and missing startup/layout tests, which led to removal of the redundant decorative `aria-label` and to explicit async-hydration and narrow-viewport coverage. The correctness reviewer identified a real world-wrap bug in the first-pass distance math, which led to the safer local `unproject(...)` measurement and a zoom-0 near-antimeridian regression test. After those fixes, targeted validation is green.

## Context and Orientation

The feature lives in the pure WEPPcloud run page. The page assembly template is `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`. It includes the map control partial `wepppy/weppcloud/templates/controls/map_pure_gl.htm`, which renders the `.wc-map` wrapper and the `#mapid` element that deck.gl uses as its parent container. The map runtime is implemented in `wepppy/weppcloud/controllers_js/map_gl.js`. Shared map helpers and pure utilities live in `wepppy/weppcloud/controllers_js/map_gl_shared.js`. Overlay-panel rendering lives in `wepppy/weppcloud/controllers_js/map_gl_layer_control.js`. Browser styling for the map shell and overlay controls lives in `wepppy/weppcloud/static/css/ui-foundation.css`. Jest coverage for the map controller lives in `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js`.

The unitizer is the project-wide unit preference system. The backend source of the unit categories is `wepppy/nodb/unitizer.py`. The browser client for those preferences is `wepppy/weppcloud/controllers_js/unitizer_client.js`. The project controller `wepppy/weppcloud/controllers_js/project.js` applies unitizer preferences to the page and dispatches the DOM event `unitizer:preferences-changed` whenever preferences are applied.

In this repository, a "scalebar" means a visual control drawn over the map that shows a real-world distance represented by a horizontal line of fixed pixel width. It is not part of any data layer and must not interfere with panning, zooming, drilldown, or the existing layer and resize controls.

## Plan of Work

Add a small map scalebar helper in the controller layer, preferably as a dedicated file `wepppy/weppcloud/controllers_js/map_gl_scale_control.js`, because the map code is already split by responsibility. The helper should create and own a DOM node mounted under the `.wc-map` host. It should expose functions to ensure the host exists, compute the represented ground distance for a candidate pixel width, choose a "nice" displayed distance, format the label for SI or English mode, and update the overlay's pixel width and text.

Wire the helper into `wepppy/weppcloud/controllers_js/map_gl.js`. During controller initialization, after the map canvas element is known and before or after deck.gl is created, instantiate the scalebar against the `.wc-map` host. Call the scalebar refresh method from the existing viewport update path so the bar tracks `setView`, `flyTo`, drag/zoom interactions, bootstrap, and `ResizeObserver` updates. The refresh code should use the current center latitude and current map width to estimate metres-per-pixel across the center of the viewport. Reuse `calculateDistanceMeters` from `map_gl_shared.js` for the spherical distance calculation rather than introducing another geodesic utility.

Use the unitizer `distance` preference to choose display mode. If the live unitizer preference payload contains `distance: "mi"`, use English display mode. In every other case, default to SI mode. In SI mode, display short bars in `m` and longer bars in `km`. In English mode, display short bars in `ft` and longer bars in `mi`. Do not mutate unitizer preferences from the map. The map only consumes them.

Add minimal CSS in `wepppy/weppcloud/static/css/ui-foundation.css` for a bottom-left overlay block that matches the current map chrome, leaves the zoom widget in the top-left, leaves the layer control in the top-right, and does not collide with the resize handle in the bottom-right. The overlay must ignore pointer events so map interactions keep working.

Add or extend Jest tests in `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` to prove the behavior. The tests should verify that the scalebar node is created on map startup, that changing the view state causes the width or label to update, and that dispatching `unitizer:preferences-changed` with `distance: "mi"` switches the label family to English units.

Rebuild the bundle with `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, run the relevant front-end checks, and record the results. After the code is stable, run an independent review subagent and an independent QA subagent, apply any necessary fixes, and update this plan with the outcome.

## Concrete Steps

From `/workdir/wepppy`:

1. Create or update the ExecPlan file and keep it current while implementing.
2. Edit the map controller files and CSS using minimal additive changes.
3. Rebuild the GL controller bundle:

       python wepppy/weppcloud/controllers_js/build_controllers_js.py

4. Run the targeted front-end validation. Prefer the repo-standard wrapper script:

       python /home/roger/.codex/skills/wepppy-tester/scripts/wepppy_tester.py --pytests "" 

   If that wrapper is too broad for this change, run the underlying targeted commands directly:

       wctl run-npm lint
       wctl run-npm test -- map_gl

5. Lint the work-package doc:

       wctl doc-lint --path docs/mini-work-packages/20260405_pure_map_scalebar_execplan.md

6. Lint any touched controller docs:

       wctl doc-lint --path wepppy/weppcloud/controllers_js/README.md
       wctl doc-lint --path wepppy/weppcloud/controllers_js/AGENTS.md

7. Run independent review and QA subagents and incorporate any fixes before handoff.

## Validation and Acceptance

Acceptance has three parts.

First, automated browser-side tests must pass. `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` must prove that the scalebar overlay is present after `MapController.getInstance()` bootstraps and that unitizer preference switching changes the displayed unit family.

Second, the built bundle must regenerate cleanly with `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.

Third, in a manual pure-page smoke test, opening a run page that uses `runs0_pure.htm` should show a visible scalebar in the lower-left of the map. Panning or zooming the map should update the scalebar smoothly. Changing the unitizer global preference from SI to English should change the scalebar label family from `m/km` to `ft/mi` without reloading the page.

## Idempotence and Recovery

The implementation is additive and should be safe to apply repeatedly. Re-running the bundle build simply overwrites `wepppy/weppcloud/static/js/controllers-gl.js` with a fresh generated bundle. Re-running Jest or lint checks is safe. If the scalebar proves unstable, the rollback path is straightforward: remove the helper file and its wiring from `map_gl.js`, remove the CSS selectors, rebuild the bundle, and re-run the tests. No backend state or persisted data changes are involved.

## Artifacts and Notes

Validation evidence:

    /workdir/wepppy$ python wepppy/weppcloud/controllers_js/build_controllers_js.py
    [exit 0]

    /workdir/wepppy$ wctl run-npm test -- map_gl
    PASS ../controllers_js/__tests__/map_gl.test.js
    Test Suites: 1 passed, 1 total
    Tests:       34 passed, 34 total

    /workdir/wepppy$ wctl run-npm lint
    [exit 0]

    /workdir/wepppy$ wctl doc-lint --path docs/mini-work-packages/20260405_pure_map_scalebar_execplan.md
    ✅ 1 files validated, 0 errors, 0 warnings

    /workdir/wepppy$ wctl doc-lint --path wepppy/weppcloud/controllers_js/README.md
    ✅ 1 files validated, 0 errors, 0 warnings

    /workdir/wepppy$ wctl doc-lint --path wepppy/weppcloud/controllers_js/AGENTS.md
    ✅ 1 files validated, 0 errors, 0 warnings

## Interfaces and Dependencies

The new helper should stay within the current browser runtime and must not add new third-party dependencies. It may rely on the existing globals `window.WCDom`, `window.UnitizerClient`, and `window.WCMapGlShared`.

At the end of the work, the browser bundle should expose the same public controller global names as before: `window.MapController`, `window.WeppMap`, and `window.WEPP_FIND_AND_FLASH`.

The internal helper interface should be small and prescriptive. A suitable shape is:

    WCMapGlScaleControl.ensureScaleControl({ hostElement, getViewState, calculateDistanceMeters, unitizerClient })
    -> returns an object with update() and destroy()

The exact names can vary if a smaller change is cleaner, but the resulting code must keep map orchestration in `map_gl.js` and keep scale-specific DOM math isolated from unrelated overlay or feature-modal code.

Change note: created this ExecPlan on 2026-04-05 to implement a pure-page map scalebar with unitizer-driven SI versus English display and to track implementation, validation, and subagent review evidence.

Change note: updated on 2026-04-05 after implementation and local validation to record completed work, validation evidence, and the remaining reviewer-closure step.

Change note: updated on 2026-04-05 after independent code-review and QA-review subagents reported findings. The plan now records the antimeridian/world-wrap fix, the accessibility cleanup, the expanded Jest coverage, and the completed review closure.
