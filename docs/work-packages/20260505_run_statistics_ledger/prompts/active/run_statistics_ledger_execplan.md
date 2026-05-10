# ExecPlan: Implement Durable WEPPcloud Run Statistics

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, WEPPcloud maintainers can report project counts by configuration, WEPP hillslope execution counts, and WATAR ash execution counts without depending on current run-directory file counts. The behavior is visible by running the maintenance rollup against fixtures or production data: repeated successful runs increase historical execution totals, TTL-deleted projects disappear from active project counts, and WATAR counts come from completed ash tasks rather than legacy `*ash.csv` globs.

This plan implements the contract in `docs/work-packages/20260505_run_statistics_ledger/spec.md`.

## Progress

- [x] (2026-05-05 20:26 UTC) Work package and draft spec created.
- [x] (2026-05-05 20:42 UTC) Storage decision revised: Postgres source-of-truth ledger; stats endpoint inventory captured.
- [x] (2026-05-05 23:05 UTC) Documentation consistency audit aligned storage, endpoint migration scope, and validation tracking.
- [ ] Implement the Postgres statistics ledger module and unit tests.
- [ ] Add deterministic backfill and rollup generation tests.
- [ ] Add WEPP hillslope and WATAR runtime hooks.
- [ ] Add TTL deletion audit-event hook (must not decrement historical totals).
- [ ] Preserve compatibility stats outputs and migrate `/stats` endpoints to database-backed rollups with route tests.
- [ ] Run targeted validation and update package closeout notes.

## Surprises & Discoveries

- Observation: The prior counter date was not inferred from data. It was an exclusive hard-coded cutoff: `first_access > datetime(2024, 1, 1)` in `wepppy/weppcloud/_scripts/compile_dot_logs.py`.
  Evidence: Source inspection and wepp1 `runs_counter.json` comparison on 2026-05-05.
- Observation: The prior WEPP hillslope count was a current file count, not an execution count.
  Evidence: `_load_run_metadata()` uses `len(glob(run_dir / "wepp" / "runs" / "*.slp"))`.
- Observation: The prior WATAR count was a legacy artifact glob and can miss current WATAR runs or count unrelated summary files.
  Evidence: `_load_run_metadata()` uses `len(glob(run_dir / "ash" / "*ash.csv"))`.

## Decision Log

- Decision: Use PostgreSQL as the durable source-of-truth ledger for historical execution counts.
  Rationale: TTL deletes run directories, flat-file append paths are collision-prone across concurrent workers, and PostgreSQL gives transactional inserts with uniqueness constraints for idempotence.
  Date/Author: 2026-05-05 20:42 UTC / Codex.
- Decision: Append runtime events after successful high-level invocations, not once per individual hillslope future.
  Rationale: This preserves repeated-run accounting with low overhead and avoids high-volume writes during thread/process pool execution.
  Date/Author: 2026-05-05 20:26 UTC / Codex.
- Decision: Treat Redis as optional cache/materialization, not ledger source-of-truth.
  Rationale: Redis durability depends on AOF/RDB policy and eviction controls; this package needs auditable long-horizon persistence semantics.
  Date/Author: 2026-05-05 20:42 UTC / Codex.
- Decision: Preserve `runs_counter.json` during the first rollout.
  Rationale: `/stats` currently serves that file; additive compatibility avoids breaking consumers while richer outputs are introduced.
  Date/Author: 2026-05-05 20:26 UTC / Codex.

## Outcomes & Retrospective

Not started. Fill this section after implementation milestones land and validation has run.

## Context and Orientation

The existing statistics path is `wepppy/weppcloud/_scripts/compile_dot_logs.py`. It scans dot access logs under `/wc1/runs` and `/geodata/weppcloud_runs`, writes `access.csv`, writes `runid-locations.json`, and writes `runs_counter.json`. It currently mixes active project discovery, access history, file-count hillslope summaries, and legacy bucket counters in one script.

The WEPP hillslope runtime path is `wepppy/nodb/core/wepp_run_service.py`. The method `WeppRunService.run_hillslopes()` submits futures and tracks `futures_n` and completed `count`. After success, it timestamps `TaskEnum.run_wepp_hillslopes`.

The WATAR ash runtime path is `wepppy/nodb/mods/ash_transport/ash.py`. The method `Ash.run_ash()` builds a list named `args` for runnable ash hillslopes, executes those tasks, runs ash post-processing, and timestamps `TaskEnum.run_watar`.

The TTL deletion path is `wepppy/rq/project_rq_delete.py`. `gc_runs_rq()` collects expiration candidates and calls `delete_run_rq()`, which can remove the run directory. Any deletion event must be recorded before the filesystem removal.

The existing public stats route is `wepppy/weppcloud/routes/stats.py`. It serves:

- `/getloadavg`
- `/access-by-year` (from `/geodata/weppcloud_runs/access.csv`)
- `/access-by-month` (from `/geodata/weppcloud_runs/access.csv`)
- `/stats` (from `/geodata/weppcloud_runs/runs_counter.json`)
- `/stats/<key>` (from `/geodata/weppcloud_runs/runs_counter.json`)

Only the file-backed statistics responses are in migration scope. `/getloadavg` is inventoried for completeness and remains unchanged unless a separate package changes host-load reporting.

## Plan of Work

Milestone 1 creates a small internal statistics module, probably under `wepppy/weppcloud/stats/`, with a `StatsEvent` construction helper, a transactional database insert function, a reader/query helper for rollups, and deterministic event-id helpers for backfill. Reuse existing database configuration and connection patterns from the WEPPcloud app stack.

