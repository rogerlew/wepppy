# Batch Runner Durability

**Status**: Open (2026-06-30)
**Timezone**: UTC

## Overview
The Batch Runner can resume work inside an enqueued watershed job by checking `RedisPrep` task timestamps, but pressing Run Batch currently enqueues every watershed feature again. This package makes Run Batch durable and restart-aware so an operator can fix a batch-wide input problem, press Run Batch again after active jobs finish, and enqueue only the missing, incomplete, or failed leaf runs.

## Objectives
- Make the default Run Batch action select only eligible watershed leaves: missing run directory, incomplete enabled task chain, or confirmed current-attempt failure.
- Persist terminal per-leaf run metadata for both success and failure so old failure records are overwritten by successful reruns.
- Preserve backward compatibility for existing batch runs that predate success metadata by treating complete enabled `RedisPrep` timestamps as successful unless a newer failure is proven.
- Add an active-batch guard so duplicate Run Batch submissions cannot overlap queued/started/deferred/scheduled batch work.
- Expose enough batch run state for the UI/API and operators to explain which leaves will rerun and why.

## Scope

### Included
- Batch enqueue selection in `wepppy/rq/batch_rq.py`.
- Per-leaf status classification and runstate reporting in `wepppy/nodb/batch_runner.py`.
- RQ Engine Run Batch behavior in `wepppy/microservices/rq_engine/batch_routes.py`.
- Regression coverage in `tests/rq/`, `tests/microservices/`, and `tests/weppcloud/`.
- Queue graph/catalog validation if enqueue dependencies or metadata edges change.
- Operator-facing docs and work-package artifacts for the `wepp1` incident signatures.

### Explicitly Out of Scope
- Automatically diagnosing or fixing WEPP `returncode=-8` model failures.
- Changing climate parameterization defaults, formulas, thresholds, or year-selection semantics.
- Reworking the Batch Runner UI beyond showing/using the durable runstate contract needed for retry decisions.
- Adding new external dependencies.
- Production deployment or hotfixing while `nasa-roses-202606-psbs` still has active jobs.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction
- **Authoritative source path(s)**: `wepppy/rq/batch_rq.py`, `wepppy/nodb/batch_runner.py`, `wepppy/microservices/rq_engine/batch_routes.py`
- **Cutover proof required**: focused tests prove a second Run Batch call enqueues only failed/incomplete/missing leaves while completed leaves are skipped; route tests prove active batch jobs return `409 batch_busy`; local runstate output explains retry eligibility.
- **Acceptance evidence type**: both

## Stakeholders
- **Primary**: WEPPcloud operators running large batch projects.
- **Reviewers**: WEPPcloud/RQ maintainers.
- **Security Reviewer**: Required because queue orchestration and worker retry behavior change.
- **Informed**: Batch Runner users, production operators.

## Success Criteria
- [ ] Pressing Run Batch for a partially completed batch enqueues only retry-eligible leaf runs when `Remove existing files` is disabled.
- [ ] Enabling `Remove existing files` remains an explicit full-rerun/replace path.
- [ ] Successful watershed jobs write `run_metadata.json` with `status: success` and overwrite stale failed metadata from prior attempts.
- [ ] Failed watershed jobs remain RQ-finished with `(False, elapsed)` only if the finalizer contract still expects that shape, but durable failure metadata and summary reporting make the failure visible.
- [ ] Existing batches with complete enabled `RedisPrep` timestamps and no success metadata are treated as complete, not rerun just because they predate the metadata contract.
- [ ] Active queued/started/deferred/scheduled batch jobs block a new Run Batch submission with an explicit conflict response.
- [ ] Tests and docs cover the `wepp1` failure mode: empty observed climate years, lock conflicts after cancellation, and later failed WEPP hillslope runs.

## Parameterization ADR Gate
- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites
- Existing Batch Runner feature flag and RQ Engine batch route.
- Existing `RedisPrep` task timestamps and per-run `run_metadata.json` failure writes.
- Active production batch jobs should finish or be canceled before any production rollout.

### Blocks
- Reliable operator retry flow for large batch projects after partial failures.
- Cleaner batch dashboard/status reporting for failed, skipped, and successful leaves.

## Related Packages
- **Related**: `docs/work-packages/20260214_nodir_archives/`
- **Related**: `docs/work-packages/20260224_redis_persistence_session_durability/`
- **Related**: `docs/schemas/rq-response-contract.md`
- **Related**: `docs/standards/hardening-lifecycle-standard.md`

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: Medium-High
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes queue enqueue selection, retry semantics, active-job conflict behavior, worker-visible status metadata, and potentially RQ dependency/cancellation behavior. The route remains admin-only, but queue surfaces are high impact by repository policy.
- **Security review artifact**: `docs/work-packages/20260630_batch_runner_durability/artifacts/2026-06-30_security_review.md`

## Hardening and Callus Softening
- **Failure signature(s)**: `ValueError: observed_start_year must be an integer year, got empty string`; `NoDirError: NODIR_LOCKED`; `Error running WEPP hillslope ... returncode=-8`; RQ watershed jobs with status `finished`, result `(False, elapsed)`, and empty `exc_info`.
- **Related prior hardening efforts**: Redis persistence/session durability, NoDir archives/lock work, RQ response contract.
- **Health signals**: Run Batch enqueues a small retry set after partial failure; stale failed metadata is overwritten by success; runstate explains retry reason; active duplicate submissions are rejected.
- **Danger signals**: Completed leaves are skipped incorrectly despite changed directives; old failed metadata causes endless reruns; active jobs are hidden by RQ status `finished`; finalizer reports success while leaves failed.
- **Observation window**: 14 days after production rollout or two large batch rerun cycles, whichever is longer.
- **Temporary calluses introduced**: None planned. Any production-only cleanup script or manual retry list must be recorded here with owner and sunset criteria.
- **Callus softening hypothesis (if applicable)**: Once success metadata and retry selection are deployed, operators should no longer need ad hoc manual failed-run lists for ordinary batch recovery.

## References
- `wepppy/rq/batch_rq.py` - parent batch job, per-watershed worker, finalizer, active-job discovery.
- `wepppy/nodb/batch_runner.py` - batch controller, task directives, runstate report, leaf project execution.
- `wepppy/microservices/rq_engine/batch_routes.py` - admin Run Batch and Delete Batch API routes.
- `tests/weppcloud/test_batch_runner_endpoints.py` - current batch blueprint/runstate coverage.
- `tests/microservices/test_rq_engine_batch_routes.py` - current RQ Engine batch route coverage.
- `docs/work-packages/20260630_batch_runner_durability/artifacts/wepp1_exception_evidence_20260630.md` - production evidence captured during scoping.

## Deliverables
- Durable per-leaf status classifier and retry-eligibility report.
- Run Batch enqueue filter that skips completed leaves by default and records skipped/enqueued counts.
- Success and failure `run_metadata.json` contract for batch leaves.
- Active-job guard for Run Batch route and worker-side safety check.
- Focused regression tests and queue graph/catalog validation.
- Security review artifact completed before production rollout.

## Follow-up Work
- Consider a later dashboard enhancement that previews the retry set before submission.
- Consider an operator CLI that prints `would_rerun` leaves for a batch without enqueueing jobs.
