# Current implementation disposition

Living execution record, 2026-09-17 UTC. Baseline inventories/probes remain
historical evidence. Scoped implementation approval is not package completion.
Reviewed implementation waves committed through `de3a1eba0`; the development
restart is complete with image, UID/GID/groups and mount parity retained in
`runtime_restart_verification.json`. Actual baseline M3/WEPP, report, C02 mixed
native export and C11 public browser workflows now have retained evidence.
Climate-change/stale/M3 rerun now passes. Live archive/restore preserves the
selected bytes/modes but restored M3 is stale due to the independently attributed
PF-R01 soil physical-inventory limitation. Normal post-restore API/RQ M3 rerun,
current browser/report and downloads now pass. Complete native/live-RQ Omni and
interleaved state acceptance now pass at their recorded boundaries. No assigned
runtime gate remains pending; explicit unresolved findings are not converted to
safe/fixed behavior. See `final_qa_review.md` and
`operation_matrix.md`.

| Consumer | Current disposition / remaining gate |
| --- | --- |
| Post-fire ordinary source/artifact currentness and download | Implemented;712 affected tests and scoped reviews pass. Restarted M3/WEPP hard-link sequence and five result downloads pass; all218 CLI hashes stay equal and accepted M3 remains current. Actual climate change→visible stale→API rerun/current browser passes. Archive selected bytes/modes and explicit post-restore API/RQ M3 recovery pass; automatic restored currentness fails for attributed PF-R01 and remains disclosed. Interleaved60-call production-digest warm-read/coexistence check passes; means739.48/862.19ms are observations without a whole-state deadline (`runtime_interleaved_state_qa.md`). |
| NoDb disk payload/version pairing | Implemented; 155 focused +76 review-regression tests, stub gates and independent reviews pass. Actual copied owners hydrate through native C02, restarted M3/WEPP and direct/live queued Omni workflows. Interleaved and archive acceptance have separate retained scopes. |
| C10 controller header ID | Implemented after984023c18;12 tests,42.68 us mean actual header read, scoped reviews pass. Restarted served/rendered IDs match `2026-09-17T08:03:11Z` before/after browser reload with zero page errors (`runtime_browser_after_wepp.json`). |
| C01 PRISM/RAP main paths | Implemented after b8c63ab1e and dbec83d30; 46 tests, native Zarr compatibility, scoped reviews pass. Complete small native RAP owner/lock acceptance passes; wider-size acceptance is not claimed. |
| C01 indirect raster inputs | **Justified unresolved, unfixed:** accepted local VRT/directory native reads can change indirect sources without main-file signature drift. PRISM TIFFs are private new intermediates; direct VSI wrapper support is not claimed. `derived_indirect_closure_correctness_disposition.md` distinguishes confirmed native counterexamples from ordinary GTiff producers and records the needed read-set authority, compatibility and full-set cost decision. No format restriction or weakened finalizer. |
| C02 feature export dependency fingerprint | Implemented after90a8a3dc9;199 affected tests and scoped reviews pass. **Restarted shipped mixed-profile native acceptance passes:** real catalog, CSV/GPKG, GeoJSON/Parquet/NoDb/Unitizer; touch/equal-byte hits and changed rows/geometry/units match fresh exports;16 prior artifacts and all3916 named files remain unchanged. See `runtime_features_dtale_qa_acceptance.md`. Arbitrary indirect/native closure outside the demonstrated profiles remains justified unresolved per `features_omni_remaining_closure_qa.md`; no generic driver-safety claim. |
| C03 Landuse MOFE pair count cache | Implemented after ceb715c08/308f9edee: joint local raster proof, actual native .27/.09→.09/.27ha regression and generated .man preparation pass; legacy misses and failed-publication isolation pass. All46 measured budget gates and scoped reviews pass. Restarted ordinary WEPP management preparation finished (`runtime_m3_hardlink_acceptance.json`); MOFE-specific source-change evidence remains the scoped native suite. |
| C04 SBS summary cache | Implemented bounded8-entry native cache with verified proof and pre-admission/post-hit checks; native restored-time/mask/world/unknown-format controls and all46 budget gates pass. Restarted real SBS uploads/replay and complete direct/live-RQ Omni workflows pass (`runtime_profile_http_acceptance.json`, `runtime_omni_sbs_correctness_acceptance.md`). |
| C05 Geneva HRU geometry | Implemented in1556df345 after31f77bef1/21aacd74f; native content/legend/ABA controls, reviews and amended budgets pass. Restarted native/canonical archive roundtrip and actual failed-artifact browse/download pass (`runtime_archive_acceptance_3a8be19a8e1e.json`, `runtime_archive_helper_public_downloads.json`). This is bounded owner/archive acceptance, not complete Geneva Run All. |
| C06 Geneva auto-burn raster | Implemented in1556df345 after31f77bef1/21aacd74f; native pixel/bound/mask controls, reviews and amended budgets pass. Same restarted owner/archive evidence as C05 passes. Whole-HRU preparation reuse has a separate justified-unresolved row below. |
| C07 Omni pruning | **Justified unresolved:** held-receipt numerical stale mechanism confirmed, while ordinary supported delineation removes/refreshes completion authority and no missed ordinary producer is demonstrated. `features_omni_remaining_closure_qa.md` records the actual read set and minimum producer→consumer comparison. Completion authority is preserved; S01 SBS acceptance cannot close C07. |
| C08 hillslope water balance | Implemented in0f2826a25 after7d78e9810;93 report tests, native/performance/archive controls and reviews pass. Restarted HTML200 and provenance-bearing cached Parquet download200 with exact source SHA pass (`runtime_reports_after_wepp_complete.json`). CSV500 remains a **confirmed existing adapter defect**, independently attributed to baseline7d78e9810 in `runtime_watbal_csv_qa_disposition.md`; it is not counted as a pass. |
| C09 average annual landuse report | Implemented in0f2826a25 after7d78e9810/32c7bed70; selected content/aliases, portable context,93 affected tests and measured budgets pass. Restarted actual HTML and CSV both return200 (`runtime_reports_after_wepp_complete.json`). |
| C11 D-Tale data/GeoJSON | Implemented incf261f6ac afterfbac92404;22 tests/no skips, reviewed guarded generations and measured large-file limits pass. **Restarted authenticated public acceptance passes:**65 checks/28 HTTP requests, four actual browser phases with zero page errors, visible old-grid rejection, same logical ID/new schema+rows on relaunch, actual GeoJSON registration refresh/removal. Evidence: `runtime_features_dtale_qa_acceptance.md`. No response interception or internal-loader shortcut; no rendered map-pixel/snapshot claim. |
| Export output SHA helper | Implemented shared verified digest after dd5d09ca7; actual restored-time probe corrected, scoped correctness/security/QA passes. |
| Config-builder executable digest | Implemented shared verified digest; rapid-rewrite probe improved from452/1000 stale to0/1000 (671 same-version cases); scoped reviews pass. |
| Post-fire soil/SQLite identity | **Justified unresolved PF-R01:** seven earlier physical-only cases and actual archive restore cause false stale. `runtime_archive_restore_soil_qa_review.md` verifies all soil/prepared bytes plus SQLite main/WAL unchanged; only raw soil inventory tuples cause failure. Read-only polling cannot create new logical proof on a cache miss. Durable README documents explicit Run M3 recovery; no runtime guards or saved provenance are changed. |
| Post-fire CLI/parquet readiness | Implemented after166c8f79d;857 affected tests and scoped reviews pass. Revised budget checkpointf7c832864 passes actual4.85/6.14ms settled, zero CLI payload rereads; original miss retained. Restarted real climate production, M3 and full WEPP tree preserve currentness after218 unchanged CLI hard links. Actual changed-climate stale→rerun/current browser passes in `runtime_browser_climate_changed.json` and `runtime_browser_rerun_current.json`; soil restore behavior is separate PF-R01. |
| Omni same-name SBS re-upload | Implemented in de3a1eba0 after c28f81f59; direct and RQ consumed receipts, guarded copy/admission and accepted association checks. Independent reviews and45 original budgets pass. Full217-hillslope/46-year native sequence, changed generated management/soils/output, four-job RQ execution with exact numerical parity and three-job consumed skip pass (`runtime_omni_sbs_correctness_acceptance.md`). All3,916 original source files retain bytes; four explicitly reviewed operational metadata exceptions mean whole-tree physical immutability is not claimed. No HTTP batch-enqueue claim; separate from C07. |
| Profile recorder/replay repeated SBS upload | Implemented in7ad0ac609 aftereb2c33b2b; reviews and27 original budgets pass. Actual HTTP capture/promotion and preauthenticated Session replay pass with exact wire/server hashes (`runtime_profile_http_acceptance.json`). Canonical CLI requests still return401 while the command exits0 (`runtime_profile_canonical_cli.log`); authentication/exit reporting is an explicit separate limitation, not replay success. |
| B-F01 GL dashboard result generations | **Justified unresolved, confirmed defect:** actual controller/query mixes old year25 with new year76 (fresh year75). `browser_generation_unresolved_disposition.md` records the missing generation/refresh UX contract, current reload/new-tab recovery and remaining risk. Related graph/batch/schema/storm/viewer candidates remain separately unconfirmed. D-Tale's passed browser workflow does not waive this finding. |
| Roads wider source/native closure | **Justified unresolved beyond verified upload/parameter ingestion.** `remaining_inventory_disposition_qa.md` traces maintained DEM/network consumers and the required normal watershed-update→Roads-rerun comparison. No supported-path numerical failure is inferred from generic native capability. |
| AgFields wider Stage4/5 closure | **Justified unresolved beyond verified workflow/mapping receipt semantics.** `remaining_inventory_disposition_qa.md` requires an actual parent-input update through maintained producers/readiness/admission before changing cross-stage currentness. Completion markers and manifest-last publication remain authority. |
| Geneva whole-HRU preparation reuse | **Justified unresolved separately from C05/C06.** `remaining_inventory_disposition_qa.md` records cached summary early-return behavior and Run All's forced rebuild, plus the missing cached-versus-forced complete native comparison/UX decision. |
| Remaining broad hash/cache consumers | Finite inventories are `remaining_semantic_inventory.md` and `remaining_services_tools_browser_inventory.md`, with search scopes retained. `remaining_inventory_disposition_qa.md` distinguishes verified receipt paths, nondependencies and justified-unresolved families. This is finite inventory disposition, not exhaustive vendor-reader/browser safety. |

Final quiet Python suite: **8,924 passed,99 skipped**,1,192.22 seconds
(`final_full_suite_quiet.log`). Frontend **899 tests/112 suites pass** and lint
passes (`final_npm_test.log`, `final_npm_lint.log`). The earlier full-suite
wall-clock failure, earlier8,721-pass run, invalid fixtures, rejected designs,
original missed budgets and explicit ratified amendments remain retained.
`quality_performance_consolidation.md` preserves the measured boundaries and
observe-only complexity limitations. No new budget is inferred from concurrent
runtime timings.

Current checkpoints remain Geneva1556df345, profile7ad0ac609, archive7b4f22df9,
Omni de3a1eba0. S01 all45 original performance gates and profile all27 gates
pass; the16MiB first capture545.60/550ms has little mean margin. Archive QA is
accepted in `archive_directory_implementation_qa_review.md`. Five-module
stubtest and the refreshed146-edge RQ graph pass. Final assigned runtime results
are consumed in `final_qa_review.md`; the interleaved check covers395/512 entries,
with actual eviction established separately by component probes. The package
root owns overall closeout; this record does not convert justified-unresolved
findings into safe/fixed behavior.