Milestone 2 adds rollup and backfill logic. Refactor `compile_dot_logs.py` carefully so `access.csv` and `runid-locations.json` keep their existing behavior, while statistics rollups come from the ledger and current active inventory. Add deterministic `project_seen` events from dot files. Add legacy artifact-inferred events only for existing directories, with strict WATAR per-hillslope filename matching.

Milestone 3 wires runtime events. In `WeppRunService.run_hillslopes()`, append `wepp_hillslopes_completed` after all futures complete and before or after the existing Redis timestamp. In `Ash.run_ash()`, append `watar_hillslopes_completed` after successful ash post-processing. Treat append failures as logged observability failures that do not fail completed model work, unless the implementation team deliberately chooses fail-closed behavior and documents it in this plan.

Milestone 4 wires deletion events. In `delete_run_rq()` or the GC path, append `project_deleted` before removing the run directory. This is audit metadata only and must never decrement historical totals. Keep active counts based on active inventory rather than trying to subtract deletion events from the full history.

Milestone 5 preserves compatibility and migrates routes. Generate `run_statistics_summary.json` and `run_statistics_by_config.csv`, keep writing `runs_counter.json` with legacy keys, and update `wepppy/weppcloud/routes/stats.py` to read database-backed rollups while keeping response shapes stable for `/stats`, `/stats/<key>`, `/access-by-year`, and `/access-by-month`. Leave `/getloadavg` unchanged.

Milestone 6 validates and documents rollout. Run targeted pytest suites, doc lint for this package, and a dry-run/report mode against fixtures. Update `tracker.md`, `package.md`, and this ExecPlan with outcomes and any deviations.

## Concrete Steps

Work from repository root `/workdir/wepppy`.

1. Read the spec and relevant source:

       sed -n '1,260p' docs/work-packages/20260505_run_statistics_ledger/spec.md
       sed -n '1,360p' wepppy/weppcloud/_scripts/compile_dot_logs.py
       sed -n '40,180p' wepppy/nodb/core/wepp_run_service.py
       sed -n '584,850p' wepppy/nodb/mods/ash_transport/ash.py
       sed -n '1,330p' wepppy/rq/project_rq_delete.py

2. Implement the ledger module and tests first. Suggested test location:

       tests/weppcloud/test_run_statistics_ledger.py

3. Extend compile/backfill tests. Existing starting point:

       tests/weppcloud/test_compile_dot_logs.py

4. Add focused runtime hook tests rather than broad integration runs. Prefer stubs/fakes around the event writer so model binaries are not launched.

5. Add route tests for stats endpoints as source migration guardrails.

6. Run targeted validation after each milestone:

       wctl run-pytest tests/weppcloud/test_run_statistics_ledger.py
       wctl run-pytest tests/weppcloud/test_compile_dot_logs.py

7. Before handoff, run relevant route/runtime targeted tests and docs lint:

       wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k interfaces_template
       wctl run-pytest tests/weppcloud/test_compile_dot_logs.py tests/weppcloud/test_run_statistics_ledger.py tests/weppcloud/routes/test_stats.py
       wctl doc-lint --path docs/work-packages/20260505_run_statistics_ledger
       wctl doc-lint --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance is behavioral:

- A fixture project that runs WEPP hillslopes twice produces an aggregate `hillslope_run_count` equal to two completed invocations, not the number of `.slp` files.
- A fixture project that runs WATAR once produces `watar_hillslope_run_count == len(args)` and ignores summary files matching broad `*ash.csv` patterns.
- A TTL-deleted project is absent from active project counts but still contributes historical execution events.
- Running backfill twice does not duplicate events.
- Existing `/stats` returns legacy keys from `runs_counter.json` until a later migration removes that compatibility path.

## Idempotence and Recovery

Runtime event appends are additive. If a runtime event append fails after model completion, the first implementation should log the failure with runid/config/job context and continue preserving the model-run contract. If production policy later requires fail-closed statistics, record that as a new decision and add rollback guidance.

Backfill must be safe to rerun. It uses deterministic event ids and should be inserted with unique constraints (`event_id` and optional `dedupe_key`). If a backfill run is interrupted, rerun it; already-written deterministic events are reused rather than duplicated.

Generated summary files should be written through temporary files and atomic replace, following the existing `_write_json()` and `_write_csv()` pattern in `compile_dot_logs.py`.

## Artifacts and Notes

Primary package docs:

- `docs/work-packages/20260505_run_statistics_ledger/spec.md`
- `docs/work-packages/20260505_run_statistics_ledger/tracker.md`
- `docs/work-packages/20260505_run_statistics_ledger/package.md`

Expected generated runtime artifacts after implementation:

- `/geodata/weppcloud_runs/run_statistics_summary.json`
- `/geodata/weppcloud_runs/run_statistics_by_config.csv`
- `/geodata/weppcloud_runs/stats_events_backfill_report.json`
- `/geodata/weppcloud_runs/runs_counter.json`

## Interfaces and Dependencies

Use existing PostgreSQL integration patterns already present in WEPPcloud. Do not add new persistence dependencies unless `docs/standards/dependency-evaluation-standard.md` is completed and the decision is recorded in this ExecPlan.

The first implementation should expose a small Python API similar to:

    insert_stats_event(event: Mapping[str, object], connection_or_session: Any) -> None
    fetch_stats_events(filters: Mapping[str, object], connection_or_session: Any) -> Iterator[dict[str, object]]
    make_runtime_event(...) -> dict[str, object]
    make_backfill_event(...) -> dict[str, object]

Exact names may change to match local style, but the implementation must keep the spec's event fields and behavior.
