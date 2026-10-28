# Execute asynchronous query catalog refresh

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current. The canonical contract controls behavior; this plan sequences implementation and evidence.

## Purpose / Big Picture

Remove catalog traversal from eligible artifact-producing requests without losing updates, breaking immediate reports, or allowing old background work to publish into a replaced project. Reproduce the Mill Creek submission failure on an isolated copy; prove responsive submission, actual model execution and correct catalog-backed consumption after repair.

The operator authorized committing the reviewed contract and scaffolding execution on 2026-10-23. The operator subsequently instructed execution of this plan; implementation and bounded validation are now complete, including the separately authorized full deployment. General enablement and user-project repair remain excluded. When instructed to execute, proceed milestone by milestone within the accepted contract; do not ask for repeated routine implementation approval.

## Progress

- [x] October 28 default-queue contract checkpoint `0e6302905`, independent reviews, runtime wiring and 129 focused real-Redis/artifact regressions; local normal-worker live job-tree readback passed.
- [x] October 28 broad sweep attempted: 6,810 passed/61 skipped, stopped by preexisting Roads provenance mismatch; explicitly not a full-suite pass. Final bounded implementation handoff complete; production migration/general enablement remain excluded.

- [x] M0–M3: reviewed contracts, native/publication/queue/lifecycle/reader implementation and local regression gates complete.
- [x] M4–M5: producer migrations and fresh October 26 full scientific/report acceptance complete; earlier October 23 failure retained as historical evidence.
- [x] October 27 remediation: all four roots/30,891 scopes discovered, bounded RQ timeout recovery, HTTP responsiveness and independent reviews passed.
- [x] Bounded admission/controller implementation and independent local gates complete; broad baseline 11,862 passed/201 skipped with final-source focused gates retained separately.
- [x] Full canonical deployment of `0da9c9071` completed on wepp1–3; source-only candidate and active-job hold superseded by authorized deployment.
- [x] Deployed pilot preflight: eight compatible consumers, production identity and matching source/native configuration across both batch hosts.
- [x] Actual shared-batch pilot: one inventory plus 16 refresh jobs, both eight-scope artifact waves, 48 query checks, receipt acknowledgment and sentinel noninterference passed.
- [x] Explicit pause, retained lease rejection and post-expiry resume preserved original budgets/window; all admitted work drained. No active-job exception was used.
- [x] Nine scratch scopes retired under lifecycle guards to private evidence storage; 711 source hashes and eight catalog hashes preserved, old managed paths absent.
- [x] Independent execution correctness/security review complete; exact evidence limits retained. Secondary QA documented separately.
- [ ] M6 general fleet rollout: complete-cycle/oldest-pending-age and new ordinary-arrival delay acceptance remain unproved and outside the authorized pilot. General async stays disabled.
- [x] M7 bounded handoff: reconcile package/tracker/contracts/operator notes and publish retained sanitized evidence; do not relabel fleet enablement complete.

## Surprises & Discoveries

2026-10-28: routing is also enforced in admission, execution claims and pilot manifests, not just the Queue constructor. Preserve the historically named ledger to avoid resetting permits. Production defaults have twelve default consumers, versus eight batch consumers.

2026-10-27 completed execution: source/native hashes and genuine worker capabilities
matched after the full deployment. An early controller resume was correctly
rejected while its old lease remained; explicit post-expiry resume preserved the
manifest, budgets and deadline. Artifact checks passed before consumer calls.
Post-acceptance canonical invalidation overwrites status metadata, so future
retirement needs a raw metadata snapshot before invalidation; never reconstruct
missing status bytes from a successful result.

2026-10-27 security reproduction: installed RQ `Job.cancel()` can label running
work canceled without stopping the process. A claimed canceled job now retains
its permit and uncertainty until the worker records execution exit; normal
finished/failed/stopped workhorse recovery remains unchanged. Actual-process
regression and final 72-test RQ suite pass. The broad run began before this final
fix; final RQ validation is therefore a separately retained source-specific gate.

2026-10-27 pilot: the normal NFS directory has the same inode on wepp1/wepp2
but local devices 105/68. Scope authority now binds stable inode to canonical
namespace/incarnation/marker, excluding host-local device numbering. A final
claim transaction watches job status as well as the admission ledger.

2026-10-27 pilot: local development images omit the bind-mounted native scanner;
the source-image gate correctly rejected that image. At that preparation checkpoint, real image derivation was being tested against
an existing local production-style image and a backport was isolated at `813d912be`.
The later full deployment superseded that optional activation path.

