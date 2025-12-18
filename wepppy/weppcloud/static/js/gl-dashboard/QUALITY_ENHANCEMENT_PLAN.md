# GL Dashboard Quality Enhancement Plan

> Targeted hardening and quality improvements post-refactor. Each phase includes trackable tasks with GitHub-style checkboxes.

## Phase 1: Documentation Hardening
- [X] Add JSDoc typedefs for all factory signatures (scenario manager, graph mode, year slider, wepp data, raster utils) to improve IDE hover help.
  - [X] `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js`
  - [X] `wepppy/weppcloud/static/js/gl-dashboard/ui/graph-mode.js`
  - [X] `wepppy/weppcloud/static/js/gl-dashboard/ui/year-slider.js`
  - [X] `wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js`
  - [X] `wepppy/weppcloud/static/js/gl-dashboard/map/raster-utils.js`
- [X] Update `docs/ui-docs/gl-dashboard.md` testing section with verified fixture path or note inline fixtures.
- [X] Add a short “page load pipeline” blurb to `AGENTS.md` (async detection; layer controls render before detection completes).

## Phase 2: Constants and Type Safety
- [X] Extract graph modes, slider placements, and graph context keys into shared constants (config or `ui/constants.js`) to eliminate magic strings.
- [X] Add JSDoc enums/typedefs for graph mode, slider placement, and context keys.

## Phase 3: Unit/Integration Tests
- [ ] Add fast unit tests for `colors.js` (colormap outputs, normalization).
- [ ] Add unit tests for detector URL construction (sitePrefix-aware) and range computations in wepp-data.
- [ ] Add unit tests for state subscriptions (setState/setValue change notifications).
- [ ] Ensure tests live alongside modules or under `static-src/tests` with clear fixture usage.

## Phase 4: Error Handling & UX Feedback
- [ ] Add lightweight error surfaces for detector failures (set state flags; optionally surface a non-blocking banner/legend note).
- [ ] Guard async detection with user-visible fallback for missing rasters/overlays (e.g., “No rasters detected—check run data”).

## Phase 5: Visual/Behavioral Coverage
- [ ] Expand Playwright smoke to assert layer controls populate after async detection (no “No raster layers” when rasters exist).
- [ ] Add Playwright check for comparison diverging legend when comparison mode/data is available.
- [ ] Add Playwright check for slider placement per context (climate/outlet bottom; RAP/WEPP Yearly top; cumulative/omni hidden).

## Phase 6: Maintenance & Cleanup
- [ ] Sweep for dead code/unused imports in `gl-dashboard.js` and modules; remove.
- [ ] Ensure `ctx.sitePrefix` usage is consistent across new code paths (audit any hardcoded URLs).
- [ ] Keep README/AGENTS/UI docs in sync when modules change (add to PR checklist).
