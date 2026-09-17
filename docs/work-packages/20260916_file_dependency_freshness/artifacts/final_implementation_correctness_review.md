# Implementation correctness consolidation through de3a1eba0

**Final scoped correctness PASS for the reviewed implementations and completed
runtime workflows, including the final interleaved-state observation.**
Reviewer: `freshness_correctness`, 2026-09-17. No unresolved medium/high
changed-code correctness finding remains in the reviewed implementations below.
This consolidates independent source reviews, the actual direct/live-RQ Omni
execution and other retained native/HTTP/browser/archive evidence. It does not
describe every original freshness defect as fixed or claim production deployment.

## Remaining findings and explicit limits

The active ExecPlan's Decision Log adopts the following bounded unresolved
dispositions. Those decisions supersede earlier blanket blocker/OPEN wording in
historical discovery records; they do not erase the observations or grant a
broader correctness guarantee.

- **PF-R01, confirmed medium false-stale limitation:** accepted M3 state can
  become stale after seven SQLite physical/metadata changes that preserve the
  consumed logical data. `production.sources` embeds `production_soils.inventory`
  into selected soil inputs, and `_source_snapshots_current` compares that state.
  Read-only polling cannot produce the required new visible logical snapshot on
  an unknown physical generation. A bounded physical-key cache does not resolve
  misses, restart or eviction. Strict soil execution/finalizer guards remain
  unchanged. Actual archive restore additionally reproduces false stale with
  unchanged soil/prepared and SQLite bytes; normal explicit API/RQ Run M3
  recovery passes. Byte/mode restoration passes; automatic restored currentness
  remains a failed, unfixed PF-R01 outcome. See
  [correctness disposition](soil_logical_currentness_correctness_proposal.md) and
  [independent restore attribution/recovery](runtime_archive_restore_soil_qa_review.md).
- **C01, confirmed indirect native-input gap:** `_derived_build.file_signature`
  verifies regular main files; its explicit directory branch preserves native
  compatibility without proving member bytes. RAP accepts local VRT/directory
  inputs whose indirect contents can change without that main identity changing.
  The bounded raster cache observer cannot repair an outside-lock numerical
  build by merely bypassing reuse. The actual small complete RAP set passes its
  numerical/lock check, but that is not general dependency closure. See
  [native evidence and disposition](derived_indirect_closure_correctness_disposition.md).
- **B-F01, confirmed medium active-view defect:** the maintained GL dashboard's
  yearly result cache can retain year2000 value25 while newly loading year2001
  value76; a fresh manager reads current year2000 value75. No browser generation
  fix shipped. Reopening guidance is a workaround, not an immutable-snapshot or
  automatic-refresh guarantee. Related browser families remain separately
  classified candidates. See [explicit disposition](browser_generation_unresolved_disposition.md).
- **C07, confirmed mechanism with unverified ordinary producer failure:**
  actual native pruning retains5 cells instead of the freshly computed1 when
  its completion receipt is deliberately held fixed. Normal subcatchment
  builders invalidate/stamp completion, so that probe does not prove an ordinary
  writer omits the receipt. Missing receipts, shared sources and restore remain
  unverified. S01 does not change this completion boundary. See
  [C02/C07 assessment](features_omni_remaining_closure_qa.md).
- **C02 and wider native/cross-stage boundaries:** Features' selected main-file
  and artifact-binding correction is verified at its stated scope. Its shipped
  mixed GeoJSON/Parquet/NoDb/Unitizer native-profile acceptance now passes in
  [the restarted runtime review](runtime_features_dtale_qa_acceptance.md).
  Initial/final comparison is not arbitrary in-operation
  snapshot isolation. Roads upstream closure, AgFields wider cross-stage/native
  closure, Geneva whole-preparation `force_rebuild=False`, contrast/unavailable
  sources and other repeated-upload families retain the exact justified
  unresolved classifications and next evidence in
  [remaining-family disposition](remaining_inventory_disposition_qa.md).

