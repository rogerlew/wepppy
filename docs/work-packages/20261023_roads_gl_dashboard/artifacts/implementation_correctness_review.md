# Roads dashboard implementation correctness review

Reviewer: `/root/roads_dashboard_correctness`. Review date: 2026-10-24 UTC.
Contract ancestor: `2399f835c`. Scope: independent source/test inspection and
bounded probes against the actual new functions, using temporary fixtures only.
No runtime source or production project files were edited by this reviewer.

## Findings

| ID | Severity | Concrete failure and evidence | Smallest correction and acceptance | Status |
| --- | --- | --- | --- | --- |
| COR-I01 | Medium | `static/js/gl-dashboard/roads.js::restoreDisplay` compares restored values against `typeof getState()[key]`. Nullable defaults such as `roadsMaxOverride`, `weppYearlySelectedYear`, OpenET selected month/year/dataset and RAP year are objects (`null`), so their legitimate numeric/string values are rejected. An independent Node probe of the actual function retained null for requested year 2003, maximum 7.5 and month 3 while restoring the nonnullable statistic. Scope navigation loses accepted compatible display choices. | Validate intended per-key values independently of the current nullable value; keep malformed hash data bounded. Exercise restore on real default state and a browser scope round trip retaining a chosen maximum and year, not just URL serialization. | Open |
| COR-I02 | Medium | `nodb/mods/roads/_detachment_view.py::_materialize` validates remainder scope but otherwise accepts any `profile_scope`. `roads.js::profileScopeText` labels unknown nonempty values as “Road profile.” A real temporary summary with `typo_scope` in both profiles was accepted and returned unchanged. Malformed scientific attribution is presented as established road-only scope. | Validate the canonical `road`, `mixed_profile`, `replacement_remainder`, `unclassified_profile` enum at the read boundary; use a conservative frontend label for unrecognized input. Add malformed scope and legitimate enum tests through the actual reader/route. | Open |
| COR-I03 | Medium | `gl-dashboard.js` restores visible layer flags after detection, then activates only graph keys present in `GRAPH_DEFS`. The supported layer-driven `wepp-yearly` graph is absent from that list. `layers/orchestrator.js::detectWeppYearlyOverlays` discovers metadata/layers without loading the yearly summary; `map/layers.js::buildWeppYearlyLayers` requires `weppYearlySummary`. The restored yearly radio is therefore selected but its map data/graph never load until a user reselects it. The existing interactive path invokes `activateWeppYearlyLayer`; restoration skips it. | Restore data-dependent selections through the existing activation/refresh paths before final rendering. Audit yearly channel and other date-dependent overlays. Verify supported yearly layer, target-scope values, selected year and graph survive both scope directions in the real browser. | Open |

COR-I02 was also noticed by the security reviewer; one shared correction suffices.
The already corrected delayed-409 and malformed nested-CRS issues remain owned
by that review rather than duplicated here.

## Positive correctness assessment

The materializer holds `lifecycle.current_read` through all JSON/Parquet reading,
CRS conversion, validation and aggregation. It returns materialized values, so no
lazy source reads escape admission. All four source paths are fixed and checked
for aliases. It preserves mandatory continuous resources, distinguishes valid
single-storm absence, retains manifest rows rather than collapsing profile IDs,
and verifies completed-summary membership. No catalog or receiving-hillslope
fallback substitutes for source profile results.

The numeric path correctly uses summed annual mass divided by summed full modeled
area, multiplied by ten. It checks finite metrics, positive areas, common integral
duration and density agreement. Partial profiles have null aggregates; remainder
profiles are excluded and counted. Effective preparation CRS takes precedence
over original/configured values, with semantic CRS comparison and explicit
longitude/latitude output. Uploaded names remain literal data, and computed
metadata overrides the reserved namespace.

Ordinary map requests retain their original reader. Explicit views dispatch only
after authorization; expected invalid-artifact errors are bounded 422 responses,
while lifecycle errors retain shared 409 handling and no-store. The unavailable
dashboard view preserves failure status and offers Baseline navigation. Optional
Roads fetches use their own controller instead of the query-engine latch.

## Validation reviewed

- `tests/nodb/mods/test_roads_detachment_view.py`: real compact Parquet/JSON and
  transformations, multi-profile weighting, typed-empty/single-storm distinction,
  partial rows, malformed identities/metrics/CRS, alias rejection, negative values,
  remainder exclusion and actual shared/exclusive guard contention.
- `tests/weppcloud/routes/test_roads_bp.py`: actual materializer integration,
  malformed CRS bounded response, absence/unknown view and authorization denial
  before view handling. Existing ordinary-map tests retain compatibility coverage.
- `static/js/gl-dashboard/__tests__/roads.test.js`: literal labels, scoped error
  isolation, invalidated responses, temporary scenario hiding, scope URL creation,
  signed/zero/missing colors and the corrected delayed-409 race.