2026-10-27 remediation: complete discovery now passes for all four roots, but
legacy needed 4,032.650 cumulative process seconds across a deliberate fenced
restart. The unchanged 3,600-second attempt budget therefore requires retained
progress and retries; a separate normal-worker timeout canary validates that
boundary with shortened test timing. Full inventory is not full reconciliation.
Some representative read-only scan samples exceed a 60-second component bound;
capacity calculations must retain those censored observations. See
[full inventory](../../artifacts/20261027_full_inventory.md) and
[capacity review](../../artifacts/capacity-independent-assessment.md).

2026-10-26 rollout gates: active owned legacy projects make the proposed three-root
configuration incomplete. A four-root candidate parses identically on all hosts,
but legacy enumeration exceeds the inventory lease before checkpointing.
Cross-host lock exclusion passes while waits reach 30.5 s; Python heartbeat
survival does not prove async HTTP event-loop readiness. Controlled production
identity reconciliation passed with both SimpleWorker and a normal forking
Worker; full fleet capacity remains unproved. See
[gate disposition](../../artifacts/20261026_rollout_gate_disposition.md).

2026-10-26: The fresh clone initially inherited an empty Parquet attempt under
`wepp/reports/cache` from the failed case. Strict initial catalog refresh rejected
it. Quarantining only the fresh clone's generated reports outside its project
allowed normal retry and receipt acknowledgment; no schema check was weakened.
Production scratch exclusion passed but post-release guard handoff took 24–26 s;
production capacity remains unproved. See the October 26 evidence artifacts.

The apparent soil writer stall followed a fast Parquet write. A missing catalog invoked native traversal of 4,561 NFS-backed files, holding the GIL long enough to miss Uvicorn's five-second heartbeat. Production probes measured 8.56 s scan and 5.70 s heartbeat gap; local temporary Parquet write was 0.011 s, not an NFS write benchmark.

Actual cross-host testing found `flock` did not exclude an NFS client from a server-local filesystem contender. POSIX `lockf` with per-owner thread coordination passed both cross-host and same-process tests. Independent review also exposed same-size/mtime schema replacement and parent-to-child source override cases; strict barriers must read actual source schema and select the current authorized source.

Existing report helpers generally check missing catalog membership, not freshness of already-indexed schemas/paths. Existing restore deletes `_query_engine`, so a lock there cannot fence managed lifecycle replacement. Queue deduplication alone cannot recover a crash between artifact publication and invalidation.

The unchanged 184-year isolated model produced duplicate daily observations in raw `H1.wat.dat` beginning simulation year 104. The strict water-balance report rejects those observations; catalog query, authenticated summary and exact-byte download pass. The watershed then failed at simulation year 100 at 22:59:54 UTC with `PASS components error: SOURCES3 date mismatch` and `STOP 1`. Original production raw output is absent, so baseline attribution is unproved; the paired native build also includes explicitly recorded preexisting calendar/HBP edits. The scoped supervisor stopped on failure without finalization. Retain these acceptance limitations without changing scientific inputs or weakening validation.

## Decision Log

- 2026-10-28: operator directs catalog maintenance onto default because batch backlog can last days. Execute the October 28 contract decision; retain cap, timing, guards and disabled production mode.
- 2026-10-27 / operator: “complete pending work” resumes the bounded pilot after the separately authorized full canonical deployment completed on all three hosts. Reuse the existing controller and normal batch workers; no source overlay, service restart, broader namespace mutation or general async enablement is needed. The canonical pilot explicitly excludes general enablement even after success; finish its evidence and disposition the distinct whole-fleet capacity gate honestly.
- 2026-10-27 / operator: “standby. we will do a full deploy when the jobs clear”. Preserve the active-job gate and select the full canonical deployment path after quiescence. The one-job exception proposal is not approved; retain the scoped candidate as historical preparation. Commit/push authorization does not resume deployment.
- 2026-10-27 / operator: “execute the bounded pilot” authorizes the proposed guard and actual shared-batch pilot. General enablement remains excluded; ordinary disabled-mode behavior must remain unchanged.

- 2026-10-27 / operator: “i don’t care about the read only mount” dispositions
  the proposed legacy-routing scope question. Keep that preexisting workflow
  limitation outside this catalog release and remove it as a rollout blocker.
  Do not infer permission to alter mounts, routing, authorization or cancellation.
  Preserve all four catalog namespaces and the passing external-guard evidence.

