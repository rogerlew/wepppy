# Implement Batch Runner Failed-Leaf Reruns

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows the repository guidance in `docs/prompt_templates/codex_exec_plans.md`. It is intentionally self-contained so a future agent can implement the feature without relying on chat history.

## Purpose / Big Picture

After this change, an operator running a large Batch Runner project can recover from a partial failure without manually tracking which watersheds failed. If a batch fails because an input was missing, the operator fixes the input and presses Run Batch again; WEPPcloud should enqueue only missing, incomplete, or failed watershed leaves. Completed leaves should not consume queue capacity again unless the operator explicitly enables the existing `Remove existing files` directive.

The observable behavior is that a second Run Batch submission for a partially completed batch produces a smaller enqueue set, reports skipped/enqueued/failed counts, and leaves successful per-run metadata behind. Running the focused tests listed in this plan should prove the retry selection before any production rollout.

## Progress

- [x] (2026-06-30 19:56 UTC) Read current batch enqueue, worker, route, and runstate implementation.
- [x] (2026-06-30 19:56 UTC) Captured production evidence from `wepp1` for `nasa-roses-202606-psbs`.
- [x] (2026-06-30 19:56 UTC) Created this ExecPlan as a scaffold.
- [ ] Implement and test durable leaf status classification in `wepppy/nodb/batch_runner.py`.
- [ ] Write success metadata in `run_batch_watershed_rq` and keep failure metadata contract.
- [ ] Filter `run_batch_rq` enqueue targets and preserve full-rerun behavior when `TaskEnum.if_exists_rmtree` is enabled.
- [ ] Add active Run Batch conflict handling in `wepppy/microservices/rq_engine/batch_routes.py`.
- [ ] Update docs, queue graph/catalog if required, and complete security review.

## Surprises & Discoveries

- Observation: `run_batch_watershed_rq` catches exceptions and returns `(False, elapsed)`, so RQ records failed leaves as job status `finished` and leaves `job.exc_info` empty.
  Evidence: On `wepp1`, the provided jobs such as `0b38b2f6-df11-4b6f-bb80-10f45f6e2b47` had `status: finished`, `result: (False, 1437.7817513942719)`, and empty `exc_info`.
- Observation: Failure metadata exists only on exception; success metadata is not currently written.
  Evidence: `wepppy/rq/batch_rq.py` writes `run_metadata.json` in the exception block, while the success path only publishes status messages and returns.
- Observation: Current runstate reports task timestamps but not terminal retry eligibility.
  Evidence: `BatchRunner.generate_runstate_report` and `generate_runstate_cli_report` iterate `RedisPrep` timestamps only.

## Decision Log

- Decision: Use enabled `RedisPrep` task completion as the compatibility source of truth for old runs, while adding success metadata for new runs.
  Rationale: Existing successful leaves have no success metadata, and stale failed metadata can remain after a later successful rerun until this package lands.
  Date/Author: 2026-06-30 19:56 UTC / Codex.
- Decision: Reuse `TaskEnum.if_exists_rmtree` as the explicit full-rerun switch.
  Rationale: The Batch Runner already exposes this directive as "Remove existing files"; keeping retry-aware behavior as the default avoids adding another route mode before the durable state contract exists.
  Date/Author: 2026-06-30 19:56 UTC / Codex.
- Decision: Treat queue orchestration changes as security-impact high.
  Rationale: Repository policy treats queue wiring and worker subprocess surfaces as high by default.
  Date/Author: 2026-06-30 19:56 UTC / Codex.

## Outcomes & Retrospective

No implementation outcome yet. The package is scaffolded with production evidence and a concrete implementation path.

## Context and Orientation

Batch Runner projects live under the batch root, normally `/wc1/batch/<batch_name>` in containers and `/geodata/wc1/batch/<batch_name>` on `wepp1`. Each watershed leaf is a run directory under `runs/<leaf_runid>`. In code, the composite run id for a leaf is `batch;;<batch_name>;;<leaf_runid>`.

The main files are:

