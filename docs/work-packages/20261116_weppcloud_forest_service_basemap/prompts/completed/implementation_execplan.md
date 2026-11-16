# Add an optional Forest Service basemap to WEPPcloud


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, Outcomes & Retrospective, and tracker.md current. Execution completed locally on 2026-11-16 after accepted ancestors 277d55fba, abd9f6156, and 630e155e1. Scoped tests, browser evidence, and independent reviews pass; production deployment is excluded.


## Purpose / Big Picture


Users can choose Forest Service cartography in the WEPPcloud run map and GL dashboard while **Google Terrain remains the default**. Map credit identifies the provider, and all landing-page variants explain the basemap source and use limitations. Existing analysis overlays and interaction remain intact.


## Progress

- [x] (2026-11-16) Ratified FSBASE-01 with two independent reviews; checkpoint `277d55fba` precedes implementation.
- [x] Prototyped official style/labels/symbols on a real populated run; evaluated and pinned existing MapLibre dependency to patched 5.24.1.
- [x] Wired run/dashboard optional selection, current-provider credit, visible failures, stale-load disposal, and all landing disclosures; Terrain remains default.
- [x] Ratified operator-approved fallback link repair at `abd9f6156`; both confirmed stale consumers now render with the real Flask routes.
- [x] Rebuilt and read back served assets; frontend lint, 126 Jest suites / 1,083 tests and 9 Node tests pass; landing pytest 2 pass.
- [x] Real browser rendering, hostile-resource/redirect/attribution, header privacy, initial-state, mobile, loaded zoom edges, and authenticated selection-box/click checks pass.
- [x] Isolated four existing dashboard smoke failures against pre-change assets; all four reproduce unchanged.
- [x] Independent security review passes with zero unresolved findings; correctness source findings closed.
- [x] (2026-11-16) Operator requested scoped tests; broad run stopped at 3,171 pass / 126 skip. Final scoped Python 327, controller 43, adapter 6 pass. Both independent final reviews and documentation checks pass; closed locally.
- [x] FSBASE-03: operator removed legacy fallback; checkpoint `630e155e1` precedes removal. Both Vite themes, real export failures, 327 scoped Python tests, and final independent reviews pass.

## Surprises & Discoveries

The raster paths cannot consume the service's PBF as images; a passive local
MapLibre underlay rendered official styling without replacing deck overlays.
The shared factory also serves the OSM-only combined viewer, so its adapter
argument remains optional. Actual development access is forest.tail305ec9.ts.net;
the old hostname returned 503 and unmatched localhost Host returned an empty 200.

The existing MapLibre 5.12.0 dependency was affected by an attribution sanitizer
advisory. Upstream backported the fix to 5.24.1; the aggregate npm advisory still
uses an overbroad range. The exact patched distribution, safe fixed credit and
hostile metadata were validated. Remote resources require runtime confinement,
not only initial origin inspection.

Real Flask rendering exposed a deleted About endpoint hidden by the template
test's mocked url_for. The operator approved the existing user-guide destination;
FSBASE-02 covers both confirmed consumers. Browser request.headers() excludes
security headers; corrected allHeaders captures substantiate privacy evidence.

Four existing dashboard smoke failures reproduced unchanged with baseline assets
on the selected run. The full Python suite includes long soil-artifact matrices;
frontend and browser acceptance finished while that gate continued.
The legacy fallback also retained an obsolete CDN renderer with a reachable
attribution sink (SEC-03). The operator directed removing the fallback entirely.

## Decision Log

2026-11-16: Preserve Google Terrain default and existing explicit selections;
add only forestService background cartography. The user authorized execution,
then explicitly authorized the checkpoint commit. Two independent contract reviews
passed before ancestor 277d55fba. No deployment is authorized.

Reuse existing MapLibre at patched 5.24.1, lazily exported from the landing build,
with deck retaining camera and interactions. This avoids another top-level
dependency, server, proxy, or map-stack replacement. The measured optional
renderer cost is documented; no speedup or model-compute benefit is claimed.

Use a validated custom protocol with fixed approved service resources, omitted
credentials/referrers and rejected redirects. Fixed DOM credits avoid remote
HTML. Asset/style failures are visible and alternate providers remain usable;
stale loads cannot replace a later selection.

After actual fallback rendering failed, the operator selected “Replace with user
guide.” Two independent FSBASE-02 reviews passed before ancestor abd9f6156 and
before either broken link was edited. No new route or access rule was introduced.
2026-11-16: Operator explicitly removed the legacy fallback, preserving both Vite
themes. Independent FSBASE-03 reviews passed before checkpoint 630e155e1.
Required missing/unreadable HTML now returns a logged, path-free 503.

## Outcomes & Retrospective

Optional run/dashboard selection and all landing disclosures are implemented and
validated on served development assets. The legacy fallback is removed at operator request (FSBASE-03); both Vite themes remain and missing/unreadable exports return HTTP 503. The corrected legacy header renders through the real Flask URL map. Independent correctness/security reviews
pass with zero unresolved findings. Tests and screenshots are retained under
artifacts; generated bytes are traced through asset_manifest.json.

