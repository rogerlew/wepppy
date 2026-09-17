# Current implementation disposition

Living execution record, 2026-09-17 UTC. Baseline inventories/probes remain
historical evidence. Scoped implementation approval is not package completion.
Reviewed implementation waves committed in `edff4db5a`. No development restart,
UI/RQ/WEPP canary or archive/restore acceptance has run; isolated live D-Tale
baselines have run on disposable inputs.

| Consumer | Current disposition / remaining gate |
| --- | --- |
| Post-fire ordinary source/artifact currentness and download | Implemented; 712 affected tests, scoped correctness/security/QA pass. Runtime, interleaved working-set and archive acceptance open. |
| NoDb disk payload/version pairing | Implemented; 155 focused + 76 review-regression tests, stub gates and independent reviews pass. Runtime open. |
| C10 controller header ID | Implemented after 984023c18; 12 tests, 42.68 us mean actual header read, scoped reviews pass. Served/rendered runtime alignment open. |
| C01 PRISM/RAP main paths | Implemented after b8c63ab1e and dbec83d30; 46 tests, native Zarr compatibility, scoped reviews pass. Complete native/locked acceptance open. |
| C01 indirect raster inputs | OPEN blocker: nested VRT flat list misses actual changing source; directory-backed Zarr GetFileList omits chunks; preserve valid local ZIP/VSI. No claimed closure. |
| C02 feature export dependency fingerprint | Implemented after90a8a3dc9: verified hashes, primary/companion publication checks, immutable prior artifacts and failed-work retention.199 affected tests and scoped reviews pass; full native dependency closure/runtime/archive remain open. |
| C03 Landuse MOFE pair count cache | OPEN actual native management areas remain .27/.09ha after pixels require .09/.27ha; closure/compatible receipt needed. |
| C04 SBS summary cache | OPEN native stale class result. Removing cache costs ~0.489s per representative call; reviewed content/closure design needed. |
| C05 Geneva HRU geometry | OPEN actual native HRU geometry/legend stale, including external .msk with unchanged main TIFF; content/closure receipt needed. |
| C06 Geneva auto-burn raster | OPEN actual raster_stacker output stale after source pixels, alternate older path and bound-grid transform changes. |
| C07 Omni pruning | OPEN risk, ordinary writer/completion sequencing needs final supported-workflow disposition. |
| C08 hillslope water balance | Implemented in `0f2826a25` after `7d78e9810`: embedded content/mapping provenance and compatible historical reads.87 report tests, actual native/performance/archive checks pass; live runtime open. |
| C09 average annual landuse report | Implemented in `0f2826a25` after `7d78e9810`/`32c7bed70`: selected content/aliases, coherent publication and portable report-local context.87 affected tests and measured budgets pass; live runtime open. |
| C11 D-Tale data/GeoJSON | Implemented in `cf261f6ac` after `fbac92404`: content+selected-target identity, guarded lazy generations, visible errors and optional-map cleanup.22tests/no skips, stub/broad gates and scoped reviews pass; actual restarted browser/map and archive acceptance open. |
| Export output SHA helper | Implemented shared verified digest after dd5d09ca7; actual restored-time probe corrected, scoped correctness/security/QA passes. |
| Config-builder executable digest | Implemented shared verified digest; rapid-rewrite probe improved from452/1000 stale to0/1000 (671 same-version cases); scoped reviews pass. |
| Post-fire soil/SQLite identity | OPEN real SQLite link/touch/replace/VACUUM/checkpoint/unrelated-table changes falsely stale logical consumed rows; strict transaction guard remains necessary. |
| Post-fire CLI/parquet readiness | OPEN actual export: CLI touch falsely unready; changed restored-time precipitation8 remains ready with old parquet4. Durable lineage needed. |
| Omni same-name SBS re-upload | OPEN supported upload/parser path skips rerun after changed raster (S01 High); separate from C07 receipt ordering. |
| Profile recorder/replay repeated SBS upload | OPEN latest seed3 but reconstructed multipart remains first1 (S02 Medium); event identity needed. |
| Remaining broad hash/cache consumers | OPEN semantic inventory; raw search counts are not closure evidence. |

Full Python sanity at the earlier implementation state: 8,721 passed, 103
skipped, 1,126.84 seconds (`full_python_sanity.log`). Newer bounded edits have
focused tests; rerun final broad sanity after final code changes. Original
failures, invalid-fixture attempts and rejected design probes remain retained.
