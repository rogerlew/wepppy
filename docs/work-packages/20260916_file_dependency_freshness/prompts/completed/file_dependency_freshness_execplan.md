# Audit and repair file dependency freshness

This completed ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Owner-authorized execution completed on2026-09-17 UTC. Implementation through
`de3a1eba0`, rebuilt development runtime and independent reviews pass within
explicit justified-unresolved dispositions. No production deployment occurred.
Historical execution entries below preserve their then-current status.

## Purpose / Big Picture


A user should be able to build climate, run post-fire assessment, then run WEPP
without unchanged climate data making the assessment stale. A real climate or
other required input change must still invalidate downstream outputs. Extend
that audit to every maintained file-based dependency consumer, fixing confirmed
defects and preserving legitimate metadata, access and concurrency safeguards.
Completion means observable correct results from rebuilt, restarted services,
not merely a changed helper or passing unit tests.

## Progress


- [x] Scaffold package, discovery seeds and operation matrix, 2026-09-17 UTC.
- [x] M1 initial scope/revision searches, independent seed inventories and real hard-link baseline.
- [x] M1 finite Python/non-Python consumer tracing and explicit dispositions completed; native indirect/completion and browser limits are not universal safety claims.
- [x] M2 first-wave and cache-admission contracts independently reviewed and committed (`43317704f`, `0fe02dc0f`).
- [x] M2 implemented-consumer checkpoints are ratified ancestors; deferred boundaries have explicit dispositions.
- [x] M3: all ratified implementation waves committed through `de3a1eba0`; scoped correctness, security and performance reviews pass. Runtime acceptance is complete.
- [x] M4: final quiet Python suite8,924 passed/99 skipped; npm112 suites/899 tests and lint, five stub surfaces, stub completeness, RQ graph and changed broad-exception gates pass. Scoped independent reviews and measured budgets pass; final runtime reviews are retained.
- [x] M5:16 development services rebuilt/recreated; actual UI/RQ/WEPP, archive/recovery, native direct/RQ Omni and interleaved state acceptance complete.
- [x] M6: complete dispositions, durable docs, final independent reviews and package closeout,2026-09-17 UTC.

## Surprises & Discoveries

Live archive/restore preserves545 selected artifact bytes/modes and84 directory
modes but reproduces the already dispositioned PF-R01 soil physical-inventory
false staleness. Only `selections.soil_inputs` causes the comparator mismatch;
all7 manifest-bound soil inputs and restored SQLite main/WAL/SHM bytes verify.
An ordinary M3 rerun restores API/browser/report currentness. Canonical profile
CLI replay separately returns two401s yet exits0; supported authenticated-session
replay preserves both event payloads. Water-balance CSV exposes an existing
unimplemented adapter; HTML and provenance-bearing Parquet download pass.
These failures remain explicit, not converted into passing runtime claims.

The normal access-log compiler rewrote source TTL and touched three empty logs
after a successful full-source audit. Independent review permits only an explicit
acceptance-harness exception requiring original bytes/lengths/modes for those
four operational files, original membership, strict other3912 versions and a
final complete hash audit. Original manifests/failures remain immutable; no
named-source repair, production guard relaxation or scheduler stop occurred.

S01 actual-owner review caught detached hydration dropping runtime logging, a
legacy skipped association resurrected after invalidation, and copyfile alias
protection lost by a streaming rewrite. Reinitialize canonical logging, snapshot
the accepted association, and compare opened source/destination inodes before
truncation. Retained original failures and independent after-probes distinguish
these fixes from normal runtime acceptance still to come.

CLI lineage prototype timings omitted mandatory strict directory traversal. The
actual predicate exceeded5/40-ms means; same-call parent descriptor reuse reduced
settled means from8.28/10.78ms to5.82/6.98ms without changing access authority.
Explicit10/50-ms budget correction is being independently reviewed and measured;
original misses remain evidence. The active GL dashboard also mixes cached old
year values with newly queried years after a same-path data replacement (B-F01).


Execution reproduced unchanged-content hard-link false staleness, a native SBS
stale-class cache, and a NoDb hydration mixed-generation race. A representative
M3 source set has 179 files (68.7 MB), exceeding the old 64-entry digest cache.
See retained M1 reviews/probes and digest baseline.

