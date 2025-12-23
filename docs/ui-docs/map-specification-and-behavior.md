# Map Specification and Behavior

> Deck.gl-backed map panel for `map_pure_gl.htm`. This document captures the UI contract, event surface, layers, and controller touch points; legacy Leaflet notes remain as parity reference.
> **See also:** `wepppy/weppcloud/controllers_js/README.md`, `docs/ui-docs/controller-contract.md`, `wepppy/weppcloud/templates/controls/map_pure_gl.htm`.

## Scope
- Run-scoped map used in WEPPcloud controls (not the gl_dashboard stub).
- MapController behavior and the UI elements it owns.
- Integration points with other controllers that add overlays or consume map state.

## DOM contract (map_pure_gl.htm)
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
- Tabs and optional panels (Modify, Rangeland Cover) are conditionally rendered based on mods; the Results tab is legacy Leaflet-only.
- Keep IDs stable; other controllers query them directly.

## MapController summary (legacy Leaflet map.js)
Legacy reference only; the active deck.gl controller lives in `wepppy/weppcloud/controllers_js/map_gl.js`.
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

## Map typography
- Map text (labels, hover hints, modal snippets) should render at 14px or larger for legibility.

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
| Gridded Output | GeoTIFF | `/resources/flowpaths_loss.tif` | SubcatchmentDelineation | Legacy Leaflet-only overlay (removed from GL path in Phase 13). |
| Outlet marker | CircleMarker | `/query/outlet/` | Outlet | Added to `markerCustomPane`. |
| Burn Severity Map | ImageOverlay | `/query/baer_wgs_map/` | Baer | Adds legend under `#sbs_legend`. |
| Selection overlays | GeoJSON + Rectangle | `/resources/subcatchments.json` | LanduseModify/RangelandCoverModify | For box and click selection. |
| Boundary overlay | GeoJSON | `context.map.boundary.url` | MapController | Added during bootstrap. |

## Run-scoped endpoints used by the map panel
- Elevation: `/runs/<runid>/<config>/elevationquery/` (POST `{ lat, lng }`).
- Drilldown: `report/sub_summary/<TopazID>/`, `report/chn_summary/<TopazID>/`.
- Subcatchments and channels: `resources/subcatchments.json`, `resources/netful.json`, `resources/channels.json`.
- Hillslope slope/aspect: `query/watershed/subcatchments/`.
- Legends: `resources/legends/<name>/`, `resources/legends/sbs/`.
- SBS image: `query/baer_wgs_map/`.
- Outlet: `query/outlet/`, `report/outlet/`, `rq/api/set_outlet`.
- Channel build: `rq/api/fetch_dem_and_build_channels`, `query/delineation_pass/`, `query/has_dem/`.
- Selection box: `tasks/sub_intersection/`.
- Landuse/Rangeland modify: `tasks/modify_landuse/`, `tasks/modify_rangeland_cover/`.
- Subcatchment overlays: `query/landuse/subcatchments/`, `query/rangeland_cover/subcatchments/`, `query/soils/subcatchments/`, `query/landuse/cover/subcatchments`.

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
  - On SBS upload, calls `map.flyToBounds` to fit the SBS extent; on bootstrap, skips fly when `flags.hasDem` is true.
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
Leaflet files are retired in Phase 13; keep this doc as parity reference for behavior only.

Templates:
- `wepppy/weppcloud/templates/controls/map_pure_gl.htm` (deck.gl map shell, keep DOM IDs/ARIA).

Feature flag + bundles:
- Deck.gl is the default; the `use_deck_gl_map` flag is removed in `runs0_pure.htm`.
- `wepppy/weppcloud/controllers_js/build_controllers_js.py` emits only `static/js/controllers-gl.js`.
  - Include core helpers (`dom.js`, `http.js`, `events.js`, `utils.js`, `control_base.js`, `bootstrap.js`, etc.).
  - Include `*_gl.js` modules and exclude Leaflet-only controllers.

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
Assumptions (historical; Phase 13 flips defaults):
- `map_pure_gl.htm` was opt-in behind a feature flag, query param, or config gate.
- Leaflet map remained default until deck.gl reached parity.
- Phase 13 removes the flag and makes deck.gl the default for `runs0_pure.htm`.

### Phase 0: scaffolding + feature flag
- Deliverables: `map_pure_gl.htm`, `map_gl.js` skeleton, feature flag routing, deck.gl script loading.
- Create `_gl` controller equivalents with stubs and no Leaflet dependencies (ex: `subcatchments_gl.js`, `channel_gl.js`, `outlet_gl.js`, `landuse_modify_gl.js`, `rangeland_cover_modify_gl.js`). These should export the same global names/methods and emit the same events, even if internals are no-ops initially.
- Tests: Jest smoke for `MapController.getInstance()` + `map:ready` emission; Playwright load of map_pure_gl page.

