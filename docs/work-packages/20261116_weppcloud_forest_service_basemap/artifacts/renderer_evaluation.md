# Renderer evaluation

## Decision and capability overlap

Reuse the existing landing MapLibre dependency as a lazy local browser asset,
with a DOM underlay beneath the existing deck canvas. Deck retains camera,
picking, controls, overlays, and all model/data behavior. Existing raster
TileLayer/BitmapLayer cannot render the service's PBF, official labels, or
sprites. A representative dashboard prototype rendered 131 official features
and preserved landuse/channel overlay layers. No new top-level dependency,
backend proxy, cache, service, CSP change, or map-stack replacement is needed.

The existing dependency is updated within its supported 5.x line to exact
5.24.1. Export its distribution and BSD-3-Clause license from the landing build
into `static/ui-lab/maplibre/`. Loading is deferred until Forest Service selection;
Terrain and the combined viewer do not load it. Restore prior package-owned
sources and regenerate assets to roll back; no run data migration.

## Dependency tax and security

Installed/locked baseline was 5.12.0 (released 2025-11-09). The 5.24.1 maintenance
release is dated 2026-11-11; upstream also maintains a 6.x line (6.0.0 released
2026-07-22). This upgrade avoids that major API change. Public MapLibre APIs
Map, jumpTo, resize, remove, transformRequest, and addProtocol implement the
adapter; no React-specific data model is imposed on run/dashboard controllers.
The landing build environment already supplies npm/Vite and the renderer.

`npm install --save-exact maplibre-gl@5.24.1 --ignore-scripts` reported 3 added,
6 removed, and 9 changed packages. The release declares 19 direct dependencies; lockfile traversal resolves 25
transitive package installations.
No native build or separate runtime environment is introduced. Maintenance is
by the MapLibre contributor project; no quantified bus-factor or future funding
guarantee is claimed. Runtime browser payload/memory measurements accompany the
acceptance receipt; do not treat institutional branding as performance evidence.

Baseline npm audit identified CVE-2026-85061 in MapLibre's attribution sanitizer.
The maintainer advisory explicitly lists 5.24.1 as patched, although the aggregate
GitHub/npm advisory range still says <=6.4.0. Inspect the installed fix and retain
hostile-attribution tests rather than treating an aggregate audit as clean.
Both landing variants already disable MapLibre attribution controls; this is an
affected dependency, not proof of an exploitable landing vulnerability.
The adapter also disables that control, strips remote attribution, uses fixed
safe DOM credits, and replaces the ArcGIS source URL with the official fixed tile
template (no TileJSON/remote attribution request).

All resource fetches use the approved HTTPS service subtree, no credentials,
no referrer, and redirect:error. A custom MapLibre protocol enforces this at the
actual fetch boundary, including font/sprite/tile requests. Unsupported remote
source types or resource destinations fail visibly; no provider fallback.

## Prototype evidence and limits

Actual development target: forest.tail305ec9.ts.net, run mipa-awake-20261102,
configuration config. The old AGENTS sample hostname returned 503 and the old
sample run was absent. Host-unmatched localhost Caddy returned an empty 200;
canonical homelab documentation identified the correct hostname. No auth or
routing configuration was changed.

Initial 5.12.0 prototype: frame interval medians 16.65 ms Terrain and 16.70 ms
vector underlay; sampled JS heap 17.1 MB for both (browser coarse telemetry,
not total renderer memory). Center projection discrepancy <1e-8 pixels. This
is a bounded feasibility sample, not a general performance guarantee. Official
sprite JSON/PNG, PBF tiles, and multiple font resources loaded without errors.
Final patched-build acceptance is recorded separately. Prototype controls still
showed Terrain because injection intentionally did not wire production selection.

## Primary references

- [MapLibre addProtocol](https://maplibre.org/maplibre-gl-js/docs/API/functions/addProtocol/)
- [Request parameters](https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/RequestParameters/)
- [Maintainer security advisory](https://github.com/maplibre/maplibre-gl-js/security/advisories/GHSA-jrc7-96c5-q579)
- [Official style](https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer/resources/styles/root.json)

Patched-build sample: median frame intervals 16.7 ms for Terrain and vector;
precise sampled JS heap 18.64 MB vs 32.18 MB. Local renderer transfer: 1,058,359
bytes JS and 70,324 bytes CSS, only after selection. This is a nonzero memory
and first-use cost; no speedup is claimed. `fs-deep.json` retains actual samples,
projection/picking checks and resource requests. `npm audit --omit=dev` reports
9 findings in the overall landing dependency tree (4 moderate, 4 high, 1 critical).
The critical MapLibre result uses the stale aggregate range; the installed
5.24.1 sanitizer fix and maintained advisory were verified. Other reported
packages are outside the renderer's 25-package transitive closure; this task
does not claim a clean audit of the entire landing build.

The later active-camera sample (60 small Deck longitude updates per provider,
software GPU) measured median frame intervals 64.4 ms Terrain vs 79.7 ms vector,
and sampled JS heap 20.74 MB vs 49.36 MB. This documents the optional renderer's
CPU/GPU and memory cost; it does not imply performance parity. Terrain pays no
lazy renderer transfer or second-context cost. The bounded optional path is
retained because it preserves existing default behavior and official styling,
with no new service or stack replacement. `fs-deep.json` identifies this method.