- 2026-10-27 / operator: “proceed as recommended” authorizes the four remediation
  steps above within this package. HTTP thread offload is a conformance fix for
  responsive serving with unchanged synchronous result/error/auth semantics and
  the already released native GIL. Regression must show unrelated requests make
  progress during a held freshness guard, and freshness still waits for release.
  Inventory design is under independent review before implementation; preserve
  durable progress and stale-writer fencing without a new service/queue/store.

- 2026-10-26 / rollout evidence: retain disabled production mode while namespace,
  inventory progress/capacity and HTTP contention conditions remain unmet. Do not
  exclude active legacy projects or change production mount permissions to make a
  preflight pass. This is a measured gate result, not an operational-default change.

- 2026-10-26 / operator: `wepp_261021` should resolve the SOURCES3 failure; proceed with acceptance and rollout-preparation steps. Regenerate both hillslope and watershed outputs on a fresh isolated clone, preserving the failed case and all scientific inputs except executable selection. Production enablement remains gated on scientific, identity, coordination and capacity evidence; no affected-user-project repair is implied.

- 2026-10-23 / operator and reviewed checkpoint: Async preferred for eligible producer notifications; preserve explicit synchronous APIs and externally synchronous readers/finalizers.
- 2026-10-23 / reviewed contract: Durable immutable receipt acknowledgment plus recurring source reconciliation; Redis admission/discovery is not sole durable intent.
- 2026-10-23 / reviewed contract: Stable external managed-owner guard; standalone local mode only outside managed identity/roots; preserve READONLY offline preparation exception.
- 2026-10-23 / implementation review: Preserve explicit permitted parent `fs_path` selection without a matching producer receipt; captured producer intent and full recurring reconciliation advance canonical child selection. Canonical Reader freshness section retains the rationale.
- 2026-10-23 / implementation: Enabled mode requires explicit root configuration; unavailable configured namespaces are degraded and retried. Default remains disabled. ADR-0104 records provisional operational bounds and required fleet measurement.
- 2026-10-23 / scaffold: Implement prerequisites and prove consumer compatibility before any producer wave is enabled. Public pending-state API/UX changes are not part of initial execution.
- 2026-10-23 / validation: Keep the full isolated scientific run unchanged after discovering duplicate raw daily records. Record the independent report failure and expected finalizer limitation separately from successful catalog behavior; a scientific repair is outside this catalog change.
## Outcomes & Retrospective

2026-10-28: default routing is implemented and focused/local normal-worker checks pass. Admission history survives migration and legacy authority is rejected. [Validation](../../artifacts/20261028_default_queue_validation.md) retains evidence and review dispositions; full pytest stopped at preexisting Roads provenance mismatch after 6,810 passed/61 skipped. No full-suite pass is claimed; production unchanged.

The authorized implementation, full deployment and actual bounded pilot are
complete. See [production acceptance](../../artifacts/20261027_shared_pilot_acceptance.md)
and [sanitized results](../../artifacts/20261027_shared_pilot/summary.json).
The pilot finished 17 jobs on seven genuine workers across both batch hosts,
verified both artifact waves and preserved ordinary disabled-mode behavior.
The reconstructed outstanding peak was seven; ten-second samples peaked at four.

General fleet enablement remains HOLD. The one ordinary job observed was already
running, so this is not new-arrival delay evidence. The intentional drained
controller restart left a 90.32-second observation gap. Lifecycle retirement
preserved source/catalog bytes and receipt histories but replaced original
refresh-status bytes before a separate snapshot; exact status replay is unavailable.
Future cleanup must snapshot that metadata first. The independent reviewer also
retained an unexercised low-priority late-deadline readback limitation.

Earlier scientific, inventory, HTTP and local regression evidence remains valid
for its recorded scope. No user project was repaired or mutated by this pilot,
and no general async configuration was enabled. Whole-fleet capacity requires a
separately bounded rollout acceptance, not another equivalent component probe.

## Context and Orientation

Authoritative specification: `docs/schemas/query-engine-catalog-refresh-contract.md`; five related canonical amendments are enumerated in `artifacts/2026-10-23_contract_decision.md`. Evidence inventory: `artifacts/caller_matrix.md` (79 calls, 41 files, transitive wrappers and direct readers/writers). Independent contract reviews and disposition are in the same artifacts directory.

