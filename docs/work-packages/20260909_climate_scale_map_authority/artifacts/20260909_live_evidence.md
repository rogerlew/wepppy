# wepp1 climate scale-map incident evidence

## Cause and inventory

Host `wepp1`, repository `/workdir/wepppy`, inspected HEAD `ce81dbe78`.
Owner account 1810 has 14 `portland-10-mofe` runs: four stored map strings `"1.1"`,
nine already-correct maps, and `free-sally` missing canonical climate.nodb.
The deployed template binds the map property. Read-only controls are serialized,
and the deployed parser assigns the submitted map. Both rq-engine and RQ workers
parse build payloads (workers replay `job.meta.build_payload`). Therefore a
request-handler-only activation cannot fully retire this mutation boundary.
The operator reported an earlier scalar-display bug; its exact originating
browser/template revision was not established. The recent label/width changes
alone do not explain or prevent the confirmed server mutation.

Redis `job.meta.build_payload` confirms submitted map `"1.1"` for all four
failed jobs; see `20260909_job_payload_evidence.json` (timestamps UTC). The later
successful under-fecundity job also carried the poison but used scaling mode 0.
Correcting the display binding alone cannot repair already-poisoned persisted
state: the old property simply returns that stored value.

Redis `job.exc_info` confirms `AssertionError: 1.1` in spatial scaling:

| Run | Failed job | Retained mode | Rebuild disposition |
| --- | --- | --- | --- |
| under-fecundity | 3ed3844f-8407-47f7-94ea-f1e786ba2439 | None (0) | A later successful climate job exists; no automatic rescaling or model rerun. |
| seductive-sabra | 248efb2b-4973-4d13-884a-ed6719e0eba6 | Spatial (4) | Rebuild climate before the next model run; old outputs retained. |
| warming-championship | 285c7f4f-51d4-4d4c-aa16-349be0e26baa | Spatial (4) | Rebuild climate before the next model run; old outputs retained. |
| asteroid-hindrance | b542738e-6293-4876-9ef9-9ef033f69578 | Spatial (4) | Rebuild climate before the next model run; scalar 1.1 retained. |

## Repair and verification

At 2026-09-09 22:19 UTC, executed the reviewed bounded repair inside weppcloud,
UID/GID 1002:130. Checked DB ownership, config resolution, existing raster,
canonical paths, and default/batch/fork-archive queued/started jobs. Only the
map domain field changed through NoDb locks/atomic dump/cache publication.
Exact protected backups: container `/wc1/.incident-backups/climate-scale-map-20260909T221933Z`
(host `/geodata/wc1/.incident-backups/climate-scale-map-20260909T221933Z`).
`20260909_repair_results.json` records before/after file hashes and samples.

Fresh process verification found all 13 existing climate files correct on disk
and through controller/cache reads. `free-sally` remained absent. Each repaired
run's `climate/wepp.cli` and representative `wepp/runs/p1.cli` hashes were unchanged;
these are sampled artifacts, not a claim about every generated file. Repeated
`--apply` reported all four already correct and skipped dump/backup. No actual
run climate or WEPP model was rebuilt during this repair.

## Production-equivalent propagation canary

At 2026-09-09 22:18:54–22:18:55 UTC, an isolated process in the real rq-worker
container (UID/GID 1002:130, actual mounts/config/environment) loaded candidate
getter/parser code and copied `seductive-sabra` NoDb files plus actual watershed
and climate inputs into `/wc1/.incident-canaries/climate-map-t0v411vn`.
Only the watershed and one representative hillslope (TOPAZ 892) were exercised.
Submitted map `"1.1"` was ignored and persisted as the configured Daymet raster.
Actual `RasterDatasetInterpolator` returned 0.8857483863830566 at the hillslope.
Actual native CLI scaling produced `scale_gridmet_observed_892_1980-2025.cli`;
actual `WeppPrepService.prep_climates` copied it to canary `wepp/runs/p1.cli`.
The bounded translator mapped that one hillslope to WEPP ID 1. This is component
workflow propagation, not a full RQ climate-download/model simulation.

- Original hillslope CLI SHA256: `e63c620c29c90034c708740c4819f03268f6d22b6222f59e870c968bf0eaaf75`.
- Scaled climate and WEPP input SHA256 both: `600d508ace61bef7943460b258211903053860419a6a876b653ec465e2c2a594`.
- Reloaded persisted/effective map: `/geodata/extended_mods_data/wepppy-locations-portland/daymet_scale.tif`.

## Recurrence during live user activity

At 22:32 UTC, new user builds started for the three originally spatial runs.
Each saved payload again carries map `"1.1"`; users now selected scalar mode 1:
seductive-sabra 0.9168, warming-championship 1.12, asteroid-hindrance 1.0688.
Tied-hauler's contemporaneous payload carries the correct configured map and
scalar 1.18. See `20260909_recurrence_payloads.json`. These are subsequent user
choices, not values introduced by this repair. Preserve them during any repeat
map repair. Scalar mode does not use the map, but the old parser still assigns it.
Raw disk readback confirms the three maps were overwritten to `"1.1"` again;
under-fecundity remains correct. See `20260909_recurrence_disk.json`.
The earlier disk/cache inventory proves the initial repair, not final immunity.

## Code activation

Permanent activation is pending the production deployment gate. Both request
handlers and RQ workers require matching code because workers replay old payloads.
The canonical script supports a web-only scope (insufficient here) or full stack
activation; its default plan rebuilds six images and recreates 24 services.
At the latest gate, default had five active jobs (including the three affected
climate rebuilds and tied-hauler); fork-archive had one. No service was restarted.
The operator skill requires explicit approval when active jobs exist, and the
canonical script independently refuses cutover until default/batch jobs drain.
After activation, repeat the bounded map repair only when its target jobs are
inactive, then verify current modes/scalars, disk/cache, and loaded worker code.

## Validation

- Focused initial Python tests: 87 passed; post-isolation subset: 23 passed.
- Climate route suite after adding the real map property to its dummy: 21 passed.
- Full suite: 8,145 passed, 72 skipped, 3,109 warnings, 813.15 seconds.
- Added real RQ payload replay test: 1 passed separately after collection of the
  full suite; full catalog map subset also passed (23 tests).
- npm lint passed; full Jest 108 suites/835 tests passed, then amended forms
  suite 14 tests passed. Rendered HTML plus actual WCForms integration was also
  exercised before separating pytest and Jest prerequisites.
- Changed broad-exception enforcement, test stub checks, and Markdown lint passed.
- Independent correctness and QA findings closed; worker replay coverage approved.