### Phase 0 handoff summary
- Historical: `use_deck_gl_map` gated `controls/map_pure_gl.htm` vs. `controls/map_pure.htm` and `controllers-gl.js` vs. the legacy Leaflet bundle in `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm` (removed in Phase 13).
- Historical: Leaflet-only assets were gated behind the flag (`leaflet.js`, `leaflet-ajax.js`, `leaflet-geotiff.js`, `glify-browser.js`, `leaflet-glify-layer.js`, `flash-and-find-by-id.js`); removed from `runs0_pure.htm` in Phase 13.
- Historical: `build_controllers_js.py` emitted `static/js/controllers-gl.js` plus a legacy Leaflet bundle; Phase 13 drops the legacy bundle.
- GL controllers: `map_gl.js` defines the MapController surface and events, plus stub controllers for subcatchments/channels/outlet/landuse-modify/rangeland-cover-modify.
- Tests: `controllers_js/__tests__/map_gl.test.js` (Jest) and `static-src/tests/smoke/map-gl.spec.js` (Playwright).

### Phase 1: base layers + view state + status
- Scope: basemap tiles (Terrain/Satellite), view state sync, `#mapstatus` updates, map resize handle.
- Tests: Jest for view state updates and `map:center:changed`; Playwright for basemap toggle + resize handle.

### Phase 1 handoff summary
- Basemap tiles: deck `TileLayer` + `BitmapLayer` with Google Terrain (default) and Satellite in `wepppy/weppcloud/controllers_js/map_gl.js`.
- View state: `setView`/`flyTo`/`getCenter`/`getZoom`/`getBounds` implemented with deck `onViewStateChange` feedback and guard to avoid recursion.
- Status + resize: `#mapstatus` updates on view changes; `invalidateSize()` remeasures and calls `deck.setProps`.
- Widgets: `ZoomWidget` enabled via UMD bundle load and wired into `widgets` on the deck instance.
- Layer control: Leaflet-style base/overlay UI rendered inside `.wc-map` (custom control), using the Leaflet layers SVG icon.
- Tests: Playwright `static-src/tests/smoke/map-gl.spec.js` now covers mapstatus text, zoom +/- keys, and base-layer switching; Jest covers layer-control presence.

### Phase 1a: fly-to location + optional zoom
- Scope: parse `#input_centerloc` values (`lon, lat, [zoom]`), `go` button and Enter key handling, `map:center:requested` event, `flyTo` behavior.
- Tests: Jest for parsing + `flyTo` call; Playwright for input entry and map center update.

### Phase 1a handoff summary
- Location parsing: accepts `lon, lat` or `lon, lat, zoom` (comma or space), keeps current zoom when omitted, validates ranges, logs warnings on invalid input.
- Events: `map:center:requested` emitted from Enter key and `Go` button; `map:center:changed` emitted on final view update.
- Fly-to: uses `FlyToInterpolator` when available with a 4000ms transition; falls back to `setView` when interpolator is missing.
- Status: `#mapstatus` updates with new center/zoom after fly-to completes.
- Tests: `controllers_js/__tests__/map_gl.test.js` covers parsing, events, validation, and transition duration.

### Potential issues
- Fly-to transitions currently emit `moveend`/`zoomend` + `map:center:changed` immediately and again when the deck transition ends; no known side effects yet, but overlay refresh hooks may double-fire.

### Phase 2: USGS/SNOTEL/NHD overlays
- Scope: GeoJsonLayer overlays with zoom gating and label updates; `map:layer:*` events.
- Tests: Jest for overlay refresh + label gating; Playwright toggle overlays and verify legend/status.

### Phase 2 handoff summary
- Overlay layers: deck `GeoJsonLayer` for USGS gages, SNOTEL locations, and NHD flowlines with Leaflet-matching styling and draw order (NHD below sensors).
- Overlay colors (approved): USGS `#ff7800`, SNOTEL `#d6336c`, NHD `#7b2cbf`.
- Refresh: `WCHttp.getJson` fetches on `moveend`/`zoomend` with a short debounce during pan/zoom; in-flight requests abort or are ignored if stale.
- Zoom gating + labels: USGS/SNOTEL gated at zoom >= 9; NHD gated at zoom >= 11, with HR label at zoom >= 14; overlay labels update to reflect thresholds.
- Events: `map:layer:refreshed` and `map:layer:error` emitted on successful/failed refreshes.
- UX: USGS/SNOTEL hover shows name; click opens a modal with HTML description (links clickable).
- Tests: Jest covers overlay registration order and zoom gating; Playwright covers overlay toggles, panel collapse, fly-to, and modal open.

