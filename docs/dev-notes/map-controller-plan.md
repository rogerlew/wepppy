# Map Controller Migration Plan
> Scoping notes for refactoring `map.js` to the helper-based controller architecture. Review with [`controller_foundations.md`](./controller_foundations.md) and the shared [`module_refactor_workflow.md`](./module_refactor_workflow.md).

## Current State (Discovery)
- **Controller surface**: Singleton wraps a Leaflet map instance (`L.map("mapid")`) and augments it with custom methods (`goToEnteredLocation`, `findById`, `hillQuery`, etc.). Heavy reliance on jQuery for DOM access (`$("#mouseelev")`, `$("#input_centerloc")`), event binding (`.on("click")`, `.on("keydown")`), DOM mutation (`.text()`, `.html()`, `.fadeOut()`), and network calls (`$.ajax`, `$.get`).
- **DOM contract**: Pure template exposes IDs like `input_centerloc`, `btn_setloc`, `btn_find_topaz_id`, `btn_find_wepp_id`, `mapstatus`, `mouseelev`, `drilldown`, `sub_legend`, `sbs_legend`. Tabset markup sits under `#setloc_form [data-tabset]` but JS still bootstraps behaviour manually. Buttons do not expose `data-*` attributes for helper delegation yet.
- **Leaflet dependencies**:
  - Creates custom panes (`subcatchmentsGlPane`, `channelGlPane`, `markerCustomPane`) and adds Google tile layers (`Terrain`, `Satellite`).
  - Uses `L.geoJson.ajax` (leaflet-ajax plugin) for USGS gage and SNOTEL overlays, then calls `.refresh([url])` with BBOX queries. Selection/highlight flows depend on globals `SubcatchmentDelineation`, `ChannelDelineation`, and `window.WEPP_FIND_AND_FLASH`.
  - `hillQuery` fetches HTML summaries and injects into `#drilldown`, plus toggles the custom tabset.
- **Backend interactions**:
  - Elevation probe: POSTs JSON `{ lat, lng }` to `/runs/<run>/<cfg>/elevationquery/` using `$.ajax`.
  - Drilldown: GETs `report/chn_summary/<id>/` or `report/sub_summary/<id>/` via `$.get`.
  - Overlay refresh: GETs `/resources/usgs/gage_locations/?bbox=…` and `/resources/snotel/snotel_locations/?bbox=…`.
  - Map change telemetry surfaces through `MapController.onMapChange()` (updates `#mapstatus`) but relies on jQuery width lookup.
- **Event model**: No `WCEvents` emitter. Map change, elevation results, and layer toggles are silent side-effects (DOM writes, console logs).
- **Throttle/Timers**: Mousemove elevation sampling gates requests by `isFetchingElevation` and a `setTimeout` cooldown inside the AJAX `complete` handler.
- **Testing**: No Jest coverage exists for the controller; backend tests only cover RQ channel payload parsing.

## Migration Goals
- **Helper adoption**:
  - Replace jQuery selectors/events with `WCDom.qs`, `WCDom.delegate`, `WCDom.setText`, `WCDom.show/hide`, and typed helpers for focus management.
  - Convert inline button IDs to `data-map-action` hooks (keep IDs for legacy bootstrap scripts) so delegation works within `#setloc_form`.
  - Use `WCHttp.postJson`/`getJson` (and `request` for HTML) in place of `$.ajax`/`$.get`. Consolidate error handling and throttling with native Promises.
- **Events**:
  - Introduce `MapController.events = WCEvents.useEventMap([...])` with topics such as `map:center:changed`, `map:elevation:requested`, `map:elevation:loaded`, `map:elevation:error`, `map:layer:toggled`, `map:drilldown:loaded`, and bridge to other controls.
  - Emit `map:center:changed` on `moveend`/`zoomend` with payload `{ center, zoom, bounds }`. Elevation fetch emits requested/loaded/error states.
- **Tabset + inspector**:
  - Keep existing tabset helper but ensure it uses DOM-only helpers; expose ability to activate tabs programmatically for `hillQuery`.
  - Document tab change events (`wc-tabset:change`) and ensure keyboard support remains intact.
- **Overlays**:
  - Replace `L.geoJson.ajax` usage with fetch-backed loaders that call `WCHttp.getJson`, then `layer.clearLayers(); layer.addData(data);`. Provide a thin `createRemoteGeoJsonLayer(options)` helper returning `{ layer, refresh(url) }`.
  - Maintain marker styling/popups, and queue refreshes on `moveend`/`zoomend` only when overlay is visible and zoom ≥ 9.
