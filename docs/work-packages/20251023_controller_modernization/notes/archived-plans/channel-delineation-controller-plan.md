# Channel Delineation Controller Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Scope and modernization tracker for the channel delineation control stack.

## Current State (2025-02)
- `wepppy/weppcloud/controllers_js/channel_delineation.js` still relies on jQuery for DOM queries, AJAX calls, and event binding; no helper usage.
- Template `templates/controls/channel_delineation_pure.htm` wires handlers inline (`onclick`, global toggles) and exposes minimal `data-*` hooks.
- Route `routes/rq/api/api.py::fetch_dem_and_build_channels` consumes `request.form` via `_parse_map_change`; payload coercion is string-based only.
- No Jest coverage exists for channel delineation behaviours, and pytest only exercises neighbouring blueprints (no direct coverage of fetch/build flow).
- WebSocket integration depends on hand-written trigger overrides rather than `controlBase` lifecycle events or a scoped `WCEvents` emitter.

## Modernization Targets
- [ ] Refactor the controller to use `WCDom`, `WCForms`, `WCHttp`, and `WCEvents`, emitting `channel:build:*` lifecycle signals.
- [ ] Replace template inline handlers with delegated `data-channel-*` hooks and document the contract.
- [ ] Update `fetch_dem_and_build_channels` route (and supporting jobs) to ingest payloads via `parse_request_payload`, normalising floats/ints/booleans.
- [ ] Backfill Jest tests covering form submission, extent toggles, WebGL layer loading hooks, and error propagation.
- [ ] Add pytest coverage for the RQ fetch/build endpoint, including batch-mode short-circuit behaviour and error handling.
- [ ] Align documentation (`controllers_js/README.md`, `controllers_js/AGENTS.md`) with the new primitives and payload schema.

## Risks & Open Questions
- Map controller integration (`MapController.onMapChange`) must continue to call `ChannelDelineation.onMapChange()` without jQuery adapters.
- Whitebox-specific options (`wbt_fill_or_breach`, `wbt_blc_dist`) require careful type coercion to avoid regressions in batch mode.
- GeoJSON fetches (`resources/netful.json`, `resources/channels.json`) must remain Leaflet-compatible after switching to `WCHttp`.

## Tracking References
- Vision & contracts: `docs/dev-notes/controller_foundations.md`
- Workflow checklist: `docs/dev-notes/module_refactor_workflow.md`
- Helper specs: `docs/dev-notes/controllers_js_jquery_retro.md`
