# File dependency freshness tracker

**Phase:** Closed. **Updated:** 2026-09-17 UTC.
**Security impact:** High; dedicated security and correctness reviews required
at execution checkpoints. All implemented checkpoints and scoped reviews pass.

## Completed

- [x] Record owner's scaffold request and incident evidence.
- [x] Initial seed scan across NoDb, reports, runtime paths, RQ and services.
- [x] Define content/metadata/identity distinctions and operation/state matrix.
- [x] Scaffold phased ExecPlan with explicit rebuild/restart/end-to-end gates.

## Ready for execution

- [x] M1 seed inventory reviews and deterministic hard-link/SBS/NoDb baseline probes.
- [x] M1 finite consumer tracing and explicit dispositions.
- [x] M2: canonical contracts, compatibility/performance decisions, reviews and checkpoint.
- [x] M3: bounded post-fire fix, then confirmed consumer groups.
- [x] M4: full applicable gates, security/correctness reviews and benchmarks.
- [x] M5: rebuilt/restarted development stack, actual UI/RQ/WEPP and archive tests.
- [x] M6: all dispositions, durable docs and implementation closeout.

## Decisions and risks

Owner authorized execution after the original scaffold. All implementation waves
are committed and development services rebuilt/recreated; actual disposable
model/UI/API acceptance is complete within the explicit dispositions. Production is not deployed.
Broad discovery is required;
mechanical removal of ctime is rejected because race/integrity checks may need it.
A stat-keyed hash cache can still hide changes; audit the cache and consumer,
not just whether a hash appears in a manifest. Avoid repeated large-file hashing
on report polls. Old signatures without hashes need explicit compatible handling.

No temporary bypasses, new infrastructure or cache clears are planned. Execution proceeds milestone by milestone with existing authority,
subject to the repository contract checkpoint and operational boundaries.

## Evidence and next action

[Seed inventory](artifacts/seed_inventory.md), [operation matrix](artifacts/operation_matrix.md),
[ExecPlan](prompts/completed/file_dependency_freshness_execplan.md).
Final Omni direct/live-RQ acceptance and two-project cache observation pass.
Implementation and final independent reviews are complete. Runtime failures and bounded recoveries remain explicit in
[development acceptance](artifacts/runtime_acceptance.md).

## Historical execution evidence

The following checkpoints retain their then-current status; final status above
and the closing entry supersede historical pending statements.

Baseline `adb4f9b004459fc578460a95f30ac01ae1421f36`; source search scope,
independent inventories and probes are under artifacts/. Ordinary post-fire
file content is the first reviewed implementation wave. NoDb hydration race,
report/raster caches, soil SQLite metadata and CLI/parquet readiness remain
explicit open findings. Do not mark the package complete after one wave.

First-wave contract ancestor: `43317704f`. Independent correctness and security
checkpoint reviews passed before runtime edits. M3 first-wave implementation
started after the retained failing artifact regression.

## Current execution checkpoint

- First-wave contract ancestors: `43317704f`, cache-admission refinement `0fe02dc0f`.
- Post-fire affected suites: 712 passed (`postfire_affected_suite.log`).
- Rapid rewrite probe after admission guard: 1,000 iterations per filesystem,
  zero stale cached hashes; 933 identical-version cases on overlayfs, 33 on the
  repository filesystem, none observed on NFS. No sleeps/mocked stat values.
- NoDb contract ancestor: `4e000950a`; descriptor-bound hydration implemented.
  Focused suite: 155 passed; stubtest and test-stub checks pass. Independent
  correctness/security reviews find no blocking code defect. Review regression
  refinements cover replacement between fstats and subsequent stale-write rejection.
- Full Python sanity at the earlier implementation state passed; reviewed runtime
  waves are committed in `edff4db5a`. Final-state validation remains open.
- Exhaustive inventory and all other confirmed findings remain open. Development
  rebuild/restart, UI/RQ/WEPP and canonical archive/restore have not run.

## Additional checkpoint progress

- C10 header checkpoint ancestor `984023c18`; metadata-result cache removed.
  Twelve tests pass, including second Flask context freshness; 1,000 actual
  bundle reads average 42.68 microseconds. Scoped correctness/QA reviews pass.
- All three earlier implementation QA findings closed: 76 NoDb regression tests
  and 35 download-route tests pass. Runtime acceptance is still pending.
- C01 actual PRISM/RAP finalizers publish after restored-time main-file rewrites
  in retained baseline probes. Main-file byte verification checkpoint is under
  review; recursive raster closure remains a separate package blocker.
- Independent GDAL probes disproved the initially proposed one-level file-list
  closure and blanket rejection of VSI members. No such runtime code was added.
