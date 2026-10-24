# Roads GL Dashboard implementation security review

## Findings and disposition

| ID | Severity | Failure path and evidence | Required correction | Status |
| --- | --- | --- | --- | --- |
| SEC-I01 | Medium | In `static/js/gl-dashboard/roads.js`, a previous request's delayed 409 JSON body could set failure and disable Roads after a newer successful load. The generation check after fetch did not protect the subsequent body await. Independent Node/jsdom reproduction against the actual module changed a present layer to absent and disabled the Roads choice. | Check request generation immediately after the 409 body await, before changing any controller/UI state; retain a regression for an obsolete failure arriving after a successful response. | Closed. Independent reproduction and permanent delayed-409 regression pass. |
| SEC-I02 | Low | In `nodb/mods/roads/_detachment_view.py`, a GeoJSON CRS declaration with null/list `properties` raised `AttributeError` at the nested `.get`, outside the new route's sanitized invalid-data handling. The existing generic wrapper returns a 500/raw exception message instead of the intended bounded 422. It logs the traceback server-side; no client traceback/path disclosure was confirmed. | Validate the nested CRS declaration shape before dereference, raise the expected validation error and cover malformed metadata through the actual map route. | Closed. Explicit mapping/name validation and actual-route malformed-file regression pass. |

## Independent scope and boundary assessment

Reviewer: `/root/roads_dashboard_security`, 2026-10-24 05:53 UTC. Reviewed the
working implementation descended from contract checkpoint `2399f835c`, including
the new materializer, existing lifecycle/auth helpers, opt-in map route, dashboard
unavailable view, controller, template and integration wiring. This reviewer made
no runtime or project-data edits. Only this artifact is reviewer-owned.

The existing authorization decorator runs before explicit `view` dispatch. The
route resolves the authorized current run's `active_root`; it accepts no arbitrary
source filename, SQL expression or remote URL. Unknown views retain bounded 400
behavior. Ordinary geometry requests retain their existing route/controller path.
The Roads blueprint supplies `Cache-Control: no-store` to the new response too.

`read_detachment_view` holds the existing shared `current_read` guard through
all source validation, Parquet reading, aggregation and CRS transformation.
The response contains materialized values, so no lazy file consumption occurs
after releasing the guard. Prepared metadata and summary use fixed relative paths
with alias rejection. Current-resource admission and single-storm rules are
inherited from the existing lifecycle reader. There is no parent source fallback,
new lock, background operation or privileged subprocess.

Geometry is restricted to lines with finite coordinates and validated
longitude/latitude output. Uploaded properties remain data; computed
`roads_detachment` metadata replaces that namespace. Hover uses Deck's text
tooltip, while table, details, diagnostic text and restored notices use
`textContent`. No source label becomes HTML, a link, a style or a resource URL.

Optional layer transport bypasses the query engine's shared unavailability latch.
Denied, unavailable and transient responses have distinct explanations and do
not reload the page. Initial Roads-page lifecycle failure is handled only after
authorization and retains 409/no-store with a Baseline link. Unauthorized failures
are re-raised without rendering project details. Scope navigation creates a
same-page URL and restores only selected display fields; scenario/comparison
state is not restored into Roads scope.

## Initial evidence and gate

The reviewer independently executed a read-only Node/jsdom probe against the
actual controller. It first reproduced SEC-I01, then passed after the generation
check was added. The probe defers an older 409 body, completes a newer successful
view, then resolves the old error and asserts that the layer remains available
and the Roads choice remains enabled. SEC-I02's type validation was re-read after
the fix. These checks do not substitute for actual browser and HTTP boundaries.

Implementation security gate: **pending validation evidence**. No unresolved
medium/high code finding remains in the inspected snapshot, but acceptance still
requires retained route authorization/422 tests, hostile-label browser checks,
optional-error noninterference and real reader/guard/currentness evidence. The
implementation and its tests remain in progress; this artifact is not a deployment
approval or a claim of completed production-equivalent validation.