- `wepppy/microservices/rq_engine/batch_routes.py`: FastAPI route for `POST /api/batch/_/{batch_name}/run-batch`. It is admin/JWT protected and currently enqueues one parent `run_batch_rq` job.
- `wepppy/rq/batch_rq.py`: RQ worker functions. `run_batch_rq` loads the `BatchRunner`, gets every watershed feature, enqueues every feature as `run_batch_watershed_rq`, and enqueues `_final_batch_complete_rq` depending on all watershed jobs. `run_batch_watershed_rq` runs one leaf and catches exceptions.
- `wepppy/nodb/batch_runner.py`: NoDb controller. It stores run directives, runs one leaf project, and can report `RedisPrep` timestamps.
- `wepppy/nodb/redis_prep.py`: Redis-backed task timestamp helper. A task is complete when `prep[TaskEnum.<task>]` returns an integer timestamp, not `None`.

Terms used in this plan:

- A "leaf" is one watershed feature/run inside a batch.
- "Enabled tasks" are `BatchRunner.DEFAULT_TASKS` whose `BatchRunner.is_task_enabled(task)` is true.
- A "complete leaf" is a leaf whose run directory exists and whose enabled tasks are all timestamped in `RedisPrep`.
- "Terminal metadata" means `runs/<leaf_runid>/run_metadata.json`. The implementation should write it for both success and failure.
- "Retry eligible" means Run Batch should enqueue the leaf in default mode because it is missing, incomplete, or has a current unsuperseded failure.

## Plan of Work

First, add a small status model in `wepppy/nodb/batch_runner.py`. Keep it simple and serializable: a dict per leaf is enough unless the surrounding code already has a dataclass pattern. It should report the leaf run id, composite run id, run directory path, whether the run directory exists, enabled tasks, missing enabled tasks, terminal metadata if readable, a normalized status such as `missing`, `incomplete`, `failed`, or `complete`, and a boolean `retry_eligible`. The compatibility rule is important: if all enabled tasks are complete, classify the leaf as complete even when `run_metadata.json` is missing or contains an older failed status. New success metadata will prevent this ambiguity for future runs.

Next, update `run_batch_watershed_rq` in `wepppy/rq/batch_rq.py` so the success path writes `run_metadata.json` with `status: success`, `runid`, `batch_name`, `started_at`, `completed_at`, `duration_seconds`, `rq_job_id`, and enough task status summary to debug the leaf. Keep the failure metadata shape backward compatible by retaining `status: failed` and the existing `error` payload, but add the same common fields where possible.

Then change `run_batch_rq` so it asks `BatchRunner` for retry-eligible features before enqueueing watershed jobs. If `batch_runner.is_task_enabled(TaskEnum.if_exists_rmtree)` is true, enqueue every feature and preserve the existing workspace reset behavior. Otherwise, enqueue only features whose status says `retry_eligible` is true. Publish or store a parent summary with total, enqueued, skipped, and missing/incomplete/failed counts. If no features are eligible, still emit a clear completion/status message and decide whether the finalizer should be skipped or run with no dependencies; keep behavior explicit and covered by tests.

Add active Run Batch conflict handling to `wepppy/microservices/rq_engine/batch_routes.py`, similar to Delete Batch. Before enqueueing the parent job, call `_active_batch_job_summaries(batch_name, redis_conn=redis_conn)`. If it returns jobs, respond with status 409, code `batch_busy`, and details listing up to five active jobs. Keep the existing auth and admin-role checks unchanged.

Update runstate reporting so `generate_runstate_report` returns the new status fields, while the CLI report can remain compact but should make retry status visible enough for an operator. Update tests to avoid requiring a live Redis service where feasible by monkeypatching `RedisPrep` or using existing project test patterns.

Finally, run focused tests and queue graph validation. If `wctl check-rq-graph` reports drift, update `wepppy/rq/job-dependencies-catalog.md` with `python tools/check_rq_dependency_graph.py --write`, then review the diff.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Add tests first:
   - Create `tests/rq/test_batch_rq_retry_selection.py`.
   - Cover a complete old-style leaf with all enabled timestamps and no metadata; it must be skipped.
   - Cover an incomplete leaf with missing `build_climate`; it must be enqueued.
   - Cover a failed metadata leaf with missing downstream WEPP tasks; it must be enqueued.
   - Cover `if_exists_rmtree` enabled; all leaves must be enqueued.
   - Cover success metadata writing from `run_batch_watershed_rq`.