### Phase 3: SBS map (image overlay)
- Scope: SBS raster fetch + deck BitmapLayer; link to Baer/Disturbed; legend injection.
- Tests: Playwright load SBS, verify legend and opacity changes.

### Phase 3 handoff summary
- Overlay layer: deck `BitmapLayer` for SBS image with run-scoped `/query/baer_wgs_map/` metadata and `resources/baer.png` fetch (bounds normalized for deck).
- Legend: `#sbs_legend` hydrated from `/resources/legends/sbs/`, with opacity slider wired to `map.sbs_layer.setOpacity`.
- Events: `map:layer:refreshed` / `map:layer:error` emitted on SBS refresh; `map:layer:toggled` on overlay toggle.
- State sync: listens for `disturbed:has_sbs_changed` to add/remove overlay and clear the legend when SBS is removed.
- Tests: Jest validates SBS refresh success/error + legend visibility; Playwright covers toggle + opacity slider updates.
- Empty-run URL for missing SBS smoke coverage: `https://wc.bearhive.duckdns.org/weppcloud/runs/unpaved-neophyte/disturbed9002/`.

### Phase 4: legends framework
- Scope: reuse existing legend targets (`#sub_legend`, `#sbs_legend`) and lock in show/hide behavior.
- Tests: Jest covers SBS legend show/hide + opacity slider; Playwright covers SBS legend toggle, slider, and empty-run resilience.

### Phase 4 handoff summary
- Legend targets: SBS and subcatchment legends stay on `#sbs_legend` / `#sub_legend`, with show/hide controlled by overlay state.
- SBS legend: loads from `/resources/legends/sbs/`, injects the opacity slider, and clears content when SBS is removed or refresh fails.
- Events: `baer:map:opacity` emitted on slider changes; SBS refresh emits `map:layer:refreshed`/`map:layer:error`.
- Tests: Jest covers SBS legend show/hide + opacity slider updates; Playwright covers toggle visibility, slider updates, and empty-run behavior.

### Phase 5: channel layer pass 1 (netful)
- Scope: GL ChannelDelineation loads `resources/netful.json` as a deck GeoJsonLayer (lines only), uses the Order palette, and registers the overlay as "Channels."
- Events: `channel:layers:loaded` on success; `channel:build:error` on failure.
- Tests: Jest `channel_gl.test.js` covers overlay registration and palette mapping; Playwright can add channel toggle coverage after delineation.

### Phase 5 handoff summary
- Overlay: GL ChannelDelineation builds `wc-channels-netful` from `resources/netful.json`, registers it as "Channels", and auto-loads on bootstrap when `data.watershed.hasChannels` is true.
- Styling: Order-based palette (same as Leaflet) with line-only rendering; rebuild hook returns a fresh deck layer on re-enable to avoid WebGL buffer errors.
- Events: `channel:layers:loaded` emitted on successful load; `channel:build:error` emitted on fetch errors.
- Tests: Jest validates overlay registration, palette mapping, and rebuild hook; Playwright smoke stubs netful data and verifies toggle on/off without console errors.

### Phase 6: elevation hover
- Scope: GL hover -> elevation query (`/elevationquery/`), `#mouseelev` updates, cooldown + abort behavior on mouseleave.
- Events: `map:elevation:requested`, `map:elevation:loaded`, `map:elevation:error`.
- Tests: Jest covers hover cooldown and mouseout abort; Playwright hover check (mock response) optional.

### Phase 6 handoff summary
- Behavior: GL map uses deck `onHover` for elevation queries plus `mouseleave` on the map container, posts to `/elevationquery/`, and updates `#mouseelev` with elevation + cursor coords.
- Throttle: cooldown uses 200ms; `mouseleave` hides the elevation after 2s and aborts in-flight requests.
- Events: `map:elevation:requested` emitted before the request; `map:elevation:loaded`/`map:elevation:error` emitted on completion.
- Tests: Jest in `map_gl.test.js` asserts single request per cooldown and abort/hide on mouseout.

### Phase 7: outlet selection
- Scope: deck `onClick` dispatches `{ latlng }` to map click handlers; outlet cursor mode submits `rq/api/set_outlet`, shows temp feedback, and renders the final outlet marker from `query/outlet/`.
- Tests: Jest covers GL outlet selection; Playwright covers cursor click + overlay cleanup.

