# Roads GeoJSON Attribute Discovery and Mapping UI

**Status**: Complete (2026-03-26, manual E2E verified)

## Overview
Roads phase-1 currently resolves `design`, `surface`, and `traffic` from hard-coded GeoJSON property names and fallbacks. Users cannot inspect uploaded attribute names, assign alternate primary fields (for example `ROADTYPE` instead of `DESIGN`), or set explicit fallback values for `surface`/`traffic` from the run UI. This package adds post-upload attribute discovery and explicit UI mapping controls so users can map GeoJSON properties to Roads semantics before segment preparation and run execution.

## Objectives
- Add deterministic discovery of uploaded GeoJSON feature-property attributes (top-level keys, field names + value previews) after `upload_geojson`.
- Add Roads UI controls that let users map GeoJSON attributes to `design`, `surface`, and `traffic`.
- Let users set explicit fallback values for `surface` (`gravel|paved`) and `traffic` (`high|low|none`).
- Apply configured mappings in both prepare-stage design eligibility and run-stage segment parameter resolution.
- Preserve fallback behavior with explicit warnings when mapped primary fields are missing at feature level.
- Allow user-configurable discovery limits while still exposing all discovered top-level field names.
- Add regression coverage across controller, API routes, and JS control behavior.
- Add explicit code-review and QA-review gates before package closeout.

## Scope
This package implements configurable attribute mapping for Roads input semantics and the required API/UI plumbing.

### Included
- `Roads` controller support for uploaded-attribute discovery metadata and mapping-aware property resolution.
- Prepare-stage design eligibility updates so mapped design fields affect lowpoint attribution.
- Run-stage mapping-aware resolution for `design`, `surface`, and `traffic` with user-selectable fallback values for `surface` and `traffic`.
- Roads control UI updates (attribute preview + mapping selects + apply action).
- Roads API payload/response updates required for the mapping workflow.
- Mapping auto-reset behavior on each new upload, followed by best-effort mapping rediscovery against the new attribute catalog.
- Targeted tests and docs/spec updates for the new mapping contract.

### Explicitly Out of Scope
- Mapping controls for `soil_texture`, `rfg_pct`, and `road_width_m` in this package.
- Heuristic ML/AI field inference beyond deterministic rules and hinting.
- Nested property-path mapping (for example `properties.meta.design`) in this package.
- New Roads design domains beyond current phase-1 inslope designs.
- Reworking Roads run orchestration or pass-combiner physics.

## Stakeholders
- **Primary**: WEPPcloud users uploading roads GeoJSON files with non-standard property names.
- **Reviewers**: Roads NoDb maintainers, WEPPcloud routes/templates/controllers maintainers, QA for Roads workflow.
- **Informed**: Documentation maintainers and operators supporting Roads run triage.

## Success Criteria
- [x] Upload responses and/or Roads config summary expose discovered GeoJSON attribute catalog data for the current upload.
- [x] Roads UI shows mapping controls after upload and allows users to assign properties to `design`, `surface`, and `traffic`, plus fallback values for `surface`/`traffic`.
- [x] `prepare_segments()` honors mapped design field for inslope eligibility/lowpoint mapping.
- [x] `run_roads_wepp()` resolves `design`, `surface`, and `traffic` from mapped fields (with documented fallback order including user-set fallback values for `surface`/`traffic`).
- [x] Missing mapped primary fields emit observable warnings and then fallback to defaults/legacy behavior as documented (no silent behavior).
- [x] New upload auto-resets stale mapping state and attempts rediscovery/match against the new uploaded attribute catalog.
- [x] Targeted tests pass for controller, route, and JS behavior; no regressions in existing Roads suites.
- [x] Manual run-page E2E passes (UI mapping flow works and Roads WEPP run completes).
- [x] Code review findings are captured/resolved and recorded in package artifacts.
- [x] QA review validates UI workflow + run-path behavior and records results in package artifacts.

## Dependencies

### Prerequisites
- Existing Roads phase-1 implementation package:
  - `docs/work-packages/20260323_roads_nodb_inslope_e2e/`
- Current Roads contracts and behavior docs:
  - `wepppy/nodb/mods/roads/specification.md`

### Blocks
- Follow-on work for richer per-segment override mapping UX (if expanded beyond design/surface/traffic).
- Reduced support burden for uploads that do not use canonical `DESIGN`/`SURFACE`/`TRAFFIC` keys.

## Related Packages
- **Depends on**: [20260323_roads_nodb_inslope_e2e](../20260323_roads_nodb_inslope_e2e/package.md)
- **Related**: [20260323_roads_wepp_reports_regen](../20260323_roads_wepp_reports_regen/package.md)
- **Follow-up**: Future Roads package for mapping additional per-segment override fields.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## References
- `wepppy/nodb/mods/roads/roads.py` - Current hard-coded property resolution and defaults.
- `wepppy/nodb/mods/roads/monotonic_segments.py` - Prepare-stage design eligibility currently keyed to `DESIGN`.
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py` - Roads upload/config/status/results route surfaces.
- `wepppy/weppcloud/templates/controls/roads_pure.htm` - Roads UI control shell.
- `wepppy/weppcloud/controllers_js/roads.js` - Roads front-end controller behavior.
- `tests/nodb/mods/test_roads_controller.py` - Existing controller coverage.
- `tests/weppcloud/routes/test_roads_bp.py` - Existing routes coverage.
- `wepppy/nodb/mods/roads/specification.md` - Roads specification baseline.

## Deliverables
- Package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Implemented mapping-aware Roads controller/API/UI behavior and tests.
- Updated Roads specification sections documenting attribute discovery + mapping contract.
- Code-review and QA-review notes stored under package artifacts.

## Follow-up Work
- Extend mapping controls to `condition`, `soil_texture`, `rfg_pct`, and `road_width_m` if needed.
- Add optional auto-suggest confidence hints for mapping candidates from value-domain matches.
- Add CSV export of discovered attribute profile for support/debug workflows.
