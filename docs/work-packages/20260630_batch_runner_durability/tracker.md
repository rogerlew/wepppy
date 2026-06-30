# Tracker - Batch Runner Durability

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-30 19:56 UTC
**Current phase**: Discovery / Backlog
**Last updated**: 2026-06-30 19:56 UTC
**Next milestone**: Implement durable leaf status classification and retry selection tests
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260630_batch_runner_durability/artifacts/2026-06-30_security_review.md`

## Task Board

### Ready / Backlog
- [ ] Add a durable leaf status classifier to `BatchRunner` that combines enabled `RedisPrep` task timestamps, run directory existence, and terminal metadata.
- [ ] Write success metadata from `run_batch_watershed_rq` and overwrite stale failed metadata on successful reruns.
- [ ] Filter `run_batch_rq` watershed enqueue targets to missing/incomplete/failed leaves when `TaskEnum.if_exists_rmtree` is disabled.
- [ ] Preserve explicit full-rerun behavior when `TaskEnum.if_exists_rmtree` is enabled.
- [ ] Add Run Batch active-job conflict handling to `wepppy/microservices/rq_engine/batch_routes.py`.
- [ ] Update runstate API/CLI output so operators can explain retry eligibility and terminal status.
- [ ] Add focused route, RQ, and blueprint regression tests.
- [ ] Run `wctl check-rq-graph` and update `wepppy/rq/job-dependencies-catalog.md` if graph drift is expected.
- [ ] Complete security review artifact before rollout.

### In Progress
- [ ] None.

### Blocked
- [ ] Production rollout blocked until active `nasa-roses-202606-psbs` batch jobs finish or are explicitly canceled.

### Done
- [x] Inspected current Batch Runner enqueue, worker, runstate, and RQ Engine route paths. (2026-06-30 19:56 UTC)
- [x] Pulled `wepp1` RQ/job/run-metadata evidence for `nasa-roses-202606-psbs`. (2026-06-30 19:56 UTC)
- [x] Scaffolded package, tracker, active ExecPlan, evidence artifact, and security review placeholder. (2026-06-30 19:56 UTC)

## Timeline

- **2026-06-30 19:56 UTC** - Package created after production batch `nasa-roses-202606-psbs` exposed retry/durability gaps during a climate-year configuration failure and restart.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Stale failure metadata causes completed leaves to rerun forever. | High | Medium | Make enabled task completion and newer success metadata authoritative. | Open |
| Active duplicate Run Batch submissions enqueue overlapping leaf jobs. | High | Medium | Reuse `_active_batch_job_summaries` in the run route and worker-side checks. | Open |
| Finalizer reports completion while leaf jobs returned `(False, elapsed)`. | Medium | High | Add summary metadata/status messages that report failed/enqueued/skipped counts. | Open |
| Queue graph/catalog drifts after enqueue filtering. | Medium | Low | Run `wctl check-rq-graph`; update catalog if dependencies change. | Open |
| Retry filter skips a leaf that should rerun after directive changes. | High | Medium | Treat `if_exists_rmtree` as explicit full-rerun mode and document directive semantics. | Open |

## Hardening Signal Log

- **Baseline health signals**: Current Run Batch enqueues every watershed feature; failed worker exceptions are caught and represented as RQ `finished` with result `(False, elapsed)`; failure metadata is written only on exception.
- **Post-change health signals**: Retry submission count matches failed/incomplete leaf count; completed leaves are skipped with reasons; stale failed metadata is cleared by success; route rejects active duplicate submissions.
- **Danger signals observed**: RQ `exc_info` is empty for failed leaves because `run_batch_watershed_rq` catches exceptions; production run metadata currently has 36 failed leaves while the live batch is still active.
- **Temporary callus register**: None.
- **Softening experiments**: Remove ad hoc/manual failed-run lists once retry selection is proven on a large batch.

## Verification Checklist

### Code Quality
- [ ] Focused RQ tests passing: `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`.
- [ ] Focused RQ Engine route tests passing: `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1`.
- [ ] Focused Batch Runner endpoint tests passing: `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1`.
- [ ] Queue graph checked with `wctl check-rq-graph`.

### Security
- [ ] Security impact triage recorded with rationale.
- [ ] Dedicated security review artifact is complete.
- [ ] No unresolved medium/high security findings remain.
- [ ] Run Batch auth, role, and queue-surface behavior are regression-tested.

### Documentation
- [ ] Work package closure notes complete.
- [ ] Operator/developer docs updated for retry semantics.
- [ ] RQ dependency catalog updated if enqueue graph changes.

### Testing
- [ ] Existing successful leaves without success metadata are skipped when all enabled tasks are complete.
- [ ] Failed or incomplete leaves are enqueued on a subsequent Run Batch.
- [ ] Missing run directories are enqueued.
- [ ] `if_exists_rmtree` enqueues all leaves and resets workspaces.
- [ ] Success metadata overwrites stale failed metadata.
- [ ] Active batch jobs return `409 batch_busy` on Run Batch.

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

## Watch List

- **Production active jobs**: `nasa-roses-202606-psbs` still had active queued jobs at the scoping sample. Re-check before any deployment or production verification.
- **Stale metadata**: Existing failed `run_metadata.json` files remain valid evidence but must not become the sole retry filter.
- **WEPP returncode -8**: Retry orchestration should expose these failures, not hide or reinterpret model-level failures.

## Communication Log

### 2026-06-30 19:56 UTC: User incident context
**Participants**: User, Codex
**Question/Topic**: Batch was started without observed climate years, canceled, fixed, and restarted. User wants Run Batch to later rerun only failed leaves based on per-project task status.
**Outcome**: Scaffold this durability package and capture `wepp1` evidence for implementation.
