# Roads dashboard implementation validation

Contract ancestor: `2399f835c`; original implementation base: `5227cb258`.
Validation uses the existing forest development Compose stack. Web workers were
gracefully reloaded to load changed routes. No production deployment, original
project mutation, Roads rerun, model calculation or persisted schema migration.

## Artifact and HTTP evidence

`live_artifact_validation.json` retains source SHA-256 values and a direct HTTP
comparison against all generated source geometry/summary records for public
`clogging-starch`, config `disturbed9002-wbt-mofe`. All 39 centerlines and 34 profile
rates agree; simulation duration is 16 years and is not divided into rates again.
The view returns HTTP 200, `Cache-Control: no-store`, in 0.051137 seconds for this
single read (not a performance benchmark). Source artifact hashes match before
and after. One source profile has annual detachment 4071.0173375 kg, area 2332.76 m²,
and displayed rate 17.451505244860165 t/ha/year.

Real temporary-file regressions exercise weighted mixed profiles, signed values,
remainder exclusion, partial diagnostics, typed empty/single-storm differences,
projected effective CRS, malformed IDs/metrics/CRS, alias rejection and a real
shared-flock versus preparation-writer contention. After invalidation, the next
read rejects retained history. Route regressions exercise actual materialization,
malformed CRS HTTP 422, no-store, unsupported view 400, lifecycle 409 and real
authorization denial before view dispatch. Existing ordinary-map tests pass.

## Commands and outcomes

- `wctl run-pytest tests/nodb/mods/test_roads_detachment_view.py tests/weppcloud/routes/test_roads_bp.py tests/weppcloud/routes/test_gl_dashboard_route.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`: 279 passed. Log `/tmp/roads-focused-final.log`.
- `wctl run-npm lint`: passed. The repository lint script targets controllers; new ES module syntax also checked directly with `node --check`.
- `wctl run-npm test`: 120 suites, 1007 tests passed. Log `/tmp/roads-npm-final.log`.
- `wctl check-test-stubs`: passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref HEAD`: passed; no added broad production exception handler.
- `git diff --check`: passed.
- Work-package and all changed canonical/user/developer documentation lint: passed.
- `wctl run-pytest tests --maxfail=1`: running; do not infer full-suite success from focused tests.

## Browser evidence

With `PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`
and `GL_DASHBOARD_ROADS_URL=https://wc.bearhive.duckdns.org/weppcloud/runs/clogging-starch/disturbed9002-wbt-mofe/gl-dashboard`,
run `npm --prefix wepppy/weppcloud/static-src run smoke -- tests/smoke/gl-dashboard-roads.spec.js`.
Three tests passed in 42.6 seconds (`/tmp/roads-browser-final.log`). They verify the
actual guarded response and every complete line's formula, rendered Deck layer,
keyboard table/details, both scope directions, scoped dataset paths and viewport,
plus yearly data/graph and Roads maximum 27 restoration. A controlled response
label injection remains literal text; a controlled 503 optional read leaves
baseline summary usable. These injected cases complement the unmocked successful
HTTP/artifact boundary; they do not claim a real production outage.

A read-only screenshot at `/tmp/roads-dashboard.png` was visually inspected:
centerlines, independent channels, scope selector, numeric jet2 legend and
unavailable gray lines render as intended. Screenshot evidence does not replace
the numerical oracle. Existing dashboard layer/state/graph smoke suites completed: 25 passed, 16 skipped,
6 failed. Two failed workflows require an Omni Scenarios section absent from this
fixture; their later RAP steps were not exercised. Four failures involved a
sidebar node detached during scrolling. A browser-only control using the ancestor
orchestrator and removing the new sidebar controls reproduced that same failure
class (3 passed, 1 detached-node failure). The implementation now limits post-load
restoration/activation to explicit scope snapshots; ordinary entry preserves its
previous path. Rechecking the four affected workflows gave 3 passed, 1 detached-node
failure. This is evidence of an existing asynchronous sidebar replacement race,
not a claim that the full general smoke suite passes. Logs:
`/tmp/roads-existing-smokes.log`, `/tmp/roads-control-smokes.log`,
`/tmp/roads-existing-recheck.log`. Temporary control files were removed.

The actual Flask app/template also passed an injected post-authorization lifecycle
failure check: HTTP 409, retained roads_results_unavailable code, no-store and
rendered Baseline escape. The older documented minus-farce smoke URL returned 404
on this host, so it was not used as a substitute fixture.

## Review and limits

Independent correctness, security and UX implementation reviews are retained
separately. Implementation findings were fixed with tests; broader regression
completion remains an independent package acceptance gate. The response is a
coherent snapshot, not live cross-session polling. This feature does not change
scientific source production or certify unrelated watershed model behavior.