The initiating CLI has two hard links: `climate/wepp.cli` and `wepp/runs/pw0.cli`.
Its ctime changed during WEPP watershed preparation, while every parsed column
including regenerated peak intensities still matches the accepted parquet over
16,802 rows. The source check uses size/mtime/ctime as accepted identity.
Hard-link causality is strongly supported but must be reproduced without relying
on inference from historical timestamps. See the retained investigation in
`docs/investigations/20260917_dead_horse_cli_freshness/`.

Initial search also found mtime/size fingerprints without content hashes, and
ctime used for caches/read-race guards. These are candidate mechanisms, not
confirmed bugs. Removing all ctime checks would conflate separate concerns.

## Decision Log

Closeout decision,2026-09-17: accept M5/M6 against the ratified finite-inventory
dispositions and actual runtime evidence. Do not expand this package into soil
logical snapshot publication, browser-generation UX, profile CLI authentication
or the existing CSV adapter. Those require separate contracts; retained failures
and durable operator guidance make this boundary reviewable. Interleaved state
acceptance tests the existing bounded-cache/no warm digest reread obligation;
whole-state latency is observational because no numerical deadline was ratified.

2026-09-17: runtime-discovered profile CLI auth/result-reporting and water-balance
CSV adapter failures are independently attributed to unchanged preexisting
code. Preserve them as failed checks with durable operator guidance; do not add
a new auth flow or choose water-balance CSV numerical/display semantics inside
the freshness change. C08 HTML/validated compact Parquet and S02 supported
authenticated HTTP event-byte parity retain their bounded passing claims.
The observed restore false-stale case is an actual runtime manifestation of the
already justified-unresolved PF-R01 boundary, with ordinary rerun recovery proven.
See `artifacts/runtime_acceptance.md` and independent runtime reviews.

2026-09-17: adopt the bounded classifications and follow-up evidence in
`artifacts/remaining_inventory_disposition_qa.md` and C07 in
`artifacts/features_omni_remaining_closure_qa.md`. Roads upstream closure,
AgFields wider cross-stage/native closure, explicit cached Geneva preparation,
other upload-event families and contrast/source-unavailable boundaries remain
justified unresolved. Their inspected controlled-ingest/completion predicates
are preserved. Source tracing is not an actual normal-workflow failure; fixing
these wider boundaries would redefine existing completion/snapshot contracts
without the required producer/result and cost evidence. C07's held-receipt
native stale mechanism remains confirmed, while an ordinary missing-receipt
producer path is unverified. Do not hide either fact or claim it fixed by S01.
C02 still requires the maintained mixed-profile export acceptance now prepared.
The finite search/disposition records define coverage, not a proof over arbitrary
vendored readers or untraced scientific internals.

2026-09-17: scoped implementations are committed: Geneva `1556df345`, profile
`7ad0ac609`, archive `7b4f22df9`, Omni `de3a1eba0`. S01 passes45 original component
budgets and11 security/10 correctness native-owner controls. Five canonical
stub surfaces pass. RQ graph regeneration changes line references only;146edges
are unchanged. Final full-suite and after-restart runtime remain open.

2026-09-17 UTC: B-F01 and the separately traced browser-family candidates receive
explicit justified-unresolved inventory dispositions under the package complexity
allowance, narrowly qualifying the generic confirmed-failure closeout gate as
for PF-R01. The confirmed mixed-year defect remains unfixed and must appear in
final limitations. Existing docs choose neither automatic post-rerun refresh nor
an immutable snapshot; inventing a generation protocol or invalidating active
analysis would select new UX beyond the demonstrated missing behavior. Durable
currentness/reopen guidance is in`docs/ui-docs/gl-dashboard.md#currentness-after-a-run-is-regenerated`;
independent QA scope/disposition artifacts retain precise candidate distinctions.
All changed-code defects, other confirmed fixes and final runtime gates remain
blocking; this does not declare all browser caches safe.

2026-09-17 UTC: PF-R01 is explicitly dispositioned as justified unresolved under
the package's inventory allowance. This narrowly qualifies the plan's generic
confirmed-failure closeout statement: the seven existing soil SQLite false-stale
cases are not fixed and cannot be included in completed-fix claims. Independent
reviews find no changed-code security exception; no strict guard is weakened.
Read-only polling and mandatory fresh visible SQLite snapshots conflict on a
new physical generation, so a process cache cannot establish logical equality
after restart/eviction/VACUUM. A future fix needs separately ratified polling/
snapshot policy or evaluated owned-native support. All changed-code findings,
other in-scope fixes and final runtime gates remain blocking.

