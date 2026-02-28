# Phase 7 Scope Matrix

- Date: 2026-02-27
- Scope lock source: `artifacts/phase7_root_resource_inventory.md`
- Scope lock resources:
  1. `landuse.parquet`
  2. `soils.parquet`
  3. `climate.<name>.parquet`
  4. `watershed.<name>.parquet`
  5. `wepp_cli_pds_mean_metric.csv`

## Locked Implementation Targets

| Surface file | Previous root behavior | Phase 7 directory-only behavior | Regression evidence | Rollback note |
| --- | --- | --- | --- | --- |
| `wepppy/runtime_paths/errors.py` | No dedicated migration-required helper for retired root resources | Added `NODIR_MIGRATION_REQUIRED` helper for explicit fail-fast payloads | `tests/runtime_paths/test_fs_parquet_contract.py` | Revert helper additions only if root fallback contract is restored globally |
| `wepppy/runtime_paths/parquet_sidecars.py` | Pickers/lookup accepted WD-root sidecars | Canonical directory lookup only; retired root inventory detection helpers added | `tests/runtime_paths/test_fs_parquet_contract.py` | Do not reintroduce root wildcard fallback without migration phase approval |
| `wepppy/runtime_paths/fs.py` | `stat/open_read` could read retired root sidecar paths via compatibility layer | Parquet access routed through directory-only resolver; retired roots fail with migration-required | `tests/runtime_paths/test_fs_parquet_contract.py` | Reverting requires coordinated query/RQ/consumer fallback restore |
| `wepppy/query_engine/catalog.py` | Logical alias mapping tolerated legacy root ids | Exact dataset path resolution only | `tests/query_engine/test_core.py`, `tests/query_engine/test_mcp_router.py` | Avoid partial alias restoration; must stay consistent with activation/runtime checks |
| `wepppy/query_engine/activate.py` | Activation could proceed with retired root sidecars and mixed root/canonical state | Activation/update now reject retired root resources and catalog canonical only | `tests/query_engine/test_activate.py` | Do not downgrade to best-effort sidecar acceptance |
| `wepppy/rq/weppcloudr_rq.py` | Optional root-sidecar parquet override map tolerated | Override plumbing removed; explicit retired-root guard before render steps | `tests/rq/test_weppcloudr_rq.py` | Compat kwarg kept (`parquet_overrides`) but ignored intentionally |
| `wepppy/wepp/interchange/_utils.py` | Climate parquet helper tolerated root `climate.*.parquet` | Canonical `climate/wepp_cli.parquet`; root retired files fail migration-required | `tests/wepp/interchange/test_utils_phase7.py` | Preserve explicit migration-required contract on legacy roots |
| `wepppy/wepp/reports/return_periods.py` | Climate asset discovery could include root `climate.*.parquet` | Canonical-only discovery; retired root climate sidecars rejected | `tests/wepp/reports/test_return_periods_phase7.py` | Do not reintroduce root climate discovery fallback |
| `wepppy/tools/migrations/parquet_paths.py` | Helper compatibility could accept root sidecars | Canonical-only helper and explicit retired-root finder utility | `tests/tools/test_migrations_parquet_backfill.py` | Keep migration helper aligned with runtime directory-only behavior |
| `wepppy/nodb/core/landuse.py` | Producer wrote `WD/landuse.parquet`; clean path removed root sidecar | Producer writes `landuse/landuse.parquet`; no root cleanup side effects | `tests/nodb/test_root_dir_materialization.py`, `tests/tools/test_migrations_parquet_backfill.py` | Root-sidecar cleanup should remain migration phase responsibility |
| `wepppy/nodb/core/soils.py` | Producer wrote `WD/soils.parquet`; clean path removed root sidecar | Producer writes `soils/soils.parquet`; no root cleanup side effects | `tests/nodb/test_root_dir_materialization.py`, `tests/tools/test_migrations_parquet_backfill.py` | Same rollback constraint as landuse |
| `wepppy/nodb/core/climate_artifact_export_service.py` | CLI parquet and recurrence CSV emitted under root sidecar layout | Writes `climate/wepp_cli.parquet` and `climate/wepp_cli_pds_mean_metric.csv` | `tests/nodb/test_climate_artifact_export_service.py` | Keep producer/consumer path parity with routes |
| `wepppy/topo/peridot/peridot_runner.py` | Watershed parquet writes/reads supported root sidecar layout | Canonical `watershed/*.parquet` writes and migration helpers | `tests/nodb/mods/test_swat_interchange.py`, `tests/tools/test_migrations_parquet_backfill.py` | Watershed parquet layout must remain canonical for query + interchange |
| `wepppy/tools/migrations/watershed.py` | Legacy generation could target root sidecars | Legacy conversion output now canonical under `watershed/` | `tests/tools/test_migrations_parquet_backfill.py` | Keep migration tool idempotent with canonical targets |
| `wepppy/rq/run_sync_rq.py` | Normalization list included root sidecar assumptions | Canonical parquet normalization only | `tests/rq/test_run_sync_rq.py` | Reversion risks false-positive root support in operational sync |
| `wepppy/nodb/skeletonize.py` | Skeletonization allowed root parquet sidecar retention | Retains canonical directory assets only | `tests/nodb/test_batch_runner.py` (indirect), targeted regression suite | Preserve canonical skeleton behavior across archive/clone surfaces |
| `wepppy/nodb/mods/omni/omni_clone_contrast_service.py` | Contrast clone path copied/linked root sidecars | Canonical `landuse/landuse.parquet` and `soils/soils.parquet` outputs | `tests/nodb/mods/test_omni.py` | Keep contrast clone canonical even when legacy roots exist |
| `wepppy/nodb/mods/omni/omni.py` | Archive sibling handling could copy/remove root sidecars | Explicit migration-required fail-fast for non-dir sibling clone path; root sidecar handling retired | `tests/nodb/mods/test_omni.py` | No silent fallback for archive siblings with retired roots |
| `wepppy/weppcloud/utils/helpers.py` | Omni helper linked root parquet sidecars into shared inputs | Root sidecar symlink behavior removed | `tests/weppcloud/utils/test_helpers_paths.py` | Keep helper behavior canonical-only; preserve existing conflict protection |

## Policy Lock Confirmation

- `apply_nodir=false` migration specification remains required artifact contract (`phase7_apply_nodir_false_migration_spec.md`).
- `apply_nodir=true` migration handling remains out of scope for Phase 7.
