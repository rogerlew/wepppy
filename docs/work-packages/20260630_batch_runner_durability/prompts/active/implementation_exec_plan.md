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
- [x] (2026-06-30 20:22 UTC) Implemented and tested durable leaf status classification in `wepppy/nodb/batch_runner.py`.
- [x] (2026-06-30 20:22 UTC) Wrote success metadata in `run_batch_watershed_rq` and kept failure metadata contract.
- [x] (2026-06-30 20:22 UTC) Filtered `run_batch_rq` enqueue targets and preserved full-rerun behavior when `TaskEnum.if_exists_rmtree` is enabled.
- [x] (2026-06-30 20:22 UTC) Added active Run Batch conflict handling in `wepppy/microservices/rq_engine/batch_routes.py` and a worker-side guard.
- [x] (2026-06-30 20:22 UTC) Updated docs, regenerated queue graph/catalog, and completed security review artifact for local implementation.
- [x] (2026-06-30 20:45 UTC) Dispatched dual-agent correctness/security reviews and fixed all actionable findings.
- [x] (2026-06-30 22:33 UTC) Hardened reused-leaf retry startup by clearing stale child NoDb locks before controller loading.
- [x] (2026-06-30 22:47 UTC) Hardened retry enqueue against stale path-scoped runtime locks left by dead prior worker containers.
- [x] (2026-06-30 23:08 UTC) Fixed parent Run Batch result serialization by returning a summary dict instead of an RQ `Job`.
- [x] (2026-06-30 23:51 UTC) Hardened watershed retries against interrupted hillslope interchange outputs.
- [x] (2026-07-01 19:54 UTC) Hardened retries against stale cloned base climate attributes by detecting `_base/climate.nodb` drift, enqueueing affected leaves, resyncing critical climate config fields, and invalidating climate/downstream timestamps.

## Surprises & Discoveries

- Observation: `run_batch_watershed_rq` catches exceptions and returns `(False, elapsed)`, so RQ records failed leaves as job status `finished` and leaves `job.exc_info` empty.
  Evidence: On `wepp1`, the provided jobs such as `0b38b2f6-df11-4b6f-bb80-10f45f6e2b47` had `status: finished`, `result: (False, 1437.7817513942719)`, and empty `exc_info`.
- Observation: Failure metadata exists only on exception; success metadata is not currently written.
  Evidence: `wepppy/rq/batch_rq.py` writes `run_metadata.json` in the exception block, while the success path only publishes status messages and returns.
- Observation: Current runstate reports task timestamps but not terminal retry eligibility.
  Evidence: `BatchRunner.generate_runstate_report` and `generate_runstate_cli_report` iterate `RedisPrep` timestamps only.
- Observation: `if_exists_rmtree` and `run_omni_contrasts` are not reliable per-leaf completion timestamps for the retry classifier.
  Evidence: `if_exists_rmtree` is a reset directive, and `run_batch_watershed_rq` does not execute `run_omni_contrasts`.