- Output-discovery SHA helper confirmed stale under real restored-time rewrite
  (`schema_digest_baseline_probe.json`); still open.
- SBS cache removal costs about 0.489 seconds per warm native summary on the
  representative compressed raster; retain caching with correct identity after
  a separate reviewed design. No SBS runtime edits yet.
- Broad-exception gate initially flagged the unchanged asset-version handler
  because cache deletion shifted its allowlisted line. Corrected only its line
  reference; revision2 gate passes. Original failure retained.

## Latest validation and remaining scope

Full Python sanity at the earlier state completed: **8,721 passed, 103 skipped**,
1,126.84 seconds. C01 main-file refinement now passes 46 tests including native
Zarr and exact prior-output preservation, with scoped reviewer passes. Actual
39-year cropped RAP main-file set (564,058 bytes) hashes in 0.536s first pass and
0.035s second; this does not measure full input/held-lock acceptance. Original
failed invalid-parquet fixture and Zarr rejection evidence are retained.

See [current disposition](artifacts/implementation_disposition.md) for every
open consumer. Shared digest checkpoint `dd5d09ca7` is implemented and committed in
`edff4db5a`; 151 focused tests, follow-up regressions, stub checks and scoped
correctness/security/QA reviews pass. The actual executable helper improved
from452 stale digests in1,000 rapid rewrites to0 (671 same-version cases).
Code-quality telemetry now includes committed implementation waves.

Independent M1 probes confirm actual stale reports, live D-Tale CSV/Parquet,
post-fire SQLite logical-equivalence and CLI/parquet lineage failures. Features
content and companion defects are fixed in `ae314b581`; post-fire logical identity
and lineage remain open. Retained probes are linked by current disposition.

## Features-export implementation checkpoint

Checkpoint90a8a3dc9 precedes content identity and primary/companion publication
changes. Final affected suite199passed (`features_affected_tests_final_revision2.log`),
with scoped correctness/security/QA passes. Real native failed packaging retains
GDB files and partial ZIP. Historical selection works after source removal.
Full preparation/recheck benchmark .2745s cold, .2255s settled with zero digest
misses, within .4996s budget including existing preparation work. Original
under-scoped performance comparison and timing-dependent test failure retained.

D-Tale implementation is committed in `cf261f6ac` after checkpoint `fbac92404`.
Independent actual C03/C05/C06 baselines confirm stale native results. Additional
confirmed blockers: supported same-name Omni SBS upload skips rerun; repeated
profile SBS uploads reconstruct first rather than event-specific bytes.

## D-Tale implementation checkpoint

Contractfbac92404; content/resolved-source identity, lazy generation checks,
visible grid failures, loader409, and optional-map cleanup implemented.22affected
tests pass with zero skips; stubtest and broad-exception gates pass. Independent
reviews close stale feature-ID/default references, partial eager startup and
symlink-loop presentation. Documented third-party startup catch logs, cleans and
rethrows. Existing bridge tests now inspect303 without following it into404;
NoDir logical config path and actual internal-loader fallback are both tested.

Real77.39MiB/3.646Mrow source: settled100-row page55ms with zero content hash
reads, warm digest0.116ms, cold/evicted page859–886ms with3full-file checks.
Source unchanged; storage cache warm, so not NFS/cold-storage proof. Fullservice
rebuild/restart, browser/maps and archive acceptance remain open.

## Report implementation evidence

C08/C09 checkpoint `7d78e9810` and report-local relocation refinement `32c7bed70`
precede their implementation. Compact caches bind rows/provenance in one atomic
Parquet; native/query work and failed candidates remain visible. Existing modes,
C08 destination checks and C09 cache symlinks are preserved. Historical missing
prerequisites are explicit; malformed/denied inputs and known changed surviving
dependencies do not become historical success.

Final affected report suite: **87 passed**, `reports_affected_final.log`.
Canonical archive/restore preserves accepted and failed-attempt bytes; actual
chmod publication denial retains prior output. Deterministic overlapping writers
and opened-descriptor replacement verify coherent generations. Root relocation,
allowed parent selections and unrelated catalog entries are covered. Stubtest
passes two modules; stub completeness and broad-exception gates pass. Original
failures include old module-level test-stub contamination and an existing wrong
Iterable override annotation, both corrected in the touched scope.

Actual representative C08 build1.574s, settled16–18ms (parquet fallback32.5ms);
C09 build51.5ms, settled11.3ms. Two hashes per build input, zero settled content
reads/producer work, actual512-path eviction requires one hash per input. Native
and DuckDB rows equal baseline and modes remain0600/0644. Scoped correctness/QA
reviews pass; security review passes after independent after-probes. Implementation committed
as `0f2826a25`. Real web/
Redis runtime and all other open consumers remain package gates.

