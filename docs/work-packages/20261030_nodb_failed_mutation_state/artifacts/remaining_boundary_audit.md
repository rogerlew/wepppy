# Remaining mutation boundary audit

2026-10-31 UTC, `/root/remaining_audit`; checkpoint ancestor `2b998e08d`.

## Search surface

Searched all Python sources under `wepppy` for manual `lock`, `dump`,
`dump_and_unlock`, `unlock`, subclasses and overrides; inspected NoDb global
`islocked` branches and simple AST-detected direct self assignments before the
first `locked` block. The AST scan is a discovery aid, not exhaustive alias dataflow.

| Boundary | File/state/reference lifetime | Stage/owner/recovery | Disposition and evidence |
| --- | --- | --- | --- |
| Watershed `require_centroid` | watershed.nodb, live controller | Global islocked branch mutated even when another detached writer owns lock; failed dump left proposed centroid | Confirmed defect; always enter owned high-level `locked`. Real-file busy-owner and failed-replace tests in `test_watershed_runtime_contract.py` |
| Soils/Landuse `clean` | soils.nodb / landuse.nodb VRT flags | Set flag before acquire; busy owner could expose rejected flag | Confirmed defect; assign only inside owned mutation or new locked scope; test `test_clean_busy_owner_does_not_publish_flag` |
| Soils/Landuse map symlink helpers | same files, VRT flags | Early flag assignment before VRT/source/catalog errors; getInstance may reuse | Confirmed defect; compute planned path locally, publish flag only at existing commit scope; real-file same-process follow-up tests |
| Ron `symlink_dem` | ron.nodb DEM flag | Early assignment before raster construction/read can fail | Confirmed defect; defer flag into existing successful commit scope; real-file same-process follow-up test |
| Watershed `symlink_channels_map` | watershed.nodb flag and WBT collaborator flag | Flags changed before polygonization/coordinate conversion/timestamp error | Confirmed defect; use planned raster path and publish both flags only at final owned mutation; failure readback test |
| Soils/Landuse `_build_spatial_api` | VRT flag retained by live object | Flag changed before remote raster request | Confirmed defect; local .tif path, flag moved to existing owned commit. Soils intermediate commit timing retained; retrieval-failure tests |
| Base `set_attrs` | arbitrary current controller fields | Global islocked is not ownership; setattr can partially fail | Confirmed shared-boundary gap; reported to base repair agent for owned-scope handling |
| Climate `_ensure_cligen_seed` | climate.nodb | Direct dump inside `run_mod_build` owned context | Shared recovery applies; preserve intermediate committed seed |
| Landuse grouped mode/build selection | landuse.nodb shallow field snapshots | Snapshot restoration occurs inside owned context and rethrows | Shared recovery subsequently establishes durable state; no new disk rollback |
| Disturbed route `_controller_lock` | no NoDb field mutation within wrapper | Manual lock wraps CSV deletion or version-checked CSV write; active variant setter occurs subsequently | Verified unaffected for NoDb contamination; external CSV publication is separate |
| Disturbed `_best_effort_read_lock` | read-only lookup selection | Lock may be busy; no NoDb field mutation in inspected body | Verified unaffected |
| UnitizerPresentationView overrides | request-local view, not durable mutation | Overrides locked/lock/unlock/dump/dump_and_unlock reject mutation | Verified unaffected; do not weaken immutability |
| RedisPrep `dump` | Redis hash mirror JSON; not NoDbBase | Independent persistence class | Outside NFMS shared NoDbBase contract; no runtime change |
| RunStatistics | independent file-lock/jsonpickle ViewModel, not NoDbBase | Similar legacy implementation, no singleton cache, non-atomic dual files | Unresolved separate boundary; active run-statistics ledger initiative, no proof of current retained caller retry. Do not claim repaired or change its persistence architecture here |
| Constructor prelock attributes in Treecanopy, RAP_TS, Revegetation, OpenET_TS, Shrubland, DebrisFlow | never-durable new instances | Initialization then owned first commit | First-create failed-instance policy is shared boundary responsibility; not schema migration |

## Caller and ownership inspection

All searched production `require_centroid` callers are climate preparation/station
services or `rq/project_rq`; none acquires the Watershed lock before calling it.
The former `islocked` branch was therefore not a needed nested successful caller.
Clean helpers do have nested owned callers (`Landuse.build`, RRED paths), so retain
that workflow via `mutation_state` only when `_owns_mutation_scope` identifies the
current thread's acquired token; otherwise acquire normally. Global lock state
must never grant mutation ownership.

Map helper callers are culvert orchestration; filesystem preparation remains in
its established order. Failed artifacts are not rolled back by this change.
Only flags move to their existing commit boundary. No file schemas, scientific
values, path names, defaults or queue wiring change.

## Validation status

Centroid regression first run before shared repair: 11 passed, one expected failure
(`held._centroid` still proposed after rejected replace), 10.27 seconds. This proves
the real mutation/serialization failure path. Final tests and broader gates must
be recorded after base helpers are integrated. Artifact failures are injected at
named preparation boundaries; controller serialization/loading remains real.

Final focused command after shared integration:

    wctl run-pytest tests/nodb/test_watershed_runtime_contract.py tests/nodb/test_failed_prelock_state.py tests/culverts/test_culverts_runner.py --maxfail=1

27 passed, 2 existing deprecation warnings, 21.40 seconds. This includes real
successful culvert DEM/channel preparation as compatibility evidence, in addition
to the new failed prelock state cases. Two nested-clean success tests were then
added to explicitly prove an already-owned outer transaction retains its commit
boundary; their focused follow-up result is recorded below.

Nested-clean follow-up: `wctl run-pytest tests/nodb/test_failed_prelock_state.py
--maxfail=1`: 10 passed, 2 existing warnings, 11.14 seconds. Both commands exited
normally. Scoped artifact documentation lint and diff whitespace check passed.
