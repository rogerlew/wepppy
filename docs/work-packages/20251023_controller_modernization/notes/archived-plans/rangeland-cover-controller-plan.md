# Rangeland Cover Controller Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Helper-first modernization notes and post-migration contract for the rangeland cover control.

## Snapshot (2025-10-22)
- `controllers_js/rangeland_cover.js` still depends on jQuery event wiring (`.on`, `.post`, `.get`) and overrides `triggerEvent` to walk controlBase callbacks; it never touches the helper stack (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`) and does not participate in the shared job lifecycle events.
- Inline handlers remain in both legacy and Pure templates (`onchange`, `onclick`), so readonly mode bypasses delegation guards and prevents reuse from the helper registry.
- Flask endpoints (`tasks/set_rangeland_cover_mode`, `tasks/build_rangeland_cover`) rely on `request.form`, expect stringified integers, and advertise success by returning the legacy `{Success: true}` payload. Booleans and numeric coercion happen ad hoc in the NoDb setters.
- There is no domain emitter; downstream modules (e.g., SubcatchmentDelineation) patch `triggerEvent` observers manually and cannot subscribe to scoped events such as `rangeland:run:*`.
- No Jest or pytest coverage exists for the control. Regression testing is manual and the controller README does not mention rangeland specifics.

## Modernization Targets
- Adopt helper-first setup: ensure `controlBase`, `WCDom`, `WCForms`, `WCHttp`, and `WCEvents` are required up front, swap jQuery adapters for helper calls, and delegate DOM events through `data-rangeland-*` hooks.
- Emit scoped events alongside inherited `job:*` events:
  - `rangeland:config:loaded` when the form is initialised and defaults applied.
  - `rangeland:mode:changed` with `{ mode }` any time the radio group toggles.
  - `rangeland:rap-year:changed` with `{ year }` when the RAP year input changes.
  - `rangeland:run:started|completed|failed` co-emitted with controlBase job telemetry for builds.
  - `rangeland:report:loaded|failed` after the summary HTML refresh completes.
- Normalise payloads through `WCForms.serializeForm` and `WCHttp.request`, mirroring the helper response contract (`detail`, `body`, etc.) and updating error handling to reuse `controlBase` stacktrace helpers.
- Replace inline template handlers with `data-rangeland-action` attributes and ensure RAP form fragments hide/show via helper toggles (no direct `style.display` manipulations).

## Event & Payload Contract
- **Domain events** (in addition to `job:started|progress|completed|failed` from `controlBase`):
  - `rangeland:config:loaded` — payload `{ mode, rapYear, defaults }`.
  - `rangeland:mode:changed` — payload `{ mode }`.
  - `rangeland:rap-year:changed` — payload `{ year }`.
  - `rangeland:run:started` — payload `{ defaults, mode }`.
  - `rangeland:run:completed` — payload `{ defaults, mode }`.
  - `rangeland:run:failed` — payload `{ error }`.
  - `rangeland:report:loaded` — payload `{ html }`.
  - `rangeland:report:failed` — payload `{ error }`.
  - Legacy bridge: `triggerEvent('RANGELAND_COVER_BUILD_TASK_COMPLETED', …)` still fires so Subcatchment controllers and legacy DOM listeners stay functional.
- **HTTP surfaces** (all routed through `parse_request_payload`):
  - `POST /runs/<runid>/<config>/tasks/set_rangeland_cover_mode/`
    - Body: `{ "mode": <int>, "rap_year": <int|null> }`.
    - Response: `{ "Success": true }` (legacy casing retained for compatibility).
  - `POST /runs/<runid>/<config>/tasks/build_rangeland_cover/`
    - Body: `{ "rap_year": <int|null>, "defaults": { "bunchgrass": <float>, "forbs": <float>, "sodgrass": <float>, "shrub": <float>, "basal": <float>, "rock": <float>, "litter": <float>, "cryptogams": <float> } }`.
    - Response: `{ "Success": true, "Content": { "job_id": <optional> } }` (job id remains optional; controller infers from WebSocket if omitted).
- **DOM hooks** (element IDs retained for backward compatibility, but helpers target `data-rangeland-*` attributes):
  - Form shell: `#rangeland_cover_form` with status fields `#info`, `#status`, `#stacktrace`, `#rq_job`, hint node `#hint_build_rangeland_cover`.
  - Mode radios expose `data-rangeland-mode="<value>"` for delegation; the RAP year wrapper carries `data-rangeland-rap-section`.
  - Build button uses `data-rangeland-action="build"` and reads defaults via helper serialization.

## Testing Checklist
- **Frontend** — Add `controllers_js/__tests__/rangeland_cover.test.js` covering:
  - Helper bootstrap (throws without helpers).
  - Delegated mode + RAP year events via `WCDom.delegate`.
  - Build lifecycle (`WCHttp.request` payload, event emission, controlBase hooks).
  - Report refresh success/failure handling.
  Run with `wctl run-npm test -- rangeland_cover`.
- **Backend** — Extend `tests/weppcloud/routes/test_rangeland_cover_bp.py` (new file) using `parse_request_payload` fixtures + NoDb singleton factory to ensure modes, RAP year, and defaults are set natively. Execute with `wctl run-pytest tests/weppcloud/routes/test_rangeland_cover_bp.py`.
- **Lint/bundle** — `wctl run-npm lint` and `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.

## Follow-ups / Open Questions
- Confirm whether downstream map panels expect `RANGELAND_COVER_BUILD_TASK_COMPLETED`; if so, emit a bridging DOM `CustomEvent` alongside `rangeland:run:completed` (document in README).
- Evaluate surfacing RAP data availability via a separate endpoint so the controller can disable RAP mode when datasets are missing (outside current scope).
- Consider migrating Modify Rangeland Cover (map tab) to the same helper stack once the main control lands.
