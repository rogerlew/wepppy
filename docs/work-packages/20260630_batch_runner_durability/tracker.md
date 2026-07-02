# Tracker - Batch Runner Durability

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-30 19:56 UTC
**Current phase**: Implementation updated locally / rollout pending
**Last updated**: 2026-07-01 19:54 UTC
**Next milestone**: Production rollout preflight after active batch jobs finish or are canceled
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260630_batch_runner_durability/artifacts/2026-06-30_security_review.md`

## Task Board

### Ready / Backlog
- [ ] Production rollout preflight: confirm no active jobs for the target batch, then deploy through the normal production gate when requested.
- [ ] Post-rollout observation: verify a completed partial batch rerun enqueues only retry-eligible leaves.

### In Progress
- [ ] None.

### Blocked
- [ ] Production rollout blocked until active `nasa-roses-202606-psbs` batch jobs finish or are explicitly canceled.

### Done
- [x] Inspected current Batch Runner enqueue, worker, runstate, and RQ Engine route paths. (2026-06-30 19:56 UTC)
- [x] Pulled `wepp1` RQ/job/run-metadata evidence for `nasa-roses-202606-psbs`. (2026-06-30 19:56 UTC)
- [x] Scaffolded package, tracker, active ExecPlan, evidence artifact, and security review placeholder. (2026-06-30 19:56 UTC)
- [x] Added durable leaf status classification combining run directory existence, enabled task timestamps, and terminal metadata. (2026-06-30 20:22 UTC)
- [x] Added retry-aware default enqueue filtering and full-rerun preservation for `TaskEnum.if_exists_rmtree`. (2026-06-30 20:22 UTC)
- [x] Added success metadata writes and retained failure metadata with task status context. (2026-06-30 20:22 UTC)
- [x] Added route-level and worker-side active batch job guards. (2026-06-30 20:22 UTC)
- [x] Updated Batch Runner README and RQ dependency graph artifacts. (2026-06-30 20:22 UTC)
- [x] Completed focused validation and security review artifact. (2026-06-30 20:22 UTC)
- [x] Dispatched dual-agent correctness/security reviews and dispositioned all actionable findings. (2026-06-30 20:45 UTC)
- [x] Fixed batch retry NoDir lock collisions by using path-scoped runtime maintenance locks for child roots. (2026-06-30 21:18 UTC)
- [x] Fixed reused-leaf retry crashes caused by stale NoDb controller locks after canceled climate builds. (2026-06-30 22:33 UTC)
- [x] Fixed stale path-scoped runtime locks left by dead prior worker containers before retry enqueue. (2026-06-30 22:47 UTC)
- [x] Fixed parent Run Batch job failure caused by returning an unserializable RQ `Job` object. (2026-06-30 23:08 UTC)
- [x] Fixed watershed retries resuming past interrupted hillslope interchange outputs. (2026-06-30 23:51 UTC)
- [x] Fixed stale cloned base climate attributes by selecting drifted leaves, resyncing critical `_base/climate.nodb` fields, and invalidating climate/downstream timestamps. (2026-07-01 19:54 UTC)

## Timeline

- **2026-06-30 19:56 UTC** - Package created after production batch `nasa-roses-202606-psbs` exposed retry/durability gaps during a climate-year configuration failure and restart.
- **2026-06-30 20:22 UTC** - Local implementation completed with focused tests and queue graph validation passing; production rollout remains blocked by active-job preflight.
- **2026-06-30 20:45 UTC** - Dual-agent review findings fixed and covered by expanded regression tests; production rollout still pending.
- **2026-06-30 21:18 UTC** - Local retry of `durability_test` exposed stale legacy NoDir locks; batch child mutation locks now use effective-root path scope with bounded retry.
- **2026-06-30 22:33 UTC** - Local retry progressed past NoDir locks and then exposed stale NoDb climate locks in reused child workspaces; batch child startup now clears NoDb cache/locks before loading controllers.
- **2026-06-30 22:47 UTC** - Local retry exposed a stale path-scoped WA-174 climate lock from a dead prior worker container; parent Run Batch now clears exact path-scoped locks for selected leaves after active-job preflight and before enqueue.
- **2026-06-30 23:08 UTC** - Parent `run_batch_rq` dashboard status showed failed/canceled despite publishing `COMPLETED`; RQ recorded `Unserializable return value`, so the parent now returns a serializable summary dict.
- **2026-06-30 23:51 UTC** - Local retry exposed missing `H.wat.parquet`/`H.pass.parquet` after an interrupted hillslope interchange conversion; watershed retries now ensure hillslope interchange outputs before watershed resumes.
- **2026-07-01 19:54 UTC** - Production retry exposed leaves initialized before base observed climate years were set; classifier now marks base-climate drift as retry eligible and worker startup resyncs critical climate config from `_base`.

## Decisions Log

### 2026-06-30 19:56 UTC: Treat task completion as compatibility source of truth
**Context**: Existing successful batch leaves do not write success metadata. Failed leaves write `run_metadata.json`, but a later successful rerun before this package lands would not overwrite old failure metadata.

**Options considered**:
1. Use only `run_metadata.json` status - simple, but stale failed metadata can cause endless reruns.
2. Use only `RedisPrep` timestamps - backward-compatible, but less explanatory and cannot carry terminal error details.
3. Combine enabled task timestamps with terminal metadata - compatible with old runs and provides durable future status.

**Decision**: Use complete enabled task timestamps as the compatibility signal for old runs, and add success metadata so future runs have an explicit terminal state.

**Impact**: Retry selection must classify a leaf as complete when all enabled tasks are timestamped, even if no success metadata exists. A failed metadata record only forces retry when it is not superseded by complete task state or by newer success metadata.

### 2026-06-30 19:56 UTC: Keep explicit full rerun behind `Remove existing files`
**Context**: Operators still need a deliberate way to regenerate every leaf after base-project or directive changes.

**Options considered**:
1. Make Run Batch always retry only failed leaves.
2. Add a new route parameter for retry mode.
3. Reuse the existing `TaskEnum.if_exists_rmtree` directive as the full-rerun switch.

**Decision**: Default Run Batch should be retry-aware. Enabling `Remove existing files` should preserve full-rerun behavior.

**Impact**: Tests must prove both paths: default skip-complete behavior and explicit full-rerun behavior.

### 2026-06-30 20:22 UTC: Exclude directive/non-leaf tasks from completion proof
**Context**: `TaskEnum.if_exists_rmtree` is a directive that resets a workspace, not a timestamped leaf task. `TaskEnum.run_omni_contrasts` is present in `BatchRunner.DEFAULT_TASKS`, but the batch watershed worker does not execute it as part of the per-leaf chain.

**Options considered**:
1. Treat every enabled directive as required completion proof - simple but makes full-rerun or contrast directives mark leaves incomplete forever.
2. Require only tasks that the leaf worker actually timestamps.

**Decision**: Completion proof excludes `if_exists_rmtree` and `run_omni_contrasts`; full rerun is still controlled by `if_exists_rmtree` before retry filtering.

**Impact**: Retry filtering reflects the actual per-leaf execution chain and avoids permanent false positives for retry eligibility.

### 2026-06-30 20:45 UTC: Treat optional and invalid leaves explicitly
**Context**: Independent review found that optional RAP/OpenET directives can be enabled when the corresponding optional NoDb controllers are absent, and that generated leaf run IDs needed path-safety validation at both template and classifier boundaries.

**Options considered**:
1. Make success metadata override every missing enabled task - simple but unsafe for asynchronous Omni scenario completion.
2. Exclude every optional-looking task permanently - could hide missing required Omni work.
3. Exclude only RAP/OpenET completion tasks when their optional NoDb files are absent, and reject unsafe leaf run IDs explicitly.

**Decision**: Completion proof excludes absent RAP/OpenET optional controllers on a per-run basis, while unsafe generated or legacy leaf IDs become validation errors or `invalid` runstate rows.

**Impact**: Successful non-RAP/OpenET leaves do not rerun forever, and runstate/retry classification does not probe outside the batch `runs/` tree.

### 2026-06-30 21:18 UTC: Use path-scoped NoDir maintenance locks for batch leaves
**Context**: A local `durability_test` retry failed with `NODIR_LOCKED` on climate and soils roots. The lock owners were legacy runtime lock keys derived from the leaf name, for example `OR-154`, which can survive canceled attempts and collide across batches using the same leaf ID.

**Options considered**:
1. Clear runtime directory locks automatically on every retry - can hide active writer contention and weaken lock safety.
2. Keep legacy runid-scoped locks and wait for TTL expiry - preserves old behavior but leaves retries blocked by stale/cross-batch leaf-name keys.
3. Use effective-root path scoped locks for batch child roots with bounded retry.

**Decision**: Batch child root mutations use `effective_root_path` lock scope and retry `NODIR_LOCKED` briefly. The old legacy leaf-name lock key is no longer part of the batch child lock contention set.

**Impact**: Distinct batch child directories no longer contend just because they share a leaf ID, and stale legacy keys from canceled attempts do not block retry. Actual same-root contention still uses path-scoped locks.

### 2026-06-30 22:33 UTC: Clear stale NoDb locks before reused-leaf retries
**Context**: After the NoDir lock fix, `durability_test` retries for `OR-154`, `OR-204`, and `OR-20` failed immediately with empty `AssertionError` while entering `build_climate`. Each climate log stopped after `assert not self.islocked()`, matching the bare assertion in `ClimateBuildRouter.build()`.

**Options considered**:
1. Remove or weaken the climate controller assertion - hides a valid controller lock invariant.
2. Clear all batch locks globally before parent enqueue - risks interfering with unrelated active work.
3. Clear NoDb cache and locks for the specific composite child run at watershed worker startup.

**Decision**: `BatchRunner.run_batch_project()` now clears `clear_nodb_file_cache(runid)` and `clear_locks(runid)` for the specific child run before `RedisPrep` and NoDb controller instances are loaded, regardless of whether the workspace is freshly copied or reused.

**Impact**: Canceled climate builds no longer leave a reused child workspace stuck behind stale `climate.nodb` locks, while active duplicate batch submissions remain guarded by the route and worker active-job checks.

### 2026-06-30 22:47 UTC: Clear exact path-scoped runtime locks before retry enqueue
**Context**: The next `durability_test` retry showed WA-174 failing with `NODIR_LOCKED` on the climate root. The prior WA-174 climate build was still writing `_prism_revision()` files at 22:38 UTC, then the compose stack restarted; Redis retained the path-scoped lock with owner container `fbdc2c500f0a`, which was no longer running. Existing `clear_runtime_locks(runid)` is unsafe here because path-scoped batch locks store the leaf run id, so clearing `WA-174` could affect another batch with the same leaf id.

**Options considered**:
1. Clear runtime locks by leaf run id - simple but can clear locks from another batch that shares a leaf id.
2. Let stale locks expire after the default six-hour TTL - safe but blocks normal retry recovery after worker/container restarts.
3. Clear only the exact `wd`/root/`effective_root_path` lock keys for leaves selected by the parent retry run, after active-job preflight passes.

**Decision**: Add `runtime_lock_statuses_for_scope()` and `clear_runtime_locks_for_scope()` to target exact runtime lock keys, and call `BatchRunner.clear_retry_runtime_locks()` from `run_batch_rq()` after retry selection and active-job preflight but before child enqueue.

**Impact**: Run Batch can recover stale path-scoped runtime locks from dead prior workers without clearing same-named leaves in other batches. Normal active duplicate batch work remains blocked by route and worker active-job guards before cleanup runs.

### 2026-06-30 23:08 UTC: Return serializable parent Run Batch summary
**Context**: The parent job `871f4334-479d-4e63-95f8-f80fe9e01c98` published `COMPLETED run_batch_rq(durability_test)` but the dashboard showed failed/canceled. Inspecting the RQ job showed `result=Unserializable return value` and no `exc_info`; the function returned the live finalizer `Job` object after enqueue.

**Options considered**:
1. Return the finalizer `Job` object and rely on metadata - causes RQ result serialization failure.
2. Return only the finalizer job id string - serializable but loses useful selection context.
3. Return a small serializable summary dict containing batch name, finalizer job id, enqueued count, and selection summary.

**Decision**: `run_batch_rq()` returns a serializable summary dict and keeps the finalizer job id in parent job metadata.

**Impact**: The parent job can finish cleanly in RQ while still exposing the finalizer job id and retry selection summary for dashboards and diagnostics.

### 2026-06-30 23:51 UTC: Repair interrupted hillslope interchange before watershed retry
**Context**: A local `durability_test` retry reached watershed-only resume for `OR,WA-101` and `OR,WA-102` because `run_wepp_hillslopes` was timestamped while `run_wepp_watershed` was still missing. The earlier run had been interrupted during `ensure_hillslope_interchange()`, leaving partial files such as `H.soil.parquet.tmp` or `H.pass.parquet.tmp` and missing required `H.wat.parquet`/`H.pass.parquet`.

**Options considered**:
1. Clear the hillslope timestamp and rerun all hillslopes - robust but expensive when raw `H*.dat` outputs already exist.
2. Treat missing interchange files as classifier-level incompleteness - explanatory, but the immediate failure happens inside watershed execution before classification can help the resumed worker.
3. Ensure hillslope interchange whenever watershed is about to run, even if hillslopes are already timestamped.

**Decision**: `BatchRunner.run_batch_project()` now calls `ensure_hillslope_interchange()` before watershed execution whenever either hillslopes or watershed will run.

**Impact**: A watershed retry can rebuild missing hillslope interchange parquet from existing raw hillslope outputs before `wepp.run_watershed()` calls post-processing that depends on `H.pass.parquet` and `H.wat.parquet`. This avoids an unnecessary hillslope rerun while still failing explicitly if the raw source outputs are not recoverable.

### 2026-07-01 19:54 UTC: Resync stale cloned base climate attributes
**Context**: Production batch `nasa-roses-202606-psbs` showed many leaves failing with `ValueError: observed_start_year must be an integer year, got empty string`. The operator had set observed year bounds in the base project after the affected leaves were initialized, so retrying reused stale cloned `climate.nodb` files.

**Options considered**:
1. Require `Remove existing files` and rerun every leaf - reliable but wastes completed work and does not make the default retry path durable.
2. Copy whole NoDb files from `_base` into leaves - simple but risks copying generated base artifacts such as `cli_fn`, `par_fn`, `monthlies`, and cached station search output into leaf runs.
3. Compare and copy only critical climate configuration fields, then clear climate/downstream timestamps.

**Decision**: Implement climate-only base attribute drift detection and resync. The classifier marks drifted leaves retry eligible with `base_project_attributes_changed`; worker startup copies selected climate config fields and removes `build_climate`, RAP/OpenET, WEPP, and Omni scenario timestamps.

**Impact**: Corrected base observed years propagate to already-initialized leaves without full workspace replacement, while DEM, watershed, landuse, and soils artifacts remain valid.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Stale failure metadata causes completed leaves to rerun forever. | High | Medium | Make enabled task completion and newer success metadata authoritative. | Mitigated |
| Active duplicate Run Batch submissions enqueue overlapping leaf jobs. | High | Medium | Reuse `_active_batch_job_summaries` in the run route and worker-side checks. | Mitigated |
| Finalizer reports completion while leaf jobs returned `(False, elapsed)`. | Medium | High | Add summary metadata/status messages that report failed/enqueued/skipped counts. | Mitigated |
| Queue graph/catalog drifts after enqueue filtering. | Medium | Low | Run `wctl check-rq-graph`; update catalog if dependencies change. | Closed |
| Retry filter skips a leaf that should rerun after directive changes. | High | Medium | Treat `if_exists_rmtree` as explicit full-rerun mode and document directive semantics. | Mitigated |
| Changed-file broad exception enforcement flags existing boundary catches in touched files. | Low | High | No new broad catches were introduced; record as residual validation risk/follow-up. | Open |
| Optional RAP/OpenET tasks keep successful leaves retry-eligible when optional mods are absent. | High | Medium | Require optional task timestamps only when the corresponding optional NoDb file exists. | Mitigated |
| Delete worker clears locks before active-job guard. | High | Low | Move worker active-job check before cache/lock cleanup. | Closed |
| Unsafe generated leaf run IDs escape the batch run tree during classification. | Medium | Low | Validate generated template run IDs and fail closed in classifier. | Closed |
| Finalizer completion signal lacks failure counts. | Medium | Medium | Publish final run summary and failure-specific trigger while preserving compatibility trigger. | Mitigated |
| Stale legacy NoDir runtime locks block batch retries after cancellation. | High | Medium | Use path-scoped maintenance locks for batch child roots and bounded retry on real path contention. | Mitigated |
| Stale NoDb controller locks from canceled child builds crash reused retries with empty `AssertionError`. | High | Medium | Clear child-scoped NoDb cache and locks before each watershed worker loads `RedisPrep` and controllers. | Mitigated |
| Stale path-scoped runtime locks from dead prior worker containers block selected leaves for the full TTL. | High | Medium | Clear exact child/root path-scoped runtime locks after active-job preflight and before enqueue. | Mitigated |
| Parent Run Batch job is marked failed after enqueue because its return value is not serializable. | Medium | High | Return a serializable summary dict instead of a live RQ `Job` object. | Mitigated |
| Interrupted hillslope interchange leaves task timestamps complete but watershed parquet dependencies missing. | High | Medium | Ensure hillslope interchange before watershed resumes on retry. | Mitigated |
| Completed leaves are skipped even though cloned climate settings drifted from `_base`. | High | Medium | Compare critical climate config fields during classification and resync/invalidate downstream timestamps at worker startup. | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: Current Run Batch enqueues every watershed feature; failed worker exceptions are caught and represented as RQ `finished` with result `(False, elapsed)`; failure metadata is written only on exception.
- **Post-change health signals**: Retry submission count matches failed/incomplete/stale-base leaf count; completed leaves are skipped with reasons; stale failed metadata is cleared by success; route and worker reject active duplicate submissions; finalizer publishes failed/incomplete/missing/invalid counts; base-climate drift increments `base_stale` and clears only climate/downstream timestamps.
- **Danger signals observed**: RQ `exc_info` is empty for failed leaves because `run_batch_watershed_rq` catches exceptions; production run metadata currently has failed leaves while the live batch is still active; broad-exception changed-file enforcement flags pre-existing broad catches in touched files; stale legacy NoDir runtime locks can survive canceled local attempts; stale child NoDb controller locks can survive canceled climate builds; path-scoped runtime locks can survive dead worker containers until TTL; RQ records `Unserializable return value` when parent jobs return live `Job` objects; interrupted hillslope interchange can leave `.tmp` parquet files and missing `H.pass.parquet`/`H.wat.parquet` while the hillslope task timestamp is already set; leaf `climate.nodb` can retain empty observed years after `_base` is corrected.
- **Temporary callus register**: None.
- **Softening experiments**: Remove ad hoc/manual failed-run lists once retry selection is proven on a large batch.

## Verification Checklist

### Code Quality
- [x] Focused RQ tests passing: `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`.
- [x] Focused RQ Engine route tests passing: `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1`.
- [x] Focused Batch Runner endpoint tests passing: `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1`.
- [x] Queue graph checked with `wctl check-rq-graph`.

### Security
- [x] Security impact triage recorded with rationale.
- [x] Dedicated security review artifact is complete.
- [x] No unresolved medium/high security findings remain.
- [x] Run Batch auth, role, and queue-surface behavior are regression-tested.

### Documentation
- [ ] Work package closure notes complete.
- [x] Operator/developer docs updated for retry semantics.
- [x] RQ dependency catalog updated if enqueue graph changes.

### Testing
- [x] Existing successful leaves without success metadata are skipped when all enabled tasks are complete.
- [x] Failed or incomplete leaves are enqueued on a subsequent Run Batch.
- [x] Missing run directories are enqueued.
- [x] `if_exists_rmtree` enqueues all leaves and resets workspaces.
- [x] Success metadata overwrites stale failed metadata.
- [x] Active batch jobs return `409 batch_busy` on Run Batch.
- [x] Optional RAP/OpenET tasks are not required when their optional NoDb files are absent.
- [x] Unsafe generated run IDs are rejected before enqueue and classified as `invalid` if encountered later.
- [x] Finalizer reports failed/incomplete/missing/invalid counts.
- [x] Batch child directory-root locks use effective-root path scope instead of legacy leaf-name scope.
- [x] Reused batch leaves clear stale child NoDb locks before `RedisPrep` and controller loading.
- [x] Parent Run Batch clears exact selected-leaf path-scoped runtime locks after active-job preflight.
- [x] Parent Run Batch returns a JSON-serializable summary instead of a live RQ `Job`.
- [x] Watershed retries ensure hillslope interchange outputs before `wepp.run_watershed()`.
- [x] Leaves with stale cloned base climate attributes are retry eligible.
- [x] Worker startup resyncs critical climate attributes from `_base` and invalidates only climate/downstream timestamps.

### Deployment
- [ ] Tested in docker-compose.dev.yml environment.
- [ ] Production rollout plan records active-job preflight.
- [ ] Post-rollout observation window started.

## Progress Notes

### 2026-06-30 19:56 UTC: Initial scoping and production evidence
**Agent/Contributor**: Codex

**Work completed**:
- Read `wepp1-operator` and `docs-maintainer` skill guidance.
- Verified `wepp1` identity with `hostname` and `/workdir/wepppy` repo path.
- Inspected `wepppy/rq/batch_rq.py`, `wepppy/nodb/batch_runner.py`, `wepppy/microservices/rq_engine/batch_routes.py`, and existing batch tests.
- Pulled RQ job summaries for seven provided job IDs and run metadata summaries for the production batch.
- Created package scaffold and production evidence artifact.

**Blockers encountered**:
- The production batch still had active queued jobs during scoping, so no production mutation or rollout should happen from this session.

**Next steps**:
- Implement the durable status classifier with tests first.
- Add success metadata writes and retry enqueue filtering.
- Add active Run Batch route guard.
- Complete security review after code changes and before rollout.

**Test results**: Not run; documentation scaffold only.

### 2026-06-30 20:22 UTC: Local implementation and validation
**Agent/Contributor**: Codex

**Work completed**:
- Added `BatchRunner.classify_batch_run_states()`, `retry_eligible_watershed_features()`, and runstate summary helpers.
- Updated `run_batch_rq` to enqueue only retry-eligible leaves by default and all leaves in explicit full-rerun mode.
- Updated `run_batch_watershed_rq` to write success metadata and preserve failure metadata with task status context.
- Added active-job guards in both rq-engine route and worker parent job.
- Added focused RQ retry-selection tests and route busy tests.
- Updated Batch Runner README and regenerated RQ graph artifacts.

**Blockers encountered**:
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` fails because existing broad boundary catches are present in touched files. No new broad catches were introduced in this package.
- Production rollout remains blocked until target batch active jobs finish or are explicitly canceled.