- `static-src/tests/smoke/gl-dashboard-roads.spec.js`: parent reports a passing run
  on clogging-starch. Source checks response profile aggregation, rendered line,
  keyboard details, viewport and scope paths in both directions. This initial
  smoke does not select a nondefault maximum/year or exercise restored yearly
  map data, so it cannot close COR-I01 or COR-I03.

Independent probes used the actual `restoreDisplay` function under Node and the
actual Python materializer with temporary JSON/Parquet generated by the new
test fixture. They reproduced COR-I01 and COR-I02; no production data changed.
Full-suite results are not claimed here while the parent's run remains active.

## Initial verdict

Implementation correctness gate: **hold pending COR-I01 through COR-I03 and
independent post-fix checks**. The coherent source and aggregation design is
sound in the inspected implementation. Remaining risk is propagation of restored
state into actual queries/rendering and schema attribution, rather than the
already accepted model formula. Browser and regression evidence must accompany
closure; this review does not authorize deployment.

## Post-fix inspection

The author's changes now validate restored preferences by explicit field types
rather than null defaults, reject unknown summary scopes and label unexpected
frontend scopes conservatively, and invoke existing yearly/channel/event/RAP/OpenET
activation and refresh paths after restoring visibility.

Independent probes against the corrected functions confirm:

- Requested year 2003, maximum 7.5 and month index 3 all restore from null defaults.
- `profileScopeText([{profile_scope: 'typo_scope'}])` yields `Unclassified profile`.
- The actual materializer rejects the previous temporary malformed Parquet fixture
  with `ValueError: Unsupported Roads profile scope.`

The permanent nullable-preference regression is present. Final closure awaits
the permanent malformed-scope regression and actual browser yearly/max round-trip
evidence; no additional medium/high source finding was identified in this pass.

## Final independent disposition

Rechecked 2026-10-24 05:59:32 UTC. **Implementation correctness review: pass;
no unresolved medium/high correctness findings.** The three initial findings
are closed by the author's corrections and the evidence below:

| ID | Closure evidence |
| --- | --- |
| COR-I01 | Explicit per-key preference validation handles nullable number/string fields. Independent actual-function probe confirms the fix and a permanent `restoreDisplay` regression is present; the real browser preserves a selected year and Roads maximum 27 across both scope directions. |
| COR-I02 | Materializer validates the canonical scope enum. Independent temporary-Parquet reproduction now raises the expected validation error; the permanent malformed-artifact parametrization includes unknown scope. Frontend unknown-scope text is conservatively unclassified. |
| COR-I03 | Restored visibility now invokes existing yearly/channel activation and event/RAP/OpenET refresh paths. The expanded browser test selects yearly soil loss, changes the year, and confirms populated yearly summary, selected layer/year, active yearly graph and maximum override after Roads and Baseline navigation. |

Reviewed `/tmp/roads-browser-final.log`: **3 passed in 42.6 seconds**, including
the original real-artifact/keyboard/scope test, hostile-label and optional-503
noninterference, and the new yearly/maximum round trip. The reviewer inspected
the actual test assertions and corrected implementation rather than inferring
closure solely from the reported result.

The remaining full-suite run is a broader acceptance gate owned by the parent;
this review does not report its unfinished result as passing. Production fixture
coverage remains the inslope case, with mixed/remainder/partial/CRS cases exercised
through compact real artifact fixtures. Deployment and model reruns are outside
this implementation review. No additional blocking correctness finding remains.

Reviewed implementation snapshot SHA-256:

| File | SHA-256 |
| --- | --- |
| `wepppy/nodb/mods/roads/_detachment_view.py` | `f7e9d1702d4a21931219cd98fe1661f69e6df584a4e5c1062163d2af1381f0a0` |
| `wepppy/weppcloud/routes/nodb_api/roads_bp.py` | `0138bfd84d48e5d4c93e53aa05f02491374deb6e861ed46656057716842961f8` |
| `wepppy/weppcloud/routes/gl_dashboard.py` | `c2d093c8a74c6b9f8e73c79a8c9fde8a8f6b249d9e1a401bc8e79688c0e8aaf4` |
| `wepppy/weppcloud/static/js/gl-dashboard/roads.js` | `f8ae275f740b3a6427bb5b0cbfdf7c51be32d3315c3cd47e83fd2bb215fe2926` |
| `wepppy/weppcloud/static/js/gl-dashboard.js` | `d456c2d8735f6482d9bc1f112b928399c84d57fd86eb0859bf9c820face37528` |
| `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js` | `3b56b24b85c6e1be1d5569a0d9d3ea7ac08d5720aa315fa5fa5e87cffeadfacc` |
| `wepppy/weppcloud/static/js/gl-dashboard/state.js` | `048bb8cf744a96207cefb3e071ff98f313c92c8611f3fb7ff2c659b24b1b5d08` |
| `wepppy/weppcloud/templates/gl_dashboard.htm` | `f17dbcba987dcd92f6714b3a2db3fe68184e5dca135598c5ae0627e8d665a63e` |
| `wepppy/weppcloud/static-src/tests/smoke/gl-dashboard-roads.spec.js` | `f17fbfb9ffd09ab4383e21390e3df9eac12e79ad4afa6729627a7a7ae85e55bf` |

