# Independent Omni SBS implementation correctness review

## Metadata

- Package: `docs/work-packages/20261116_omni_sbs_reload/`.
- Reviewer: independent `reviewer` agent `/root/contract_correctness`.
- Date: 2026-11-16 UTC.
- Base/checkpoint: `67468cf86`; reviewed uncommitted implementation diff.
- Scope: `controllers_js/omni.js`, `rq_engine/omni_routes.py`, paired targeted
  controller/route tests, existing scenario naming, parser, and freshness helpers.
- Authority: OSR-01 `docs/ui-docs/contracts/omni-sbs-control-contract.md`, UFS-01
  `docs/schemas/user-file-staging-contract.md`, and SBS freshness contract.
- Related review: `20261116_contract_correctness.md`; security review separate.

## User outcome and failure class

Users should reload an accepted SBS map, read its filename, and resubmit without
another upload. Available inputs may be staged or copied into the associated
scenario. A fresh replacement should not erase the old accepted input on failure.
The implementation separates pending Files from saved references and resolves
server-owned associations rather than request-row position.

The broken shared assumption is that an empty browser file input means no map
exists. It affects both submission and the controller's generic definition reader,
which supplies deletion/selection identities. Legacy numeric type hydration is
another supported-state variant of the same user-visible reload failure.

## Findings

| ID | Severity | Surface | Finding and required action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Hydrated row selection/deletion | `readScenarioDefinition` omitted the saved reference while `serializeScenarios` retained it. `refreshScenarioOptions` and `collectSelectedScenarios` consequently computed generic `sbs_map`, not the accepted child name. Repair shared saved-state reading and assert hydrated deletion identity. Also keep deletion pointed at the accepted map while a replacement File is pending. | Closed: shared reader and accepted-identity deletion/pruning regression |
| COR-02 | Medium | Supported numeric saved type | The backend accepts and persists integer `8`, but hydration assigned it directly to a select containing `sbs_map`. This rendered a blank row, hid the current filename, and omitted the saved scenario on submit. Use existing type normalization at hydration and retain a regression. | Closed: normalized hydration and passing numeric-type regression |

Both findings were sent promptly to the implementation owner. No unrelated
production edits were made by this reviewer.

## Valid-state and input coverage

| State | Required behavior | Reviewed evidence |
| --- | --- | --- |
| Never-used/empty SBS row | Missing-input guidance; no accepted mutation | Route validation; preexisting missing-input tests |
| Saved staged map | Exact saved association survives reload/submit | New JS saved-state test and reordered-row filesystem test |
| Consumed input, child exists | Validate/restage outside reset; preserve bytes | New real-raster restoration plus actual `SbsExecution.copy_to` test |
| Legacy child without receipt | Same input resolution; normal output freshness | Restoration test deliberately has no historical receipt |
| Numeric saved scenario type | Hydrate SBS controls and saved identity | COR-02 requires regression |
| Same child from distinct saved paths | Reject ambiguous recovery | New basename-collision test |
| Forked old staging prefix | Resolve only local corresponding locations | Parameterized old-prefix recovery test |
| Invalid/symlink/traversal source | Explicit failure; no stale fallback | New actual raster/containment tests |
| Replacement or pending edit | Isolated bytes; correct accepted display and deletion | New isolation/UI tests; COR-01 includes pending deletion gap |
| Postcommit enqueue error | Reconcile accepted state; preserve submission error | New controller rejection/reconciliation test |
| Concurrent saved definition/content change | Reject before commit under real lock | Implementation callback inspected; direct persistence evidence pending |

The matrix separates stored state from request variants (replacement/no File,
blank/deleted rows, multiple maps, same-name files). It is not an exhaustive claim.

## User-reachable errors and partial state

Missing/unknown saved association, missing maps, ambiguous child identity, invalid
staging paths, containment failure, invalid raster, oversized source, and detected
copy/selection drift have explicit failure paths. Failed validation does not
publish new accepted scenario state. New uploads use separate directories, so
orphan files can remain without overwriting an accepted input. The contract
permits these unreferenced files and forbids selecting them by directory scan.