2026-09-17 UTC: preserve strict O_RDONLY/no-follow authority for CLI readiness.
Profile and optimize same-call work before proposing an explicit prototype-budget
correction; no cross-request descriptor cache or weakened access checks. Final
actual measurements and independent reviews must ratify the correction.


2026-09-17 UTC: stage M2/M3 checkpoints by coherent consumer group while keeping
the exhaustive M1 inventory open. Independent discovery found distinct report,
NoDb and raster cache contracts; forcing them into the post-fire fix would
violate the package complexity budget. The first wave covers ordinary post-fire
source/artifact content only. No inventory finding is waived and M4–M6 cannot
close until every required disposition and acceptance is complete.

2026-09-17 UTC: owner requested execution of this work package. This authorizes
its planned checkpoint commits, implementation, reviews and disposable
development acceptance; retain unrelated working-tree changes. M1 source
searches and independent correctness/security inventory reviews are underway.

2026-09-17 UTC: scaffold only, as requested. Cover all maintained dependency
tracking mechanisms; avoid a global mechanical timestamp replacement. Begin
with a deterministic hard-link reproduction and use the smallest compatible
fix. Preserve source hard-link materialization unless evidence independently
shows it is wrong. Content freshness, cache hints, access control and coherent
read/publication identity must be assessed separately.

Restart and actual end-to-end acceptance are explicit completion gates, based
on the owner's earlier requirement that runtime delivery be verified. They are
future execution work, not authorization to restart during this scaffold turn.
Use disposable runs for mutations; do not silently rerun existing user projects.

- C01 indirect native closure is explicitly justified unresolved under the package
  inventory allowance. The retained native counterexamples cannot be fixed by
  the bounded GTiff/AAIGrid cache observer's uncached fallback: RAP already builds
  outside its finalization lock. Preserve accepted local VRT/directory inputs
  and strict main checks; an owned native read-set proof requires separate scope.
  This supersedes earlier blanket blocker wording without claiming the defect
  fixed. The RAP README's "Dependency freshness limit" records the durable user
  limitation. Actual complete small RAP analysis used40files/234nativecalls,
  retained1,638equal rows,53.3ms finalizer hashing and3.968s lock residence; this
  is one small copied workflow, not universal performance/runtime acceptance.

## Outcomes & Retrospective

All six milestones are complete. Actual WEPP preparation changes218 CLI
ctimes/link counts with unchanged hashes and preserves accepted M3 currentness;
actual changed climate invalidates it. All implemented waves are committed
through `de3a1eba0`, with final8,924 Python/899 frontend passes and independent
review records. Sixteen dev services were recreated with preserved identities
and mounts; no production deployment occurred. Omni direct/live-RQ outputs and
consumed-source skips agree. Two interleaved working sets retain395/512 digest
entries,12,840 added hits and zero warm misses/direct uncached payloads. Whole
state means739.48/862.19ms are observations, not an invented latency budget.

Archive/restore preserves545 selected files and84 directory modes but exposes
PF-R01 physical-soil false staleness; normal M3 recovery passes. Canonical profile
CLI401/false success and water-balance CSV500 are existing defects, separately
documented with supported authenticated replay and HTML/Parquet alternatives.
Indirect-reader, dashboard-generation and completion-receipt boundaries remain
explicitly unresolved under the inventory allowance. The final source audit
preserves all3,916 original bytes/modes; four operational metadata changes are
recorded, so whole-tree physical immutability is not claimed.

The central lesson is that content equivalence, coherent publication and access
identity need separate evidence. Retaining failed prototypes and actual runtime
failures prevented passing component tests from hiding unsupported claims.
Canonical contracts and operator guidance live outside this closed package;
`artifacts/runtime_acceptance.md` and independent final reviews retain provenance.
The optional Geneva module stubtest remains limited by existing native/typing
errors; canonical stub surfaces pass.

## Context and Orientation


Work from `/home/workdir/wepppy` on the current branch. Read root and relevant
nested AGENTS before edits. `wepppy/nodb/mods/postfire_debris_flow/production.py`
defines signature/currentness; report and rq-engine routes consume related
identities. `wepppy/runtime_paths/wepp_inputs.py` materializes WEPP inputs with
hard links. `_prep_channel_climate` in `wepppy/nodb/core/wepp.py` creates `pw0.cli`.
`wepppy/nodb/_derived_build.py` contains publication primitives. Export dependency
tracking, core NoDb caching, soil snapshots and browser caches have other
signatures; follow the seed inventory rather than assuming shared semantics.