**Next steps**:
- Human review of local implementation.
- Decide whether to address existing broad exception debt in this package or track as separate broad-exception work.
- Production preflight and rollout when requested.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 6 passed.
- `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1` - 9 passed.
- `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1` - 8 passed.
- `wctl check-rq-graph` - passed after regenerating graph artifacts.
- `git diff --check` - passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - failed on pre-existing broad catches in changed files.

### 2026-06-30 20:45 UTC: Dual-agent review disposition
**Agent/Contributor**: Codex with two spawned review agents

**Work completed**:
- Dispatched independent correctness/RQ and security/data-integrity reviews.
- Fixed optional RAP/OpenET completion semantics.
- Moved delete worker active-job guard before cache/lock cleanup.
- Made explicit full-rerun mode bypass pre-reset classification.
- Added generated run ID validation and classifier `invalid` state.
- Made metadata task-status diagnostics best-effort with `metadata_warnings`.
- Added finalizer run summary and failure-specific trigger.
- Validated run-batch route names before path resolution.

**Blockers encountered**:
- Concurrent endpoint/RQ pytest execution can collide on distributed BatchRunner locks; endpoint tests pass sequentially.
- Existing broad exception boundary catches remain a changed-file enforcement residual.

**Next steps**:
- Run final RQ graph/docs/static validation after documentation updates.
- Production preflight and rollout when requested.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 14 passed.
- `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1` - 10 passed.
- `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1` - 9 passed.