State can commit before queue failure; UI reconciliation preserves the reported
error. No rollback of accepted files or outputs is claimed. Existing queue and
archive behavior is retained rather than redesigned.

## Generated-artifact evidence chain

| Stage | Evidence reviewed | Status |
| --- | --- | --- |
| User intent/request | Scoped JS serialization assertions | Scoped tests passed; log inspected |
| Normal-reader persisted state | `persistence_tests.log` and `runtime_followup.json` durable readback | Passed for unchanged and concurrent-change rejection cases |
| Restored intermediate raster | Real raster helper plus byte comparison in route tests | Scoped tests passed; log inspected |
| Consumed SBS input after reset | Actual `SbsExecution.copy_to` after test child deletion | Scoped tests passed; log inspected |
| Generated landuse/soil/WEPP input | `runtime_followup.json`: 218 management, soil, and run files; samples/digests | Regeneration demonstrated; complete semantic/model-result gate remains open |
| Execution output and browser report | 217 fresh hillslope outputs; `pw0.err` climate-year mismatch; browser submission 202 | Hillslope execution and browser submission passed; watershed/report blocked |

The reviewer inspected owner-produced `/tmp/omni-js-after.log` (26 controller
tests passed) and `/tmp/omni-scoped-python.log` (116 targeted Python tests passed,
7 warnings). No full suite was run. Native-produced child validation, browser
presentation, and generated model artifact readbacks remain to be attached by
the implementation owner.
This review does not establish deployment, affected-run repair, or incident
resolution. Final verdict depends on finding closure and evidence disposition.

## First post-fix verification

COR-02 is closed: both hydration assignments use `normalizeScenarioTypeToken`,
and the parameterized saved-map regression passes for `sbs_map` and integer `8`.

COR-01 is partly repaired: the shared reader preserves saved references, and
`collectSelectedScenarios` requests the accepted definition when replacement is
pending. However, actual file-change events still update `omniScenarioName` to
the pending name, and `pruneDeletedScenarios` uses that dataset. A successful
backend deletion of the accepted map can therefore leave the row displayed.
The initial pending-replacement regression did not dispatch the file-change
event or assert response-driven pruning. Complete this same finding by using
accepted identity for pruning and testing the complete event/response path.

Code review gate: pending the remaining COR-01 fix. Native/browser/generated
artifact gate: pending, independently of code/test review.

## Final code-gate disposition — 2026-11-16 19:25 UTC

COR-01 is closed. `readScenarioDefinition` carries the saved SBS path when no
replacement is selected; its accepted-state mode is now used by both deletion
selection and response-driven pruning. The regression dispatches the real
file-change event, returns the accepted old scenario in `removed`, and asserts
that the row disappears. Rechecked `/tmp/omni-js-after.log`: all 26 targeted
controller tests pass after this correction.

Both medium code findings are closed. The code correctness/UX gate is accepted
for this reviewed diff and scoped tests. This is separate from the native/browser
and generated-artifact acceptance gate, which remains pending owner evidence.
No environment-validated, deployed, or incident-resolved claim is made here.

## Runtime evidence disposition — 2026-11-16 19:31 UTC

Inspected `persistence_tests.log`: two real NoDb commit tests passed. These use
actual `Omni.parse_scenarios` and detached reload, with a concurrent saved-state
mutation injected before the commit validator. The stable case accepts input;
the drift case returns 400, preserves the concurrent saved definition, and keeps
the raster available. The inspected earlier targeted suite remains 116 passing;
these two commit tests were executed separately.

Inspected `runtime_followup.py` and its retained JSON result. Under uid 1000/gid
993 on the disposable project `qa-omni-reload-20261116`, actual run admission
restored a consumed child's SBS file to staging and the normal durable reader
returned the saved definition. A real forced scenario execution then reset the
child and consumed/copied that staging source. The source/restored/child main
raster digest matched (`7d1ed360d8e639050cf3879293efcdbee216bd9a4faac4e03399442416d97405`);
the resulting raster is 836 by 714, one band, GDAL checksum 28186. Native work
regenerated 218 management, 218 soil, and 218 run files, and 217 fresh hillslope
loss outputs. This supports the input-restoration/reset boundary and substantial
native execution, not a complete watershed-result claim.