Ctime is inode status-change time, mtime is content-modification time, and a
hard link is another pathname for the same inode. Neither timestamp proves
content equality. A digest is a hash of bytes; a cached digest is only reliable
when its invalidation/read-coherence conditions hold. A semantic fingerprint
identifies selected parsed values and must have an explicit domain contract.

Use `docs/standards/contract-first-change-standard.md`,
`docs/standards/hardening-lifecycle-standard.md`,
`docs/standards/artifact-observability-standard.md` and the NoDb/RQ response and
persistence contracts. Historical packages provide evidence, not live authority.

## Plan of Work


M1 retains repository revision, complete search commands and scope. Build an
inventory covering every seed plus additional findings from timestamp, signature,
hash, ETag and completion-event searches across languages. Trace callers and
writers, including external masks, source settings and generated outputs.
Classify each as content dependency, object identity, race guard, cache hint,
completion order, display metadata or unrelated. Retain safe/nondependency
classifications; do not equate grep counts with an exhaustive semantic audit.
Reproduce hard-link false staleness and probe false-current equal-size/restored-
mtime cases. End with concrete failing cases and contract owners.

M2 writes `artifacts/contract_decision.md`, per-consumer operation/state matrices,
and a compatibility/regression plan before any persisted schema mutation.
Measure cold/warm costs on representative files and agree bounded budgets before
selecting digest/cache behavior. Define missing-hash legacy handling, source
provenance, sidecar closure and concurrent-read rules. Amend canonical contracts
with implementation pending. For UI-coupled changes, obtain the required explicit
behavior authority, two independent read-only correctness/security reviews and
a standalone checkpoint ancestor commit before implementation. Check existing
execution authorization first; do not ask repeatedly for already approved work.

M3 fixes the confirmed post-fire path first, with a real filesystem regression
that fails before the change and passes afterwards. Detect both harmless hard
links and actual changed input. Then work through independently reviewable
consumer groups, updating each contract, tests and inventory disposition.
Avoid a shared abstraction until repeated compatible behavior demonstrates its
need. Do not weaken digest validation, locking, symlink containment or NoDb
serialization to make old tests pass. Compatibility must reach actual generated
run artifacts, not only constructors or test fixtures.

M4 runs the affected suites and required repository gates, including the full
Python sanity suite for substantive changes. Run frontend lint/tests for changed
browser paths, Go tests for changed services, stub checks for API changes and
RQ graph/live job validation if wiring changes. Review changed complexity and
broad exceptions. Independently review correctness and security, closing all
medium/high code findings. Retain before/after performance data and verify that
polling does not repeatedly hash large unchanged raster inputs. Any unresolved
inventory consumer must have explicit, justified scope disposition; confirmed
in-scope correctness failures block closeout.

M5 inspects canonical development orchestration, preserves baseline evidence,
rebuilds affected services/assets and restarts the development stack using wctl.
On a disposable representative clone, build climate and an assessment through
ordinary UI/RQ, then run normal WEPP preparation/execution. Confirm no false stale
assessment after hard-link creation. Make a controlled genuine climate change
through the supported workflow and confirm invalidation, rerun and fresh results.
Use isolated fixtures for equal-size/restored-mtime, metadata, symlink and race
cases. Check state, preflight, report, downloads and reload consistently across
processes with production-equivalent identities, groups, mounts and umask.
Canonical archive/restore on isolated copies must preserve artifacts and correct
freshness decisions. Repeat representative live paths for every changed boundary;
a single post-fire canary cannot validate unrelated NoDb/export/cache fixes.

M6 closes the inventory and review disposition, updates affected user/operator/
developer docs and promotes durable rules outside this package. Record rollout,
compatibility and recovery instructions without inferring production deployment.
Update tracker and PROJECT_TRACKER, move the plan to completed, and report exact
validation coverage and remaining acknowledged limitations. Never claim success
from a restart alone or from tests that stub the filesystem operation at issue.

## Concrete Steps


Start with the search protocol in `artifacts/seed_inventory.md` and store its
results/revision in artifacts. Run reproductions in disposable directories.
Use `wctl run-pytest tests/<affected-path>` for iteration and
`wctl run-pytest tests --maxfail=1` before substantive implementation handoff.
Use `wctl run-npm lint` and `wctl run-npm test` when frontend changes apply.
Inspect `docker/docker-compose.dev.yml` and Docker/WCTL instructions before
recording exact rebuild and `wctl restart` commands. Production deployment uses
its existing separate authorization and canonical entry point.