### 2026-06-30 21:18 UTC: Retry NoDir lock collision fix
**Agent/Contributor**: Codex

**Work completed**:
- Changed batch child directory-root mutation locks to use `effective_root_path` scope.
- Added bounded retry for real `NODIR_LOCKED` contention.
- Added regression coverage proving path-scope lock use and retry behavior.

**Blockers encountered**:
- Existing stale legacy Redis runtime locks may remain until TTL or manual clearing, but they no longer block batch child path-scoped locks.

**Next steps**:
- Re-run local `durability_test` after this change to verify the retry proceeds past climate/soils lock acquisition.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 14 passed.

### 2026-06-30 22:33 UTC: Retry stale NoDb lock cleanup
**Agent/Contributor**: Codex

**Work completed**:
- Diagnosed empty retry `AssertionError` failures as `ClimateBuildRouter.build()` asserting `not climate.islocked()` after canceled climate builds left stale child NoDb locks.
- Added child-scoped NoDb cache/lock cleanup at the start of every batch watershed run, including reused workspaces where `init_required` is false.
- Added regression coverage for the cleanup helper and ordering before `RedisPrep.getInstance()`.

**Blockers encountered**:
- Raw venv lock-status inspection could not authenticate to Redis; per-run climate logs and metadata were sufficient to confirm the failure path.

