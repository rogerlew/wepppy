# Renderer capability audit — preliminary

Read-only inspection on 2026-11-16; no renderer recommendation or acceptance.

The dependency precedent registry has no MapLibre/Esri entry. The run map and
dashboard use deck TileLayer/BitmapLayer image rendering. PBF geometry cannot
be substituted for an image URL; official label/symbol layout requires a styled
vector renderer. Existing deck overlays should retain interaction ownership.

`weppcloud-ui-lab/package.json` declares MapLibre `^5.12.0`, react-map-gl `^8.1.0`,
and deck core/layers/react `^9.2.2`. Its lockfile resolves MapLibre 5.12.0 and
local node_modules includes it. `wepppy/weppcloud/static-src/package.json` and
lockfile have no MapLibre entry, and its node_modules does not contain MapLibre.
Thus a landing dependency is not yet an available run/dashboard browser asset.

Remaining gates: inspect exact browser-served libraries, transitive count and
vulnerability exposure, maintenance/API/license evidence, and worker/CSP needs.
Prototype official relative source/font/sprite resolution, camera synchronization,
resize, overlay picking/editing and cleanup before selecting an adapter. Compare
frame responsiveness, transferred bytes and memory against Terrain on an authorized
representative run. No benchmark, browser rendering, or new dependency approval
is claimed by this inventory. Keep external research and bounded prototype
receipts separate from production wiring.