## PF-R02 checkpoint in review

After report implementation `0f2826a25`, retained producer probes establish both
stale CLI lineage and failed native writes deleting prior output. Proposed
`docs/schemas/climate-parquet-lineage-contract.md` binds verified snapshot source
identity to atomically published rows. Correctness/security reviews and actual
export/readiness budget measurement are in progress; no CLI runtime edits yet.
Legacy calendar/report reads remain compatible, but new post-fire readiness needs
producer proof. Attempt retention across normal climate directory cleanup is an
open design finding that must close before the ancestor checkpoint.

Recursive raster discovery retains actual nested VRT, archive-external VRT,
symlinked Zarr and reader-version cases; real settled discovery/digest costs are
~2 ms SBS, ~3.7 ms DEM and ~78 ms for 39 cropped RAP inputs. No universal GDAL
closure claim or runtime changes. Soil discovery retains 21 coherent snapshots
with original main/WAL/SHM unchanged: logical identity costs 46–209 ms warm;
physical digests alone cannot replace logical identity. Both designs remain open.

## Reviewed conformance follow-up

Cross-checking CLI atomic publication exposed two report permission regressions.
C09 now retains its former inode write authorization; C08 retains the different
native atomic-writer behavior. Both sidecar repairs retain their own write access
and mode. This restores the existing checkpoint access contract. Independent
before/after filesystem probes and 93 report tests pass; scoped security approval
is restored. Original failure evidence is retained.

PF-R02 ancestor checkpoint is `166c8f79d`; implementation has begun. Retained
QA found the actual strict predicate exceeded its original5/40-ms prototype
budget. Same-call parent reuse passes nine independent security probes and
reduces measured settled means to5.82/6.98ms; explicit10/50-ms contract correction
is under final review/measurement. The original failures remain retained. Export
latency and row/type parity pass. This is not whole-project/live-service
acceptance; full package gates remain open.

PF-R02 final affected gate:857passed,34warnings,255.49s. Both native producers,
post-fire M1/M3, parent replacement, publication and archive boundaries are in
the combined run. Stub completeness, changed broad-exception and docs gates pass.
Explicit performance correction committed asf7c832864: actual settled4.85/6.14ms,
eviction14.69/27.86ms, full export394/876ms, zero settled CLI payload reads,
exact row/type parity. Original budget failures remain retained. Scoped CLI
implementation reviews pass; whole-state/live-runtime acceptance remains open.

CLI producer/readiness implementation committed as36744f3b3 after the reviewed
performance amendmentf7c832864. Next C03/C04 checkpoint is deliberately limited
to verified local GTiff/AAIGrid reuse; VRT/Zarr/VSI and unproven layouts retain
native uncached behavior. Eager remote references in auxiliary or internally
encoded overview relationships require eligibility before GetFileList. Native
probes and whole-consumer baselines are retained; no raster runtime edits yet.

PF-R01 is explicitly justified unresolved, not fixed: seven existing SQLite
metadata/physical-only operations can still false-stale M3. The narrow deferral
is authorized by the package inventory allowance and independently reviewed;
no polling, snapshot or strict execution control changes. README records the
limitation and ordinary explicit rerun recovery. The plan's Decision Log records
why a process cache is insufficient and what separate future authority is needed.
All other implementation/runtime closeout gates remain active.

C03/C04 ancestor checkpoint`ceb715c08` accepted; implementation/reviews in
progress. Guard-inclusive native regression and measured whole-consumer budget
acceptance remain pending. B-F01 independent QA confirms a dashboard currentness
contract gap; retained review is not a fix or final disposition.


C03/C04 final scoped acceptance passes after the whole-native read-guard fix:
163 tests passed, one skipped; latest joint-observation test and stubtest pass.
Independent correctness/security/QA reviews accept the revised implementation.
All 46 measured budget gates pass, including twelve actual 512-entry eviction
exercises. Settled SBS hits average 9.83/9.96 ms; large TOPAZ validation averages
45.86–47.91 ms settled and 331–343 ms cold/evicted. Maximum mean added operation/
lock times are 358.60/350.35 ms (450-ms budget). Settled digest payload reads are
zero. Original failures and interrupted superseded measurements are retained.
This accepts the bounded raster implementation, not package/runtime completion.

Geneva C05/C06 ancestor checkpoint is `31f77bef1`. Implementation and independent
reviews are active; four initial actual-native regressions pass. Existing mocked
raster fixtures are being replaced with real native output assertions. Publication
and typed-drift failure-path review findings remain open. S01/S02 checkpoint
budget measurements are in progress; no S01/S02 production changes yet.