**Next steps**:
- Re-run local `durability_test` after this change to verify the retry proceeds past climate startup.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 16 passed.

### 2026-06-30 22:47 UTC: Retry stale path-scoped runtime lock cleanup
**Agent/Contributor**: Codex

**Work completed**:
- Diagnosed WA-174 `NODIR_LOCKED` as a stale path-scoped climate lock retained in Redis after the prior worker container died during climate revision generation.
- Added exact-scope runtime lock status/clear helpers so cleanup can target one child root instead of clearing every `WA-174` lock across batches.
- Wired parent `run_batch_rq()` to clear exact path-scoped locks for selected leaves after active-job preflight and before enqueue.
- Added runtime-path and BatchRunner/RQ regression coverage.

**Blockers encountered**:
- Existing stale locks in a running container still require worker restart or manual exact-scope clearing until the patched parent code is loaded.

**Next steps**:
- Restart/reload the batch worker before the next local retry so `run_batch_rq()` uses the new cleanup path.

**Test results**:
- `wctl run-pytest tests/runtime_paths/test_mutations_thaw_freeze_contract.py::test_clear_runtime_locks_for_scope_only_deletes_exact_path_scope --maxfail=1` - 1 passed.
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 17 passed.

### 2026-06-30 23:08 UTC: Parent Run Batch result serialization fix
**Agent/Contributor**: Codex