### Phase 7 handoff summary
- Click wiring: Map GL uses deck `onClick` to emit `{ latlng }` click events so `Outlet.setClickHandler` works like Leaflet.
- Temp feedback: blue circle (fill 0.5, stroke 2) plus "Setting outlet..." dialog anchored via deck layers; cleaned on success or error.
- Outlet marker: GeoJsonLayer with overlay label "Outlet", registered in the overlay control; temp layers removed when the marker renders.
- Tests: Jest `outlet_gl.test.js` covers cursor submit, temp layer creation, and completion cleanup; Playwright keeps a stubbed cursor click flow with temp overlay and outlet marker assertions.
- Test run: https://wc.bearhive.duckdns.org/weppcloud/runs/air-cooled-broadening/disturbed9002/

### Phase 7 final handoff
- Delivered: GL map click dispatch, outlet cursor selection, temp feedback layers, and outlet marker overlay parity with Leaflet.
- Controller parity: `outlet_gl.js` now mirrors the Leaflet controller lifecycle (status stream, job polling events, report load).
- Overlay stability: Outlet layer rebuild hook avoids WebGL errors when toggling the overlay on/off.
- Tests: Jest outlet coverage + Playwright stubbed outlet smoke remain; removed brittle public-run smoke to avoid external state flakiness.

### Phase 7b: channels GL parity (controller + UX)
- Scope: bring `channel_gl.js` to functional parity with `channel_delineation.js` (build action, status/polling, report loading, map hooks) while reconciling Leaflet vs. GL interface differences.
- Notes: this is controller parity only; channel layer pass 2 and labels remain in Phase 8.
- Tests: Jest for build/report flow + polling failure; Playwright build channels -> report load.

### Phase 7b handoff summary
- Controller parity: `channel_gl.js` now wires the build form, status/stacktrace panels, status stream, job id handling, and report loading while keeping the netful overlay.
- Build flow: `rq/api/fetch_dem_and_build_channels` submission sets the job id, uses an idempotent completion guard, and triggers report + netful reload on completion.
- Bootstrap: job id recovery checks `fetch_dem_and_build_channels_rq`, applies `zoomMin`, and loads report + netful when channels already exist.
- Map integration: `onMapChange` binds to map move/zoom + `map:ready`, updates map input fields, and gates the build button by zoom min.
- Tests: Jest `controllers_js/__tests__/channel_gl.test.js` covers build payload, completion idempotence, failure job:error, and map gating; Playwright `static-src/tests/smoke/map-gl.spec.js` adds a build flow with report and layer assertions.

### Phase 7c: outlet GL parity (controller + UX)
- Scope: bring `outlet_gl.js` to functional parity with `outlet.js` (cursor mode, status/polling, report loading, marker rendering) while reconciling Leaflet vs. GL interface differences.
- Notes: this is controller parity for the outlet UI; outlet map feedback layers can stay as Phase 7 delivered.
- Tests: Jest for submit/complete/poll failure; Playwright cursor click -> temporary feedback -> outlet marker + report.

### Phase 7c handoff summary
- Controller parity: `outlet_gl.js` wires DOM hooks, status/stacktrace panels, status stream, job id handling, and controlBase lifecycle events (`job:started`, `job:completed`, `job:error`).
- Cursor flow: cursor toggle uses map click events, posts `rq/api/set_outlet`, and cleans up temporary feedback layers on success or error.
- Display: `query/outlet/` renders the outlet marker overlay and `report/outlet/` hydrates the info panel; emits `outlet:display:refresh` after successful render.
- Tests: Jest `controllers_js/__tests__/outlet_gl.test.js` covers cursor submit, completion idempotence, and report refresh; Playwright smoke asserts temp feedback and final marker/report.

### Phase 8: channel layer pass 2 + labels + drilldown
- Scope: channel pass 2, labels via TextLayer/IconLayer, click -> `chnQuery`.
- Tests: Playwright click channel -> drilldown panel update.

### Phase 8 handoff summary
- Pass 2: `query/delineation_pass/` routes to SUBWTA channels via `resources/channels.json`, with pickable GeoJsonLayer, fill enabled, and palette opacity ~0.6.
- Labels: `Channel Labels` TextLayer renders unique TopazID labels with SDF outline styling (blue text + white stroke), registered in the overlay control and hidden by default.
- Hover labels: when labels are hidden, hovering a channel shows an offset TopazID label; hover labels are suppressed when the labels overlay is visible.
- Legend: channel order legend is injected into `#sub_legend` when pass 2 renders.
- Drilldown: `map_gl.js` now implements `hillQuery` + `chnQuery` to load `report/chn_summary/<topazId>/` into the drilldown panel.
- Tests: Jest covers pass 2 overlay + click drilldown, label styling, hover label behavior, and overlay toggle cleanup; Playwright stubs pass 2 data and confirms labels + drilldown panel update. `wctl run-npm test -- channel_gl.test.js` clean.

