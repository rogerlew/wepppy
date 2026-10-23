# Execute asynchronous query catalog refresh

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current. The canonical contract controls behavior; this plan sequences implementation and evidence.

## Purpose / Big Picture

Remove catalog traversal from eligible artifact-producing requests without losing updates, breaking immediate reports, or allowing old background work to publish into a replaced project. Reproduce the Mill Creek submission failure on an isolated copy; prove responsive submission, actual model execution and correct catalog-backed consumption after repair.

The operator authorized committing the reviewed contract and scaffolding execution on 2026-10-23. This scaffold does not start implementation or authorize production deployment/repair. When instructed to execute, proceed milestone by milestone within the accepted contract; do not ask for repeated routine implementation approval.

## Progress

- [x] 2026-10-23 UTC: Contract and independent reviews committed as standalone ancestor `dc2b2ddbe8cfedbd4bae024310f03447ca813c32`.
- [x] 2026-10-23 UTC: Caller inventory and all ten review dispositions retained; execution plan, launch prompt and evidence matrix scaffolded.
- [ ] M0: Revalidate source inventory, native baseline, environment and implementation ownership.
- [ ] M1: Implement coordinated atomic publication and lifecycle identity, plus native GIL release.
- [ ] M2: Implement durable invalidation, coalesced admission, worker and recovery.
- [ ] M3: Implement internal freshness barriers and safe maintenance status.
- [ ] M4: Migrate incident producer wave and prove immediate consumers.
- [ ] M5: Migrate remaining eligible managed producers; preserve offline APIs.
- [ ] M6: Complete failure/race, artifact/browser/archive and regression validation; independent implementation reviews.
- [ ] M7: Record deployment/recovery readiness; deployment and production repair remain separately authorized actions.

## Surprises & Discoveries

The apparent soil writer stall followed a fast Parquet write. A missing catalog invoked native traversal of 4,561 NFS-backed files, holding the GIL long enough to miss Uvicorn's five-second heartbeat. Production probes measured 8.56 s scan and 5.70 s heartbeat gap; local temporary Parquet write was 0.011 s, not an NFS write benchmark.

Existing report helpers generally check missing catalog membership, not freshness of already-indexed schemas/paths. Existing restore deletes `_query_engine`, so a lock there cannot fence managed lifecycle replacement. Queue deduplication alone cannot recover a crash between artifact publication and invalidation.

## Decision Log

- 2026-10-23 / operator and reviewed checkpoint: Async preferred for eligible producer notifications; preserve explicit synchronous APIs and externally synchronous readers/finalizers.
- 2026-10-23 / reviewed contract: Durable immutable receipt acknowledgment plus recurring source reconciliation; Redis admission/discovery is not sole durable intent.
- 2026-10-23 / reviewed contract: Stable external managed-owner guard; standalone local mode only outside managed identity/roots; preserve READONLY offline preparation exception.
- 2026-10-23 / scaffold: Implement prerequisites and prove consumer compatibility before any producer wave is enabled. Public pending-state API/UX changes are not part of initial execution.

## Outcomes & Retrospective

Scaffold only. No runtime source edits, queue mutations, native builds, deployment or production repair. Contract ancestry gate is satisfied for future work based on this branch; runtime conformance remains pending.

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

Add `request_catalog_refresh(wd, asset_path=None)` without changing the synchronous API return shapes. Persist unique request receipts after artifact publication; return durable intent/admission distinctly. Implement one active admission per exact scope using existing Redis/RQ transactions and canonical prefixed maintenance IDs. Use existing batch queue and scheduler dispatch; verify every eligible consumer's protocol/storage/coordination compatibility.

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