## Final independent evidence review

2026-10-24 06:00 UTC: inspected final implementation changes, permanent tests,
their actual assertions and recorded results. Both findings are closed; no new
security finding was identified. Explicit restored-preference validation and
conservative profile-scope labeling add no new privilege or source-selection
capability.

| Evidence | Independent assessment |
| --- | --- |
| `/tmp/roads-focused-final.log`: 279 passed | Includes actual temporary geometry/Parquet materialization, shared flock contention during transformation, subsequent invalidation, symlink rejection, empty/single-storm distinction and malformed numeric/identity/CRS/scope states. No fabricated transport replaces the materializer. |
| `tests/weppcloud/routes/test_roads_bp.py` in that focused run | Actual route returns 200/no-store with expected rate, then 422 for malformed CRS nested properties without root path or traceback text. Missing state returns lifecycle409, unknown view returns400. Real authorization with its test bypass disabled returns403 for both views before materialization. |
| `tests/weppcloud/routes/test_gl_dashboard_route.py` in that focused run | Real lifecycle admission produces409/no-store and chooses the Baseline-escape template. An injected authorization denial preserves403 and renders no project state; this latter test checks route ordering, not a production identity matrix. |
| `/tmp/roads-npm-final.log`: 120 suites, 1007 passed | Includes `static/js/gl-dashboard/__tests__/roads.test.js`: permanent SEC-I01 regression, late-success invalidation, literal labels, distinct401/403/409/404/500 states, baseline preservation, scenario exclusion and scope-state round trips. |
| `/tmp/roads-browser-final.log`: 3 passed | Actual artifact/keyboard/scope test plus a hostile name injected into a real response. The browser renders literal markup, creates no image element and executes no handler. An injected503 leaves baseline summary populated and removes the Roads layer. Third case preserves yearly data and maximum override through both scope directions. |
| `artifacts/live_artifact_validation.json` | Recorded real HTTP200/no-store, 39 prepared lines and 34 summary profiles, all geometry/rates matching source, and unchanged before/after source hashes. Read took 0.051137 seconds. This is the existing inslope project; mixed/partial/remainder cases use real temporary artifact fixtures. |

The reviewer independently reproduced and retested SEC-I01 earlier; the final
suite/browser runs above were executed by the implementation author and reviewed
here. No claim is made that this reviewer reran all suites or production model
execution. The live source evidence supports read-only propagation, not a model
rerun or deployment.

Reviewed implementation SHA-256 values:

| File under `wepppy/` | SHA-256 |
| --- | --- |
| `nodb/mods/roads/_detachment_view.py` | `f7e9d1702d4a21931219cd98fe1661f69e6df584a4e5c1062163d2af1381f0a0` |
| `weppcloud/routes/nodb_api/roads_bp.py` | `0138bfd84d48e5d4c93e53aa05f02491374deb6e861ed46656057716842961f8` |
| `weppcloud/routes/gl_dashboard.py` | `c2d093c8a74c6b9f8e73c79a8c9fde8a8f6b249d9e1a401bc8e79688c0e8aaf4` |
| `weppcloud/static/js/gl-dashboard/roads.js` | `f8ae275f740b3a6427bb5b0cbfdf7c51be32d3315c3cd47e83fd2bb215fe2926` |
| `weppcloud/static/js/gl-dashboard.js` | `d456c2d8735f6482d9bc1f112b928399c84d57fd86eb0859bf9c820face37528` |
| `weppcloud/templates/gl_dashboard_unavailable.htm` | `35597895f9e5afc4265225d9e6672962ab3a461fbb0da5af9c4f3d839f968b3d` |

Implementation security gate: **pass**. Open findings: high 0, medium 0, low 0.
No unresolved risk acceptance was used. The broader Python regression run remains
a separate acceptance gate owned by the parent; its unfinished result is not
reported as passing here. This verdict covers the inspected implementation and
retained evidence, and does not authorize deployment or project mutations.