These limitations must remain visible in final user/operator reporting. They are
not changed-code findings being silently waived. Finite maintained-source
inventories establish the enumerated coverage, not proof over arbitrary native
drivers, vendored readers or untraced scientific owners.

## Reviewed implementations and compatibility

| Scope and concrete owner | Correctness/compatibility conclusion | Retained review and meaningful evidence |
| --- | --- | --- |
| Postfire `production.py` and `rq_engine/postfire_debris_flow_routes.py` | Ordinary accepted-source/artifact equality uses bytes while strict execution/publication identity remains separate. Legacy strict-stat behavior, no-follow authority and expected409 translation remain explicit. Cache admission fixes actual same-version stale reuse; it does not promise immunity to arbitrary concurrent writers. | [First-wave follow-up](first_wave_correctness_followup.md), [point-in-time clarification](nodb_implementation_correctness_review.md);712 affected tests. Original collisions, mixed-read probes and failed timestamp assumption are retained. |
| NoDb `base.py`, `_read_retry.py` | Both disk loaders carry text and descriptor metadata together. An opened complete old atomic generation remains valid with its own version; it cannot be tagged with a later pathname version. Subsequent stale writes reject through the existing lock/write contract. | [Implementation review](nodb_implementation_correctness_review.md);155 focused and76 review-regression passes, including real replacement between descriptor stats and actual stale-dump rejection. |
| Shared `all_your_base/file_digest.py`; output discovery and config-builder registry | Bounded512-entry digest/observation caches preserve verified opening and uncached admission. Re-observation cannot resurrect an older digest. Caller expectation checks, executable access/error rules and permitted ordinary symlinks remain intact. | [Implementation review](shared_digest_implementation_correctness.md); actual registry452/1000 stale baseline becomes0/1000, with671 equal-version observations;151 focused tests and follow-up eviction/caller-error cases. |
| C10 `weppcloud/utils/assets.py` | Only the metadata-result cache is removed. The existing80-line parser, unknown/error behavior and one-request rendered/asset identity remain unchanged. | [Implementation review](bundle_header_implementation_correctness_review.md);12 tests and actual bundle read42.68µs mean. Restarted browser/reload verifies matching served/rendered ID2026-09-17T08:03:11Z with zero page errors in `runtime_browser_after_wepp.json`. |
| C01 `nodb/_derived_build.py` | Regular-file SHA is appended to the existing transaction tuple; existing mtime conflicts, publication and lock ownership remain. Directory-backed Zarr compatibility is restored with explicit absent digest, not a failed-read fallback. | [Main-path review](derived_main_implementation_correctness.md);46 tests and native Zarr regression. [Complete small RAP evidence](derived_indirect_closure_correctness_disposition.md):40files/234native calls,1,638 equal rows,53.3ms finalizer hashes and3.968s held lock. |
| C02 `features_export/dependency_tracker.py`, `service.py` | Selected request/catalog/files/units are rechecked before admission. Companion conversion requires verified producer provenance and its own format-correct manifest. Historical publication derives identity from the artifact binding. Prior artifacts and failed native candidates remain available. | [Implementation review](features_implementation_correctness_review.md);199 affected tests, actual GeoPackage/OpenFileGDB conversion and failed packaging retention. [Restarted shipped mixed-profile acceptance](runtime_features_dtale_qa_acceptance.md) passes real native row/geometry/unit controls and retains16 unchanged prior artifacts. |
| C03/C04 `all_your_base/raster_freshness.py`, `core/landuse.py`, `baer/sbs_map.py` | Bounded eligible local GTiff/AAIGrid proofs include explicit companions; inspection authority is restricted without changing numerical native options. Unproven formats use the original native operation uncached. Same-acquisition physical/config guards span native work separately from content cache identity; failed pair counts cannot mutate prior management summaries. | [Implementation review](raster_implementation_correctness_review.md);18 independent cases across retained runs, actual old/new/old native rejection and generated management preparation; all46 measured consumer gates pass under [QA scope](raster_implementation_qa_review.md). |
| C05/C06 Geneva `collaborators/_cache_freshness.py`, geometry/alignment services | Geometry binds legend/raster inputs; alignment binds source plus the effective retained bound profile. Joint guard/digest/membership validation remains complete through publication and native-error paths. Clean targets publish atomic payload/proof; existing auxiliary-bearing targets deliberately retain the weaker original native overwrite with no reusable proof. | [Implementation review](geneva_implementation_correctness_review.md);15 independent native probes;135 combined Geneva/profile/archive tests, not a Geneva-only count. [QA](geneva_implementation_qa_review.md) records all16 fresh amended gates after21aacd74f; original failed budgets remain failed. |
| C08/C09 `wepp/reports/_cache_freshness.py`, water-balance/landuse reports | Rows and proof share one committed Parquet generation. Current, built and historical-unverified are distinct. Partial history cannot conceal malformed/denied surviving inputs. Report-local relocation binds observations and actual SQL to the same selected project. C09's inode-write requirement, C08's original native replacement behavior and sidecar-specific write/mode rules are preserved. | [Correctness review](reports_implementation_correctness_review.md), [authorization follow-up](reports_write_authorization_security_review.md);93 affected tests and actual native/DuckDB, overlap, relocation, archive and failure-preservation controls. |
| C11 `webservices/dtale/dtale.py` | Rows/overlays use content and selected resolved paths. Lazy operations validate their loaded generation and return the upstream-visible error shape; eager failures clean partial state. Shared overlay identifiers/defaults are refreshed coherently. Stable-ID explicit relaunch does not promise per-tab snapshots or automatic reload. | [Implementation review](dtale_implementation_correctness_review.md);22 affected tests and actual large-Parquet paging evidence. [Restarted public acceptance](runtime_features_dtale_qa_acceptance.md) passes65 checks/28 HTTP requests and four browser phases, with visible guidance and actual overlay registration refresh/removal. No rendered map-pixel claim. |
| PF-R02 `climates/cli_parquet.py`, climate exporter, interchange `_utils.py`, postfire readiness | Both producers parse retained snapshots and publish rows with embedded lineage. Fresh owner selection, same-generation footer observation and `content=False` readiness remain checked. Legacy calendar/history stays readable; new execution requires producer proof. Target access, confidential attempts and postcommit status handling retain their explicit contracts. | [Implementation review](cli_lineage_implementation_correctness_review.md);857 affected tests and actual producer/admission/archive probes. Same-call directory reuse preserves authority; final10/50ms readiness and unchanged export budgets pass after explicitf7c832864 amendment. |
| S02 `profile_recorder/sbs_seed.py`, `assembler.py`, `playback.py` | Marked response events bind immutable per-event payloads to the actual replay pair. Verified bytes survive through multipart encoding. Failed entries cannot fall back to prior canonical bytes; unmarked legacy events retain historical behavior. Trailing-slash UI dispatch and optional lower-priority discovery are corrected. | [Implementation review](profile_sbs_implementation_correctness_review.md);11 independent paired/multipart/failed-duplicate controls. [QA](profile_sbs_implementation_qa_review.md) records27 actual component gates, including complete configured first capture;16MiB case545.60/550ms has narrow measured headroom. |
| A-S01 `rq/project_rq_archive.py` | Explicit UNIX directory metadata is validated before cleanup, staged restrictively before payload and finalized deepest-first, including0000. Root modes, legacy missing metadata, existing file behavior and original restore failure semantics remain explicit. | [Correctness endorsement](archive_directory_implementation_correctness_review.md);9 real security/ZIP/lifecycle probes and30 repository passes/10 deselections. No atomic restore or arbitrary ACL guarantee is added. |
| S01 `omni_sbs_freshness.py`, direct orchestration, clone/mode services and `rq/omni_rq.py` | Main-byte receipts pass through existing direct/RQ signatures. Reset invalidation and success/skip admission refresh durable state under the existing lock. Captured associations cannot be resurrected after invalidation; runtime logging survives refresh. Same-file copying rejects before truncation; complete child guards and observed replacement-upload preservation remain. Non-SBS semantics and queue edges stay unchanged. | [Correctness review](omni_sbs_implementation_correctness_review.md);61 affected tests,10 independent flow controls across retained phases and11 security controls. [QA](omni_sbs_implementation_qa_review.md) records all45 original component gates. [Actual runtime PASS](runtime_omni_sbs_correctness_acceptance.md): full46-year direct generations/skips, live four-job execution/three-job skip and exact five-table numerical parity. |

