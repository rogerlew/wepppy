# Treatments Controller Migration Plan
> Bring the treatments control onto the helper stack while preserving WEPPcloud workflows.

## Snapshot (2025-10-22)
- **Controller** (`controllers_js/treatments.js`) now boots through `controlBase`, uses `WCDom` delegation for all interactions, serializes state with `WCForms`, posts via `WCHttp`, and exposes a scoped emitter through `WCEvents.useEventMap`. The controller emits rich telemetry for list hydration, mode/selection changes, run lifecycle, job lifecycle, and status updates while proxying StatusStream triggers for legacy listeners.
- **Template** (`templates/controls/treatments_pure.htm`) applies `data-treatments-*` hooks across radios, selection dropdown, upload field, RQ badge, and hint text. Mode-specific stacks use `data-treatments-panel="selection"` / `"upload"`, keeping visibility logic in the controller instead of inline handlers. Status/stacktrace/info nodes remain inside the form so `controlBase` and StatusStream stay wired without jQuery.
- **Routes**: `POST /runs/<runid>/<config>/tasks/set_treatments_mode/` now runs through `parse_request_payload`, accepts JSON or legacy form posts, coerces `mode` to the `TreatmentsMode` enum, and returns `success_factory()`. `POST /runs/<runid>/<config>/rq/api/build_treatments` continues to accept multipart uploads, persisting mapping selection before enqueuing `build_landuse_rq`.
- **Testing**: Jest coverage lives in `controllers_js/__tests__/treatments.test.js` (helper bootstrap, delegated mode/selection flows, job orchestration, error handling). Backend coverage is provided by `tests/weppcloud/routes/test_treatments_bp.py`, which uses `tests.factories.singleton_factory` to validate enum coercion and legacy form fallbacks. Both suites are part of the standard refactor workflow.
- **Telemetry**: When available, the controller attaches to the `treatments` StatusStream channel (including stacktrace enrichment); otherwise it falls back to `WSClient`. `appendStatus` keeps the DOM, hint, and RQ badge synchronized while emitting `treatments:status:updated` payloads for dashboards.

## Remaining Gaps / Risks
- `landuse_management_mapping_selection` remains a build-only concern; consider surfacing mapping choices in the UI when mode 4 is active or documenting why it remains outside the controller contract.
- Job completion details depend on StatusStream event naming—confirm downstream dashboards listen to the new `treatments:job:*` helper events instead of scraping legacy tokens.
- NoDb does not currently persist the most recent single-selection value; evaluate whether that state should be recorded for resume/audit scenarios and hydrated via `WCForms.applyValues`.

## Event & Payload Contract
- **Event allow list**: `treatments:list:loaded`, `treatments:scenario:updated`, `treatments:mode:changed`, `treatments:mode:error`, `treatments:selection:changed`, `treatments:run:started`, `treatments:run:submitted`, `treatments:run:error`, `treatments:job:started`, `treatments:job:completed`, `treatments:job:failed`, `treatments:status:updated`.
- **Mode payload** (`tasks/set_treatments_mode/`): `{ mode: <int>, single_selection: <str | null> }`. Flask coerces `mode` to `TreatmentsMode` and ignores `single_selection` today (future enhancement TBD).
- **Build payload** (`rq/api/build_treatments`): multipart `FormData` with the active mode, optional `treatments_single_selection`, and optional raster upload (`input_upload_landuse`). When mode 4 is active the route still requires `landuse_management_mapping_selection`.

## Testing & Tooling Checklist
- `wctl run-npm lint`
- `wctl run-npm test -- treatments`
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-pytest tests/weppcloud/routes/test_treatments_bp.py`
- Run a StatusStream-enabled smoke test to verify job telemetry (`treatments:job:*`) reaches dashboards.

## Follow-ups
- Decide whether to persist `treatments_single_selection` in NoDb and hydrate it during restore flows.
- Revisit the controller once `controlBase.submitJob` APIs land to trim the remaining manual job wiring.
- After other domains adopt the same telemetry pattern, document shared job payload semantics (e.g., expected stacktrace metadata) in `docs/dev-notes/controller_foundations.md`.
