# Track complete WEPP workflows for single-flight admission

This ExecPlan is a living document maintained according to `docs/prompt_templates/codex_exec_plans.md`. The required sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.

## Purpose / Big Picture

WEPPcloud must never start two WEPP workflows against the same run directory at once. After this change, a second normal, watershed, prep-only, or no-prep submission receives the existing conflict response while executable work remains anywhere in the first workflow's RQ tree. A failed tree does not strand the run behind dependents that can no longer execute.

## Progress

- [x] (2026-08-03 06:41 UTC) Diagnose the production overlap and identify the short-lived-root tracking gap.
- [x] (2026-08-03 06:41 UTC) Record the normative behavior in `docs/schemas/rq-response-contract.md` and create package scaffolding.
- [x] (2026-08-03 06:52 UTC) Implement descendant-aware tracking and focused regression coverage.
- [x] (2026-08-03 06:56 UTC) Run targeted tests, RQ graph validation, stub validation, docs lint, and diff checks; record environmental/baseline blockers.
- [x] (2026-08-03 06:57 UTC) Complete independent `reviewer` and `qa_reviewer` passes and resolve actionable findings.
- [x] (2026-08-03 06:57 UTC) Close package documentation and archive this plan.

## Surprises & Discoveries

- Observation: The 30-second Redis lock serializes only the route's check-and-enqueue transaction; it is released as soon as the root job is submitted.
  Evidence: Both normal and bootstrap route helpers release `wepp:submit_lock:<runid>` in `finally` after `prep.set_rq_job_id(...)`.
- Observation: Every pipeline child is stored directly on the orchestration root under `job.meta["jobs:..."]`, so the existing root ID is sufficient for complete workflow inspection.
  Evidence: `wepppy/rq/wepp_rq_pipeline.py::_record_enqueue` saves every child ID on the same `parent_job`.
- Observation: The pinned RQ 1.16.2 status values are `JobStatus` enums, and `str(JobStatus.STARTED)` is `"JobStatus.STARTED"`, not `"started"`.
  Evidence: A local virtualenv probe printed both `str(value)` and `value.value`; the pre-change helper normalized the former and therefore could miss active roots as well as descendants.
- Observation: In pinned RQ 1.16.2, `Job.dependency_ids` returns byte Redis keys such as `b"rq:job:<id>"`, not raw job IDs.
  Evidence: Independent code and QA reviewers identified the mismatch, and inspection of `Job.dependency_ids.fget` confirmed it calls `Job.key_for(...)`.

## Decision Log

- Decision: Preserve the orchestration root as the persisted status/cancellation identity and inspect its child links during admission.
  Rationale: Repointing to the final job would lose the existing root tree and can permanently block retries when an upstream failure strands the final job as deferred.
  Date/Author: 2026-08-03 / Codex.
- Decision: A queued, started, or scheduled descendant always means the workflow is active. Each deferred descendant counts as active unless its own transitive dependency chain contains a failed, stopped, or canceled job.
  Rationale: This blocks real work without converting dependency-failure residue into a permanent run lockout.
  Date/Author: 2026-08-03 / Codex.

## Outcomes & Retrospective

WEPP single-flight admission now follows active descendants after the orchestration root finishes and correctly interprets pinned RQ 1.16.2 enums and byte dependency keys. All five workflow keys share the behavior, failed dependency tails permit recovery, and unrelated viable branches still block duplicates. Focused validation passed with 118 tests; independent correctness and QA review closed without unresolved High or Medium findings. A queue outage exceeding the root's seven-day retention remains a documented low-probability follow-up.

## Context and Orientation

The rq-engine route stores one job ID per operation in `RedisPrep`. That ID is the root orchestration job implemented in `wepppy/rq/wepp_rq.py`. The root calls pipeline builders in `wepppy/rq/wepp_rq_pipeline.py`, which enqueue the actual preparation, model-run, and post-processing jobs and record every child ID in root metadata. The root then exits in about a second while children may run for hours. `get_active_wepp_job` currently checks only the root status, which creates a window for a second workflow after the root reaches `finished`.

The term “viable deferred job” means a dependency-waiting job that can still become queued. RQ can leave downstream jobs deferred after an upstream job fails; those jobs cannot execute and must not behave like a permanent lock.