Test counts above overlap across suites and are not additive. The linked reviews
retain individual resolved findings, exact before/after evidence, fixture errors
and unsupported claims. This consolidation does not replace those records.

## Source binding and final review checks

[Source bindings](final_implementation_correctness_source_bindings.json) compare
34 concrete production files with commit `de3a1eba0`: every working file matches
its committed bytes. The scoped archive, Geneva, profile and Omni final source
hashes also match their reviewed implementations. There are no production/test
edits in this consolidation.

One earlier raster review lists SHA7e218d1e… while the committed helper has
SHAb5e1602a…. Independent readback reproduced the old SHA by removing only the
added `RasterDependencyObservation.check_unchanged` method and its separating
newline. That method is the same-call guard used by the reviewed Geneva
refinement; it does not change C03/C04 identity/admission. It checks recorded
resolved files, companion-parent versions and effective configuration. Geneva
surrounds the complete member digest/membership pass with all observations'
guards. This explains the source-binding difference rather than silently
treating the older hash as the final file.

The separate hash loops intentionally retain different authority/error/identity
contracts. No generic retry, digest fallback, blanket timestamp removal, new
service or format restriction is justified merely to make them uniform.
Stat fields remain valid for coherent-read guards, NoDb atomic-writer versions,
strict transaction checks, completion ordering, TTLs and display. A digest's
presence alone does not prove complete source selection or atomic publication.

