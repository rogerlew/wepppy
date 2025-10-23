# BAER Controller Modernization Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Scope notebook for migrating `wepppy/weppcloud/controllers_js/baer.js` to the shared helper stack.

## Current State
- Controller relies heavily on jQuery (`$`, `.on`, `.post`, `.get`) and manual DOM manipulation.
- Upload form (`#sbs_upload_form`) wires inline `onclick` handlers in `controls/baer_upload.htm`.
- Websocket lifecycle is delegated through `controlBase.attach_status_stream`; UI status/stacktrace areas are managed directly via jQuery wrappers.
- Map overlay logic calls directly into `MapController` and injects a slider via raw HTML string plus jQuery listeners.
- Backend routes live in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` and expect form posts/JSON without `parse_request_payload`.
- No dedicated Jest coverage for BAER; backend tests piggyback on disturbed module fixtures.

## Key Dependencies
- **Frontend helpers**: `controlBase`, `controlBase.attach_status_stream`, `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `MapController`, `SubcatchmentDelineation`.
- **Templates**: `wepppy/weppcloud/templates/controls/baer_upload.htm`, run page includes (`runs0_pure.htm`).
- **Backend**: `disturbed_bp` routes (`tasks/upload_sbs`, `tasks/remove_sbs`, `tasks/build_uniform_sbs/<value>`, `tasks/modify_burn_class`, `tasks/modify_color_map`, `tasks/set_firedate`, `query/baer_wgs_map`, `view/modify_burn_class`, legend/resource endpoints).
- **NoDb mods**: `wepppy.nodb.mods.baer`, `wepppy.nodb.mods.disturbed` (shared interface for map operations).

## Modernization Targets
1. Replace jQuery with helper modules:
   - Use `WCDom.delegate` and `data-*` attributes for events.
   - Serialize payloads via `WCForms.serializeForm` or targeted readers.
   - Perform HTTP requests with `WCHttp.request`, capturing structured errors.
2. Expose lifecycle events through `WCEvents.createEmitter` (`baer:upload:*`, `baer:map:*`, job orchestration hooks).
3. Integrate `controlBase` job tracking (`job:started`, `job:completed`, `job:error`) in upload/remove/build uniform flows.
4. Rebuild legend/opacity slider via helper-driven DOM updates; avoid raw HTML concatenation where possible.
5. Align templates with helper expectations: remove inline JS, add `data-action`, `data-mode`, etc., for delegation.

## Backend Alignment Notes
- Flask routes now rely on `parse_request_payload` for structured inputs:
  - `tasks/set_firedate/` accepts JSON `{"fire_date": "<YYYY-MM-DD>"}` and persists via `Disturbed.fire_date`.
  - `tasks/modify_burn_class` consumes `{"classes": [int, int, int, int], "nodata_vals": "<tokens>"}` and returns an error when breaks are missing/invalid.
  - `tasks/modify_color_map` requires a mapping of `"R_G_B": "<severity>"` and guards malformed RGB tokens.
  - `tasks/modify_disturbed` still streams full row payloads; single-row inputs are re-wrapped into lists after parsing so CSV writers see the legacy shape.
- Upload endpoints enforce secure filenames and error out when `input_upload_sbs` is absent.
- `authorize_and_handle_with_exception_factory` decorates BAER task routes so authorization and exception handling align with other modules.

## Event Surface & Helper Usage
- Controller attaches a scoped emitter via `WCEvents.useEventMap` covering:
  - `baer:mode:changed`, `baer:upload:*`, `baer:remove:*`, `baer:uniform:*`
  - `baer:firedate:*`, `baer:classes:*`, `baer:color-map:*`
  - `baer:map:shown`, `baer:map:error`, `baer:map:opacity`
- `controlBase` lifecycle events (`job:started`, `job:completed`, `job:error`) fire for upload/remove/uniform flows alongside BAER-specific topics.
- The opacity slider is generated under `#sbs_legend` with id `baer-opacity-slider`, dispatching `input/change` updates through the emitter and `L.imageOverlay.setOpacity`.

## Testing Strategy
- **Frontend**: `controllers_js/__tests__/baer.test.js` exercises delegated handlers, FormData submissions, slider opacity updates, and error surfacing. Keep fixtures in sync with template data attributes (`data-baer-*`) whenever markup evolves.
- **Backend**: `tests/weppcloud/routes/test_disturbed_bp.py` now asserts class-break coercion, RGB parsing, fire-date persistence, and the single-row wrapping logic introduced by `parse_request_payload`.
- **Commands**: Standard cadence—`wctl run-npm lint`, `wctl run-npm test`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py`, then `wctl run-pytest tests --maxfail=1`.

## Open Questions / Follow-ups
- Confirm whether `nodata_vals` expects comma-separated string or requires parsing into iterable for `Baer.modify_burn_class`.
- Determine if opacity slider should be shared via `control_base` events for other map controllers.
- Audit status-stream integration—ensure `controlBase.attach_status_stream` events do not duplicate existing socket updates and that any legacy `WSClient` references are removed.
- Verify backend can safely coerce missing map data (should return `error_factory` as today).

*Last updated: 2025-10-22.*
