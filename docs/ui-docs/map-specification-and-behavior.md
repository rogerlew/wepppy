# Map Specification and Behavior

> Leaflet-backed map panel for `map_pure.htm`. This document captures the UI contract, event surface, layers, and controller touch points to preserve during the deck.gl swap.
> **See also:** `wepppy/weppcloud/controllers_js/README.md`, `docs/ui-docs/controller-contract.md`, `wepppy/weppcloud/templates/controls/map_pure.htm`.

## Scope
- Run-scoped map used in WEPPcloud controls (not the gl_dashboard stub).
- MapController behavior and the UI elements it owns.
- Integration points with other controllers that add overlays or consume map state.

## DOM contract (map_pure.htm)
| Selector or attribute | Owner | Purpose |
| --- | --- | --- |
| `#setloc_form` | MapController | Delegated click handling for `data-map-action`. |
| `#input_centerloc` | MapController | Center input for lon/lat/zoom or ID lookup. |
| `[data-map-action="go|find-topaz|find-wepp"]` | MapController | Go/Find actions. |
| `#mapid` | MapController | Map container (`L.map`). |
| `.wc-map [data-map-resize-handle]` | Map resize script | Resize handle, calls `map.invalidateSize()`. |
| `#mapstatus` | MapController | Center/zoom/status line. |
| `#mouseelev` | MapController | Cursor elevation output (aria-live). |
| `#drilldown` | MapController | Drilldown HTML injection target. |
| `#sub_legend` | SubcatchmentDelineation | Subcatchment legend HTML target. |
| `#sbs_legend` | Baer/Disturbed | Burn severity legend HTML target. |
| `#setloc_form [data-tabset]` | MapController | Tabset root for `Layers/Drilldown/Modify/Results`. |
| `input[data-subcatchment-role="cmap-option"]` | SubcatchmentDelineation | Color map radio controls. |
| `input[data-subcatchment-role="scale-range"]` | SubcatchmentDelineation | Scale sliders (WEPP/RHEM results). |
| `canvas#landuse_sub_cmap_canvas_cover` and peers | SubcatchmentDelineation | Color scale render targets via `render_legend`. |

Notes:
- Tabs and optional panels (Modify, Rangeland Cover, Results) are conditionally rendered based on mods.
- Keep IDs stable; other controllers query them directly.

## MapController summary (controllers_js/map.js)
- Singleton: `window.MapController` and `window.WeppMap` expose `getInstance()`.
- Uses `L.map("mapid")`, disables scroll wheel zoom, and creates panes:
  - `subcatchmentsGlPane` z-index 600
  - `channelGlPane` z-index 650
  - `markerCustomPane` z-index 700
- Base maps: Google Terrain and Google Satellite tiles (Terrain is default).
- Overlays: USGS gages, SNOTEL, NHD flowlines; backed by remote GeoJSON.
- `map.ctrls = L.control.layers(baseMaps, overlayMaps)` added to map.
- Theme: toggles `wc-map--invert-base` on map container when `data-theme` or `wc-theme:change` indicates dark mode.
- Exposes adapters on the map instance for legacy DOM access:
  - `map.drilldown`, `map.sub_legend`, `map.sbs_legend`, `map.mouseelev`.
- Exposes helper methods:
  - `goToEnteredLocation`, `findByTopazId`, `findByWeppId`
  - `subQuery`, `chnQuery`, `hillQuery`
  - `addGeoJsonOverlay`, `registerOverlay`, `unregisterOverlay`
  - `suppressDrilldown`, `releaseDrilldown`, `isDrilldownSuppressed`
  - `loadUSGSGageLocations`, `loadSnotelLocations`, `loadNhdFlowlines`
  - `onMapChange`

### Bootstrap contract
`map.bootstrap(context)` reads from `context.map` or `context.controllers.map`:
- `center`: `[lat, lng]`
- `zoom`: number
- `containerSelector`: default `.wc-map` (used for ResizeObserver)
- `boundary`: `{ url, layerName, style }` (added via `addGeoJsonOverlay`)
- Emits `map:ready` once after setting view.
- Falls back to `[44.0, -116.0]` and zoom 6 if center is missing.