## Plan of Work

Extend `get_active_wepp_job` with small internal helpers that fetch root-linked descendants, normalize statuses, and return a real active descendant when found. Preserve root-first behavior during the orchestration interval. If no queued, started, or scheduled descendant exists, inspect each deferred descendant's transitive dependencies and suppress only those blocked by a failed, stopped, or canceled dependency. An unrelated failed sibling does not invalidate a viable deferred branch. Missing expired child jobs are ignored like missing roots, while missing dependency records are treated conservatively as viable.

Add a focused unit module under `tests/rq/` with deterministic fake jobs. Parameterize all keys in `WEPP_RQ_JOB_KEYS`, explicitly including `run_wepp_watershed_rq`, `prep_wepp_watershed_rq`, and `run_wepp_watershed_noprep_rq`. Cover finished root plus running child, viable deferred tree, failed tree with deferred tail, active sibling despite another failure, and missing child records.

Update `wepppy/rq/README.md` to explain that the stored root remains the status/cancellation receipt and admission follows its child metadata. No enqueue site or dependency edge is intended to change; nevertheless run the repository graph drift gate.

After implementation and local gates, request two independent reviews: a correctness/regression review and a QA/test-maintainability review. Store their findings and dispositions under this package's `artifacts/` directory, remediate medium/high findings, rerun affected gates, update the tracker, and move this plan to `prompts/completed/` only when done.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/rq/test_wepp_singleflight_tracking.py tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py --maxfail=1
    wctl check-rq-graph
    wctl run-stubtest wepppy.rq.wepp_rq
    wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260802_wepp_singleflight_tracking --path wepppy/rq/README.md --path PROJECT_TRACKER.md
    git diff --check

Run `wctl run-pytest tests --maxfail=1` as the substantive-change pre-handoff sanity gate. Record any unrelated baseline failure with exact test and traceback summary.

## Validation and Acceptance

The focused tests must demonstrate that a finished root with a started hillslope or watershed child returns an active-job record and causes `ensure_no_active_wepp_job` to raise `WeppSingleFlightConflict`. They must also show that a failed child plus only deferred descendants returns no active job, while a simultaneously queued/running sibling still blocks. Every key in `WEPP_RQ_JOB_KEYS` must participate in the same logic.

The RQ graph gate must report no drift because this package changes observation, not enqueue edges. Documentation lint and `git diff --check` must pass. Both independent reviews must have no unresolved medium/high finding before closure.

## Idempotence and Recovery

All edits and tests are repeatable. The change performs read-only Redis job inspection during submission and does not mutate existing jobs. If inspection reveals an unsafe ambiguity, revert only package-owned changes with a targeted patch; never discard the existing NAS incident-report modification.

## Artifacts and Notes

Production evidence: two no-prep root submissions for `compositional-disorganization` completed seconds after enqueue, while child `_run_hillslopes_rq` jobs `7e7e884d-ca25-4fec-ba07-f02ab8b9adad` and `0fd3cd53-df74-4f70-968f-74183587b036` overlapped on separate workers.

## Interfaces and Dependencies

`get_active_wepp_job(prep, redis_conn) -> dict[str, str] | None` remains the public helper and return shape. `ensure_no_active_wepp_job` retains `WeppSingleFlightConflict` and its existing message. Internal inspection uses `rq.job.Job.fetch`, `Job.get_status(refresh=False)`, root `meta` keys beginning with `jobs:`, and `rq.exceptions.NoSuchJobError`. No dependency or public response schema is added.

Revision note (2026-08-03 06:41 UTC): Initial plan created from the production duplicate-WEPP incident and the user's explicit requirement for watershed tracking plus dual-agent review.

Revision note (2026-08-03 06:48 UTC): Added the RQ `JobStatus.value` normalization defect discovered during validation; the implementation and tests now cover the production enum rather than only string test doubles.

Revision note (2026-08-03 06:52 UTC): Corrected the pinned RQ version, recorded its byte dependency-key representation, and narrowed deferred viability wording to each job's transitive dependency chain after dual-review findings.

Revision note (2026-08-03 06:57 UTC): Recorded completed implementation, validation limitations, dual-review disposition, residual receipt-retention risk, and plan archive at package closure.
