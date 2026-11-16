# WEPPcloud Forest Service basemap and attribution

**Status**: Closed 2026-11-16 — implemented and locally validated
**Updated**: 2026-11-16
**Owner**: WEPPcloud maintainers; implementation owner Codex

## Overview

Add the Forest Service vector basemap as an optional choice in WEPPpy's WEPPcloud run map and GL dashboard, with visible map credit and attribution on the landing page. **Google Terrain remains the default**, as explicitly directed by the user. Implemented on the forest development stack with retained browser evidence. Production deployment is excluded.

## Scope

Include `controllers_js/map_gl.js` and its layer control, the GL dashboard basemap/configuration/state/template paths, and attribution in both Vite landing variants. Add user-facing use limitations and maintainer documentation. Inventory shared consumers before editing so controller reuse does not leave related run-map surfaces inconsistent.

Exclude CULVERT companion repositories, scientific/model behavior, persisted project schema changes, static report cartography, offline maps, bulk tile redistribution, replacement of current map stacks, and deployment. Landing-page attribution does not authorize replacing its existing background map.

## Required behavior and rationale

- Preserve Google Terrain as the initial/default basemap in the run map and GL dashboard. Preserve existing explicit selections and supported saved/hash state. Missing or unknown selection continues to resolve under the existing Terrain contract.
- Add a distinct “Forest Service Basemap” choice. Selecting it changes background cartography only; overlays, tooltips, drawing/editing, picking, extent, zoom, and analysis behavior remain intact.
- Show “USDA, U.S. Forest Service” linked to the official item when this basemap is displayed. Retain service-provided “Forest Service - Geospatial Office” credit where applicable. Show actual provider credit after switching.
- Add dedicated basemap credit to light and dark landing pages, with an accessible limitations link/section. Institutional logos or funding credit alone do not identify the basemap.
- Explain that the map cannot establish ownership, legal boundaries, jurisdiction, or access rights; private-land permission and public-land restrictions must be checked; motor-vehicle access requires official Motor Vehicle Use Maps or Forest Service advice; hazards may be absent; the map is unsuitable for navigation.
- Use ordinary browser basemap display. Do not infer unrestricted hosting/redistribution rights from silence in item terms or use map features as model inputs.

User decisions and rationale: on 2026-11-16 the user corrected the target from CULVERT to WEPPpy, then explicitly retained Google Terrain as default. An additive choice preserves the existing workflow while supplying Forest Service cartography. Capture these rules in the canonical contract before implementation, with the accepted contract-decision checkpoint required by the contract-first standard.

## Resolved implementation decisions

| Issue | Disposition |
| --- | --- |
| Raster versus vector | Existing run/dashboard paths use deck.gl raster TileLayer/BitmapLayer. PBF vector tiles cannot replace an image URL; official style, fonts, symbols, and labels need a compatible renderer. |
| Renderer integration | Reuse MapLibre 5.24.1 as a lazy local underlay. Prototype and served-browser receipts prove alignment, official styling, and overlay interaction. |
| Dependency boundary | Landing export now publishes the pinned local renderer and license for lazy run/dashboard loading. Tax, advisory evidence, and representative measurements are retained. |
| Default and state | Google Terrain stays default. New key `forestService` is implemented under FSBASE-01. No new persistence mechanism. |
| Failure behavior | Visible “Forest Service basemap unavailable. Choose another basemap.” with usable alternatives; no silent provider substitution. |
| Landing variants | Credit light/dark Vite sources; regenerate and inspect exported assets. Preserve the landing map's existing provider and its credit. |
| Coverage and zoom | Service source reports zoom 2–19 and regional bounds. Test uncovered views and overzoom without globally clamping current map controls. |
| Data freshness | Endpoint suffix 20240617 does not pin a snapshot; current item reports November 2026 updates. |

## Complexity budget

Reuse deck.gl overlays, existing controls/state, current frontend builds, and existing owned helpers. Permit a bounded browser-renderer prototype and small integration changes. No new backend service, proxy, queue, datastore, credentials, offline cache, or global CSP relaxation. Reuse of the existing MapLibre dependency at patched 5.24.1 is documented in artifacts/renderer_evaluation.md; no new top-level dependency was added.

