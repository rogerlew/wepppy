# Tracker - Geneva HRU Choropleth WP03 (Deck.gl Map UI and Themed Controls)

> Living tracker for WP03 report UI implementation.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-29 06:34 UTC  
**Current phase**: Completed
**Last updated**: 2026-04-29 08:09 UTC
**Next milestone**: Hand off to WP04 validation and release docs
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffolded and linked from orchestration board (2026-04-29 06:34 UTC).
- [x] Added Geneva HRU map geometry query endpoint `POST /query/geneva/hru_map_features` with additive availability envelope and canonical join keys (`hru_value`, `hru_id`) (2026-04-29 07:32 UTC).
- [x] Added run-scoped cached HRU polygon vectorization (`geneva/hru_map_features.wgs.geojson`) from `geneva/hru_map.tif` + legend crosswalk (2026-04-29 07:36 UTC).
- [x] Added Geneva summary deck.gl map panel and themed map controls using existing `wc-map-*` visual language (2026-04-29 07:54 UTC).
- [x] Implemented map data loading via query-engine-style POST payloads (`schema_version`, event/measure filters) and empty/error handling (`legacy_hru_event_measures_missing`, unavailable geometry) (2026-04-29 07:58 UTC).
- [x] Applied `winter` color mapping for runoff measures and added legend/status updates wired to event selection (2026-04-29 08:01 UTC).
- [x] Added JS regression coverage for map geometry+rows render flow in `geneva_summary_report.test.js` (2026-04-29 08:04 UTC).

## Decision Log

### 2026-04-29 07:21 UTC: Geometry source contract for HRU choropleth
**Context**: WP02 row payload provides event/measure values but no HRU polygon geometry artifact.

**Options considered**:
1. Defer map until a separate geometry artifact work package.
2. Materialize a run-scoped geometry artifact from `hru_map.tif` and legend crosswalk.

**Decision**: Option 2.

**Impact**: Enables deck.gl vector choropleth now while keeping joins canonical (`hru_value` + `hru_id`) and preserving WP02 row contracts.

---

### 2026-04-29 07:29 UTC: Query surface shape for WP03 UI
**Context**: WP03 required query-engine-style calls and robust unavailable handling.

**Options considered**:
1. Fetch geometry through ad hoc static file paths.
2. Add dedicated query endpoint with explicit availability envelope.

**Decision**: Option 2 (`POST /query/geneva/hru_map_features`).

**Impact**: Keeps report calls contract-driven and consistent with existing Geneva query envelopes.

---

### 2026-04-29 07:50 UTC: Measure control split from summary measure
**Context**: Summary measure includes watershed-only `peak_discharge`, which is unsupported for HRU map scope.

**Options considered**:
1. Reuse summary measure selector and surface frequent scope errors on map.
2. Add dedicated map measure selector restricted to `runoff_depth|runoff_volume`.

**Decision**: Option 2.

**Impact**: Preserves watershed-level summary behavior while keeping map requests scope-valid by design.

## Validation Evidence

- `wctl run-pytest tests/nodb/mods/geneva/test_geneva_hru_map_geometry_service.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py --maxfail=1` (pass)
- `wctl run-npm test -- geneva_summary_report` (pass)
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` (pass)
- `wctl run-npm lint` (fails due pre-existing unrelated `jest/no-conditional-expect` issues in `controllers_js/__tests__/landuse_map_inline.test.js`)
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls --path docs/work-packages/20260428_geneva_hru_choropleth_series --path wepppy/nodb/mods/geneva/specification.md` (pass)
- `git diff --check` (pass)