The watershed run stopped because the fixture channel climate begins in 2007
while hillslope/watershed pass files begin in 1980. The retained `pw0.err` tail
explicitly reports this mismatch and simulation stop. Do not repair unrelated
fixture climate/model data inside the SBS UI scope or count the blocked report
as successful. Full watershed and fresh report acceptance remain open.

Inspected the completed authenticated `browser_acceptance.json` and
`browser_saved_map.png`. The real page displayed `Current SBS map` and
`qa_omni_reload.tif` with zero selected Files. Clicking the actual Run Omni button
returned 202 and job `3dd9ac8f-b0ab-483d-aae8-dba1d946b45d`; reloading preserved
the same filename and serialized saved reference. The screenshot confirms the
canonical filename display is visibly rendered. This establishes browser
reload/resubmission acceptance, not job completion.

**Final disposition:** code correctness/UX findings remain closed. Scoped tests,
real persistence, native input recovery/reset, and browser reload/submission are
validated at their stated boundaries. Full environment/artifact completion is
blocked by the unrelated watershed fixture mismatch. No deployment, affected-user
run repair, or incident-resolved claim is supported.

## Authorized fixture repair and final evidence review — 2026-11-16 19:49 UTC

This addendum supersedes the earlier fixture-blocked environment disposition.
The operator authorized repairing the disposable acceptance fixture; this
reviewer inspected the repair/evidence scripts and results without running or
mutating the fixture. No production-code scope was added. All three entries in
`candidate_hashes.json` still match the reviewed route, controller, and built
bundle.

`repair_fixture.py` confines regeneration to `qa-omni-reload-20261116`, backs up
654 prepared climate/run/error files, and prepares inputs from that fixture's
existing climate. `fixture_repair.json` records all 217 prepared climate files
matching their source digests and exactly the years 2007–2024. Normal hillslope
and watershed execution completed, with 217 fresh hillslope outputs. The source
project's inspected NoDb and climate input hashes remained unchanged. This is a
fixture repair, not a climate-policy or model-parameterization change.

`runtime_repaired.py` and `runtime_repaired.json` demonstrate complete native
execution after admission recovered the consumed scenario map to staging. The
saved definition survived durable reload; forced scenario execution reset the
child, consumed the staging copy, and retained the expected SBS digest and raster
metadata. It regenerated 218 management/soil/run inputs and 217 fresh hillslope
outputs. Both baseline and scenario output year sets are 2007–2024; native
watershed execution completed and the normal scenario report has 22 rows.

The reviewer parsed `runtime_repaired.csv` and `browser_repaired_report.csv`:
they are identical, contain 11 finite-valued metrics for each of the baseline
and intended SBS scenario, and include matching contributing area, precipitation,
water discharge, and sediment metrics. This confirms semantic report contents,
not merely report existence or job success.

`browser_repaired.json` records authenticated actual-button resubmission with no
selected File, HTTP 202, and preserved saved reference/filename after reload.
`browser_repaired_jobs.json` records all three jobs finished for root
`a858ffa4-ad26-4e5d-b0c9-53b00eb6539d`. The tree contains compilation/finalization
and no scenario execution child, consistent with unchanged-input reuse after the
separately proven forced native run. It does not claim a second fresh execution.

The final authenticated report request was repeated after the queued tree
completed. `browser_final_report.json` records HTTP 200 and that ordering;
`browser_final_report.html` contains the intended SBS scenario. The reviewer
recomputed the HTML digest and matched the retained receipt. Thus the visible
report is checked after queue settlement, not inferred from a pre-completion
page or a successful sibling request.

**Final verdict:** no unresolved medium/high correctness finding remains. The
former watershed/report blocker is closed by the authorized fixture repair and
retained native, queued-reuse, semantic report, and browser evidence. The scoped
repair is environment validated on the disposable forest/dev project at the
recorded candidate hashes. This does not claim production deployment, repair of
the originally affected user's project, or broader upload-consumer conformance.
