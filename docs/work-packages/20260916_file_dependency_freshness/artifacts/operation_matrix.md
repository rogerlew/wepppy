# Required operation and state matrix

Acceptance expectations for content-dependent outputs; classify other consumers
by contract before applying them. The runtime evidence below is finite and
boundary-specific. Current implementation dispositions and open gates are in
[implementation_disposition.md](implementation_disposition.md).

| Operation | Content-freshness expectation | Separate obligation |
| --- | --- | --- |
| Add/remove another hard link | Remain current if content/provenance unchanged | Inode/link metadata may change; access and race guards still apply |
| Create/remove a symlink pointing at the input | Target remains current | Do not weaken symlink rejection or containment rules |
| Chmod/chown or metadata-only touch | Content alone remains current | Access loss/ownership policy can independently make workflow unavailable |
| Same-byte atomic replacement or archive restore | Revalidate identity; remain content-current where contracted | Verify path/provenance and old/new schema rules |
| Changed bytes with changed size/time | Stale/rebuild as contracted | Never serve old output as current |
| Equal-size changed bytes with restored mtime | Still detect content change | Stat-only cache hit must not silently mask it |
| Repoint input symlink or path to different content | Reject or invalidate under existing policy | Content equality cannot override unauthorized path semantics |
| Change required sidecar/mask/metadata units | Invalidate affected output | Inventory dependencies beyond the main filename |
| SQLite commit, WAL change, checkpoint or backup | Evaluate coherent logical/byte snapshot per contract | No partial main/WAL view or writing to live DB just to inspect |
| Concurrent mutation during hash/read/publication | Retry boundedly or fail explicitly | No inconsistent accepted snapshot; preserve previous acceptance |
| Delete/unreadable/truncated required input | Explicit unavailable/stale outcome | No silent fallback or digest of empty substitute |
| Change model settings/source identity/tool version | Invalidate where contracted | Equal file bytes do not imply equal scientific meaning |
| Byte changes with equal parsed values | Consumer-specific decision | No blanket semantic equivalence policy |

Cover never-used optional state, present-empty state, populated state, supported
legacy signatures, missing required state and malformed/hostile records.
Keep tests on real filesystem operations for every changed boundary; mock-only
stat tuples do not prove the hard-link/race contract. Use the actual container
uid/gid, mounts and filesystem for live acceptance. Record NFS/local differences
where the supported workflow crosses them; do not assume timestamp granularity.

Measure cold hashing and repeated warm status reads using representative climate,
large raster and SQLite artifacts before choosing optimization. Record bytes
read, cache hit/revalidation behavior and elapsed latency. Set explicit per-path
budgets from the measured baseline before implementation; do not invent a global
latency threshold. Verify cached hashes against replacement and restored-mtime
cases under the actual producer/concurrency contract.

## Retained operation evidence after restart

The service image, ordinary UID/GID/groups and mounted paths were verified in
`runtime_restart_verification.json`. Runtime timings overlapped other canaries
and do not amend the independently measured performance gates. “Focused” below
means the retained native/filesystem review tests, not a public live request.