## Event surface (MapController.events)
Emitted via `WCEvents.useEventMap`:
- `map:ready` (viewport payload)
- `map:center:requested`
- `map:center:changed`
- `map:search:requested`
- `map:elevation:requested`
- `map:elevation:loaded`
- `map:elevation:error`
- `map:drilldown:requested`
- `map:drilldown:loaded`
- `map:drilldown:error`
- `map:layer:toggled`
- `map:layer:refreshed`
- `map:layer:error`

## Data sources and layers
| Layer | Type | Source | Owner | Notes |
| --- | --- | --- | --- | --- |
| Google Terrain | Tile | `https://{s}.google.com/vt/lyrs=p...` | MapController | Default base layer. |
| Google Satellite | Tile | `https://{s}.google.com/vt/lyrs=s...` | MapController | Alternate base. |
| USGS gages | GeoJSON | `/resources/usgs/gage_locations/?bbox=` | MapController | Min zoom 9; label shows zoom requirement. |
| SNOTEL | GeoJSON | `/resources/snotel/snotel_locations/?bbox=` | MapController | Min zoom 9; label shows zoom requirement. |
| NHD flowlines | GeoJSON | `https://hydro.nationalmap.gov/...` | MapController | Min zoom 11; HR at zoom 14. |
| Subcatchments | glify | `/resources/subcatchments.json` | SubcatchmentDelineation | Click -> `subQuery(TopazID)`. |
| Subcatchment labels | LayerGroup | From subcatchments | SubcatchmentDelineation | Div icon markers. |
| Channels (pass 1) | glify | `/resources/netful.json` | ChannelDelineation | No click handler. |
| Channels (pass 2) | glify | `/resources/channels.json` | ChannelDelineation | Click -> `chnQuery(TopazID)`. |
| Channel labels | LayerGroup | From channels | ChannelDelineation | Div icon markers. |
| Gridded Output | GeoTIFF | `/resources/flowpaths_loss.tif` | SubcatchmentDelineation | Uses `leaflet-geotiff`. |
| Outlet marker | CircleMarker | `/query/outlet/` | Outlet | Added to `markerCustomPane`. |
| Burn Severity Map | ImageOverlay | `/query/baer_wgs_map/` | Baer | Adds legend under `#sbs_legend`. |
| Selection overlays | GeoJSON + Rectangle | `/resources/subcatchments.json` | LanduseModify/RangelandCoverModify | For box and click selection. |
| Boundary overlay | GeoJSON | `context.map.boundary.url` | MapController | Added during bootstrap. |

## Run-scoped endpoints used by the map panel
- Elevation: `/runs/<runid>/<config>/elevationquery/` (POST `{ lat, lng }`).
- Drilldown: `report/sub_summary/<TopazID>/`, `report/chn_summary/<TopazID>/`.
- Subcatchments and channels: `resources/subcatchments.json`, `resources/netful.json`, `resources/channels.json`.
- Gridded loss: `resources/flowpaths_loss.tif`.
- Legends: `resources/legends/<name>/`, `resources/legends/sbs/`.
- SBS image: `query/baer_wgs_map/`.
- Outlet: `query/outlet/`, `report/outlet/`, `rq/api/set_outlet`.
- Channel build: `rq/api/fetch_dem_and_build_channels`, `query/delineation_pass/`, `query/has_dem/`.
- Selection box: `tasks/sub_intersection/`.
- Landuse/Rangeland modify: `tasks/modify_landuse/`, `tasks/modify_rangeland_cover/`.
- Subcatchment results: `query/*/subcatchments/`, `query/landuse/cover/subcatchments`, query-engine endpoints (for loss metrics).

External services:
- NHD ArcGIS REST (`hydro.nationalmap.gov`) for flowlines.
- Google tile servers for base maps.

## Touch points with other controllers
- `SubcatchmentDelineation`
  - Loads subcatchment GeoJSON, builds glify layer, registers overlays.
  - Updates `#sub_legend` via `MapController.sub_legend`.
  - Uses `data-subcatchment-role` radios and scale sliders from the map tabs.
  - Uses `MapController.subQuery` for click drilldown.
- `ChannelDelineation`
  - On `map.on("move|zoom")` updates hidden extent inputs and enables build button.
  - Adds channel glify layers and labels to `channelGlPane`.
  - Uses `MapController.chnQuery` for click drilldown.
- `Outlet`
  - Binds map `click` to `set_outlet` when cursor mode is on.
  - Adds outlet marker overlay and temporary feedback marker.
  - Updates cursor style by selecting `.leaflet-container`.