### Phase 9: subcatchments + gridded loss
- Scope: GeoJsonLayer subcatchments, color map modes, labels, gridded loss raster.
- Tests: Jest for color mapping; Playwright toggle subcatchment layers + legend range.

### Phase 9 handoff summary
- Subcatchments: GL GeoJsonLayer loads `resources/subcatchments.json`, registers `Subcatchments` overlay, and renders default fill/outline styling.
- Labels: `Subcatchment Labels` TextLayer built from unique TopazID (polylabel if available), SDF outline styling (orange text + white stroke), registered but hidden by default.
- Color maps: `setColorMap` supports slope/aspect, landuse, soils, cover, WEPP loss/runoff metrics (query-engine), phosphorus, ash, and RHEM modes with legend label updates.
- Gridded loss: `Gridded Output` BitmapLayer loads `resources/flowpaths_loss.tif`, updates +/- range from `#wepp_grd_cmap_range_loss`, and refreshes unit labels (kg/m^2).
- Tests: Jest `controllers_js/__tests__/subcatchments_gl.test.js` covers overlay registration, color map mode updates, range slider refresh, and gridded loss raster load. `wctl run-npm test -- subcatchments_gl.test.js` clean.

### Phase 9b: remove Results tab from map tabset
- Scope: remove the `Results` tab from the map control tabset in both `map_pure.htm` and `map_pure_gl.htm` (WEPP/RHEM results live in GL dashboard now).
- Notes: keep the results templates available for the GL dashboard; this is a UI removal only. Verify no JS relies on the missing tab content.
- Tests: smoke map tabset renders without `Results` and no console errors.

### Phase 9c: subcatchments GL parity (controller + UX)
- Scope: bring `subcatchments_gl.js` to functional parity with `subcatchment_delineation.js` (build action, status/polling, report loading, legend updates, preflight gating) while reconciling Leaflet vs. GL differences.
- Notes: assumes Phase 9 delivered the GL subcatchment layers/colormap; this pass focuses on controller wiring and UI parity.
- Tests: Jest for build/report/poll failure; Playwright build subcatchments -> report + legend update.

### Phase 9c handoff summary
- Build: `sub.build()` posts `rq/api/build_subcatchments_and_abstract_watershed`, wires status stream, records job id, and emits `subcatchment:build:started`/`subcatchment:build:error`.
- Completion: `BUILD_SUBCATCHMENTS_TASK_COMPLETED` triggers `sub.show()` + channel refresh; `WATERSHED_ABSTRACTION_TASK_COMPLETED` loads report, disconnects status stream, enables slope/aspect, and updates WEPP phosphorus.
- Report: `report/subcatchments/` HTML is injected into `#info`, status updated, and `Project.set_preferred_units()` invoked.
- Preflight gating: radios for slope/aspect, landuse, rangeland cover, and soils are enabled based on `window.lastPreflightChecklist`, with a `preflight:update` listener attached once.
- Manual validation: Safari (poll-only, no websockets) renders subcatchments and pass 2 channels after build completion.
- Tests: Jest `controllers_js/__tests__/subcatchments_gl.test.js` covers build flow, completion idempotence, and preflight gating. Smoke test stubs build submit in `static-src/tests/smoke/map-gl.spec.js`.

### Phase 10: WEPP find and flash
- Scope: deck picking + highlight, reuse search input workflows.
- Tests: Playwright find Topaz/WEPP ID -> flash + drilldown.

### Phase 10 handoff summary
- Integration: GL map now uses a `WEPP_FIND_AND_FLASH` helper (lazy stub in `map_gl.js` if the Leaflet helper is missing) and wires `findByTopazId`/`findByWeppId` through `map.findById`.
- Flash overlay: temporary GeoJsonLayer with a pulsed white outline/fill is added via `map.addLayer` and removed after the timeout (not registered in the layer control).
- Drilldown: Topaz hits call `subQuery`; channel hits call `chnQuery`, matching Leaflet behavior.
- Manual validation: browser search for Topaz/WEPP IDs flashes geometry and opens drilldown.
- Tests: Jest `controllers_js/__tests__/map_gl.test.js` covers find/flash delegation and flash teardown.