| Operation or valid state | Actual evidence and disposition | Remaining limit |
| --- | --- | --- |
| Add/remove hard link, unchanged scientific bytes | **Public/native runtime pass:** all218 CLI ctimes/link counts changed during the finished WEPP job tree; all hashes stayed equal and the accepted M3 attempt stayed current. Browser reload agrees (`runtime_m3_hardlink_acceptance.json`, `runtime_browser_after_wepp.json`). The NFS helper also passes link add/remove. | Single development host/service on `/wc1`; no cross-host NFS coherence guarantee. |
| Metadata-only touch and readable chmod | **Runtime pass:** C02 both shipped profiles and C11 table touch preserve results/ID or artifact; actual NFS helper readable chmod/touch preserves digest (`runtime_features_dtale_qa_acceptance.md`, `runtime_nfs_digest.json`). | Real chown/access-loss policy is established by focused ownership/access tests, not this public canary. |
| Identical-byte replacement | **Runtime pass:** both shipped Features profiles reuse exact prior artifacts after atomic replacement of selected regular dependencies; public D-Tale reuses rows/logical ID after same-byte rewrite. | Does not prove equal parsed values with unequal bytes should reuse. |
| Same-name SBS replacement and consumed-source reuse | **Direct/live RQ native pass:** actual low/high217-hillslope/46-year runs change numerical management/soil/output; consumed sources skip. Four-job queued execution matches five direct-generation Parquets exactly; three-job queued skip preserves numerical hashes/versions (`runtime_omni_sbs_correctness_acceptance.md`). | Canonical tracked developer queue admission, not HTTP batch enqueue. All3,916 named source bytes unchanged; four reviewed operational metadata exceptions are disclosed rather than called whole-tree physical immutability. Separate from C07 pruning. |
| Archive/restore and private/empty attempts | **Preservation plus explicit recovery passes:** Geneva native/helper controls and actual archive/restore API/RQ preserve545 selected artifacts/84 directory modes. Public failed-work downloads match. Restored M3 is stale solely from known soil inventory metadata; normal API/RQ Run M3 restores current/browser/report/download behavior (`runtime_archive_restore_soil_qa_review.md`). | Automatic post-restore M3 currentness failed and remains PF-R01; successful explicit recovery does not waive it. Profile repository archival is a separate boundary. |
| Changed bytes, ordinary size change | **Native/runtime pass:** real C02 Parquet/geometry changes rebuild and match fresh exports; actual Unitizer changes alter converted values. C11 browser rejects the old lazy generation and relaunches correct rows. Actual climate production change yields stale M3, and normal API rerun yields current state/browser (`runtime_postfire_climate_changed.json`, `runtime_postfire_rerun_current.json`). | Limited to the recorded supported scientific windows and maintained producers. |
| Equal-size changed bytes with restored mtime | **Public runtime pass:** actual Parquet schema/rows and GeoJSON property registration update in C11; old grid returns visible `changed_source`, then the shared logical ID is rebuilt (`dtale_public_runtime_initial.json`, `dtale_public_browser_revision3.json`). NFS helper reports0 mismatches across1000 restored-time rewrites. | The C02 numeric mutation changes size by1 byte and is not used as this row's proof. Native raster/control tests supply their own equal-size evidence. |
| Symlink creation/repointing and logical path selection | **Focused boundary evidence:** ordinary digest, D-Tale selected-target, strict post-fire and raster/CLI authority tests retain their existing allow/deny policies and before/after guards. | No new generic public symlink workflow is asserted; byte equality never waives path authority. |
| Required companions, mapping, profile and units | **Focused/native plus selected runtime evidence:** raster mask/world/config, report translator/catalog and Geneva bound/legend controls pass. Real C02 geometry/Unitizer and public C11 overlay changes pass. | C01 indirect native membership and broader native/completion families remain explicitly unresolved. |
| Missing optional input | **Public runtime pass:** removing the C11 subcatchment overlay drops its registration while the channel overlay and table remain usable. | This optional-map contract must not become a required-input fallback. |
| Missing/unreadable/truncated required state, malformed proof, denied output | **Focused native/filesystem pass** in scoped NoDb, post-fire, CLI, reports, raster, Geneva, profile, and Omni reviews, preserving failure status and prior artifacts. | No universal live permission matrix or silent historical fallback is inferred. |
| Concurrent mutation during read/native work/publication | **Focused deterministic native pass:** same-opened-fd replacement, publication barriers, native A→B→A and temporary companion/config guards are retained in the boundary reviews. | Bounded observation under the producer contract; arbitrary-writer snapshot isolation is not claimed. |
| SQLite commit/WAL/checkpoint/backup and soil metadata restore | **Justified unresolved PF-R01:** physical-only changes cause false stale. Actual archive restore independently reproduces it with all7 manifest-bound soil hashes and accepted main/WAL bytes unchanged; only raw soil inventory comparisons fail (`runtime_archive_restore_soil_qa_review.md`). Explicit rerun recovery passes. | No SQLite connection/checkpoint or old-provenance rewrite is introduced for polling; generic digest/archive-byte passes do not close logical currentness. |
| Settings/source identity/tool version and empty/legacy states | **Focused contract tests pass** for implemented readers/producers; C02 real Unitizer changes, legacy report/CLI controls and actual changed-climate stale→rerun/current browser pass. | These semantics do not certify unrelated caches. |
| Interleaved independent working sets | **Measured warm-read/coexistence pass:**30 local full-state calls per copy add12,840 production-digest hits and0 misses/uncached payloads;395 of512 entries used (`runtime_interleaved_state_qa.md`). Initial observed states are recovered root current and copied Omni parent stale. | Means739.48/862.19ms are observations with no agreed whole-state deadline; not HTTP timings or zero total filesystem reads. This run is below capacity; actual eviction is established by separate component probes. No cross-host claim. |
| Real report presentation and download | **Public pass at stated paths:** C09 HTML/CSV200; C08 HTML200 and cached Parquet200 with exact source SHA; five M3 artifacts200 (`runtime_reports_after_wepp_complete.json`). | C08 CSV500 is an independently confirmed existing adapter defect. Keep it failed and use documented HTML/Parquet recovery; do not count the entire report format matrix passed. |

## Explicit finite unresolved dispositions

- **C01 indirect inputs:** confirmed native VRT/directory/archive-child
  counterexamples remain unfixed; the complete small40-input RAP/held-lock pass
  covers ordinary copied GTiffs. See
  `derived_indirect_closure_correctness_disposition.md`.
- **C02 beyond demonstrated shipped profiles:** real mixed-profile runtime now
  passes; generic reader capability still does not prove every catalog/native
  dependency is complete. See `runtime_features_dtale_qa_acceptance.md` and
  `features_omni_remaining_closure_qa.md`.
- **C07 pruning:** a deliberately fixed completion receipt reproduces numerical
  staleness, but a missed ordinary maintained producer is not demonstrated.
  Preserve completion authority pending the actual producer/consumer experiment
  in `features_omni_remaining_closure_qa.md`.
- **Roads/AgFields/Geneva whole preparation:** source traces establish specific
  valid receipt/rebuild paths, not all cross-stage native closure.
  `remaining_inventory_disposition_qa.md` records each narrower safe boundary,
  unresolved workflow and minimum follow-up.
- **Browser families:** B-F01 is a confirmed active GL mixed-generation defect;
  related graph/batch/schema/storm/viewer candidates remain unconfirmed.
  `browser_generation_unresolved_disposition.md` retains the missing UX decision,
  new-tab/reload recovery and lack of snapshot guarantee. Public D-Tale acceptance
  closes only its own workflow.

Changed-climate/M3 rerun, actual archive preservation plus explicit M3 recovery,
interleaved multi-project state and complete direct/live-RQ Omni now have actual
retained results at their stated scope. Failed automatic restored currentness,
existing CSV/CLI errors and finite unresolved findings remain disclosed. Final
QA consumes those results in `final_qa_review.md`; the package root owns overall
closeout. No original failed budget is relabeled passed.
