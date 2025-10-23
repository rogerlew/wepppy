# Rangeland Cover Modify Controller Plan
> Helper-first migration tracker for the Modify Rangeland Cover control.

## Current State Snapshot
- **Controller:** `wepppy/weppcloud/controllers_js/rangeland_cover_modify.js` now runs helper-first. `WCDom`, `WCForms`, `WCHttp`, and `WCEvents` power DOM hydration, delegated wiring, payload serialization, and event emission; jQuery usage has been removed. The singleton exposes a scoped emitter (`rangeland:modify:*`, legacy `RANGELAND_COVER_MODIFY_TASK_COMPLETED`, and `job:*`) and keeps compatibility with `controlBase`.
- **Map integration:** Leaflet selection is still driven through `MapController`, but listeners are attached/detached via helper wiring. Box selections, hover styles, and layer indexing remain encapsulated while selection state synchronizes to the textarea and cover summary fetches.
- **Templates:** `templates/controls/modify_rangeland_cover.htm` now carries `data-rcm-action` / `data-rcm-field` hooks on toggles, the textarea, and all cover inputs. Status, stacktrace, and RQ job panels stay under the form shell for `controlBase`.
- **Backend routes:** `rangeland_bp.task_modify_rangeland_cover` and `rangeland_cover_bp.query_rangeland_cover_current` both rely on `parse_request_payload`, normalizing Topaz IDs, coercing floats, validating `0–100` cover ranges, and returning descriptive `exception_factory` payloads on failure.
- **Tests:** Jest coverage (`controllers_js/__tests__/rangeland_cover_modify.test.js`) exercises summary hydration, run submission, and validation paths. Pytest coverage (`tests/weppcloud/routes/test_rangeland_cover_bp.py`) now verifies modify payload parsing, error handling, and legacy fallbacks alongside existing build/mode checks.
- **Events/refresh:** Successful runs emit helper events, relay `job:*` telemetry, and still trigger a Subcatchment + Rangeland report refresh. Summary and request errors push stacktraces while surfacing `rangeland:modify:error`.

## Modernization Goals
1. **Helper-first controller**
   - Replace all jQuery usage with `WCDom`, `WCForms`, `WCHttp`, and `WCEvents`.
   - Use `controlBase` helpers for status handling; emit scoped events (e.g., `rangeland:modify:loaded`, `rangeland:modify:selection:changed`, `rangeland:modify:run:started|completed|error`, plus `job:*` proxies).
   - Normalize payload building through a single serializer (Topaz ID parsing, cover value coercion) before calling backend endpoints.
2. **Template alignment**
   - Introduce semantic `data-rcm-*` hooks for buttons, toggles, and textareas to support delegated event wiring.
   - Ensure form markup keeps status/stacktrace panels compatible with `controlBase` without inline handlers.
3. **Backend cohesion**
   - Update modify endpoint to use `parse_request_payload`, validate numeric ranges, and ensure native numeric/array types reach `RangelandCover.modify_covers`.
   - Confirm current cover summary route accepts normalized arrays (no empty string artifacts).
4. **Testing**
   - Add Jest coverage for controller initialization, selection toggles, payload serialization, helper event emission, and error handling.
   - Extend pytest coverage with fixtures from `tests/factories/` to validate modify payload parsing (arrays, validation errors, legacy compatibility).
5. **Documentation**
   - Update `controllers_js/README.md` & `controllers_js/AGENTS.md` with emitted events, helper usage, and test expectations.
   - Record payload schema, helper touchpoints, and open questions here as development progresses.

## Implementation Notes (February 2025)
- Controller emits `rangeland:modify:loaded`, `rangeland:modify:selection:changed`, `rangeland:modify:run:(started|completed|error)`, `rangeland:modify:error`, plus the legacy DOM event and `job:*` proxies. Selection deduplication prevents redundant summary calls.
- Cover summaries and run submissions both travel through `WCHttp.postJson`, sharing a single normalization pipeline (`readCoverValues` + `_coerce_cover_values` on the backend) to guarantee float coercion and range checks.
- Validation failures (missing covers, out-of-range values, empty selection, unknown Topaz IDs) surface via `exception_factory`, mirroring to the stacktrace panel and `rangeland:modify:error` event payloads.
- Jest suite stubs `MapController`, `SubcatchmentDelineation`, and `RangelandCover` to verify refresh behaviour without a full Leaflet environment; backend tests rely on `tests.factories.singleton_factory` to capture modify calls.

## Open Questions / Follow-ups
- Should the Leaflet selection helpers (layer indexing, rectangle drawing) be abstracted into a shared utility for other map-based modify controllers?
- Consider extending `controlBase` with a first-class `submitJob` helper so controllers like this one can trim boilerplate around status labels and job telemetry.
- Monitor Redis/WebSocket telemetry to ensure the new `rangeland:modify:*` events cover downstream dashboard needs; add additional payload fields if observers request them.

## Next Steps
- [x] Inventory existing helper patterns (landuse modify, ash controller) for reference implementations.
- [x] Design event map (`WCEvents.useEventMap`) covering selection, payload, and run lifecycle.
- [x] Draft helper-first controller skeleton before porting map logic.
- [x] Align template `data-*` hooks and ensure tests capture DOM wiring.
- [x] Update pytest fixtures to use `parse_request_payload` and native types.
- [ ] Evaluate extracting common Leaflet selection utilities into a shared helper module (track in future work if adopted).
