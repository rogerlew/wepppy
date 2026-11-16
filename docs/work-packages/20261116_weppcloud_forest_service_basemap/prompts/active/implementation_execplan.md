# Add an optional Forest Service basemap to WEPPcloud


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, Outcomes & Retrospective, and tracker.md current. Execution was requested on 2026-11-16. Contract checkpoint preparation is active; production implementation awaits the required accepted ancestor commit.


## Purpose / Big Picture


Users can choose Forest Service cartography in the WEPPcloud run map and GL dashboard while **Google Terrain remains the default**. Map credit identifies the provider, and all landing-page variants explain the basemap source and use limitations. Existing analysis overlays and interaction remain intact.


## Progress


- [x] (2026-11-16 18:00 UTC) Corrected scope to WEPPpy, inventoried map/landing source, and recorded the user's explicit Google Terrain default requirement.
- [x] Retrieved public item, service, and style metadata.
- [x] (2026-11-16) Draft FSBASE-01 canonical contract, linked amendments, consumer inventory, and contract-decision artifact.
- [x] (2026-11-16) Two independent contract reviews pass after COR-01/SEC-01 corrections.
- [ ] Obtain explicit checkpoint commit authority.
- [ ] Commit accepted checkpoint, then complete renderer feasibility evaluation.
- [ ] Implement optional basemap plus map and landing attribution.
- [ ] Rebuild assets, test, and retain real-browser evidence.
- [ ] Complete independent correctness/security reviews and documentation.


## Surprises & Discoveries

The combined watershed viewer calls the shared dashboard raster factory directly with OSM-only definitions. Preserve that interface without a vector dependency. The contract-first standard requires explicit checkpoint commit authority; the execution request does not explicitly grant commits.


WEPPpy run/dashboard basemaps are raster deck.gl layers, unlike the initially inspected companion application. The vector endpoint cannot be substituted into image loading. MapLibre already exists in the separate landing build, but run/dashboard compatibility remains unproven. Landing has light and dark Vite variants plus a Flask fallback, so editing one template is insufficient. The date embedded in the service name does not pin its content.


## Decision Log

2026-11-16 execution: draft `forestService` selection and visible loading/unavailable behavior in FSBASE-01. Existing choices provide recovery; stale loads cannot change the current choice. Prepare independent reviews before requesting the required standalone commit authority. No production edits precede that ancestor.


On 2026-11-16 the user corrected the implementation target to WEPPpy and explicitly instructed that Google Terrain remain default. The plan therefore adds an optional choice without replacing current defaults or landing-page map providers. CULVERT files are excluded. Renderer selection remains subject to evidence and dependency evaluation, not a predetermined library adoption. No runtime or production action is authorized by scaffolding alone.


## Outcomes & Retrospective

Execution has produced a reviewable canonical contract and consumer inventory. Renderer feasibility, production edits, builds, browser evidence, and final reviews remain pending. Checkpoint approval must not be mistaken for implementation acceptance.


The corrected scaffold identifies actual WEPPpy integration seams and the rendering feasibility question. No code, build, browser validation, or deployment has occurred. Later milestones in this package deliver the wired feature; documentation alone cannot close implementation.


## Context and Orientation


Work in `/home/workdir/wepppy`. Read root and nearest AGENTS instructions for controllers_js, gl-dashboard, weppcloud-ui-lab, usersum, and tests before touching those areas. Preserve unrelated dirty changes and do not switch branches.

The run map is `wepppy/weppcloud/controllers_js/map_gl.js`, with basemap radio UI in `map_gl_layer_control.js`. The GL dashboard defines providers in `wepppy/weppcloud/static/js/gl-dashboard/config.js`, renders them in `map/basemap-controller.js`, and exposes a selector in `wepppy/weppcloud/templates/gl_dashboard.htm`. Both currently use deck.gl to load image tiles and draw bitmap layers. A vector tile instead contains geometry requiring style evaluation, label placement, fonts, and symbols.

Landing sources are `weppcloud-ui-lab/src/AppLight.tsx` and `src/App.tsx`. Their export command writes `wepppy/weppcloud/static/ui-lab/`; Flask's `routes/weppcloud_site.py::_render_landing_page` serves those exports or `templates/landing.htm` as fallback. The landing build already declares MapLibre, a styled-vector renderer; its availability there does not establish run-map support.

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

Add dedicated map-data credit and accessible limitations disclosure to both React landing variants and the fallback template. Reuse their existing sources/attribution presentation. Preserve current landing background provider credit. Extend `wepppy/weppcloud/routes/usersum/weppcloud/data-attribution.md` after reading its nearest instructions.

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

    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests/weppcloud/routes/test_landing_template.py
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