The dependency standard registry now links the retained MapLibre evaluation and real acceptance evidence. Compare a candidate against existing-map frame responsiveness, load cost, memory, rendering fidelity, and interaction correctness on representative runs. If a renderer needs extra mechanisms, record the smallest extension and recovery cost before expansion.

## Success criteria

- [x] Canonical contract and accepted ancestor checkpoint capture optional selection, Google Terrain default, attribution, limitations, state, and failure behavior.
- [x] Run map and GL dashboard initially show Google Terrain; selecting Forest Service renders the official cartography.
- [x] Switching back to Terrain/Satellite preserves overlays, viewport, editing/picking, and appropriate credit.
- [x] Supported existing explicit selections still hydrate correctly; absent/unknown basemap state retains existing Terrain behavior.
- [x] Light and dark landing pages contain readable basemap credit and accessible limitations without changing their map provider.
- [x] Real browser tests cover source resources, zoom/coverage edges, failures, rapid switching, mobile layout, and existing map interactions.
- [x] Rebuilt controller and landing artifacts are actually served and inspected.
- [x] Correctness/security review findings at medium/high severity are closed; tests and documentation are complete.

## Generated artifact validation gate

Applicable: controller bundle and exported landing assets. Trace source edits through the canonical build, served script/HTML URLs, actual style/tile/font/sprite requests, and rendered user outcome. Record exact revisions, artifact paths, representative run, screenshots, and network evidence. File existence or passing mocks do not prove rendering. Highest current claim: rebuilt sources and served artifacts validated in Chromium on forest; see artifacts/asset_manifest.json, browser receipts, and review reports. Operator-requested scoped checks pass; full-suite completion is not claimed.

## Security impact and review gate

Triage: **high** under repository external-egress/public-route rules; no vulnerability is asserted. Dedicated `artifacts/security_review.md` and independent `artifacts/correctness_review.md` are required during implementation using the repository templates. Review resource origins, script supply chain, CSP/worker requirements, credential/referrer exposure, safe credit links, and valid-state noninterference. Never send application tokens to ArcGIS or inject remote metadata HTML.

## Parameterization and compatibility

No scientific defaults, formulas, model fallback heuristics, or project schemas change; parameterization ADR is not currently required. Google Terrain remains default. Any changed default or fallback heuristic requires reassessment before implementation. Use additive basemap state and maintain legacy selections without changing scientific outputs.

## Deliverables and dependencies

Deliver canonical UI contract amendments, a reviewed renderer feasibility result, optional basemap integration, landing-page attribution, user/operator/developer docs, rebuilt assets, tests, browser evidence, and review artifacts. Acceptance used the actual forest frontend and representative run mipa-awake-20261102/config. Deployment remains separately authorized.

## References

- [ExecPlan](prompts/completed/implementation_execplan.md)
- [Tracker](tracker.md)
- [Discovery](notes/discovery.md)
- [Official item](https://www.arcgis.com/home/item.html?id=2e1593463c30495e9c802098527e3d1b)
- [Service metadata](https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer?f=pjson)


## Implementation outcome

FSBASE-01 checkpoint `277d55fba` preceded implementation. FSBASE-02 checkpoint
`abd9f6156` preceded the operator-approved repair of the two deleted About-link
consumers. The lazy local MapLibre underlay preserves the existing deck overlay
stack and OSM-only factory. All three landing variants now expose credit and
keyboard-accessible limitations. The obsolete Flask fallback is removed per FSBASE-03; missing/unreadable exports return a clear 503. The legacy header links to the user guide.
See artifacts/security_review.md and artifacts/correctness_review.md.

Four dashboard smoke failures reproduce identically against pre-change assets
on this representative run; they do not block the basemap change. Deployment
and cross-browser certification are not claimed. The operator replaced the broad Python gate with scoped tests: 327 Python,
43 controller and 6 adapter tests pass. The interrupted broad run had 3,171
passes and 126 skips with no failures.