**Work completed**:
- Inspected RQ job `871f4334-479d-4e63-95f8-f80fe9e01c98` and confirmed status `canceled`, `result=Unserializable return value`, and no `exc_info`.
- Changed `run_batch_rq()` to return a serializable summary dict instead of the finalizer `Job` object.
- Updated type stubs and regression coverage to JSON-serialize the parent return.

**Blockers encountered**:
- Existing failed parent job status cannot be repaired retroactively; the next parent run will use the new return contract after worker reload.

**Next steps**:
- Restart/reload the batch worker before the next local retry so both runtime-lock cleanup and serializable parent return are active.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 17 passed.

### 2026-06-30 23:51 UTC: Watershed retry hillslope interchange repair
**Agent/Contributor**: Codex

**Work completed**:
- Diagnosed `OR,WA-101` and `OR,WA-102` retry failures as watershed-only resumes with missing hillslope interchange parquet dependencies (`H.wat.parquet` and `H.pass.parquet`).
- Confirmed the run directories still had raw `H*.pass.dat`/`H*.wat.dat` source outputs but partial `.tmp` interchange files from an interrupted prior conversion.
- Changed `BatchRunner.run_batch_project()` so watershed retries call `ensure_hillslope_interchange()` before `wepp.run_watershed()`, even when the hillslope task timestamp is already set.
- Stopped the remaining active `durability_test` old-code jobs, canceled the stale finalizer, restarted `rq-worker-batch`, and confirmed active `durability_test` queue count is zero.

