# Audit and repair file dependency freshness

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. The owner authorized execution on 2026-09-17 UTC after scaffolding. M1 remains active alongside scoped reviewed implementation waves. Remaining
behavior changes stay gated on their own reviewed contract checkpoints.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective throughout execution.

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
- [ ] M1 remaining exhaustive hash/cache-only consumer tracing and full disposition.
- [x] M2 first-wave and cache-admission contracts independently reviewed and committed (`43317704f`, `0fe02dc0f`).
- [ ] M2 remaining consumer checkpoints; NoDb hydration checkpoint committed (`4e000950a`).
- [ ] M3: reviewed post-fire, NoDb hydration, bundle header, derived main-file and shared ordinary-digest waves committed in `edff4db5a`; scoped tests/reviews pass. Features-export content/publication implemented in `ae314b581` (199 affected tests). D-Tale checkpoint `fbac92404` implemented in `cf261f6ac` with 22 tests and scoped reviews; remaining consumer waves open.
- [ ] M4: first broad Python sanity passed (8,721 passed, 103 skipped); final-state gates, complete reviews and performance evidence remain open.
- [ ] M5: rebuild/restart development stack and real UI/RQ/WEPP acceptance.
- [ ] M6: complete dispositions, promote durable docs and close package.

## Surprises & Discoveries

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

## Outcomes & Retrospective


Execution now retains baseline source searches, independent inventories, real
filesystem failing probes and initial digest costs. First-wave checkpoint and the measured cache-admission amendment are committed.
Committed runtime waves pass 712 post-fire tests, 155 NoDb tests, scoped header/derived/shared-digest suites, stub checks and the real-clock cache collision probe. Implementation reviews found no blocking
code defect; full inventory disposition, remaining consumer fixes and all
restarted-stack acceptance remain open; this is not package completion.

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
that fails before the change and passes afterward. Detect both harmless hard
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
