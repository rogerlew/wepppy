# Landuse Controller Migration Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Information-gathering checklist for the upcoming `landuse.js` refactor. Review `docs/dev-notes/controller_foundations.md` first so this plan stays aligned with the shared controller strategy.

## Controller Surface Audit
- Inventory every jQuery touchpoint in `wepppy/weppcloud/controllers_js/landuse.js`:
  - Delegated form handlers, DOM-ready hooks, `.on()` namespaces.
  - AJAX utilities (`$.ajax`, `$.get`, `$.post`) and any `$.Deferred` chains.
  - DOM writes (`hide/show`, `data`, `attr`, HTML/text injections).
- Map each responsibility to the vanilla helper to be used:
  - `WCDom` for selection, delegation, visibility, class toggles.
  - `WCForms` for serialization/hydration of form state.
  - `WCHttp` (plus `WCHttp.HttpError`) for network calls, CSRF, timeouts.
  - `WCEvents` if the controller emits or listens for cross-module events.
- Note shared utilities leveraged today:
  - `controlBase` mixin for job orchestration and telemetry.
  - `unitizer_client.js` usage (value rendering, reactive updates).
  - Map overlays / Leaflet integrations that may require helper-friendly wrappers.
- ✅ Landuse controller now runs solely on helper modules—`WCDom` wraps the legacy adapters, delegated report actions, and visibility toggles, while `WCHttp` handles FormData uploads and JSON posts. `WCEvents.createEmitter` backs a scoped event bus (`landuse:build:*`, `landuse:report:loaded`, etc.) so neighboring controllers can subscribe without polling DOM state.

## Template Contract
- Review `wepppy/weppcloud/templates/controls/landuse*.htm` and any included partials.
  - Catalog IDs, data attributes, and structural assumptions the controller relies on.
  - Decide whether vanilla delegation needs markup tweaks (e.g., add `data-action` hooks).
- Flag inline scripts that reference `$` or expect jQuery globals.
  - Plan equivalent bootstrap strategy (DOMContentLoaded listeners, direct module initialization).
- ✅ No template changes required for the helper migration; existing `data-landuse-*` hooks are now consumed via `WCDom.delegate`.

## Backend Touchpoints
- Enumerate controller API calls and match to Flask endpoints:
  - Primary routes under `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`.
  - Secondary interactions (e.g., disturbed, soils, wepp endpoints triggered downstream).
- Define payload expectations per endpoint once helpers are adopted:
  - Whether to send JSON bodies vs. URL-encoded forms.
  - How `parse_request_payload` should normalize booleans, arrays, numeric values.
- Assess transition approach:
  - Determine if endpoints must support both legacy form posts and new JSON during rollout.
  - Decide whether the refactor will update all call sites in one sweep to avoid dual-mode maintenance.
- ✅ All Landuse routes now use `parse_request_payload`, coerce numeric inputs (`mode`, coverage values, Topaz IDs), and return descriptive errors when payload fields are missing.
- ✅ The RQ build endpoint now calls `Landuse.parse_inputs` to hydrate native integers/booleans and reuses `parse_request_payload` for JSON + form parity. New pytest coverage (`tests/weppcloud/routes/test_rq_api_landuse.py`) verifies Redis task wiring, disturbed flags, and user-defined uploads.

## State & Data Structures
- Catalog complex payloads (selected landuse rows, mapping updates, units) that need explicit JSON structures.
- Confirm how checkboxes/toggles are currently interpreted (`"on"`, `None`, etc.) and define the target boolean representation (`true/false`) for the new helpers.
- Identify any server-side expectations for field names or ordering that must remain stable.

## Dependencies on Other Controllers
- Identify shared DOM regions or cooperative workflows with nearby controllers (soils, treatments, BAER).
- Determine coordination needs:
  - Event broadcasts when landuse changes should trigger updates elsewhere.
  - Shared widgets (unitizer panels, map overlays) that may require helper enhancements or new event contracts.
- Note if unitizer interactions expose gaps in current helpers that should be addressed before the refactor.

## Testing & Tooling
- Jest coverage targets:
  - Form submission happy path and error surfaces (mock fetch responses).
  - UI toggles (table filters, mapping controls) to guard DOM rewrites.
  - Unitizer interactions or event emission if they change.
- Backend validation:
  - Identify pytest suites to exercise updated endpoints (e.g., `tests/weppcloud/routes/test_landuse*.py`).
  - Plan integration tests for payload shape changes (arrays, booleans).
- Ensure `npm test` and `python wepppy/weppcloud/controllers_js/build_controllers_js.py` remain part of the handoff validation.
- ✅ Added `controllers_js/__tests__/landuse.test.js` (jsdom) plus expanded `tests/weppcloud/routes/test_landuse_bp.py` to cover JSON/form parity.
- ✅ Added RQ-flavoured regression tests (`tests/weppcloud/routes/test_rq_api_landuse.py`) to guard async job orchestration and ensure RedisPrep/job queue side effects remain stable during helper migrations.

## Rollback Strategy
- Pinpoint high-risk areas (large historical run archives, landuse data migrations) that could be impacted.
- Define rollback path:
  - Ability to revert the controller bundle to the last known good version.
  - Potential feature toggles or config flags to disable the new behavior quickly if needed.
- Document monitoring signals (Redis logs, WebSocket events, user feedback channels) to watch post-deploy.

---

Use this document to guide discovery before coding. Update it with findings as the landuse migration proceeds.