Validate documentation with `wctl doc-lint --path
 docs/work-packages/20260916_file_dependency_freshness` and lint each changed
canonical document. Record commands, failures, recovery and final results;
update this section with exact narrowed paths as inventory resolves scope.

## Validation and Acceptance


The operation matrix and valid-state matrix must pass for every changed consumer.
Content-equivalent operations leave content-based outputs current where access
and provenance still permit use; changed content cannot appear current even
when size/mtime match. Concurrent operations cannot publish mixed generations.
Legacy readers remain explicit and compatible. Real users can complete the
restarted-stack workflow and inspect/archive its artifacts. Measured performance
meets the path-specific budgets ratified at M2. All in-scope findings have closed
dispositions, not merely proposed fixes or a generic helper shipped unused.

## Idempotence and Recovery


Never mutate named investigation runs during discovery. Keep input/result hashes
and logs from every canary; retain failed/intermediate evidence. Reuse normal
archive and backup mechanisms. For schema changes, define reader/writer rollback
compatibility before edits and retain old accepted results. No production data
migration, mass cache deletion, hidden fallback, directory ownership change or
new deployment mechanism is authorized by the scaffold.

## Artifacts and Interfaces


Keep inventory, contracts/reviews, reproduction scripts, benchmarks and live
acceptance evidence under this package's artifacts. Project-generated records
remain in normal visible module/attempt paths and canonical archives. Never
retain credentials. New callable signatures are fixed only after M1 demonstrates
shared semantics; no universal signature API is prescribed by this plan.

Revision 2026-09-17 UTC: scaffolded the owner's repository-wide audit/fix request;
explicitly retained contract, security, compatibility and restarted-stack gates.

Revision note (2026-09-17 UTC): activated execution on owner instruction and
retained discovery scope/revision before implementation.

Revision note (2026-09-17 UTC): recorded two contract ancestors, actual
timestamp-collision correction and partial focused validation; package remains
active, with NoDb checkpoint and all final acceptance gates outstanding.

Revision note (2026-09-17 UTC): C10 checkpoint committed (`984023c18`), 12 tests
and actual-bundle benchmark pass. NoDb/download review regressions close scoped
QA findings. C01 main-file checkpoint under review; original flat GDAL closure
proposal rejected by real nested-VRT and local-ZIP evidence, retained as an open
separate raster dependency wave. Full Python sanity is still running.

Revision note (2026-09-17 UTC): C01 main-file checkpoint (`b8c63ab1e`) and
native directory compatibility precision (`dbec83d30`) implemented; 46 focused
tests and scoped reviews pass. Shared ordinary-file digest checkpoint
(`dd5d09ca7`) implemented for output and executable identities; 151 tests pass,
actual registry rapid-rewrite stale count falls from 452 to zero. Stub and
implementation reviews underway. All unresolved scientific cache and raster
closure findings remain package blockers, as does live acceptance.

## Latest execution evidence

2026-09-17 08:04UTC: final quiet full suite8,924passed/99skipped in1192.22s.
Frontend112suites/899tests and lint pass; stub completeness passes. Static build
initially lacked host Jinja2; repeated canonical wctl build with repository venv
PATH succeeds. Original failure retained. Read-only preflight finds all three
queues empty; canonical16-service dev recreation is in progress using the
completed local image. Runtime acceptance has not yet been claimed.


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

2026-09-17 UTC: independent actual-consumer probes reproduced stale water-balance
and landuse reports, live D-Tale CSV/Parquet behavior, post-fire soil logical
false staleness and CLI/parquet lineage defects. Features-export service ZIP
and native GDB companion probes both confirm stale output; companion retry also
deletes an accepted ZIP on conversion failure. A reviewed content/publication
checkpoint includes all three features-export paths and distinct retained
companion candidates. No scope waiver or package completion is implied.
Current per-consumer status: `artifacts/implementation_disposition.md`.

