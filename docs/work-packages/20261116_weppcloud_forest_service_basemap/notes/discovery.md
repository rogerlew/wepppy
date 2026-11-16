# Discovery — WEPPpy target

**Updated**: 2026-11-16 18:00 UTC. Read-only source inspection; no browser/runtime validation.

## Target correction

The user specified WEPPpy after the initial CULVERT interpretation and explicitly retained Google Terrain as default. The implementation scope is WEPPcloud in this repository. Companion-app discoveries do not apply.

## Source inventory

| Surface | Current evidence | Planned touchpoints |
| --- | --- | --- |
| Run map | `wepppy/weppcloud/controllers_js/map_gl.js` defines Google Terrain/Satellite and defaults to `googleTerrain`; raster basemap creation | Add optional typed vector basemap support after contract/prototype, preserving existing defaults and overlays. |
| Run-map controls | `controllers_js/map_gl_layer_control.js` renders basemap radios; `templates/controls/map_pure_gl.htm` provides the map template | Reuse controls and accessible presentation; no separate map application. |
| GL dashboard | `static/js/gl-dashboard/config.js` defines providers; `map/basemap-controller.js` fetches image blobs and uses TileLayer/BitmapLayer; `templates/gl_dashboard.htm` owns selector | Integrate renderer, selector, state hydration, and actual-provider credit together. |
| Vite landing | `weppcloud-ui-lab/src/AppLight.tsx`, `src/App.tsx` | Add credit/disclosure to both variants while retaining existing map/provider credit. |
| Fallback landing | `wepppy/weppcloud/templates/landing.htm` | Add equivalent credit/disclosure. |
| Landing route/build | `routes/weppcloud_site.py::_render_landing_page` prefers exported index-light.html/index.html then falls back; `weppcloud-ui-lab/scripts/export-landing.mjs` builds/copies to `static/ui-lab` | Test served exported assets and fallback, not source alone. |
| Attribution docs | `wepppy/weppcloud/routes/usersum/weppcloud/data-attribution.md` | Extend user-facing basemap sources/limitations; read nearest usersum instructions first. |
| Tests | `controllers_js/__tests__/map_gl.test.js`, `tests/weppcloud/routes/test_landing_template.py`, `static-src/tests/smoke/landing-keyboard.spec.js`, GL dashboard smoke tests | Extend meaningful behavior/real browser coverage. |

All abbreviated controller/static/template paths are below `wepppy/weppcloud/`.

## Renderer and dependency evidence

The observed run/dashboard basemap paths expect raster images. Service PBF vector data cannot be rendered by changing the URL in those paths. Official styling includes labels and sprites, so decoding geometry alone does not satisfy acceptance.

The landing package already declares `maplibre-gl ^5.12.0`, `react-map-gl ^8.1.0`, and deck.gl dependencies. The fallback template references MapLibre 3.6.0. These are separate asset paths, not proof of compatible run-map integration. The dependency precedent registry has no existing MapLibre/Esri evaluation row. Evaluate existing-capability reuse and its build/runtime cost before recommending a renderer; do not silently import a second stack or new CDN bundle.

## Live service observations — 2026-11-16 17:52 UTC

Item, service, and style JSON were retrieved via unauthenticated HTTPS and parsed. This establishes metadata accessibility, not successful browser rendering or comprehensive legal clearance.

- [Item JSON](https://www.arcgis.com/sharing/rest/content/items/2e1593463c30495e9c802098527e3d1b?f=pjson): supports web/GIS basemap display, credits USDA/U.S. Forest Service, and gives the ownership/access/navigation limitations summarized in package.md. Its licenseInfo contains no identified fee, commercial restriction, or explicit attribution clause; silence is not an unrestricted hosting or redistribution license.
- [Service](https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer?f=pjson): “Forest Service - Geospatial Office” credit, 512-pixel PBF tiles, Web Mercator 3857, relative `tile/{z}/{y}/{x}.pbf` path.
- [Style](https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer/resources/styles/root.json): version 8, 609 layers, source zoom 2–19, bounds approximately [-180, 4.40482, -28.4482, 73.3321]. Bounds do not guarantee complete data coverage.
- Relative source `../../`, sprites `../sprites/sprite`, and glyphs `../fonts/{fontstack}/{range}.pbf` require compatible service/style resolution. Direct style support must be tested, not assumed.
- Item history reports November 2026 data updates; the endpoint date is not a snapshot pin.

