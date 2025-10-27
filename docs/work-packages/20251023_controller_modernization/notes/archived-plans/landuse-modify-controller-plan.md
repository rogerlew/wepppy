# Landuse Modify Controller Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Scoping notes for the helper migration of `landuse_modify.js`. Review alongside [`docs/dev-notes/controller_foundations.md`](../../../../dev-notes/controller_foundations.md) and the module refactor workflow.

## Current State (Discovery)
- **Controller surface**: Singleton wraps `#modify_landuse_form`, relies heavily on jQuery (`$`, `.on`, `.post`, `.get`) for DOM lookup, event binding, and AJAX. Map selection toggles call into `MapController`, `SubcatchmentDelineation`, and optionally `Landuse` after a successful modification.
- **DOM contract**: Template exposes IDs (`checkbox_modify_landuse`, `textarea_modify_landuse`, `selection_modify_landuse`, `btn_modify_landuse`) and assumes inline jQuery handlers. Selection mode depends on a checkbox, while the textarea tracks comma-separated Topaz IDs. Status/stacktrace panels are already in the `ui.status_panel`/`ui.stacktrace_panel` layout but still expect the controller to call `hide()`/`show()` directly.
- **Map workflow**: Leaflet layer fetched from `resources/subcatchments.json`. Selection works via click handlers and a manual rectangle selection (Shift+drag). The code maintains `selected` and `selectionRect` sets but stores UI state by writing raw values into the textarea through `textarea.val(...)`.
- **Backend interactions**:
  - `tasks/modify_landuse/` expects `topaz_ids` (string or list) and `landuse`; route already uses `parse_request_payload` but still re-parses comma-separated strings and stores them as ints before handing to `Landuse.modify`.
  - `tasks/sub_intersection/` (handled elsewhere) provides rectangle selection results; current controller posts JSON via jQuery.
- **Telemetry**: Extends `controlBase` but overrides `triggerEvent` manually to piggy-back on `LANDCOVER_MODIFY_TASK_COMPLETED`. Stacktrace + status panels are updated using jQuery `.html()` / `.hide()`. No emitter for `WCEvents`.
- **Testing**: No dedicated Jest coverage for the controller. Flask tests cover route parsing but expect form-encoded posts.

## Migration Goals
- Switch to helper primitives:
  - DOM: `WCDom.qs`, `WCDom.delegate`, `WCDom.toggle`, etc., for binding buttons/checkboxes and handling visibility.
  - Forms: `WCForms` for reading/writing checkbox + textarea values (avoid manual `.val()`).
  - HTTP: `WCHttp.request/postJson` for both rectangle selection and modify submissions.
  - Events: `WCEvents.useEventMap` to publish domain events (`landuse:modify:*`, `landuse:selection:*`) and hook into `controlBase` lifecycle without overriding `triggerEvent`.
- Maintain Leaflet integration but store selection state separately from textarea, then reflect conversions via helper-friendly updates.
- Normalize payload shape: submit JSON with `topaz_ids` as an array and `landuse` as integer strings, use `parse_request_payload` boolean coercion for selection toggles, and keep rectangle selection POST JSON behaviour intact.
- Ensure `controlBase` job lifecycle wiring (`job:started`, `job:completed`, `job:error`) remains intact; leverage emitter to notify SubcatchmentDelineation/Landuse controllers via events instead of manual `triggerEvent` overrides.

## Risks / Unknowns
- Subcatchment map dependencies: verify the controller still cooperates with `MapController` and `SubcatchmentDelineation` singleton contracts after removing jQuery.
- Rectangle selection: confirm `tasks/sub_intersection/` route supports the JSON body posted via `WCHttp.postJson`. If not, add route adjustments or request wrapper to stay compatible.
- Selection state: ensure `WCForms` hydration handles empty arrays vs. empty string so the backend receives `[]` rather than `""`.
- Event propagation: the legacy `triggerEvent('LANDCOVER_MODIFY_TASK_COMPLETED')` is consumed by other modules; the refactor must either emit the same controlBase event or forward it through the new emitter so existing listeners continue to function.

## Test Strategy
- **Jest**: add `controllers_js/__tests__/landuse_modify.test.js` using jsdom to validate delegation, selection toggles, payload assembly, event emission, and error handling.
- **Pytest**: extend `tests/weppcloud/routes/test_landuse_bp.py` to cover JSON payload with array inputs and confirm `Landuse.modify` receives normalised values. Keep using shared factories (`tests/factories/rq_environment.py`, `tests/factories/singleton_factory.py`) when interacting with async routes.
- **Manual**: smoke test selection toggles and modification workflow in dev stack after bundle rebuild.

## Follow-ups
- Consider extracting shared Leaflet selection helpers if other controllers (e.g., BAER, disturbance) replicate the pattern.
- Evaluate whether `tasks/sub_intersection/` needs its own helperized client or if it should become part of a shared map utility module.
- Document emitted events in `controllers_js/README.md` and flag any helper gaps for the shared primitives backlog.

## Implementation Snapshot (2025 helper migration)
- **DOM contract**: `modify_landuse.htm` exposes `data-landuse-modify-action="toggle-selection|submit"` plus `data-landuse-modify-field="topaz-ids|landuse-code"` so `WCDom.delegate` can manage checkbox toggles, textarea syncing, and submit clicks without direct selectors.
- **Event surface**: `LanduseModify.getInstance().events = WCEvents.useEventMap(['landuse:modify:started', 'landuse:modify:completed', 'landuse:modify:error', 'landuse:selection:changed', 'job:started', 'job:completed', 'job:error'])`. Success flows still invoke downstream controllers via the legacy `LANDCOVER_MODIFY_TASK_COMPLETED` signal.
- **Transport**: controller posts JSON (`{ topaz_ids: [...], landuse: '<code>' }`) to `tasks/modify_landuse/` and extent payloads to `tasks/sub_intersection/`. The Flask route now normalises IDs through `_coerce_topaz_ids` / `_coerce_landuse_code`, so downstream NoDb helpers always receive integer-safe strings.
- **Testing**: `controllers_js/__tests__/landuse_modify.test.js` covers selection toggles, map enablement, event emission, and error handling with stubbed `MapController`/Leaflet globals. Backend coverage in `tests/weppcloud/routes/test_landuse_bp.py` exercises JSON + form payloads and error cases; keep them in sync with future payload tweaks.