2026-09-17 UTC: features-export checkpoint90a8a3dc9 and implementationae314b581
close the bounded catalog-main-file/companion publication wave; recursive native
closure remains open. D-Tale checkpointfbac92404 precedes generation guards and
optional-map cleanup.22tests pass without availability skips; stub/broad gates
pass. Review fixes close overlay feature-ID/default propagation, eager partial
registration and alias-loop error presentation. Real77MiB Parquet pages show
settled55ms/zero hash bytes versus859–886ms/three full hash reads during cold
admission or eviction, within the reviewed budget. Normal restarted browser
workflows remain untested; intercepted UI error-envelope evidence is distinct.

2026-09-17 UTC: C08/C09 report checkpoint drafted with additive embedded Parquet
provenance, effective mapping/query inputs and explicit historical compatibility.
Independent reviews and measured budgets precede implementation.

2026-09-17 UTC: C08/C09 implementation follows checkpoints `7d78e9810` and
`32c7bed70`.87 report tests pass, including actual archive/restore, read and
publication denial, concurrent generations and relocated catalogs. Scoped reviews
close historical/malformed/access/root-selection findings; scoped security review passes and implementation is committed as `0f2826a25`. Large native and DuckDB measured
build/hit budgets pass. Recursive raster closure and soil logical-identity
performance discovery continue independently; no remaining blocker is waived.

Revision note (2026-09-17 UTC): PF-R02 producer-lineage/publication checkpoint is
under independent review after report commit0f2826a25. Native export failure
removes prior output; source mutation/selection during parse admits old rows.
No runtime edits precede checkpoint. New attempt retention across climate rebuild
cleanup is an unresolved design finding. Recursive raster discovery and 21
nonmutating soil snapshot benchmarks are retained; neither has a ratified
implementation contract yet. Package final runtime/gates remain outstanding.

Revision note (2026-09-17 UTC): PF-R02 ancestor166c8f79d ratified lineage and
atomic publication after independent correctness/security review and measured
46/120-year CLI budgets. Implementation now covers both producers, retained
snapshot parsing, owner/fallback re-selection, strict bounded footer proof and
content=False readiness, private anchored history, skeleton/archive retention.
84 then91 focused tests and17 dedicated boundary tests passed. A broader850-test
run stopped after583passes at a proofless analytical M3 fixture; replaced that
fixture with a real30-year breakpoint export preserving exact10mm/40,20,10
intensities. Final affected run, implemented QA timings and scoped security review
remain open. No runtime deployment/acceptance claim.

Security cross-check restored report authorization in57e60aae9: C09 target write
access and both version-sidecar access/modes preserve former writer behavior;
C08 native target behavior stays unchanged. Independent eight after-probes and
93reporttests pass; original permission regressions retained. All first-wave and
recursive raster/soil discovery evidence is committed inafe5aed36.

Revision note: CLI same-call authority probes pass; actual budget correction and
final affected tests remain open. C03/C04 recursive-raster checkpoint drafted,
without runtime edits. Non-Python audit adds active GL dashboard finding B-F01;
M1 and final runtime gates remain open.

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

C03/C04 bounded raster contract checkpoint committed as`ceb715c08` after
correctness/security/QA design approval. Implementation now in progress: shared
local GTiff/AAIGrid observation, guarded native SBS LRU admission and joint MOFE
count validation. Final implementation tests, performance and reviews remain
open; initial unverified formats preserve native uncached execution. No claim
that this observer closes C01/C02/C05/C06 publication scope.

C03/C04 inspection sibling refinement committed as`308f9edee` after retained
mask-replacement and hidden-worldfile/RPB findings. Actual implementation has
143affected tests (one skip),23native observer regressions, stubtest and scoped
independent correctness/security PASS; actual guard-inclusive timing is running.
Native management preparation evidence reaches`wepp/runs/p7.man`; this is not
a substitute for final RQ/model execution. Geneva C05/C06, S01 and S02 contracts
are being drafted without their runtime edits.

R-CI03/R-I03 reopened C03/C04 after an actual native changed-then-restored source
probe failed: content-only comparisons accepted intermediate numerical results.
Keep initial failure and partial performance baseline (terminatedoutside locks).
Correction retains same-acquisition physical/context guards separately from
content-key equality, validates them before admission and on hits, and preserves
metadata-only inter-call reuse. Final reviews/timing reopened;58focused aftertests
pass, additional paired/serialization/path tests running. This is conformance to
the existing read-coherence requirement, not a new numerical identity policy.


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

Revision2026-09-17: closed all milestones after final direct/live-RQ source audit,
interleaved cache observation and independent reviews; retained all failed and
unresolved boundaries explicitly rather than claiming universal freshness.
