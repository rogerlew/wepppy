# Subcatchment Delineation Controller Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Initial discovery notes before the helper migration. Align implementation with `docs/dev-notes/controller_foundations.md` and `docs/dev-notes/module_refactor_workflow.md`.

## Discovery Log (2025-10-22)
- Legacy controller (`wepppy/weppcloud/controllers_js/subcatchment_delineation.js`) is still jQuery-heavy: direct `$("#...")` bindings, `.on()` namespaced listeners, and manual AJAX flows.
- Job orchestration rides on `controlBase.attach_status_stream`, but custom `triggerEvent` overrides gate downstream controllers (`ChannelDelineation`, `Wepp`). Need to translate these into `WCEvents` contracts (`subcatchment:build:*`) while keeping the legacy notifications alive.
- Color-map UI relies on radio groups, range inputs, and explicit `render_legend` calls. Sliders/radios are wired via bespoke helpers (`bindSlider`, `bindRadioGroup`). Expect to replace these with `WCDom` delegation + targeted helpers.
- GeoJSON rendering toggles `L.layerGroup` and a custom WebGL layer with palette lookups. Need to ensure helper adoption does not break Leaflet integrations or label overlays.
- Current payload assembly happens via form serialization and manual boolean coercion (`"on"`). Backend endpoints likely accept legacy form posts; will move to `parse_request_payload` for consistent typing.
- Templates (`wepppy/weppcloud/templates/controls/subcatchment_delineation*.htm`) still surface inline IDs & handlers; must audit for data-attribute gaps prior to swapping in `WCDom`.
- Tests appear thin: no Jest suite targeting this controller; pytest coverage exists under `tests/weppcloud/routes/test_subcatchment_delineation*.py` but will need updates to match payload changes.

## Refactor Checklist
- [x] Confirm helper coverage (WCDom, WCForms, WCHttp, WCEvents, controlBase). Capture any helper gaps in this note for follow-up.
- [x] Define the new event map (`subcatchment:build:*`, websocket updates) and document consumer expectations.
- [x] Normalize backend payloads via `parse_request_payload`; ensure NoDb controller methods accept typed booleans/arrays/numbers.
- [x] Update templates with `data-*` hooks required for delegated listeners; avoid inline JS.
- [x] Add Jest coverage for form submission success/failure, map toggle interactions, and event emissions. Mock fetch + WS behavior as needed.
- [x] Extend pytest suites to validate new payload shapes and RQ orchestration, mirroring `module_refactor_workflow.md`.
- [x] Run required validation commands (`wctl run-npm lint/test`, bundle rebuild, targeted pytest`) and finish with `wctl run-pytest tests --maxfail=1`.
- [x] Update docs (`controllers_js/README.md`, `controllers_js/AGENTS.md`) to describe the new controller contracts and testing guidance.

## Implementation Notes (2025-10-22)
- Controller now bootstraps entirely via helpers: `WCDom.delegate` handles build actions, color-map radios (`data-subcatchment-role="cmap-option"`), and slider inputs (`data-subcatchment-role="scale-range"`); network writes flow through `WCHttp.postJson`, and the singleton exposes a scoped emitter via `WCEvents.useEventMap(["subcatchment:build:*", "subcatchment:map:mode", "subcatchment:legend:updated"])`.
- `controlBase` responsibilities stay intact—`build()` triggers the WebSocket job machinery, but build lifecycle also emits `subcatchment:build:started`/`completed`/`error` so neighbouring controllers subscribe without inspecting DOM internals. Existing `triggerEvent` overrides still fire to keep Channel/WEPP legacy hooks alive.
- Backend route `/rq/api/build_subcatchments_and_abstract_watershed` consumes JSON or form data through `parse_request_payload`, coercing booleans (`clip_hillslopes`, `walk_flowpaths`, `mofe_buffer`, `bieger2015_widths`) and numerics before mutating the `Watershed` singleton. Pytest coverage (`tests/weppcloud/routes/test_rq_api_subcatchments.py`) verifies queue wiring and batch-mode short-circuit behaviour.
- Templates shed inline `onclick` handlers; buttons expose `data-subcatchment-action="build"` and color-map controls reuse shared Pure macros with helper-friendly attributes. Map legends continue to render through `render_legend`, but legend HTML now flows through `setSubLegend`, which tolerates both jQuery and raw elements.
- Added Jest suite `__tests__/subcatchment_delineation.test.js` to lock in build submission, delegated color-map toggles, and error propagation (via the new event bus). Stubs cover `MapController`, the StatusStream wiring, Leaflet glify layers, and ensure these tests run under jsdom without touching the real map stack.

## Open Questions / Follow-ups
- Do existing helpers expose a clean abstraction for Leaflet WebGL layer lifecycle? If not, document the gap and implement minimal wrappers without regressing performance.
- Confirm whether other controllers listen to `BUILD_SUBCATCHMENTS_TASK_COMPLETED` or similar events; ensure the new event bus preserves compatibility (possibly dual-emitting legacy names temporarily).
- Validate that websocket-driven status updates remain functional once DOM bindings move to helper-based listeners.