- `LanduseModify`
  - Enables selection mode over subcatchments; adds `L.geoJSON` overlay.
  - Disables `map.boxZoom`, binds `mousedown/mousemove/mouseup`.
  - Calls `map.suppressDrilldown()` and releases on exit.
- `RangelandCoverModify`
  - Similar selection overlay and box select; does not suppress drilldown.
- `Baer`
  - Adds/removes `L.imageOverlay` for burn severity map.
  - Injects legend into `#sbs_legend` and adds opacity slider.
  - Uses `map.flyToBounds` when DEM is missing.
- `Disturbed`
  - Delegates SBS removal to Baer and clears map overlay + legend.
- `WEPP_FIND_AND_FLASH` helper
  - Used by `findByTopazId`/`findByWeppId` to flash subcatchments/channels.
  - Calls `subQuery`/`chnQuery` based on hit type.

## Map API surface expected by other controllers
Maintain or replace with compatible shims:
- Map instance: `on`, `off`, `addLayer`, `removeLayer`, `hasLayer`, `getCenter`, `getZoom`, `getBounds`, `distance`, `setView`, `flyTo`, `flyToBounds`, `invalidateSize`.
- Controls: `map.ctrls.addOverlay`, `map.ctrls.removeLayer` (used directly when `registerOverlay` is absent).
- Zoom handlers: `map.boxZoom.disable()` and `map.boxZoom.enable()`.
- Custom panes: `createPane`, `getPane` (for z-index ordering).
- MapController helpers: `registerOverlay`, `unregisterOverlay`, `subQuery`, `chnQuery`, `suppressDrilldown`, `releaseDrilldown`, `isDrilldownSuppressed`.
- Adapters: `map.drilldown`, `map.sub_legend`, `map.sbs_legend`, `map.mouseelev`, `map.centerInput`.
- Event emitter: `MapController.getInstance().events`.

## Deck.gl swap: non-negotiables
- Preserve DOM IDs/data attributes and the tabset behavior.
- Preserve `MapController` singleton surface and event names.
- Maintain overlay control UI and overlay naming behavior (including zoom-gated labels).
- Keep map resize handle behavior (`invalidateSize` or equivalent).
- Preserve run-scoped endpoint usage and external data sources.
- Provide a compatible map API for dependent controllers or refactor them in lockstep.

## gl-dashboard patterns worth reusing
References:
- `wepppy/weppcloud/static/js/gl-dashboard.js` (orchestrator + dynamic imports)
- `wepppy/weppcloud/static/js/gl-dashboard/map/controller.js` (Deck wrapper)
- `wepppy/weppcloud/static/js/gl-dashboard/map/basemap-controller.js` (TileLayer + BitmapLayer)
- `wepppy/weppcloud/static/js/gl-dashboard/map/raster-utils.js` (GeoTIFF + SBS canvas pipeline)
- `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` (color/legend helpers)

Reusable patterns (adapt to MapController/WCHttp):
- Thin Deck controller wrapper: `createMapController({ target, initialViewState, onViewStateChange, layers })`.
- Basemap controller with `TileLayer` + `BitmapLayer` and `createImageBitmap` for tile render.
- Raster utils to render GeoTIFF and SBS imagery to canvas (useful for gridded loss and SBS map).
- Layer utils + color scale helpers for legend generation and normalized colormaps.
- Central state object with explicit setters; avoid ad-hoc globals.

Non-reusable as-is:
- gl-dashboard uses direct `fetch` and no `WCHttp`/`url_for_run`; map_pure_gl must keep run-scoped helpers.
- gl-dashboard is a standalone page; `map_pure_gl` must preserve the existing DOM contract and event surface.

## Proposed file structure and code organization
Keep existing Leaflet files as reference and fallback (no removals).

Templates:
- `wepppy/weppcloud/templates/controls/map_pure_gl.htm` (deck.gl map shell, keep DOM IDs/ARIA).

Feature flag + bundles:
- Use a Jinja flag (ex: `use_deck_gl_map`) to select `map_pure.htm` + `controllers.js` or `map_pure_gl.htm` + `controllers-gl.js`.
- Extend `wepppy/weppcloud/controllers_js/build_controllers_js.py` to emit `static/js/controllers-gl.js`.
  - Include core helpers (`dom.js`, `http.js`, `events.js`, `utils.js`, `control_base.js`, `bootstrap.js`, etc.).
  - Include `*_gl.js` modules and exclude Leaflet `map.js` when GL mode is enabled.
  - Keep the legacy bundle intact for safe fallback and regression comparisons.