## Current runtime and validation disposition

[The final quiet Python suite](final_full_suite_quiet.log) passed8,924 tests/99
skips in1,192.22seconds; [frontend tests](final_npm_test.log) passed899 tests/112
suites and [lint](final_npm_lint.log) passed. Root records passing
stub completeness, five stub modules,146-edge RQ graph and changed
broad-exception gates. The earlier full-suite attempt's wall-clock failure,
isolated rerun, earlier8,721-pass source state, initial harness errors and
original missed budgets remain historical evidence. None is relabeled as a
passing attempt, and concurrent runtime durations establish no new budget.

`runtime_restart_verification.json` binds all16 recreated development services
to source`de3a1eba0` and image`00a3e43a88a5...`, with preserved ordinary
UID1000/GID993/groups, mounts and umask. The completed operation records establish:

- Actual climate API/RQ production, M3 and the18-job WEPP pipeline finish.
  All218 CLI files retain identical bytes through hard-link metadata changes while accepted
  M3 remains current in API/browser. A supported climate change makes M3 visibly
  stale; normal rerun publishes a new current result. The initial2019–2021
  scientific window has explicitly partial long-return-period coverage.
- Restarted served/rendered bundle identities match on browser reload. Ordinary
  cross-process NoDb updates and the actual NFS digest controls pass at their
  measured scope; they do not prove arbitrary acquisition races or cross-host
  NFS coherence.
- Shipped mixed native Features profiles and authenticated public D-Tale
  rows/schema/overlay/browser controls pass. The stated driver, profile,
  registration and explicit-relaunch boundaries remain; no arbitrary native
  closure or rendered map-pixel guarantee is inferred.