`wepppy/query_engine/activate.py` owns current update/activation and catalog publication. `context.py`, `core.py`, server/MCP routes, `wepppy/wepp/reports/helpers.py` and domain readers consume catalog-selected paths/schema. `wepppy/rq/wmesque_rq.py` supplies transactional admission precedent; Runs catalog is a separate PostgreSQL projection, not a destination for these assets. `wepppy/tools/scheduler.py` and `docker/scheduled-tasks.yml` provide existing scheduling. Project fork/archive/restore and combined-viewer preparation also modify catalog state.

Native GIL boundary: sibling repository `/home/workdir/wepppyo3`, `wepp_interchange/src/lib.rs:catalog_scan` and `catalog.rs`. Observed scaffold baseline: `c941cb6f17884904bf1420ad0ed8a808bac5c330`; record actual revision and dirty state before implementation. Do not overwrite or absorb unrelated sibling changes. No new branch without operator direction.

## Milestones and Plan of Work

### M0 — Admission and environment map

Verify `git merge-base --is-ancestor dc2b2ddbe HEAD`. Read nearest AGENTS for every touched subsystem and sibling native repository; read the testing skill before gates and production operator skill before production access. Re-run direct/aliased call inventory against current source; annotate drift in caller matrix rather than treating old line numbers as permanent truth. Record supported project roots, nested scenarios, shared batch consumers, standalone tools, lock-order participants and current queue/scheduler behavior. Name exact source files for each implementation slice before editing them.

Acceptance: no unresolved authority conflict or unclassified new caller; native paired-release/build path and production-equivalent test environment identified. Missing environment access blocks that evidence grade, not unrelated local implementation work.

### M1 — Publication, identity and native boundary

Implement catalog identity, atomic catalog publication and digest-bound status using focused query-engine collaborators. Bring all synchronous and asynchronous publishers into the shared guard protocol before enabling background work. Include combined-viewer exclusive publication/rollback and project lifecycle operations; preserve their existing contracts. Managed guard lives outside replaceable trees, with documented lock ordering. Standalone temporary directories retain synchronous operation without Redis or `/wc1` access.

Refactor native catalog traversal to release the GIL during filesystem work and construct Python objects only with the GIL held. Exclude exactly `_query_engine/refresh/**` from query indexing while preserving browse/archive records; implement matching subtree behavior. Preserve existing catalog schema, path precedence and offline best-effort API semantics. Native release/build instructions come from that repository, not an invented wheel workflow.

Acceptance: real concurrent publishers never expose partial JSON or overwrite newer publication; restore/delete/recreate rejects old-incarnation scans; standalone and READONLY offline preparation pass. Native heartbeat probe runs during real catalog traversal. Cross-host NFS guard evidence is required before rollout even if local tests pass.

### M2 — Durable request, queue admission and recovery

Add `request_catalog_refresh(wd, asset_path=None)` without changing the synchronous API return shapes. Persist unique request receipts after artifact publication; return durable intent/admission distinctly. Implement one active admission per exact scope using existing Redis/RQ transactions and canonical prefixed maintenance IDs. Use existing default queue and scheduler dispatch; verify every eligible consumer's protocol/storage/coordination compatibility.

Worker snapshots finite receipt IDs, coalesces paths, performs index-only scan/update, publishes under the shared guard with current revision/incarnation checks, records acknowledgment and removes only incorporated receipts. Failed or late requests remain pending. Implement ownership-safe release/successor and bounded passes. Reconciliation discovers durable requests despite Redis loss and performs recurring source reconciliation for changes with no receipt. Define measured cycle/backoff/budget configuration and operator visibility; assess ADR requirements before introducing thresholds/defaults under the parameterization standard.

Acceptance: real Redis concurrency, WATCH contention, ambiguous enqueue outcome, kill/restart, final-check race and no-worker cases converge without duplicate active admission or lost requests. Kill immediately after artifact rename before receipt creation; reconciliation must repair without a later user request. Demonstrate bounded admission and visible cycle progress for representative project counts.

### M3 — Freshness barriers and maintenance disclosure

Upgrade internal readers affected by candidate producers before migration. A freshness barrier validates required receipt/source identity, incorporates required changes, reads actual schema/path selection and reloads held contexts. Existing catalog presence is not sufficient. Cover report helpers, run context, Geneva, query planning, return-period initial activation and domain finalizers. Preserve external synchronous response shapes, report-cache selection checks, GL session reload behavior, Roads source lifecycle and explicit activation semantics. Do not wait on a child task queued behind the only worker occupied by its parent; use coordinated inline finalization or a proven dependency layout.