Controllers (controllers_js):
- `wepppy/weppcloud/controllers_js/map_gl.js` (Deck-based MapController; exports `window.MapController` when GL template is active).
- `wepppy/weppcloud/controllers_js/map_gl_layers.js` (layer registry, overlay control UI, shared layer helpers).
- `wepppy/weppcloud/controllers_js/subcatchments_gl.js` (Deck GeoJsonLayer, colormaps, legends).
- `wepppy/weppcloud/controllers_js/channel_gl.js` (channels pass 1/2, labels, drilldown clicks).
- `wepppy/weppcloud/controllers_js/outlet_gl.js` (outlet marker + click handling).
- `wepppy/weppcloud/controllers_js/landuse_modify_gl.js` (selection + box select using deck picking).
- `wepppy/weppcloud/controllers_js/rangeland_cover_modify_gl.js` (selection + cover form).
- `wepppy/weppcloud/controllers_js/find_flash_gl.js` (WEPP_FIND_AND_FLASH equivalent or adapter).

Shared deck helpers (static/js or controllers_js modules):
- `wepppy/weppcloud/static/js/map_gl/` (optional ES module helpers to mirror gl-dashboard layout).
  - `map/controller.js`, `map/basemap-controller.js`, `map/raster-utils.js`, `map/layers.js`.

Testing:
- `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` and per-controller tests.
- `wepppy/weppcloud/static-src/tests/smoke/*` Playwright checks (new cases for map_pure_gl).

## Multiphase implementation plan (low-risk increments)
Assumptions:
- `map_pure_gl.htm` is opt-in behind a feature flag, query param, or config gate.
- Leaflet map remains default until deck.gl reaches parity.

Phase 0: scaffolding + feature flag
- Deliverables: `map_pure_gl.htm`, `map_gl.js` skeleton, feature flag routing, deck.gl script loading.
- Create `_gl` controller equivalents with stubs and no Leaflet dependencies (ex: `subcatchments_gl.js`, `channel_gl.js`, `outlet_gl.js`, `landuse_modify_gl.js`, `rangeland_cover_modify_gl.js`). These should export the same global names/methods and emit the same events, even if internals are no-ops initially.
- Tests: Jest smoke for `MapController.getInstance()` + `map:ready` emission; Playwright load of map_pure_gl page.

### Phase 0 handoff summary
- Feature flag: `use_deck_gl_map` gates `controls/map_pure_gl.htm` vs. `controls/map_pure.htm`, plus `controllers-gl.js` vs. `controllers.js` in `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`.
- Leaflet-only assets are gated behind the flag (`leaflet.js`, `leaflet-ajax.js`, `leaflet-geotiff.js`, `glify-browser.js`, `leaflet-glify-layer.js`, and `flash-and-find-by-id.js`).
- GL bundle: `build_controllers_js.py` emits `static/js/controllers-gl.js` from helpers + `*_gl.js` stubs and keeps `controllers.js` Leaflet-only.
- GL controllers: `map_gl.js` defines the MapController surface and events, plus stub controllers for subcatchments/channels/outlet/landuse-modify/rangeland-cover-modify.
- Tests: `controllers_js/__tests__/map_gl.test.js` (Jest) and `static-src/tests/smoke/map-gl.spec.js` (Playwright).

Phase 1: base layers + view state + status
- Scope: basemap tiles (Terrain/Satellite), view state sync, `#mapstatus` updates, map resize handle.
- Tests: Jest for view state updates and `map:center:changed`; Playwright for basemap toggle + resize handle.

Phase 1a: fly-to location + optional zoom
- Scope: parse `#input_centerloc` values (`lon, lat, [zoom]`), `go` button and Enter key handling, `map:center:requested` event, `flyTo` behavior.
- Tests: Jest for parsing + `flyTo` call; Playwright for input entry and map center update.

Phase 2: USGS/SNOTEL/NHD overlays
- Scope: GeoJsonLayer overlays with zoom gating and label updates; `map:layer:*` events.
- Tests: Jest for overlay refresh + label gating; Playwright toggle overlays and verify legend/status.

Phase 3: SBS map (image overlay)
- Scope: SBS raster fetch + deck BitmapLayer; link to Baer/Disturbed; legend injection.
- Tests: Playwright load SBS, verify legend and opacity changes.