2. Update existing route tests:
   - In `tests/microservices/test_rq_engine_batch_routes.py`, add a `test_run_batch_busy_returns_409` mirroring the delete-batch busy test.
   - Update `test_run_batch_enqueues_job` if the route now calls `_active_batch_job_summaries`.

3. Implement the classifier and runstate changes:
   - Edit `wepppy/nodb/batch_runner.py`.
   - Add helper methods near the Report section so they can reuse `DEFAULT_TASKS`, `is_task_enabled`, `get_watershed_features_lpt`, and `RedisPrep`.
   - Keep JSON read errors explicit in the returned status rather than swallowing them silently.

4. Implement worker changes:
   - Edit `wepppy/rq/batch_rq.py`.
   - Add a small metadata writer helper if it keeps success and failure paths consistent.
   - Change `run_batch_rq` to filter features by classifier output and publish/store summary counts.

5. Implement route active-job guard:
   - Edit `wepppy/microservices/rq_engine/batch_routes.py`.
   - Reuse the delete route's conflict response style and code `batch_busy`.

6. Validate:
   - Run `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`.
   - Run `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1`.
   - Run `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1`.
   - Run `wctl check-rq-graph`.
   - Run `wctl doc-lint --path docs/work-packages/20260630_batch_runner_durability`.

## Validation and Acceptance

The main acceptance behavior is a simulated partial batch rerun. A focused RQ test should create three watershed features: one complete old-style run, one failed/incomplete run, and one missing run. With `Remove existing files` disabled, `run_batch_rq` should enqueue only the failed/incomplete and missing leaves. With `Remove existing files` enabled, it should enqueue all three leaves.

The route acceptance behavior is that `POST /api/batch/_/demo/run-batch` returns `409` with error code `batch_busy` when `_active_batch_job_summaries` returns active jobs, after auth succeeds.

The metadata acceptance behavior is that a successful `run_batch_watershed_rq` writes `run_metadata.json` with `status: success`, and a later failed run writes `status: failed` with an `error` payload. A successful rerun should overwrite stale failed metadata.

Before production rollout, manually verify on a safe batch or staging environment that the runstate report shows retry eligibility and that the enqueue summary matches the expected leaf count. Do not run production mutation commands while active jobs exist for the same batch.

## Idempotence and Recovery

The implementation should be safe to run repeatedly. Classification only reads run directories, `RedisPrep`, and metadata. Success and failure metadata writes replace one leaf's `run_metadata.json` atomically enough for current NoDb filesystem conventions; if a metadata write fails, the worker should log a warning but should not hide the leaf's actual execution failure.

If tests reveal that a complete leaf with old failed metadata is being rerun, stop and fix the classifier before touching production. If queue graph validation changes unexpectedly, update the catalog only after inspecting whether dependency semantics actually changed.

## Artifacts and Notes

Production evidence is captured in `docs/work-packages/20260630_batch_runner_durability/artifacts/wepp1_exception_evidence_20260630.md`. The most important findings are that provided RQ job IDs were `finished` with `(False, elapsed)` and empty `exc_info`, and that leaf `run_metadata.json` held 36 failed entries during the live batch sample.

The live production sample at 2026-06-30 19:56 UTC still had active queued jobs, so this plan must not be treated as approval for immediate production rollout.

## Interfaces and Dependencies

Add or preserve the following interfaces:

- In `wepppy/nodb/batch_runner.py`, a public method such as `classify_batch_run_states()` returning a dict keyed by leaf run id, and a helper such as `retry_eligible_watershed_features()` returning `WatershedFeature` objects to enqueue.
- In the returned status dict, include at minimum `runid`, `composite_runid`, `status`, `retry_eligible`, `missing_tasks`, `enabled_tasks`, and `metadata_status`.
- In `run_metadata.json`, preserve existing failure keys and add success-compatible common keys: `runid`, `batch_name`, `status`, `started_at`, `completed_at`, `duration_seconds`, and `error` only when failed.
- In `wepppy/microservices/rq_engine/batch_routes.py`, preserve existing admin/JWT requirements and response shape for successful enqueue, while adding the `409 batch_busy` conflict response.