- Two full46-year direct Omni generations and both consumed-source skips pass.
  A live four-job dispatcher/native-worker/compile/finalize tree and three-job
  skip pass. Five actual tables match same-input direct/RQ values and dtypes
  exactly, while changed severity changes real management/soil parameters and
  six watershed values. All3,916 named source files retain original bytes.
  The initial queued preflight correctly caught four operational metadata
  changes. Its retained failure and independently reviewed, opt-in exception
  preserve original bytes/lengths/modes, strict guards on all other files and
  full final hashing; whole-tree physical immutability is explicitly false.

See [runtime operation evidence](runtime_acceptance.md),
[Features/D-Tale QA](runtime_features_dtale_qa_acceptance.md),
[Omni correctness acceptance](runtime_omni_sbs_correctness_acceptance.md) and
[source operational-drift disposition](runtime_source_operational_drift_security_disposition.md).
Detailed records that predate later completion remain chronological evidence;
the current dispositions here supersede their earlier pending-gate wording.

### Failed outcomes retained alongside scoped passes

**PF-R01/archive:** live archive and restore API/RQ jobs finish and preserve all
545 selected file bytes/modes and84 directory modes. Automatic restored M3
currentness fails despite identical soil/prepared sources and SQLite main/WAL/
SHM archive bytes; independent controls isolate the raw soil physical inventory.
Normal explicit API/RQ Run M3 recovery publishes a new current attempt, verified
by browser/reload, actual report-page/query and five downloads. The separate
bounded native Geneva/archive operation preserves accepted and failed-attempt
artifacts, private modes and authorized live browse/downloads. These are passes
for preservation, observability and explicit recovery. They do not repair or
retroactively pass automatic restored currentness. See
[restore attribution/recovery](runtime_archive_restore_soil_qa_review.md) and
[Geneva/archive scope](runtime_archive_security_review.md).

**S02 canonical CLI:** actual `wctl run-test-profile` uploads return401 while the
CLI exits0 and reports success. This confirmed existing authentication/result-
reporting defect remains unfixed; the canonical workflow is not passed. Actual
HTTP capture/promotion and the existing preauthenticated `PlaybackSession`
pass distinct event seed→multipart→server hash checks without an auth change.
That accepted S02 boundary does not substitute for canonical client success.
Credential-safe evidence and the separate cookie-output hazard remain in
[runtime security disposition](runtime_profile_security_review.md) and its
linked durable operator guidance.

**C08 CSV:** the offered water-balance CSV route returns500 because its adapter
reaches unimplemented `ReportBase.__iter__`. Actual current traceback plus
source comparison with checkpoint7d78e9810 establish the preexisting method-
dispatch defect; no baseline HTTP replay is claimed. C08 HTML and provenance-
bearing cached-Parquet download pass, as do C09 HTML/CSV and M3 downloads.
The CSV500 remains failed in the overall HTTP record. See
[independent disposition](runtime_watbal_csv_qa_disposition.md) and the reports
README's specific HTML/Parquet workaround; a separate iterator/unit-aware CSV
adapter is needed to close that workflow.

The final [interleaved-state observation](runtime_interleaved_state.json) and
[execution log](runtime_interleaved_state.log) pass the stated cache-reuse
assertions:30 alternating observations per independent project,395 occupied
entries within the512 bound,12,840 additional hits, zero new cache misses and
zero instrumented direct uncached digest payloads. Complete request means are
739.48ms and862.19ms; these are observations, not a newly accepted whole-state
latency budget. The initially recorded states are current and stale respectively.
The harness does not count all filesystem reads or establish cross-host cache
coherence; this is one service process on the same NFS geography.

These known failures and the finite-inventory limitations above remain explicit
accepted unresolved dispositions, not silent safety claims or changed-code
findings waived by broad test counts. All assigned runtime evidence has been
reviewed; no additional execution is outstanding for this scoped correctness
review. Root owns final package disposition and commit, with these limitations
preserved in the durable operator guidance and final handoff.
