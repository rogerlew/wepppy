# deck.gl Cheat Sheet (WEPPcloud)

> Quick onboarding for deck.gl usage in this repo. Keep this dense.
> **See also:** `docs/ui-docs/map-specification-and-behavior.md`, `docs/ui-docs/gl-dashboard.md`.

## Quick orientation
- deck.gl appears in two stacks:
  - **Map GL** (run-scoped map controls): `wepppy/weppcloud/controllers_js/map_gl.js`.
  - **GL dashboard** (standalone page): `wepppy/weppcloud/static/js/gl-dashboard.js` + `static/js/gl-dashboard/`.
- The stacks are independent: Map GL uses `WCHttp` + `url_for_run`; GL dashboard uses direct `fetch`.

## Core deck.gl basics
- A `Deck` instance owns view state + layers. Update via `deck.setProps({ layers, viewState })`.
- Always set stable layer `id`s. Use `updateTriggers` for data-driven styling.
- `viewState` fields: `longitude`, `latitude`, `zoom`, `pitch`, `bearing`, `minZoom`, `maxZoom`.
- Controller options live under `controller` (e.g., `dragRotate`, `touchRotate`, `keyboard`).

## Picking + coordinates
- Preferred: use `info.coordinate` inside `onHover`/`onClick` callbacks.
- For raw DOM pointer events, unproject with the viewport or view manager:

```javascript
function eventToLngLat(event, deckInstance) {
  const canvas = deckInstance.getCanvas ? deckInstance.getCanvas() : deckInstance.canvas;
  if (!canvas) {
    return null;
  }
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const coords = deckInstance.viewManager?.unproject([x, y])
    || deckInstance.getViewports?.()[0]?.unproject([x, y]);
  return coords && coords.length >= 2 ? { lng: coords[0], lat: coords[1] } : null;
}
```

- `info.x`/`info.y` are canvas-relative pixels; `info.srcEvent` is the raw event.

## Input handling
- Prefer `pointerdown`/`pointermove`/`pointerup` over mouse events for Deck canvases.
- For Shift+drag selection, gate on `event.shiftKey` and suppress map drag only while Shift is down.

## Map GL onboarding (controllers_js/map_gl.js)
- Entry: `wepppy/weppcloud/controllers_js/map_gl.js` (`window.MapController`).
- DOM contract: `#mapid` is the map container (same IDs as Leaflet).
- Public API mirrors Leaflet: `map.on/off`, `addLayer/removeLayer`, `setView/flyTo`, `getCenter/getZoom`, `boxZoom`, `suppressDrilldown`.
- Run-scoped endpoints must use `url_for_run()` and `WCHttp`.
- `map._deck` is the Deck instance. For raw pointer events, use `map._deck.viewManager.unproject(...)`.
- Build the bundle: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.
- Tests live in `wepppy/weppcloud/controllers_js/__tests__/`.

## GL dashboard onboarding
- Entry: `wepppy/weppcloud/static/js/gl-dashboard.js` (dynamic ES module imports).
- Map wrapper: `wepppy/weppcloud/static/js/gl-dashboard/map/controller.js` (`createMapController`).
- Basemap wiring: `static/js/gl-dashboard/map/basemap-controller.js`.
- Context: `window.GL_DASHBOARD_CONTEXT` (e.g., `sitePrefix`, `mapCenter`, `mapExtent`, `zoom`).
- State: `static/js/gl-dashboard/state.js` with `getState`, `setValue`, `initState`.
- Tests:
  - Unit tests: `wepppy/weppcloud/static/js/gl-dashboard/__tests__/`.
  - Playwright: `wepppy/weppcloud/static-src/tests/smoke/gl-dashboard-*.spec.js`.

## Common pitfalls
- `deck.unproject` is not a public method on the `Deck` instance; use `viewManager` or `getViewports()`.
- `info.coordinate` only exists inside deck picking callbacks.
- Use the **canvas** bounds for x/y (not the outer map container).
- Map GL and GL dashboard are different stacks; do not mix helpers or state.
