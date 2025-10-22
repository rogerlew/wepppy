# Subcatchment Delineation Controller Plan
> Initial discovery notes before the helper migration. Align implementation with `docs/dev-notes/controller_foundations.md` and `docs/dev-notes/module_refactor_workflow.md`.

## Discovery Log (2025-10-22)
- Legacy controller (`wepppy/weppcloud/controllers_js/subcatchment_delineation.js`) is still jQuery-heavy: direct `$("#...")` bindings, `.on()` namespaced listeners, and manual AJAX flows.
- Job orchestration rides on `controlBase` + `WSClient`, but custom `triggerEvent` overrides gate downstream controllers (`ChannelDelineation`, `Wepp`). Need to translate these into `WCEvents` contracts (`subcatchment:build:*`) while keeping the legacy notifications alive.
- Color-map UI relies on radio groups, range inputs, and explicit `render_legend` calls. Sliders/radios are wired via bespoke helpers (`bindSlider`, `bindRadioGroup`). Expect to replace these with `WCDom` delegation + targeted helpers.
- GeoJSON rendering toggles `L.layerGroup` and a custom WebGL layer with palette lookups. Need to ensure helper adoption does not break Leaflet integrations or label overlays.
- Current payload assembly happens via form serialization and manual boolean coercion (`"on"`). Backend endpoints likely accept legacy form posts; will move to `parse_request_payload` for consistent typing.
- Templates (`wepppy/weppcloud/templates/controls/subcatchment_delineation*.htm`) still surface inline IDs & handlers; must audit for data-attribute gaps prior to swapping in `WCDom`.
- Tests appear thin: no Jest suite targeting this controller; pytest coverage exists under `tests/weppcloud/routes/test_subcatchment_delineation*.py` but will need updates to match payload changes.

## Refactor Checklist
- [ ] Confirm helper coverage (WCDom, WCForms, WCHttp, WCEvents, controlBase). Capture any helper gaps in this note for follow-up.
- [ ] Define the new event map (`subcatchment:build:*`, websocket updates) and document consumer expectations.
- [ ] Normalize backend payloads via `parse_request_payload`; ensure NoDb controller methods accept typed booleans/arrays/numbers.
- [ ] Update templates with `data-*` hooks required for delegated listeners; avoid inline JS.
- [ ] Add Jest coverage for form submission success/failure, map toggle interactions, and event emissions. Mock fetch + WS behavior as needed.
- [ ] Extend pytest suites to validate new payload shapes and RQ orchestration, mirroring `module_refactor_workflow.md`.
- [ ] Run required validation commands (`wctl run-npm lint/test`, bundle rebuild, targeted pytest).
- [ ] Update docs (`controllers_js/README.md`, `controllers_js/AGENTS.md`) to describe the new controller contracts and testing guidance.

## Open Questions / Follow-ups
- Do existing helpers expose a clean abstraction for Leaflet WebGL layer lifecycle? If not, document the gap and implement minimal wrappers without regressing performance.
- Confirm whether other controllers listen to `BUILD_SUBCATCHMENTS_TASK_COMPLETED` or similar events; ensure the new event bus preserves compatibility (possibly dual-emitting legacy names temporarily).
- Validate that websocket-driven status updates remain functional once DOM bindings move to helper-based listeners.