### Phase 11: slope + aspect overlays
- Scope: split the combined slope/aspect mode into two distinct subcatchment colormaps ("Slope" and "Aspect") to match the GL dashboard behavior.
- Data: reuse `query/watershed/subcatchments/` payload; slope uses `slope_scalar` (0-1) with viridis, aspect uses a hue wheel palette keyed to degrees.
- UI: replace `sub_cmap_radio_slp_asp` with separate radios (slope + aspect), update defaults (prefer slope), and keep a compatibility alias so legacy `slp_asp` requests map to `slope`.
- Legend: replace `slope_aspect` legend with separate slope + aspect legends (new templates or dynamic legend rendering).
- Tests: Jest for colormap switching + normalization; Playwright toggles slope/aspect modes and validates legend updates.

### Phase 11 handoff summary
- UI: `map_pure_gl.htm` now has separate `sub_cmap_radio_slope` and `sub_cmap_radio_aspect` radios (GL only; Leaflet template unchanged).
- Data fetch: `query/watershed/subcatchments/` provides `slope_scalar` (0-1) and `aspect` (0-360) per TopazID; both modes reuse this single payload.
- Color mapping: slope uses viridis on `slope_scalar`; aspect uses the gl-dashboard hue wheel mapping (degrees -> hue).
- Compatibility alias: `slp_asp` mode requests map to `slope` in `subcatchments_gl.js` to avoid breaking existing run context defaults.
- Legends: slope and aspect legends are injected inline by `subcatchments_gl.js` (slope = viridis canvas, aspect = hue wheel swatches).
- Stroke behavior: subcatchment stroke color now follows fill color (matches fill via `getLineColor: colorFn`) for consistent choropleth rendering.
- Rendering fix: added `updateTriggers: { getFillColor: [mode], getLineColor: [mode] }` to force deck.gl re-render when mode changes (critical for choropleth updates).
- Tests: Jest `subcatchments_gl.test.js` covers slope/aspect mapping and alias handling; Playwright `map-gl.spec.js` toggles slope/aspect and verifies legend updates.
- Manual validation: browser toggles between slope/aspect on https://wc.bearhive.duckdns.org/weppcloud/runs/air-cooled-broadening/disturbed9002/ show slope viridis and aspect hue-wheel choropleths with matching stroke colors.

Technical notes:
- Deck.gl layer updates: without `updateTriggers`, deck.gl does not detect getFillColor changes when the layer id remains constant. The `updateTriggers` prop is required to signal when accessors need re-evaluation.
- Stroke-follows-fill: changed `getLineColor` from static `lineColor` to `colorFn(feature)` to render subcatchment boundaries in the same color as the fill, improving visual clarity.

### Phase 11b: landuse + soils overlays
- Scope: landuse/soils colormaps and legend updates.
- Tests: Playwright toggle landuse/soils modes and validate legends (`map-gl.spec.js`).

### Phase 11b handoff summary
- Overlays: Dominant Landcover and Dominant Soil choropleths already functional from Phase 9 implementation; confirmed working with updateTriggers from Phase 11.
- Mode mapping: `dom_lc` radio maps to `landuse` mode via `renderLanduse()`; `dom_soil` radio maps to `soils` mode via `renderSoils()`.
- Colors: Landuse renders with NLCD color palette (e.g., yellow `[255, 255, 0]` for cropland, tan `[226, 226, 193]` for grassland); Soils render with hash-based colors per mukey (e.g., `[255, 226, 138]`, `[187, 238, 255]`, `[68, 136, 153]`).
- Stroke-follows-fill: Both landuse and soils overlays benefit from Phase 11 stroke color matching fill color for improved visual consistency.
- updateTriggers: Both overlays include `updateTriggers: { getFillColor: [mode], getLineColor: [mode] }` to force deck.gl re-render when switching between modes.
- Preflight gating: Radios remain disabled until data loads; `updateLayerAvailability()` enables them based on `window.lastPreflightChecklist`.
- Tests: Playwright `map-gl.spec.js` confirms legends toggle for dominant landuse/soils; diagnostic deep-dive spec lives under `static-src/tests/smoke/diagnostics/`.
- Manual validation: browser toggles between Dominant Landcover and Dominant Soil show distinct color palettes with matching stroke colors.

### Phase 12: landuse modify + rangeland cover modify
- Scope: selection mode with box select, outline overlay, modify forms.
- Tests: Playwright selection + submit; E2E run covering modify steps.
- Deck.gl input: `mousedown/mousemove/mouseup` are unreliable for drag in deck.gl; use `pointerdown/pointermove/pointerup` (capture phase) and gate box select on `Shift`.

