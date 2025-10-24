# Frontend Integration & Smoke Automation

**Status**: Open (2025-02-24)

## Overview
The controller modernization and StatusStream cleanup landed, but the last stretch of the UI upgrade requires coordinated work: finish the remaining Pure-template migrations, rewrite the run-page bootstrap script, and ship a repeatable smoke validation flow. This work package tracks that integration push.

## Objectives
- Deliver a Pure-first runs0 page with modernized controllers (map/delineation + treatments conversions outstanding).
- Replace legacy `run_page_bootstrap.js.j2` wiring with helper-driven initialization that works for the Pure shell.

## Scope
- Update remaining templates/controllers (map, delineation, treatments) to Pure + StatusStream patterns.
- Refactor bootstrap initialization to use controller emitters/helpers instead of direct DOM manipulation.
- Align docs (`control-ui-styling`, `AGENTS.md`) with the new bootstrap implementation.

## Out of Scope
- Deep UX redesign of map/delineation controls beyond necessary modernization.
- Non-controller front-end improvements (e.g., command bar redesign, htmx adoption).
- Full end-to-end Playwright suite (planning only unless time permits).

## Stakeholders
- Frontend controllers team (implementation)
- QA/ops (smoke testing tooling)
- Docs maintainers

## Success Criteria
- Map/delineation and treatments controls run on Pure templates with consistent StatusStream telemetry.
- `run_page_bootstrap.js.j2` supports modern controllers without legacy shim calls.
- Documentation refreshed to match the new entry points and validation steps.

## Remaining 2 % Checklist
- [x] **Map / delineation bundle** – Pure templates verified (map, channel delineation, subcatchments) with StatusStream wiring; control inventory updated.
- [x] **Treatments control** – Pure template + controller confirmed; no legacy fallback required and documentation refreshed.
- [x] **Bootstrap overhaul** – Controller bootstrap contract in place (`run_page_bootstrap.js.j2` + `WCControllerBootstrap`).
- [x] **Map initialization guard** – Fixed race condition where `buildViewportPayload()` was called before map center/zoom set; added Leaflet container reinitialization protection (2025-10-23).
- [x] **Docs & guidance (non-smoke)** – Finalize front-end documentation updates tied to bootstrap changes.
- ⏩ Smoke automation (profiles, CLI, extended flows) tracked under [20251023_smoke_tests](../20251023_smoke_tests/package.md).

## Known Issues & Fixes

## 2025-01-23: Fixes

### Map Bootstrap Fix (Complete)
**Issue**: Map bootstrap logic had three conditional branches, but only one called `setView(center, zoom)` properly. The other two either called `setZoom()` alone or relied on `fitBounds()`, leaving the map without a defined center.

**Fix** (`wepppy/weppcloud/controllers_js/map.js`):
- Refactored `bootstrap()` to ensure ALL branches call `this.map.setView(center, zoom)` with valid coordinates
- Added fallback defaults: `center = center || [0, 0]` and `zoom = zoom || 2`
- Now guarantees map center is always initialized before any controller attempts to read it

**Result**: Eliminates "Set map center and zoom first" errors during page load.

---

### Preflight Script Compatibility Fix (Complete)
**Issue**: `wepppy/weppcloud/static/js/preflight.js` referenced undefined `readonly` variable

**Fix**:
- Exposed `window.readonly` in `run_page_bootstrap.js.j2` template
- Added fallback check in preflight.js: `readonly = window.readonly !== undefined ? window.readonly : false;`

**Result**: Preflight checklist renders without console errors.

---

### URL Construction Fix for Climate/Team Endpoints (Complete)
**Issue**: Climate and team controllers used relative URLs like `"view/closest_stations/"` which resulted in 404 errors because they were missing the config segment in the path (going to `/weppcloud/runs/{runid}/view/...` instead of `/weppcloud/runs/{runid}/{config}/view/...`).

**Root Cause**: The `url_for_run()` utility function only added the `?pup=` parameter but didn't construct the full run-scoped path. When combined with the HTTP helper's `applySitePrefix()`, URLs were incorrectly formed.

**Fix** (utils.js):
- Updated `url_for_run()` to build the complete run-scoped path: `/runs/{runid}/{config}/{url}`
- Uses `window.runId` and `window.runConfig` (available from bootstrap template)
- Properly URL-encodes path segments
- Still adds `?pup=` parameter when needed for pup runs

**Usage** (climate.js, team.js):
- Controllers now use: `url_for_run("view/closest_stations/")`
- Which produces: `/runs/{runid}/{config}/view/closest_stations/`
- HTTP helper then prepends site prefix: `/weppcloud/runs/{runid}/{config}/view/closest_stations/`

**Result**: All run-scoped endpoints now resolve to correct paths with both runid and config segments.

---

## Follow-up
- Smoke automation (profiles, CLI, extended Playwright flows) continues under [20251023_smoke_tests](../20251023_smoke_tests/package.md).