- Observation: Broad exception enforcement currently fails on touched files even though this implementation did not add new broad catches.
  Evidence: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` reports existing broad boundary catches in `batch_routes.py` and `batch_rq.py`.
- Observation: Default-enabled RAP/OpenET directives are optional in the leaf worker when their NoDb controllers are absent.
  Evidence: `BatchRunner.run_batch_project()` calls `RAP_TS.tryGetInstance()` and `OpenET_TS.tryGetInstance()` before those acquisitions; completion proof now requires those timestamps only when the corresponding optional NoDb file exists.
- Observation: `run_batch_watershed_rq` writes leaf success metadata before asynchronous Omni scenario finalization can timestamp `run_omni_scenarios`.
  Evidence: success metadata is written after `run_omni_scenarios_rq()` returns its final job, so success metadata cannot be a blanket replacement for required task timestamps.
- Observation: Reused child workspaces can retain stale NoDb controller locks after a canceled climate build.
  Evidence: Local `durability_test` retries for `OR-154`, `OR-204`, and `OR-20` failed immediately with empty `AssertionError`; each climate log stopped after `assert not self.islocked()`, matching `ClimateBuildRouter.build()`.
- Observation: Path-scoped runtime locks can survive a dead worker container and block retry for the full lock TTL.
  Evidence: Local WA-174 climate generation was writing `_prism_revision()` files at 22:38 UTC; after the compose stack restarted, a retry failed with `NODIR_LOCKED` held by old owner `fbdc2c500f0a:199` and no matching running container.
- Observation: Returning live RQ `Job` objects from parent workers causes the dashboard to show failed/canceled even after enqueue succeeded.
  Evidence: Parent job `871f4334-479d-4e63-95f8-f80fe9e01c98` had `result=Unserializable return value`, `status=canceled`, and no `exc_info` after publishing `COMPLETED run_batch_rq(durability_test)`.
- Observation: A canceled/interrupted retry can timestamp `run_wepp_hillslopes` while leaving hillslope interchange conversion incomplete, then the next retry skips hillslope/interchange and fails inside watershed post-processing.
  Evidence: `OR,WA-101` failed missing `H.wat.parquet` with `H.soil.parquet.tmp` present; `OR,WA-102` failed missing `H.pass.parquet` with `H.pass.parquet.tmp` present. Both had `run_wepp_hillslopes` set and `run_wepp_watershed` missing.
- Observation: Existing leaves can carry stale cloned climate configuration even after an operator fixes `_base`.
  Evidence: On 2026-07-01, `nasa-roses-202606-psbs` leaves failed with `ValueError: observed_start_year must be an integer year, got empty string` after observed years were set on the base project; a leaf initialized before that fix still had empty `_observed_start_year` and `_observed_end_year`.

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
- Decision: Exclude directive-only and non-leaf tasks from retry completion proof.
  Rationale: A task must be both enabled and actually timestamped by the leaf worker to prove completion; otherwise retry filtering would permanently rerun leaves for directives that are not part of the leaf chain.
  Date/Author: 2026-06-30 20:22 UTC / Codex.
- Decision: Validate batch leaf run IDs at template and classifier boundaries.
  Rationale: Leaf IDs are used to resolve paths below `runs/`; unsafe legacy/generated IDs should not probe outside that tree even for admin-created batches.
  Date/Author: 2026-06-30 20:45 UTC / Codex.
- Decision: Preserve `BATCH_RUN_COMPLETED` and add a failure-specific signal instead of replacing the trigger.
  Rationale: Existing clients may depend on `BATCH_RUN_COMPLETED`; the new summary and `BATCH_RUN_COMPLETED_WITH_FAILURES` make partial failure visible without breaking compatibility.
  Date/Author: 2026-06-30 20:45 UTC / Codex.
- Decision: Clear child-scoped NoDb cache and locks at the start of every batch watershed run.
  Rationale: The climate controller assertion is a valid lock invariant; the retry worker must remove stale lock/cache state left by canceled child builds before loading `RedisPrep` and NoDb controllers. Cleanup is scoped to the composite child run id and remains protected from active duplicate submissions by route and worker active-job guards.
  Date/Author: 2026-06-30 22:33 UTC / Codex.
- Decision: Clear exact selected-leaf path-scoped runtime locks before child enqueue.
  Rationale: Runid-wide runtime lock clearing is unsafe for batch leaves because path-scoped locks store the leaf id, such as `WA-174`, and different batches can share that id. The parent run has already passed active-job preflight, so clearing only the exact `wd`/root/`effective_root_path` keys for selected leaves removes stale dead-worker locks without disturbing other batches.
  Date/Author: 2026-06-30 22:47 UTC / Codex.
- Decision: Return a serializable parent Run Batch summary.
  Rationale: RQ must serialize worker return values; a live finalizer `Job` object is not a durable result. The finalizer job id plus selection summary is enough for dashboards and diagnostics.
  Date/Author: 2026-06-30 23:08 UTC / Codex.
- Decision: Ensure hillslope interchange before watershed retries.
  Rationale: Watershed execution depends on `H.pass.parquet` and `H.wat.parquet`, and `run_wepp_hillslopes` can be timestamped before batch post-processing has finished. Rebuilding missing interchange from existing raw hillslope outputs is cheaper and more targeted than forcing a full hillslope rerun.
  Date/Author: 2026-06-30 23:51 UTC / Codex.
- Decision: Resync only critical climate configuration fields from `_base/climate.nodb` into existing leaves, and invalidate only climate/downstream timestamps.
  Rationale: The confirmed stale path is a cloned climate configuration defect. Copying generated climate outputs would risk moving base-run artifacts into a leaf, and clearing DEM/watershed/landuse/soils timestamps would waste work unrelated to climate year bounds. Broader landuse, soils, WEPP, Ron, and watershed resync rules require separate confirmed incidents and artifact-compatibility tests.
  Date/Author: 2026-07-01 19:54 UTC / Codex.

## Outcomes & Retrospective

Local implementation is complete after dual-agent review disposition and local retry hardening. The batch runner now classifies leaf runs, skips completed old-style leaves by default, handles absent optional RAP/OpenET controllers, rejects unsafe generated leaf IDs, preserves explicit full rerun through `Remove existing files`, writes success metadata with best-effort task diagnostics, rejects active duplicate submissions at both route and worker boundaries, clears stale child NoDb locks before reused-leaf retries, clears exact selected-leaf path-scoped runtime locks before child enqueue, ensures hillslope interchange before watershed retries, detects and repairs stale base climate configuration in existing leaves, returns a serializable parent summary, and publishes final failed/incomplete/missing/invalid counts. Focused RQ, runtime-path, rq-engine route, and batch endpoint tests pass. Production rollout remains pending, and changed-file broad exception enforcement still flags existing broad boundary catches in touched files.

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
- "Base project attribute drift" means a critical configuration field in an existing leaf's NoDb file differs from the same field in `_base`. The current implemented drift rule covers `climate.nodb` configuration only, not generated climate artifacts.

## Plan of Work

First, add a small status model in `wepppy/nodb/batch_runner.py`. Keep it simple and serializable: a dict per leaf is enough unless the surrounding code already has a dataclass pattern. It should report the leaf run id, composite run id, run directory path, whether the run directory exists, enabled tasks, missing enabled tasks, terminal metadata if readable, a normalized status such as `missing`, `incomplete`, `failed`, or `complete`, and a boolean `retry_eligible`. The compatibility rule is important: if all enabled tasks are complete, classify the leaf as complete even when `run_metadata.json` is missing or contains an older failed status. New success metadata will prevent this ambiguity for future runs.

Next, update `run_batch_watershed_rq` in `wepppy/rq/batch_rq.py` so the success path writes `run_metadata.json` with `status: success`, `runid`, `batch_name`, `started_at`, `completed_at`, `duration_seconds`, `rq_job_id`, and enough task status summary to debug the leaf. Keep the failure metadata shape backward compatible by retaining `status: failed` and the existing `error` payload, but add the same common fields where possible.

Then change `run_batch_rq` so it asks `BatchRunner` for retry-eligible features before enqueueing watershed jobs. If `batch_runner.is_task_enabled(TaskEnum.if_exists_rmtree)` is true, enqueue every feature and preserve the existing workspace reset behavior. Otherwise, enqueue only features whose status says `retry_eligible` is true. Publish or store a parent summary with total, enqueued, skipped, and missing/incomplete/failed counts. If no features are eligible, still emit a clear completion/status message and decide whether the finalizer should be skipped or run with no dependencies; keep behavior explicit and covered by tests.

Add active Run Batch conflict handling to `wepppy/microservices/rq_engine/batch_routes.py`, similar to Delete Batch. Before enqueueing the parent job, call `_active_batch_job_summaries(batch_name, redis_conn=redis_conn)`. If it returns jobs, respond with status 409, code `batch_busy`, and details listing up to five active jobs. Keep the existing auth and admin-role checks unchanged.

Update runstate reporting so `generate_runstate_report` returns the new status fields, while the CLI report remains compact as run ID plus task glyphs for the Batch Progress panel. Update tests to avoid requiring a live Redis service where feasible by monkeypatching `RedisPrep` or using existing project test patterns.

For the 2026-07-01 stale-base-climate hardening, add a resync rule in `wepppy/nodb/batch_runner.py` that compares selected configuration fields in `_base/climate.nodb` and `runs/<leaf>/climate.nodb`. If any field differs, classify the leaf as retry eligible with retry reason `base_project_attributes_changed`. At watershed worker startup, after `RedisPrep` exists but before loading NoDb controllers, copy those selected fields from base to leaf and remove timestamps for `build_climate`, `build_rap_ts`, `build_openet_ts`, `run_wepp_hillslopes`, `run_wepp_watershed`, and `run_omni_scenarios`.

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
   - Add the climate base-project drift check and expose `base_sync_changed_attributes`, `base_sync_error`, and `stale_tasks` in the status dict.

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

The base-resync acceptance behavior is that a leaf with complete timestamps but empty cloned observed climate year bounds is retry eligible when `_base/climate.nodb` now contains valid year bounds. When the leaf worker starts, it writes those base bounds into the leaf `climate.nodb` and removes climate/downstream timestamps while leaving unrelated timestamps such as `fetch_dem` intact.

Before production rollout, manually verify on a safe batch or staging environment that the runstate report shows retry eligibility and that the enqueue summary matches the expected leaf count. Do not run production mutation commands while active jobs exist for the same batch.

## Idempotence and Recovery

The implementation should be safe to run repeatedly. Classification only reads run directories, `RedisPrep`, and metadata. Success and failure metadata writes replace one leaf's `run_metadata.json` atomically enough for current NoDb filesystem conventions; if a metadata write fails, the worker should log a warning but should not hide the leaf's actual execution failure.

Base climate resync is also idempotent. If the selected fields already match `_base`, no file is written and no timestamps are cleared. If they differ, the worker writes only the selected configuration fields, leaves generated climate output fields untouched, and removes the same downstream timestamps on every attempt until the leaf is rebuilt successfully.

If tests reveal that a complete leaf with old failed metadata is being rerun, stop and fix the classifier before touching production. If queue graph validation changes unexpectedly, update the catalog only after inspecting whether dependency semantics actually changed.

## Artifacts and Notes

Production evidence is captured in `docs/work-packages/20260630_batch_runner_durability/artifacts/wepp1_exception_evidence_20260630.md`. The most important findings are that provided RQ job IDs were `finished` with `(False, elapsed)` and empty `exc_info`, and that leaf `run_metadata.json` held 36 failed entries during the live batch sample.

The live production sample at 2026-06-30 19:56 UTC still had active queued jobs, so this plan must not be treated as approval for immediate production rollout.

## Interfaces and Dependencies

Add or preserve the following interfaces:

- In `wepppy/nodb/batch_runner.py`, a public method such as `classify_batch_run_states()` returning a dict keyed by leaf run id, and a helper such as `retry_eligible_watershed_features()` returning `WatershedFeature` objects to enqueue.
- In the returned status dict, include at minimum `runid`, `composite_runid`, `status`, `retry_eligible`, `missing_tasks`, `enabled_tasks`, `metadata_status`, `base_sync_changed_attributes`, `base_sync_error`, and `stale_tasks`.
- In `run_metadata.json`, preserve existing failure keys and add success-compatible common keys: `runid`, `batch_name`, `status`, `started_at`, `completed_at`, `duration_seconds`, and `error` only when failed.
- In `wepppy/microservices/rq_engine/batch_routes.py`, preserve existing admin/JWT requirements and response shape for successful enqueue, while adding the `409 batch_busy` conflict response.

Plan revision note, 2026-07-01 19:54 UTC: Added stale base climate attribute resync after production showed leaves initialized before observed year bounds were set on `_base`.