Operator-requested scoped checks pass: Python 327, map-controller 43, adapter 6.
The broad run was stopped after 3,171 passes / 126 skips with no failures; full
suite completion is not claimed. Four broader smoke failures reproduce against
pre-change assets and are not attributed to this feature. Production deployment
and cross-browser certification are excluded. Exact state, resource, attribution,
and navigation rules live in the canonical FSBASE-01/02/03 contract rather than
only this execution record.
## Context and Orientation


Work in `/home/workdir/wepppy`. Read root and nearest AGENTS instructions for controllers_js, gl-dashboard, weppcloud-ui-lab, usersum, and tests before touching those areas. Preserve unrelated dirty changes and do not switch branches.

The run map is `wepppy/weppcloud/controllers_js/map_gl.js`, with basemap radio UI in `map_gl_layer_control.js`. The GL dashboard defines providers in `wepppy/weppcloud/static/js/gl-dashboard/config.js`, renders them in `map/basemap-controller.js`, and exposes a selector in `wepppy/weppcloud/templates/gl_dashboard.htm`. Both currently use deck.gl to load image tiles and draw bitmap layers. A vector tile instead contains geometry requiring style evaluation, label placement, fonts, and symbols.

Landing sources are `weppcloud-ui-lab/src/AppLight.tsx` and `src/App.tsx`. Their export command writes `wepppy/weppcloud/static/ui-lab/`; Flask's `routes/weppcloud_site.py::_render_landing_page` requires those exports and returns a clear 503 when unavailable. The landing build already declares MapLibre, a styled-vector renderer; its availability there does not establish run-map support.

Use the service:

    https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer

Its style is `resources/styles/root.json`, with version 8, 609 layers, source zoom 2–19, relative source/sprite/font URLs, and 512-pixel Web Mercator PBF tiles. Official item:

    https://www.arcgis.com/home/item.html?id=2e1593463c30495e9c802098527e3d1b


## Plan of Work


### Milestone 1: Contract and feasibility


Identify current canonical contracts including `docs/ui-docs/controller-contract.md`, applicable `docs/ui-docs/contracts/` documents, and the current GL dashboard specification. Follow `docs/standards/contract-first-change-standard.md`, including its accepted contract-decision artifact and ancestor checkpoint before production edits. Add or ratify a canonical basemap contract at `docs/ui-docs/contracts/forest-service-basemap-contract.md` if none already governs this scope, using the prescribed registration/checkpoint process.

Specify that Google Terrain remains the initial default in both run and dashboard maps, including absent or unknown selection under the existing fallback contract. Preserve supported explicit choices and saved/hash state. Add a new optional key (proposed `forestService`) without a persistence migration. Specify active-provider credit, resource-failure presentation, and usable alternative choices. Landing-page attribution does not change its background map.

Inventory all consumers of the shared map controller and dashboard basemap state. Read `docs/standards/dependency-evaluation-standard.md`; no relevant renderer precedent was found in its registry during scaffolding. Audit existing MapLibre/deck capabilities, installed versus browser-served versions, build boundaries, license and dependency tax. Use current primary documentation when evaluating actual APIs.

Run a bounded prototype of styled vector rendering alongside existing deck overlays. Verify relative ArcGIS source/style URLs, sprite/font loading, camera synchronization, resize, pointer handling, ordering, and cleanup. Compare responsiveness, load cost, and memory against the existing map on representative runs. Existing raster support cannot consume PBF as images; geometry decoding alone does not reproduce the official cartography. Select the smallest proven integration, not a map-stack replacement. No new dependency or global CSP relaxation is approved; document failed simpler acceptance and minimal escalation before expanding the budget.

Milestone success is an accepted contract checkpoint and a reproducible prototype proving official labels/symbols with existing overlay interactions. If infeasible within budget, retain findings and narrow the blocker rather than silently using a different raster service.


### Milestone 2: Wire the optional layer and attribution


Implement the proven adapter at the run-map and dashboard seams. Preserve Google Terrain defaults and existing Satellite behavior. Reuse current basemap controls; avoid new persisted settings or duplicate application stacks. Handle rapid selection changes and disposal so stale resource loads cannot switch the user's current choice. Keep zoom, center, picking, drawing, and overlays intact.

Show “USDA, U.S. Forest Service” linked to the item when Forest Service is displayed; retain service credit “Forest Service - Geospatial Office” as applicable. Keep other providers' credit accurate. Implement the ratified visible unavailable state without silent substitution.

Add dedicated map-data credit and accessible limitations disclosure to both React landing variants. Reuse their existing sources/attribution presentation. Preserve current landing background provider credit. Extend `wepppy/weppcloud/routes/usersum/weppcloud/data-attribution.md` after reading its nearest instructions.

Disclose all published limitations: no ownership, legal boundary, jurisdiction, or access-right determination; obtain private-land permission and check public restrictions; use official Motor Vehicle Use Maps or Forest Service advice for driving access; hazards may be absent; unsuitable for navigation. Do not inject remote metadata HTML or imply institutional endorsement. Update `weppcloud-ui-lab/landing.spec.md`, relevant controller/dashboard developer docs, and operator notes on external resource failure and rollback.