## Final restoration guard and broader smoke disposition

Rechecked 2026-10-24 06:06:17 UTC. The post-detection restoration/activation block
now runs only when `scopeRestore.layers` is present. Removing only that guard
and its indentation exactly reconstructs the previously reviewed orchestrator
hash. `scopeNavigationUrl` always emits the layers object, so intentional scope
restoration still reaches the data activation that closes COR-I03. Ordinary
entries avoid an unnecessary additional sidebar rebuild/activation pass.

Final `static/js/gl-dashboard.js` SHA-256:
`e7e16a8c91b98148b7c2b53ce6ac49ea7bb8dbd407e62486c0ea40d668573a74`.
The `roads.js` hash remains the previously reviewed `f8ae275f...fe2926`.

Reviewed broader smoke evidence:

- `/tmp/roads-existing-smokes.log`: 25 passed, 16 skipped, 6 failed. Four failures
  occur at detached sidebar nodes during `scrollIntoViewIfNeeded`. Two Omni/RAP
  workflow tests fail first because the `Omni Scenarios` section is absent; those
  results provide no coverage of their later RAP assertions on this fixture.
- `/tmp/roads-control-smokes.log`: the parent's ancestral-orchestrator control
  reproduced a detached-node failure with three other selected tests passing.
- `/tmp/roads-existing-recheck.log`: the guarded implementation likewise has one
  detached-node failure and three passes; the failing individual test differs,
  but the failure mechanism is the same sidebar-node replacement race.

This supports recording a preexisting browser-smoke/runtime synchronization
limitation rather than attributing the shared failure class to the Roads feature.
It does not justify saying all existing smoke tests passed or prove unchanged
failure frequency. Scenario-dependent cases need a fixture with their prerequisite
outputs for meaningful coverage. Keep the logs and these limits in final validation;
no unrelated harness or dashboard redesign is required to close this feature's
confirmed findings. Correctness approval remains unchanged, with no new blocker.

## Scoped invalidation follow-up

The 2026-10-24 06:19 UTC correction hides `.gl-main` on scoped Roads invalidation,
covering old legends and cached graph DOM as well as the map. The sidebar is
outside that container, so the actionable reason and Baseline navigation remain
usable. Optional overlay errors retain their separate request path. Reviewed
`/tmp/roads-browser-complete.log`: all four feature smoke tests pass in 39.7 seconds,
including injected query-engine 409, no automatic reload, hidden invalid scene
and successful fresh Baseline recovery. The visual invalidation correction passes.

One additional error-state finding surfaced while reviewing that callback:

| ID | Severity | Failure and correction | Status |
| --- | --- | --- | --- |
| COR-I04 | Medium | Shared read contention uses `roads_results_unavailable` with an explicit wait-for-busy-operation message. `data/query-engine.js::readResponse` discards the response body when calling `ctx.onRoadsUnavailable()`, and the new non-reloading callback calls `roadsController.unavailable()` with its prepare/run-again default. A transient busy read therefore tells the user to rerun. Forward the server's string `error` or `error.message` through the callback, with the default only for absent text, and retain a regression asserting the busy explanation without a rerun instruction. | Open pending correction |

### COR-I04 closure and final accepted snapshot

Rechecked 2026-10-24 06:21:47 UTC. **COR-I04 closed; correctness approval restored
with no unresolved medium/high findings.** The query helper now preserves the
server's string or nested error message, forwards it into the invalidation callback
and retains the lifecycle code/message on its thrown error. Explicit
`roads_operation_busy` receives the same bounded handling. The orchestrator passes
the reason to the Roads controller without replacing it with rerun guidance.

An independent Node probe of the actual query helper confirms both lifecycle codes
retain their original code and nested busy message in callback and thrown error.
Permanent tests cover both codes. Reviewed `/tmp/roads-npm-complete.log`:
**120 suites, 1012 tests passed**. Reviewed `/tmp/roads-browser-accepted.log`:
**4 passed in 41.7 seconds**. The final browser case explicitly checks busy/wait
guidance, absence of a prepare/run instruction, hidden invalid scene, no reload
and fresh Baseline recovery. Existing broad-smoke limitations recorded above remain.

Final hashes superseding earlier entries:

| File | SHA-256 |
| --- | --- |
| `wepppy/weppcloud/static/js/gl-dashboard.js` | `d94e2ac4c00eb9ad31e00d8e3d0d492a49c2a9034502463a5d2f3955fff2049f` |
| `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js` | `5ca763aa0154df418cb0e33eab65f2789067a8b6b5f95a2dd76f6b6e8e8e9ea0` |
| `wepppy/weppcloud/static-src/tests/smoke/gl-dashboard-roads.spec.js` | `1a2eedce78bdb666c02fb938af20677ff45bd0caae340b149dbbb4911948a9fa` |
