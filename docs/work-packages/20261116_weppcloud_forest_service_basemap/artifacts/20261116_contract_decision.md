# FSBASE-01 contract decision

## Revision and authorization

Starting implementation revision: `917708c90dce46bbab920ecf9ce5f315e8611290`.
The operator requested “execute docs/work-packages/20261116_weppcloud_forest_service_basemap/”
on 2026-11-16. This authorizes the package's optional choice, retained Terrain
default, attribution, limitations, and bounded feasibility work. Deployment is
excluded. The operator replied “proceed” on 2026-11-16 to the explicit checkpoint commit
request, granting authority to commit this reviewed checkpoint and continue.

## Canonical authority and delta

New authority: `docs/ui-docs/contracts/forest-service-basemap-contract.md`,
FSBASE-01, including its acceptance matrix. Shared authority:
`docs/ui-docs/controller-contract.md`; dashboard authority:
`docs/ui-docs/gl-dashboard.md` and
`wepppy/weppcloud/static/js/gl-dashboard/README.md` (named by nearest AGENTS).
Landing presentation: `weppcloud-ui-lab/landing.spec.md`.
The combined viewer contract remains unchanged:
`docs/ui-docs/contracts/combined-watershed-viewer-contract.md`.

This is an intended additive enhancement, not a conformance repair. Add the
optional `forestService` key and official styled vector display, accurate credit,
visible loading/unavailable status, and landing limitations. Retain all existing
providers/defaults/state, overlay interactions, and the combined viewer's OSM
factory call. No data/schema, model, queue, authorization, or deployment change.
The exact normative rules and rationale live in FSBASE-01; renderer choice stays
pending feasibility. No new dependency is approved.

## Consumer and source boundary

Run-map source: `controllers_js/map_gl.js`, its existing shared/layer-control
helpers, controller bundle template/build, `templates/controls/map_pure_gl.htm`
and `routes/run_0/templates/runs0_pure.htm` (actual map template consumer).
Dashboard source: `static/js/gl-dashboard.js`, `gl-dashboard/config.js`,
`state.js`, map controller and basemap controller, and `templates/gl_dashboard.htm`.
Shared consumer: `gl-dashboard/combined-viewer.js` directly calls
`createBasemapController(...).createBaseLayer('osm')`; preserve this API.
All these paths are relative to `wepppy/weppcloud/`.
Landing: both `weppcloud-ui-lab/src/App*.tsx`, export build, Flask landing template,
and user data-attribution documentation. Extend existing tests at these seams.
Small shared vector adapter/assets may be selected only after feasibility.

## Security and regression evidence

High security triage: new external resource loading on public frontend surfaces.
Review worker/CSP requirements, resolved origins, referrers, credentials, safe
credit links, stale loads, and valid-state noninterference. No global CSP
relaxation, server proxy, or new credentials. Dedicated final security and
correctness reviews remain required.

Use FSBASE-01's separate selection-input and runtime-state matrices, real representative-run prototype, focused
Jest and landing-template tests, existing broad frontend/Python gates, and real
browser lifecycle/rendering evidence. Rebuild and inspect served controller and
all landing variants. No runtime or prototype acceptance is claimed yet.

## Checkpoint disposition

Both independent contract reviews pass; COR-01 and SEC-01 are closed. See
`contract_reviews.md`. Checkpoint commit authorized; ancestor revision will be recorded in tracker.md. Implementation
must not begin until the accepted standalone ancestor exists. Review artifacts
and disposition belong in this directory; record the ancestor in tracker.md.