Raster implementation is committed as `5bf504dbe`. Geneva now has85focused tests
plus canonical archive bytes/cache acceptance; independent findings closed.
Its original C06 performance gate failed, retained and undergoing measured
same-call graph-validation optimization. Archive directory-mode loss was
separately confirmed in the existing canonical archive writer/restore path;
that integration gate is open. S02 checkpoint`eb2c33b2b` and S01 checkpoint
`c28f81f59` are ratified ancestors. S02 implementation has begun; first combined
Geneva/profile suite106passed. S01 production changes have not begun.

C01 indirect closure is justified unresolved, with retained correctness scope
and the RAP README limitation. Complete small RAP native analysis/held-lock
measurement passes; no universal indirect-native proof or fullruntime claim.


2026-09-17 latest scoped acceptance: Geneva passes135 combined Geneva/profile/archive
tests and all16 amended performance gates after checkpoint `21aacd74f`; profile
SBS passes all27 original performance gates (16MiB first capture545.60/550ms is
close to the mean limit). Archive directory-mode implementation passes9 independent
security probes; QA review is in progress. S01 direct/RQ implementation is active:
61 focused tests pass; independent actual-owner review found and closed alias
truncation, late child drift, legacy association resurrection and detached-refresh
logger loss. Final S01 probes and implementation timing remain open. The dev
stack has not been rebuilt/restarted; live HTTP/RQ/WEPP/archive acceptance and
final full-suite gates remain mandatory. Earlier status paragraphs are historical.


Current checkpoints: Geneva1556df345, profile7ad0ac609, archive7b4f22df9,
Omni de3a1eba0. S01 all45 original performance gates pass; final five-module
stubtest and refreshed146-edge RQ graph pass. Independent remaining-family
classifications are adopted as documented in ExecPlan Decision Log and
remaining_inventory_disposition_qa.md, without claiming indirect or completion
boundaries fixed. Final fullsuite is running; dev restart/native HTTP acceptance
has not started. Browser dev-agent authentication/discovery has succeeded.


Runtime preparation update: the canonical dev image built successfully as
`sha256:00a3e43a88a5c9079a7e58a8423432d69f22b7b09c0a9288078b67abbca1d3f8`.
Sixteen running shared-image service identities/mounts are retained before
restart. The first fullsuite stopped after3881passes/51skips on the unchanged
simulated HTTP timing assertion (1.2377s versus1s) during build/copy work.
The isolated quiet rerun passed; a complete quiet rerun is now running, with
native acceptance still held. No assertion was relaxed. The full independent
canary copy has3916files/6,375,730,842logical bytes and no shared source inodes at
`/wc1/runs/qa/qa-freshness-runtime-7e24c8d1`; original source hashes and versions
are in its retained copy manifest. Browser login/setup and run-scoped discovery
succeeded. An initial config-token0 GET returned404; the stored config stem is
`config`, whose pipeline/readiness/schema calls return200. No model job has yet
been submitted. S02 canonical cookie-only playback has a separately reviewed
preexisting bearer-auth mismatch; actual per-request failure evidence and an
authorized Session HTTP control will be retained after restart.

2026-09-17 08:04UTC: final quiet full Python suite8,924passed/99skipped; npm899tests/112suites and lint pass. Static assets rebuilt using canonical wctl with repository venv after retained missing-host-Jinja2 failure. Queues empty; development recreation in progress, actual acceptance still open.

2026-09-17 runtime: normal18-job WEPP pipeline changes218CLIctime/linkcounts but zero hashes; M3 remains current. Supported climate change invalidates all218CLI and M3; rerun restores current UI/API. Live archive/restore preserves545artifact files/84directory modes, exposes retained PF-R01 physical-soil staleness; normal M3 recovery and actual report/downloads pass. Existing canonical-profileCLI401/exit0 and waterbalanceCSV500 remain explicit failures. Native Features/D-Tale/Geneva/profile/NoDb/NFS scopes pass. Direct Omni two46-year generations/consumed skips pass; liveRQ and interleaved-state final gates remain open.


## Final closeout — 2026-09-17

All six milestones are complete under explicit inventory dispositions. Omni
actual direct/live-RQ numerical and skip checks pass; full final source audit
preserves all3,916 original file bytes/modes with four reviewed operational
metadata differences. Sixty alternating state reads have zero new digest
misses/direct payload reads and395/512 entries; mean whole-state timings
739.48/862.19ms are observations, not a new latency gate. Final independent
reviews,8,924 Python/899 frontend passes and runtime limitations are linked
from [package outcome](package.md#delivered-outcome-and-follow-up).