### Phase 12 handoff summary
- Shared selection utilities live in `wepppy/weppcloud/controllers_js/selection_utils.js` (legacy adapters, payload parsing, Topaz ID helpers, deck unproject, selection box layer).
- GL modify controllers pull helpers from `WCSelectionUtils` and use `pointerdown/pointermove/pointerup` (capture phase) with `Shift` gating; pan/zoom remains intact when Shift is not held.
- Deck coordinate lookup uses `viewManager.unproject` (or `getViewports().unproject`) against the deck canvas bounds; avoids `deck.unproject` which is not public on the `Deck` instance.
- Drilldown is suppressed while selection mode is active in both landuse and rangeland cover modify (`suppressDrilldown`/`releaseDrilldown` tokens).
- Console logging for pointer events remains enabled to debug selection initiation (only active when selection mode is on).
- Tests: Jest coverage in `wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` and `wepppy/weppcloud/controllers_js/__tests__/rangeland_cover_modify_gl.test.js`; Playwright smoke additions live in `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js`.

### Phase 13: WEPP results cleanup + GL default
Goal: remove legacy WEPP results map overlays and finalize the deck.gl-only path.

Checklist:
- [x] Remove Leaflet-only controllers from `wepppy/weppcloud/controllers_js/`: `map.js`, `outlet.js`, `landuse_modify.js`, `rangeland_cover_modify.js`.
- [x] Remove legacy Jest coverage tied to the Leaflet controllers: `wepppy/weppcloud/controllers_js/__tests__/map.test.js`, `outlet.test.js`, `landuse_modify.test.js`, `rangeland_cover_modify.test.js`.
- [x] Update `wepppy/weppcloud/controllers_js/build_controllers_js.py` to emit only `static/js/controllers-gl.js` and drop the legacy bundle output.
- [x] Update `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm` to always load deck.gl, `controllers-gl.js`, and `controls/map_pure_gl.htm`; remove the `use_deck_gl_map` flag and Leaflet assets (`leaflet.js`, `leaflet-ajax.js`, `leaflet-geotiff.js`, `glify`, `flash-and-find-by-id.js`).
- [x] Remove vestigial WEPP results map overlays and toggle hooks from GL controllers (focus on `wepppy/weppcloud/controllers_js/map_gl.js` and `subcatchments_gl.js`).
- [x] Audit templates still referencing the legacy bundle and migrate to `controllers-gl.js` (ex: `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm`, `wepppy/weppcloud/routes/batch_runner/templates/*.htm`, `wepppy/weppcloud/routes/readme_md/templates/readme_editor.htm`, `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm`, `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm`, `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2`).
- [x] Update `docs/ui-docs/map-specification-and-behavior.md` to reflect the deck.gl default and retire Leaflet references.
- [x] Update `docs/ui-docs/control-ui-styling/control-inventory.md` and other docs that still reference the Leaflet bundle or removed controllers.
- [x] Validate bundle and smoke: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, then run `wctl run-npm test -- map_gl outlet_gl landuse_modify_gl rangeland_cover_modify_gl` and the Playwright map smoke (`wctl run-npm smoke -- --project=runs0 map-gl.spec.js`).

### Phase 13 handoff summary
- GL-only default: removed Leaflet controllers/tests, `controllers-gl.js` is the single bundle, and runs/templates/scripts now load the GL bundle by default.
- Results overlays: removed legacy WEPP/RHEM/ash/gridded-loss overlay hooks from `subcatchments_gl.js` and related controllers to complete results cleanup.
- SBS behavior: BAER controller is included in the GL bundle; SBS upload renders the classify summary, adds the overlay, and fly-to-fits the SBS extent; reload honors `flags.hasDem` and skips the fly-to when a DEM already exists.
- Map fly-to-extent: `map_gl.js` `flyToBounds` now uses `WebMercatorViewport.fitBounds` so the view zooms to fit the SBS extent instead of just recentering.
- Docs/tooling: docs sweep updated bundle references to `controllers-gl.js`; deploy/build scripts point to the GL bundle.

### Phase 14: overlay order + SBS gating + outlet marker + channel legend
- Scope:
  - Layer control: hide `Burn Severity Map` when SBS is absent.
  - Outlet marker: swap to `map-marker.png` atlas (IconLayer) with tip anchor and geographic sizing (360m).
  - Channel order legend: show whenever pass 2 channels are visible; remove `Order 0`.
  - Render order: enforce deterministic overlay render ordering without changing layer control order.
  - SBS: default opacity set to 0.3 so the legend slider starts lower.
- Tests:
  - Jest: `map_gl.test.js` overlay ordering + SBS gating; `outlet_gl.test.js` marker data; `channel_gl.test.js` legend visibility + no Order 0.
  - Playwright: `map-gl.spec.js` overlay ordering; pass 2 channel legend visibility; SBS gating on empty run.