Phase 4: legends framework
- Scope: deck legend panel or reuse existing legend targets (`#sub_legend`, `#sbs_legend`).
- Tests: Jest for legend updates; Playwright for legend visibility and content.

Phase 5: channel layer pass 1 (netful)
- Scope: GeoJsonLayer for channels pass 1; overlay control entry.
- Tests: Playwright show channels after delineation; verify overlay toggles.

Phase 6: elevation hover
- Scope: mouse move -> elevation query; `#mouseelev` updates; cooldown/abort behavior.
- Tests: Jest for debounce + error handling; Playwright hover check (mock response).

Phase 7: outlet selection
- Scope: map click for outlet, marker rendering, cursor mode toggle.
- Tests: Playwright set outlet via cursor; E2E run flow through outlet step.

Phase 8: channel layer pass 2 + labels + drilldown
- Scope: channel pass 2, labels via TextLayer/IconLayer, click -> `chnQuery`.
- Tests: Playwright click channel -> drilldown panel update.

Phase 9: subcatchments + gridded loss
- Scope: GeoJsonLayer subcatchments, color map modes, labels, gridded loss raster.
- Tests: Jest for color mapping; Playwright toggle subcatchment layers + legend range.

Phase 10: WEPP find and flash
- Scope: deck picking + highlight, reuse search input workflows.
- Tests: Playwright find Topaz/WEPP ID -> flash + drilldown.

Phase 11: landuse + soils overlays
- Scope: landuse/soils colormaps and legend updates.
- Tests: Playwright toggle landuse/soils modes and validate legends.

Phase 12: landuse modify + rangeland cover modify
- Scope: selection mode with box select, outline overlay, modify forms.
- Tests: Playwright selection + submit; E2E run covering modify steps.

Phase 13: WEPP results visualization
- Scope: results modes (runoff, loss, phosphorus, ash) + scale controls.
- Tests: Playwright switch results modes; E2E run through WEPP build + map visuals.

## Test and verification gates (per phase)
- Unit (Jest): new controller tests under `controllers_js/__tests__`.
- UI (Playwright): extend `static-src/tests/smoke` with map_pure_gl cases.
- E2E run: create run via `/tests/api/create-run`, step through outlet -> channel -> subcatchments -> landuse -> soils -> wepp.
- Keep old Leaflet path running in CI as regression baseline until parity is proven.

## Testing quickstart (Phase 0)
Run the GL controller Jest smoke:
```bash
wctl run-npm test -- map_gl.test.js
```

Run the Playwright GL smoke with the configured test project:
```bash
MAP_GL_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/rlew-appreciated-tremolite/disturbed9002/" \
  wctl run-npm smoke -- --project=runs0 map-gl.spec.js
```

## Ops note: restart weppcloud on bearhive
```bash
wctl restart weppcloud
```
TLS termination runs through pfSense and HAProxy in front of Caddy. Wait ~5 seconds after restart before hitting `https://wc.bearhive.duckdns.org/` to avoid transient HAProxy 502s.

## Additional concerns and risk reducers
- Compatibility: provide a `MapController` adapter that preserves event names and method signatures; avoid touching legacy controllers until deck equivalents exist.
- Adapter responsibilities: implement the "Map API surface expected by other controllers" in this doc (map methods, `ctrls.addOverlay/removeLayer`, `map.drilldown`/`sub_legend`/`sbs_legend`/`mouseelev` adapters) and keep `MapController.events` emission identical so existing subscriptions do not break. Keep the `window.WeppMap` alias in GL mode.
- Legacy controller strategy: when deck.gl is active, swap to `_gl` controller equivalents (even if stubs). Avoid partial refactors that leave a mixed Leaflet/deck state. Stubs should be intentionally safe: emit events, guard UI, and log a clear warning for unimplemented behaviors so tests can proceed without Leaflet.
- Overlay control UI: Leaflet control must be replaced with a deterministic, tested UI (consider reusing gl-dashboard layer list patterns).
- Selection tools: implement a deck-based box select layer; do not rely on Leaflet-specific `boxZoom` or `.leaflet-container` class.
- Performance: large GeoJSON (subcatchments/channels) needs batching or simplified geometry; validate on large runs early.
- WebGL errors: add a visible error banner if WebGL context creation fails.
- Rollout: keep feature flag off by default; add a URL toggle for testing and Playwright.