**Blockers encountered**:
- Existing failed leaf metadata remains as evidence and should be superseded by the next successful retry; the old failed attempts cannot be repaired retroactively.

**Next steps**:
- Re-run local `durability_test`; expected behavior is that `OR,WA-101`/`OR,WA-102` rebuild missing hillslope interchange outputs before watershed execution.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 18 passed.

### 2026-07-01 19:54 UTC: Stale base climate attribute resync
**Agent/Contributor**: Codex

**Work completed**:
- Diagnosed the repeated `observed_start_year must be an integer year, got empty string` failures as existing leaves retaining cloned `climate.nodb` state after `_base` was corrected.
- Added climate base-attribute drift detection to `BatchRunner.classify_batch_run_state()`.
- Added worker-side climate resync before NoDb controller loading and invalidated only climate-dependent timestamps.
- Documented the implemented climate resync contract and deferred landuse/soils/WEPP/Ron/watershed resync criteria.

**Blockers encountered**:
- Production rollout remains pending; no production mutation was performed in this session.

**Next steps**:
- Deploy/reload batch workers through the normal production gate after active-job preflight.
- Re-run the target batch in retry mode and verify the selection summary reports stale-base leaves as enqueued.

**Test results**:
- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 21 passed.
- `wctl doc-lint --path docs/work-packages/20260630_batch_runner_durability` - 6 files validated, 0 errors, 0 warnings.
- `wctl doc-lint --path wepppy/nodb/README.batch-runner.md` - 1 file validated, 0 errors, 0 warnings.
- `wctl doc-lint --path PROJECT_TRACKER.md` - 1 file validated, 0 errors, 0 warnings.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - passed with net delta +0.
- `git diff --check` - passed.

## Watch List

- **Production active jobs**: `nasa-roses-202606-psbs` still had active queued jobs at the scoping sample. Re-check before any deployment or production verification.
- **Stale metadata**: Existing failed `run_metadata.json` files remain valid evidence but must not become the sole retry filter.
- **WEPP returncode -8**: Retry orchestration should expose these failures, not hide or reinterpret model-level failures.

## Communication Log

### 2026-06-30 19:56 UTC: User incident context
**Participants**: User, Codex
**Question/Topic**: Batch was started without observed climate years, canceled, fixed, and restarted. User wants Run Batch to later rerun only failed leaves based on per-project task status.
**Outcome**: Scaffold this durability package and capture `wepp1` evidence for implementation.

### 2026-07-01 19:54 UTC: User incident context
**Participants**: User, Codex
**Question/Topic**: Production retry still failed because leaves were initialized before observed climate dates were set in the base project. User requested hardening that resyncs critical base attributes and an assessment of invalidation criteria.
**Outcome**: Implemented climate-only base attribute drift detection/resync with targeted climate/downstream timestamp invalidation, and documented broader resync criteria.