### Phase 14 handoff summary
- SBS gating: `map_gl.js` hides the Burn Severity Map overlay entry when `flags.initialHasSbs` is false and updates on `disturbed:has_sbs_changed`; overlay appears unchanged when SBS exists.
- SBS opacity: `SBS_DEFAULT_OPACITY` is now `0.3`, so the slider and initial overlay opacity default to 30%.
- Outlet marker: GL outlet marker uses `map-marker.png` via IconLayer (`iconAtlas` + `iconMapping`), anchored at the tip (99, 320) with `sizeUnits: "meters"` and a 360m size; tests validate atlas mapping and sizing.
- Channel legend: `channel_gl.js` renders channel order legend for pass 2 only, skips Order 0, and clears the legend when Channels are toggled off.
- Overlay order: layer render ordering is enforced without changing control list order; Jest/Playwright cover the ordering expectations (smoke enables overlays before asserting stack order).
- Tests: updated Jest (`map_gl.test.js`, `outlet_gl.test.js`, `channel_gl.test.js`) and Playwright (`map-gl.spec.js`) to cover the Phase 14 behaviors; smoke results may vary by run state.

## Test and verification gates (per phase)
- Unit (Jest): new controller tests under `controllers_js/__tests__`.
- UI (Playwright): extend `static-src/tests/smoke` with map_pure_gl cases.
- Note: hover interactions are flaky in Playwright; prefer Jest for hover-specific checks.
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

## Diagnostic smoke specs (manual only)
- Location: `wepppy/weppcloud/static-src/tests/smoke/diagnostics/`
- Enable with `SMOKE_DIAGNOSTICS=1` and run a single spec file explicitly.
- Prefer `MAP_GL_URL` or `SMOKE_RUN_PATH` to target a known run.

## Developer onboarding: custom map layer control (GL)
Purpose: replace Leaflet `L.control.layers` with a deterministic, deck-compatible UI.

Core files:
- `wepppy/weppcloud/controllers_js/map_gl.js` (control creation + behavior).
- `wepppy/weppcloud/static/css/ui-foundation.css` (styling).

How it works:
- `ensureLayerControl()` builds the control DOM inside `.wc-map` with a toggle button (Leaflet layers SVG) and a panel containing Base Layers and Overlays sections.
- Base layers use radio inputs from `map.baseMaps` and call `map.setBaseLayer(key)` on change.
- Overlays use checkbox inputs from `map.overlayMaps` / `overlayNameRegistry` and call `map.addLayer()` / `map.removeLayer()` on change.
- `map.ctrls.addOverlay()` / `map.ctrls.removeLayer()` refresh the overlay list and keep `map.overlayMaps` in sync.
- `map.addLayer()` / `map.removeLayer()` update deck layers and sync checkbox state.
- Panel behavior: the overlay panel collapses on map pan, zoom, and focus interactions (pointer down or wheel) to avoid obscuring the map while navigating.

Adding a new overlay:
1. Create the deck layer in the relevant controller.
2. Register it with `map.registerOverlay(layer, "Overlay Label")` (or `map.ctrls.addOverlay(layer, name)`).
3. The overlay appears in the control and toggles on/off by calling `map.addLayer` / `map.removeLayer`.

Changing base layers:
- Update `basemapDefs` in `map_gl.js` and the `map.baseMaps` entries (use a stable `key`).
- The radio list is regenerated in `renderBaseLayerControl()`. Selection updates `baseLayerKey` and re-applies layers.

Testing:
- Jest: `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` asserts control render and base radio inputs.
- Playwright: `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` asserts Satellite selection updates the deck base layer id.

## Overlay render order groups (GL)
Render order is independent of the layer control ordering. Use grouped indices to leave space for future layers.

Grouped indices (bottom -> top):
- Group 1 (base rasters): Burn Severity Map -> 10
- Group 2 (hydro lines): NHD Flowlines -> 20
- Group 3 (polygons): Subcatchments -> 30
- Group 4 (polygons): Channels -> 40
- Group 5 (points): USGS Gage Locations -> 50
- Group 6 (points): SNOTEL Locations -> 60
- Group 7 (points): Outlet -> 70
- Group 8 (labels): Subcatchment Labels -> 80
- Group 9 (labels): Channel Labels -> 90

Overlay order reference (bottom -> top):
1. Burn Severity Map
2. NHD Flowlines
3. Subcatchments
4. Channels
5. USGS Gage Locations
6. SNOTEL Locations
7. Outlet
8. Subcatchment Labels
9. Channel Labels

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