Classify `query_catalog_refresh_` before job payload deserialization in all relevant polling paths. Preserve successful jobstatus shape; job-info returns only the contract's sanitized fields. Unknown/expired, recursive, batch, failed imports and rollback-retained IDs remain safe. Detail remains in existing authorized project inspection.

Acceptance: already-cataloged files with changed schema/alias/fs_path cannot produce stale immediate queries/reports; contexts reload. Public polling cannot disclose paths, receipts or traceback. Existing synchronous activation and finalizer tests pass with real required-entry readback.

### M4 — Incident producer wave

Migrate managed soils, landuse, DEM and watershed notifications in the caller matrix to explicit asynchronous requests. Cover alias/import injection and best-effort wrappers; invalidation failure must be observable and recoverable, not silently swallowed. Reusable standalone operation remains explicit synchronous mode. Coalesce overlapping Peridot paths. Preserve primary model job responses and generated input values.

Acceptance: isolated Mill Creek project with absent catalog submits without catalog traversal in the serving process. Inspect generated model input/output and catalog semantics, then run immediate UI/report consumer and finalizer. Repeat with populated and malformed catalog, queue/storage outage, and simultaneous projects. No production project mutation is required for the reproduction.

### M5 — Remaining producer waves

Convert eligible managed climate, module, interchange and nested Omni/PathCE notifications by caller family. Keep mixed A/C reusable scientific functions operable without Redis when standalone. Return-period trailing notifications are separate from the retained initial barrier. Leave migrations/admin CLI, explicit activation APIs, READONLY combined-viewer workflow and readiness finalizers synchronous unless their required barrier is implemented within the existing response contract.

Acceptance: update every matrix row with implemented source revision, regression/artifact evidence or explicit retained-sync disposition. No blanket rename. Verify nested scope admission independence and authorized parent-source precedence. No completed wave may rely solely on mocks of catalog writes.

### M6 — Validation and independent implementation review

Populate `artifacts/execution_evidence.md`. Run focused tests after each slice; complete substantive repository gates once changes settle. Update RQ dependency documentation, generated graph if drift is reported, and inspect a real job tree. Validate visible diagnostics through authenticated browser/download plus byte-preserving archive/restore under actual identities/mounts/umask. Check reconciliation capacity rather than assuming coalescing bounds distinct-project backlog.

Obtain independent correctness and security reviews; agents do not approve their own implementation. Close medium/high findings with post-fix confirmation. Update affected developer, operator and user docs to explain actual readiness/status and recovery. Retain limitations and distinguish local tests from environment validation.

### M7 — Handoff and separately authorized rollout

Record exact Python/native revisions, build artifacts and compatibility preflights. Inspect canonical deployment entry point before proposing rollout. Preserve existing identities, mounts and orchestration. Deployment is not included in scaffold authority. When separately authorized, verify live workflow, queue/tree and artifact readback before claiming incident resolved; repairing Jackson's runs is a distinct recorded action.

Rollback: stop new admission, reconcile/drain workers and preserve pending receipts/diagnostics. Restore synchronous producers only with compatible common publication/lifecycle guard; keep maintenance-ID sanitization through retention. No mixed-version publisher rollout without demonstrated coordination compatibility.

## Concrete Steps and Validation Commands

Run from `/home/workdir/wepppy`, using canonical wrappers and nearest instructions:

```bash
git merge-base --is-ancestor dc2b2ddbe HEAD
wctl run-pytest tests/query_engine --maxfail=1
wctl run-pytest tests/nodb tests/rq --maxfail=1
wctl check-rq-graph
wctl run-pytest tests --maxfail=1
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref dc2b2ddbe
python3 tools/code_quality_observability.py --base-ref dc2b2ddbe
wctl doc-lint --path docs/work-packages/20261023_query_catalog_async_refresh
```

Select focused new/existing report, lifecycle and route tests before broader suites. Run `wctl run-stubtest <changed-module>` and `wctl check-test-stubs` if API/stubs change. Frontend edits require `wctl run-npm lint` and `wctl run-npm test`; this plan does not authorize an unnecessary frontend redesign. Run native tests/build per sibling guidance and record exact commands/results. After graph drift, use only `python tools/check_rq_dependency_graph.py --write`, then recheck. Capture failures and dependencies honestly; no arbitrary pass counts are promised.

## Interfaces and Dependencies

