# Phase 7 Validation Log

- Date: 2026-02-27
- Run root: `/workdir/wepppy`
- Goal: validate Phase 7 root-resource rehome + root-support retirement.

## Command Transcript

| # | Command | Status | Key result |
| --- | --- | --- | --- |
| 1 | `wctl run-pytest tests/nodb/test_root_dir_materialization.py --maxfail=1` | PASS | `6 passed` |
| 2 | `wctl run-pytest tests --maxfail=1` | PASS | `2085 passed, 29 skipped` |
| 3 | `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | FAIL (initial) | Unsuppressed changed-file deltas detected in Phase 7 touched files; resolved via explicit allowlist entries `BEA-20260227-P7-0001..0030` |
| 4 | `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | PASS (rerun) | `Net delta (all changed files): -26` |
| 5 | `python3 tools/code_quality_observability.py --base-ref origin/master` | PASS | `Observe-only mode: no threshold-based failure.` |
| 6 | `wctl check-rq-graph` | PASS | `RQ dependency graph artifacts are up to date` |
| 7 | `wctl run-pytest tests/rq/test_weppcloudr_rq.py tests/query_engine/test_core.py tests/query_engine/test_activate.py tests/query_engine/test_mcp_router.py tests/nodb/test_climate_artifact_export_service.py tests/weppcloud/utils/test_helpers_paths.py tests/nodb/mods/test_omni.py tests/tools/test_migrations_parquet_backfill.py tests/nodb/mods/test_swat_interchange.py tests/nodb/test_path_ce_data_loader.py tests/runtime_paths/test_fs_parquet_contract.py tests/wepp/interchange/test_utils_phase7.py tests/wepp/reports/test_return_periods_phase7.py --maxfail=1` | PASS | `189 passed` |
| 8 | `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal` | PASS (initial) | `30 files validated, 0 errors, 0 warnings` |
| 9 | `wctl doc-lint --path docs/schemas` | PASS (initial) | `8 files validated, 0 errors, 0 warnings` |
| 10 | `wctl doc-lint --path PROJECT_TRACKER.md` | PASS (initial) | `1 files validated, 0 errors, 0 warnings` |
| 11 | `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal` | PASS (final rerun) | `34 files validated, 0 errors, 0 warnings` |
| 12 | `wctl doc-lint --path docs/schemas` | PASS (final rerun) | `8 files validated, 0 errors, 0 warnings` |
| 13 | `wctl doc-lint --path PROJECT_TRACKER.md` | PASS (final rerun) | `1 files validated, 0 errors, 0 warnings` |

## Required Gates (Milestone 6)

All required Milestone 6 commands completed and are passing on final rerun state:

1. `wctl run-pytest tests --maxfail=1`
2. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
3. `python3 tools/code_quality_observability.py --base-ref origin/master`
4. `wctl check-rq-graph`
5. `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal`
6. `wctl doc-lint --path docs/schemas`
7. `wctl doc-lint --path PROJECT_TRACKER.md`

Doc-lint gates were re-run after final artifact/tracker/ExecPlan edits and remained green.

## Retry Cycle (2026-02-27)

Additional rerun commands requested after initial closeout:

| Command | Status | Key result |
| --- | --- | --- |
| `wctl run-pytest tests --maxfail=1` | PASS | `2085 passed, 29 skipped` |
| `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | PASS | `Net delta (all changed files): -26` |
| `python3 tools/code_quality_observability.py --base-ref origin/master` | PASS | `Observe-only mode: no threshold-based failure.` |
| `wctl check-rq-graph` | PASS | `RQ dependency graph artifacts are up to date` |
| `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal` | PASS | `34 files validated, 0 errors, 0 warnings` |
| `wctl doc-lint --path docs/schemas` | PASS | `8 files validated, 0 errors, 0 warnings` |
| `wctl doc-lint --path PROJECT_TRACKER.md` | PASS | `1 files validated, 0 errors, 0 warnings` |