- **UI feedback**:
  - Swap jQuery `fadeOut` for helper-managed timers (e.g., `setTimeout` + `WCDom.hide`). Preserve existing cooldown semantics.
  - Ensure map status + elevation strings use `WCDom.setText`. Consider adding `aria-live` messaging for readers already present in template.

## Open Questions / Risks
- **Leaflet plugin parity**: Need to verify replacement refresh logic matches `L.geoJson.ajax` behaviour (especially concurrent requests and feature deduplication). May need lightweight cache or abort handling; document fallback if plugin removal introduces regressions.
- **WEPP_FIND_AND_FLASH coupling**: Ensure the modernized controller still integrates with the global search helper. Evaluate whether `findAndFlashById` requires jQuery wrappers (appears to accept `map` + controllers directly).
- **Hill query**: Response is HTML; confirm `WCHttp.request` respects existing CSRF requirements (GET only) and update error handling to surface messages in inspector instead of silent console logs.
- **Elevation throttle**: Evaluate whether `mousemove` + Promise-based fetch leads to overlapping requests when network is slow. Need to reinstate cooldown so we never hold multiple inflight probes; may require explicit abort controller or queue.
- **Template affordances**: Some legacy code (e.g., unit tests or other controllers) might read button IDs directly. Keep IDs but document new data hooks to avoid breaking tests.

## Test Strategy
- **Jest**:
  - Add `controllers_js/__tests__/map.test.js` covering tabset activation, delegated actions (`data-map-action`), event emissions for map change/elevation, layer toggles (with stubbed Leaflet layers), and error handling on failed requests.
  - Mock `WCHttp` to assert JSON/HTML requests and throttle logic; simulate `mousemove` events to ensure cooldown.
- **Pytest**:
  - Extend `tests/weppcloud/routes/test_rq_api_channel.py` if payload shape or map events change (e.g., additional fields). Ensure `parse_request_payload` continues to accept JSON + form posts, and document any new map bounds text behaviour.
  - Add/extend tests for elevation endpoint if backend signature changes (likely stays the same—only front-end moves to fetch).
- **Manual**:
  - Verify in dev stack: map pan/zoom updates status, center Go button works with coordinates and IDs, drilldown content loads, elevation readout updates + hides, overlay checkboxes still populate features.

## Documentation + Follow-ups
- Update `controllers_js/README.md` with the new Map controller contract (DOM hooks, event surface, transport expectations).
- Extend `controllers_js/AGENTS.md` to describe map events and helper patterns (delegation namespace, overlay loader helper).
- Capture helper gaps (e.g., reusable remote GeoJSON loader, throttle utility) for backlog.
- After migration, audit downstream modules (Unitizer, Landuse Modify) to subscribe to map events instead of reading DOM state directly.

## Implementation Snapshot (2025 helper migration)
- **DOM**: `map.js` now binds toolbar buttons via `data-map-action="go|find-topaz|find-wepp"`, wraps legends/drilldown nodes in lightweight adapters, and drives status/elevation text through `WCDom.setText`/`show`/`hide`. The tabset is managed by a vanilla helper that dispatches `wc-tabset:change`.
- **Events**: `MapController.events = WCEvents.useEventMap([...])` publishes `map:ready`, `map:center:requested`, `map:center:changed`, `map:search:requested`, `map:elevation:*`, `map:drilldown:*`, and `map:layer:*` signals so neighbouring controllers react without scraping DOM.
- **Transport**: Elevation probes call `WCHttp.postJson("/runs/<run>/<cfg>/elevationquery/")`; drilldown summaries fetch HTML via `WCHttp.request`; remote overlays (USGS, SNOTEL, ad-hoc GeoJSON) refresh through a fetch-backed loader that clears/adds features and emits `map:layer:refreshed`/`map:layer:error`.
- **Leaflet integration**: `L.geoJSON` layers now gain a helper-driven `refresh` method (with AbortController support) and overlay toggles relay through the emitter. Gage/SNOTEL refreshes respect zoom thresholds and overlay visibility.
- **Testing**: `controllers_js/__tests__/map.test.js` (jsdom) validates tabset activation, delegated button actions, search flows, elevation success/error, overlay refresh, and event emission with mocked Leaflet primitives and helper stubs.
