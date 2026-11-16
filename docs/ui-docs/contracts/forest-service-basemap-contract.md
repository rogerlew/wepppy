# Forest Service basemap (FSBASE-01)

Status: intended behavior authorized by the 2026-11-16 request to execute the
Forest Service basemap package; independent contract reviews passed; checkpoint commit pending. Implementation
conformance pending; this document does not claim deployment.

## Scope and rationale

Add `forestService`, labeled “Forest Service Basemap”, to the WEPPcloud run map
and GL dashboard. Google Terrain remains the default. The additive choice
preserves established workflows while offering official Forest Service styling.
The shared [controller contract](../controller-contract.md), dashboard module
contracts, and [dashboard specification](../gl-dashboard.md) continue to apply.
No scientific input, output, parameter, authorization, or persistence schema changes.

The combined watershed viewer reuses the dashboard raster factory with its own
OSM-only definitions. Preserve that factory interface and OSM behavior without
requiring a vector renderer or adding choices to that viewer. Static reports,
companion repositories, and the landing background provider are excluded.

## Selection and lifecycle

Fresh run/dashboard maps use `googleTerrain`. Absent, empty, or unknown initial
selection resolves to Terrain. Supported explicit keys and existing run-map
Terrain/Satellite aliases retain their meaning. Preserve supported saved/hash
state; introduce no new persistence mechanism. Unknown interactive dashboard
selection remains a no-op. Never interpret selection text as a resource URL.

Selection changes only background cartography. Preserve center, zoom, bearing,
pitch, overlays, drawing/editing, picking, tooltips, legends, and analysis state.
Rapid changes must cancel or invalidate stale loads; disposal releases renderer
resources and event handlers. Raster-only consumers must work without MapLibre.
Do not globally clamp current zoom or map coverage to the vector source bounds.

## Loading, failure, and recovery

Selecting Forest Service shows “Loading Forest Service basemap…” until its
style and visible resources render. Do not silently substitute another provider.
A style, tile, font, sprite, or renderer failure affecting the displayed map
shows “Forest Service basemap unavailable. Choose another basemap.” in readable,
accessible map status. Keep the selector and overlays usable. Partial imagery
may remain but must not be described as complete. Empty coverage is not a
network error; it must not change selection or hide overlays. Recovery uses
existing choices; reselecting Forest Service retries loading. A late completion
or error must never overwrite a newer selection or its credit/status.

Rationale: visible failure prevents misleading provider identification while
letting users recover with familiar controls; no new service or fallback layer.

## Credit and limitations

When Forest Service cartography is shown, display “USDA, U.S. Forest Service”
linked to <https://www.arcgis.com/home/item.html?id=2e1593463c30495e9c802098527e3d1b>
and retain “Forest Service - Geospatial Office” credit. Credit must track actual
visible providers through loading, failure, and switching, without implying
that a pending selection already rendered. Preserve other providers' credits.

Light and dark Vite landing pages and the Flask fallback identify the optional
Forest Service basemap separately from their existing background provider, with
an accessible limitations disclosure or link. Explain that this map cannot
establish ownership, legal boundaries, jurisdiction, or access rights. Obtain
private-land permission and check public-land restrictions. For motor-vehicle
access, consult official Motor Vehicle Use Maps or the Forest Service. Hazards
may be absent; the map is unsuitable for navigation. No endorsement is implied.

## Resource boundary

Use ordinary browser display of the official FSBasemap_20240617 vector service
and its official style, labels, fonts, and symbols. Renderer adoption requires
the dependency evaluation and representative browser prototype before wiring.
No backend proxy, credentials, offline cache, bulk redistribution, new external
dependency, or global CSP relaxation is authorized. Do not use map features as
model inputs. Omit application credentials from third-party requests and avoid
sending run URL/query details in referrers. Use fixed safe credit text/links;
never inject remote metadata HTML. Inspect resolved style/source/font/sprite
origins before adoption; service metadata accessibility alone is insufficient.
Confine resource requests at runtime to the approved HTTPS service resource
origins/paths recorded by the feasibility evaluation. Resolve official relative
URLs against their service/style base before validating them. Reject URL
credentials and unapproved same-origin, internal, or foreign resource targets
before dispatch; redirects must not escape that boundary. If the renderer
cannot enforce this within the approved budget, report a feasibility blocker.
Test valid official resources and hostile style/TileJSON URLs at the actual
request boundary, rather than only mocking the validator.

## Selection input matrix

| Input | Required outcome |
| --- | --- |
| Missing, null, empty, or unknown initial selection | Terrain |
| Supported explicit key or run-map alias | Preserve its existing provider meaning |
| `forestService` | Load the official style; preserve view and analysis |
| Unknown interactive dashboard key | No-op; keep the current selection |
| URL-like or hostile selection | Never treat it as a URL or executable markup |
| Rapid sequence of supported selections | Last selection wins |

## Runtime state matrix

| State | Required outcome |
| --- | --- |
| Never selected; absent or empty optional state | Terrain; no migration or required Forest Service fetch |
| Existing supported selection or alias | Same provider and view; existing state continues working |
| Forest Service selected with populated overlays | Official labels/symbols; overlays and interactions preserved |
| Unknown initial key | Terrain; no arbitrary fetch |
| Unknown interactive dashboard key | Existing selection unchanged |
| Delayed resources; rapid switching; disposal | Current choice wins; no leaked renderer or stale status |
| Failed resources | Visible unavailable status; overlays and other choices usable |
| Outside coverage; native zoom and overzoom | View controls retained; no silent provider substitution |
| Empty or populated analysis state | Basemap independent of analysis availability |
| Archived/restored run | Existing restore/access rules; no new persisted basemap requirement |
| Hostile key or remote metadata | No URL injection, executable HTML, credential or run-referrer leak |
| Combined viewer | Existing OSM raster call works without vector dependencies |

Resource/renderer failures are exceptional external-display failures governed
by “Loading, failure, and recovery”; they must not become analysis failures.
Absent optional state and empty geographic coverage are expected states, not
corruption or network errors. Normal project access/restore errors retain their
existing contracts; this feature introduces no new user-reachable exceptions.

Validate desktop/mobile and keyboard use on served rebuilt controller and
landing assets, with real style/tile/font/sprite network evidence and screenshots.
Compare responsiveness, transfer cost, and memory with Terrain on a representative
run. Retain focused regression tests plus independent correctness/security
reviews. Mocks or a successful build alone cannot establish conformance.

## Fallback navigation repair (FSBASE-02)

Operator approved on 2026-11-16: replace the fallback's broken “About WEPPcloud”
link with “WEPPcloud user guide,” targeting the existing
`usersum.view_markdown` route for `weppcloud/user-guide.md`. The deleted
`weppcloud_site.about` endpoint currently prevents fallback rendering before
credit can be displayed. Apply the same endpoint correction to the legacy
global header, the only other confirmed template consumer, without changing
any access rules or other navigation. This repairs a confirmed render failure;
it creates no new route. Verify URL building with the real Flask application
and render the fallback disclosure in a browser. Conformance pending.
