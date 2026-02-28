# Phase 1 Handoff

## Scope Completed

Phase 1 inventory and classification are complete for 130 NoDir-referencing files. The matrix now assigns every touchpoint an explicit `action`, `target_phase`, `priority`, blocker field, and validating test command.

## Phase 2 First-PR Candidate Scope

Recommended first PR objective: disable new NoDir default/archive-root creation paths with minimal surface area.

Candidate runtime files:

1. `wepppy/weppcloud/routes/test_bp.py`
2. `wepppy/weppcloud/utils/helpers.py`
3. `wepppy/microservices/rq_engine/project_routes.py`
4. `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
5. `wepppy/nodb/batch_runner.py`

Candidate test updates in same PR:

1. `tests/weppcloud/routes/test_test_bp.py`
2. `tests/weppcloud/utils/test_helpers_paths.py`
3. `tests/microservices/test_rq_engine_project_routes.py`
4. `tests/microservices/test_rq_engine_upload_huc_fire_routes.py`
5. `tests/nodb/test_batch_runner.py`

## Required Validation Commands for First PR

Run from `/workdir/wepppy`:

1. `wctl run-pytest tests/weppcloud/routes/test_test_bp.py tests/weppcloud/utils/test_helpers_paths.py tests/microservices/test_rq_engine_project_routes.py tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/nodb/test_batch_runner.py`
2. `wctl run-pytest tests/microservices tests/weppcloud --maxfail=1`
3. `wctl run-pytest tests/rq --maxfail=1`
4. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
5. `python3 tools/code_quality_observability.py --base-ref origin/master`

## Unresolved Blockers Requiring Human Decision

1. `decide_legacy_archive_browse_window`
- Question: Keep temporary browse/download/diff access to `.nodir` archives during Phase 3 cutover, or hard-fail immediately after Phase 2.
- Impacted files: `wepppy/microservices/browse/*`, `wepppy/microservices/_gdalinfo.py`, `wepppy/weppcloud/routes/diff/diff.py`.

2. `decide_mixed_state_recovery_cutoff`
- Question: Keep automatic mixed-state recovery in queue workers through migration window, or remove recovery once migration tooling is rolled out.
- Impacted files: `wepppy/rq/wepp_rq.py`, `wepppy/rq/wepp_rq_stage_helpers.py`, `wepppy/rq/omni_rq.py`.

3. `decide_nodir_cache_handling_during_cutover`
- Question: Preserve `.nodir/cache` exclusions while legacy runs exist, or remove exclusions immediately with strict directory-only policy.
- Impacted files: `wepppy/rq/project_rq_archive.py`, `wepppy/rq/project_rq_fork.py`.

4. `decide_cli_retention_for_one_time_migration`
- Question: Keep `wepppy/tools/migrations/nodir_bulk.py` as a temporary operational CLI for Phase 3 only, or replace with external/manual migration procedure.
- Impacted files: `wepppy/tools/migrations/nodir_bulk.py`, `tests/tools/test_migrations_nodir_bulk.py`.

5. `decide_clone_support_for_legacy_archive_runs`
- Question: Preserve cross-run clone compatibility from `.nodir` roots during migration window, or require pre-conversion before clone operations.
- Impacted files: `wepppy/nodb/mods/omni/omni_clone_contrast_service.py`.

## Execution Reminder for Phase 2 Agent

Use `artifacts/phase1_classification_matrix.csv` as the source of truth for scope and sequencing. Do not start Phase 4 removals before Phase 2 files above are merged and Phase 3 blocker decisions are resolved.
