# Landing cutover assessment

The operator accepted the Forest preview design on November 22. WIP checkpoint
`e06a305ca` on `task/pure-landing` contains implementation `08562c8f0`.
Proceed with cutover preparation. Public deployment and UI Lab deletion are
premature until the two conditions below are satisfied.

## Conditions for retirement

1. **Provide equivalent access to Atlas project details.** Keyboard panning,
   zoom, metrics and a quadrant summary are present. Individual public run
   IDs and record fields are drawn on the canvas or exposed on pointer hover.
   Verify a keyboard and screen-reader user can obtain the same information.
   A possible small change is keyboard selection on the existing map with
   accessible text for the selected marker, including co-located projects.
   Preserve the uncluttered default map. Exercise the populated, empty and
   unavailable states and document manual results against the landing
   contract's Accessibility acceptance section.
2. **Move the shared renderer before deleting either UI Lab tree.** The
   landing template loads MapLibre directly. The shared Forest Service
   loader in `static/js/forest-service-basemap.js` resolves its own script URL
   to the same directory for Runs and GL dashboards. Vendor the existing
   5.24.1 JS, CSS and license together under WEPPcloud static vendor assets.
   Update both loading paths and remove the UI Lab export step. On the
   candidate build, check bytes, MIME types and real map rendering on the
   Atlas, a Run and a GL dashboard. Switch Terrain → Forest Service → Terrain
   on both project interfaces and verify the raster-only path.

| Served MapLibre 5.24.1 file | SHA-256 on Forest and in Git |
| --- | --- |
| maplibre-gl.js | `a9c9e2aa36d4d5b63b131f27c1272f1a28883eeecc0eddd1e0dbfae4033bc7c9` |
| maplibre-gl.css | `ab1e70d59ec40465bae7e7030da2f3ccf28133fd502e62bd598eefbadfd7a732` |
| LICENSE.txt | `ee5fc05a0677eaf69601d2c7db0d9ecd6cc27c3abc1d0733bc9ed34707cf8ef2` |

## Proposed URL disposition for approval

Paths below are relative to the WEPPcloud mount. Keep mount-aware URL generation.

| Surface | Cutover behavior |
| --- | --- |
| Home and `/landing/` | Serve the same Jinja renderer and no-store responses. Preserve Login/My Runs, persisted theme, and the hero, about and map fragment IDs. |
| `/landing/light/`, `/landing/dark/`, `/landing/preview/` | Redirect to the canonical landing, preserving query strings and fragment navigation. Use the shared theme preference. |
| `/run-locations.json`, landing and both variant JSON aliases | Keep all four backed by the same server-compiled snapshot. Let the public filter roll over with the normal scheduled compilation. |
| `/static/runid-locations.json` | Retire the obsolete static copy. Forest's current public path still returned 200; verify 404 against the actual static server after deployment. |
| Root, landing and variant Vite asset aliases, Vite SVG routes and exported HTML/bundles | Retire after the replacement pages load entirely through their normal asset URLs. Check old asset URLs return 404 through the front proxy. |
| Indexing | Permit indexing of landing content. Proposed implementation: fetch public Atlas rows from the canonical JSON endpoint with an X-Robots-Tag of noindex on the JSON response, preserving server-rendered metrics and geographic summary. This avoids embedding individual records in indexable home HTML. Confirm the indexing choice before implementing it. |

## Removal and integration scope

Remove the 29 tracked files under `weppcloud-ui-lab/` and the exported
`wepppy/weppcloud/static/ui-lab/` tree after relocating the three renderer
files. Retire the Vite export, state injection, legacy asset helpers and
export-specific 503 tests in favor of Jinja home and compatibility tests.
Keep the snapshot compiler, public-feed handlers, Deck.gl controller, CARTO
basemap and the Atlas attribution. UI Lab retirement eliminates its React
and Vite build. The interactive Atlas still uses the existing Deck.gl runtime.

Amend FSBASE-03 and the landing contract together before route changes.
Update controller and GL-dashboard READMEs and the landing-spec link in
the logo style guide. Supersede old tracker instructions while retaining
closed package history. No environment selection flag is needed.

At assessment time upstream master was `ecadc9d30`; a Git merge-tree trial
with the WIP checkpoint reported no conflicts. Recheck on the integration
base and test the integrated build. After candidate acceptance, use the
existing deployment workflow. Keep the prior release available for rollback
of routes and static assets together. Preserve the public-feed filter across
a frontend rollback.

## Verification on November 22

- Forest served the old Vite app at home, landing and both explicit variants
  (HTTP 200). The isolated preview served Jinja, 14 stack rows, no-store and
  noindex. All four JSON aliases responded as JSON. This confirms routing;
  visibility after deployment is checked at the next normal snapshot rollover.
- The landing and compiler suites passed 55 tests. The Forest Service
  basemap Node suite passed 6. Full-page Chromium axe scans found zero
  automated violations across all five AA themes. Axe marked the theme
  selector, both overlay legend items and wheel tip for manual contrast
  review. Automated checks do not establish manual assistive-technology acceptance.
- The broad pytest preflight did not start tests. The isolated runtime
  reported missing browser dependency manifests, shape and GeoParquet
  parser binaries/provenance, and Comrak. Retry against a compatible
  runtime before releasing the integrated candidate.