Success is an actual run map and dashboard starting in Terrain, switching to official Forest Service cartography and back, with preserved interactions and accurate credit. All three landing paths must display the disclosure.


### Milestone 3: Build, validate, and review


Rebuild controller and landing assets through canonical commands. Inspect served HTML/script paths and actual browser network/rendering, not just source changes. Test absent/empty/populated map state, legacy explicit selections, unknown keys, resource failures, slow responses, rapid switching, coverage edges, source-native zoom and overzoom, viewport changes, mobile layout, and keyboard controls.

Use an authorized representative run in the development environment with production-equivalent frontend assets/configuration. Inspect actual style, tile, glyph (font), and sprite (symbol) requests and ensure application credentials are never sent to third-party hosts. No bulk tile download. Record exact revision, URLs, build artifacts, screenshots, interaction outcomes, and skipped states.

Create independent correctness and dedicated security review artifacts using `docs/prompt_templates/correctness_review_template.md` and `security_review_template.md`; close all medium/high findings. Security triage is high because the repository classifies external-egress/public-route changes that way, not because an exploit is known. Promote durable rules outside this package before closure. Deployment is separate.


## Concrete Steps


Begin in the repository root:

    git status --short
    rg -n 'basemapDefs|googleTerrain|currentBasemapKey' wepppy/weppcloud/controllers_js/map_gl.js wepppy/weppcloud/static/js/gl-dashboard
    rg --files docs/ui-docs wepppy/weppcloud/templates | rg 'map|dashboard'

After contract and implementation work, run:

    wctl exec weppcloud python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests/weppcloud/routes/test_landing_routes.py
    wctl run-pytest tests --maxfail=1

From `weppcloud-ui-lab/`, follow its own AGENTS and run:

    npm run lint
    npm run export:landing

The export rebuilds and replaces its generated target directory; inspect the resulting diff and preserve unrelated assets. Read smoke-test AGENTS before authenticated Playwright runs. Use the existing GL dashboard and landing keyboard smoke suites, adding focused basemap lifecycle/default assertions and real rendering checks. Record exact runtime URLs and test commands when choosing the authorized run; do not assume historical sample runs still exist. Add focused Jest coverage in `controllers_js/__tests__/map_gl.test.js` and the appropriate dashboard suite, using behavior assertions rather than literal URL tests.

Lint changed Markdown with `wctl doc-lint --path <file>` and preview spelling with `diff -u <file> <(uk2us <file>)`. For substantive code also run required changed-code broad-exception enforcement and observe code quality under root guidance. This scaffold itself needs only documentation checks.


## Validation and Acceptance


Fresh run/dashboard pages display Google Terrain by default. Choosing Forest Service renders the official style, labels, and symbols; choosing Terrain/Satellite again preserves state and interaction. Existing explicit selections continue working. Failed or delayed resources do not mislabel another provider or erase overlays. All landing variants show credit and readable limitations without changing their background provider.

Require browser evidence from served rebuilt artifacts, not mocked tiles or a successful HTTP status alone. Tests pass with any unrelated baseline failures explicitly isolated. Unavailable live validation limits the completion claim; never label a scaffold or unit-only result environment validated.


## Idempotence and Recovery


Inspection and tests are repeatable. Keep prototype artifacts isolated and remove abandoned prototype wiring before handoff. Revert only package-owned frontend source and rebuild its assets to restore prior behavior; no data migration or bulk project rewrite is planned. Preserve Terrain as default throughout. No deployment, proxy, backend fetch, credential addition, or offline cache is in scope.


## Artifacts and Notes


Retain consumer inventory, contract decision, dependency evaluation, prototype receipts, compact metadata extracts, generated-asset manifest/readback, test logs, browser screenshots/network results, and review artifacts under `artifacts/`. Exclude tokens and private run data. Update package/tracker/PROJECT_TRACKER with the highest supported claim.


## Interfaces and Dependencies


Preserve the run controller event/API contract and dashboard `createBasemapController` state hooks. Extend basemap selection additively with the ratified key. Keep current Terrain resolution behavior and existing provider definitions. Decide the vector adapter API only after milestone 1 proves official styling and overlay compatibility. No new server endpoints or model interfaces are required.


## Revision Note


2026-11-16 18:00 UTC: Replaced the mistaken companion-app plan with WEPPpy-specific architecture and recorded the user's explicit requirement that Google Terrain remain default.


2026-11-16 execution update: prepared canonical FSBASE-01 and amendments, consumer
inventory, preliminary capability audit, and two passing independent contract
reviews. Production implementation remains gated on explicit standalone
checkpoint commit authority; no runtime or deployment acceptance is claimed.

2026-11-16 closeout: operator replaced the broad Python gate with scoped tests.
All scoped checks and independent reviews pass; exact receipts and the four
reproduced baseline smoke failures are retained. This plan is complete for local
implementation/validation, not production deployment.