Proposed focused implementation locations (names may follow adjacent established patterns): `query_engine/catalog_refresh.py` for durable intent/status/barrier helpers; `rq/query_catalog_rq.py` for admission/worker; existing scheduler integration. Prefer cohesive small helpers over a generic queue framework. `request_catalog_refresh` is additive; synchronous update/activation retain signatures/returns. Filesystem receipts, status, attempt evidence and reserved job prefix follow the canonical contract exactly. Lifecycle/native files are coupled prerequisites, not optional later hardening.

No new service, queue, datastore, dependency or deployment topology. File coordination on existing shared storage is explicitly contracted. Registry/roots enumeration and companion consumers must be resolved in M0, not guessed.

## Idempotence and Recovery

All probes use isolated copies and unique namespaces unless explicitly authorized otherwise. Repeated admission coalesces; repeated acknowledgment replays safely; failures retain evidence. Never remove an external guard inode as cleanup. Preserve unrelated dirty files and generated Usersum index. Maintain the package tracker and this plan after every milestone. Contract changes discovered during execution require a new reviewed ancestor checkpoint before affected behavior changes.

## Artifacts and Acceptance Claims

Use `artifacts/execution_evidence.md` for status, exact commands, project IDs, timestamps, revisions and semantic readback. Record implemented, locally validated, environment validated, deployed, repaired and incident resolved separately. Persisted state/RQ success alone cannot prove output correctness. This package closes only after every selected migration row is implemented or explicitly retained synchronous, reviews are clear, and residual deployment/repair scope is accurately handed off.

2026-10-23 revision note: recorded completed implementation/review and segmented regression, the transactional enqueue metadata correction, and the terminal scientific failure. M4/M6 remain open because successful catalog behavior cannot substitute for the failed full-workflow acceptance criterion. All isolated model workers stopped; private diagnostic artifacts remain available for follow-up.

Commit/push handoff: user authorized committing and pushing the implementation. This checkpoint includes the reviewed task files and retained validation evidence; paired native commit is `47e51b8e73146872056b68934977db56d91c9119`. Earlier uncommitted-state notes are chronological. Scientific acceptance remains blocked, async rollout remains disabled, and no deployment or production repair is authorized by this push.

## 2026-10-26 resumed acceptance and compatibility plan

Preserve `/wc1/runs/qc/qcat-mill-creek-20261023` and its failure artifacts. Create
`qcat-mill-creek-20261026` from its scientific inputs using independent files,
excluding generated model outputs, admission/catalog state, run logs and inherited
job markers. Rebase NoDb paths with canonical fork helpers and reset fork metadata.
Record the exact binary/sidecar hashes and input comparison before submission.
Select only `wepp_261021`; preserve 184 years and 1908 hillslopes. Use scoped local
queues and process-local async settings so normal consumers are not reconfigured.
Validate raw daily uniqueness/calendar progression, full watershed completion,
finalizers, catalog convergence, report semantics and authenticated downloads.
No schema/data migration of existing projects is performed.

In parallel, retain read-only production native/protocol/identity/mount and
consumer-fleet evidence, bounded inventory/capacity measurements and a concrete
root/configuration/rollback proposal. Reconcile deployment chronology in package
status without treating deployed-but-disabled code as async acceptance.

2026-10-26 revision: refreshed deployment chronology and retained the strict clone-cache failure/recovery and production latency limitation while full model acceptance executes.

Revision (2026-10-27): reconciled the completed full deployment and bounded shared-batch pilot; retained the separate general-capacity hold and exact observation/retirement evidence limits. No runtime code or general enablement changed.

## October 28 execution sequence

Review and commit `artifacts/20261028_default_queue_contract_decision.md` with
canonical amendments first. Update `query_catalog_rq.py`, `_query_catalog_admission.py`,
`_query_catalog_pilot.py` and `tools/query_catalog_pilot.py` for default routing,
queue-bound compatibility and historical evidence retention. Update actual Redis
worker fixtures and add backlog/isolation/legacy regressions. Run focused tests,
`wctl check-rq-graph`, local live job-tree/artifact checks and broad pytest. Update
the queue catalog, operations guide and this plan/tracker with exact results.
Rollback local code through an ordinary revert; production queue migration is
separate, requires old-work drain, and must preserve receipts/ledger/pilot history.

Acceptance means jobs actually run on default with verified catalog artifacts
while batch backlog exists, default backlog defers admission, and incompatible
workers cannot execute. No production deploy or general enablement is claimed.
