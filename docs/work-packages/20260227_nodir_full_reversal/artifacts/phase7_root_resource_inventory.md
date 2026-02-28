# Phase 7 Root Resource Inventory (Comprehensive)

- Generated: 2026-02-27
- Scope: WD-root resources that currently participate in NoDir-era sidecar compatibility and must be retired from root support.
- Goal: directory-only runtime contract (`<root>/<name>.parquet` no longer valid for in-scope resources).

## Canonical Comprehensive Resource Set

### In-Scope Root Parquet Resources

| Root pattern | Canonical directory target | Status |
| --- | --- | --- |
| `landuse.parquet` | `landuse/landuse.parquet` | Must rehome + retire root fallback |
| `soils.parquet` | `soils/soils.parquet` | Must rehome + retire root fallback |
| `climate.<name>.parquet` | `climate/<name>.parquet` | Must rehome + retire root fallback |
| `watershed.<name>.parquet` | `watershed/<name>.parquet` | Must rehome + retire root fallback |

### In-Scope Root CSV Resources

| Root filename | Canonical directory target | Status |
| --- | --- | --- |
| `wepp_cli_pds_mean_metric.csv` | `climate/wepp_cli_pds_mean_metric.csv` | Must rehome writer + reject root-only dependency |

## Known Concrete Filenames in Current Runtime

- `landuse.parquet`
- `soils.parquet`
- `climate.wepp_cli.parquet`
- `watershed.hillslopes.parquet`
- `watershed.channels.parquet`
- `watershed.flowpaths.parquet`
- `wepp_cli_pds_mean_metric.csv`

Wildcard coverage is still required for legacy or migrated runs that may carry additional sidecars:
- `climate.<name>.parquet`
- `watershed.<name>.parquet`

## Evidence Surfaces

### Root-sidecar producers (must be rehomed)

- `wepppy/nodb/core/landuse.py` writes `WD/landuse.parquet`
- `wepppy/nodb/core/soils.py` writes `WD/soils.parquet`
- `wepppy/topo/peridot/peridot_runner.py` writes `WD/watershed.*.parquet`
- `wepppy/nodb/core/climate_artifact_export_service.py` writes `WD/climate.wepp_cli.parquet`
- `wepppy/nodb/core/climate_artifact_export_service.py` writes `WD/wepp_cli_pds_mean_metric.csv` via `parquet_path.with_name(...)`
- `wepppy/nodb/mods/omni/omni_clone_contrast_service.py` writes contrast outputs to WD root sidecars

### Fallback/alias resolution (must be retired)

- `wepppy/runtime_paths/parquet_sidecars.py`
- `wepppy/query_engine/catalog.py`
- `wepppy/query_engine/activate.py`
- `wepppy/rq/weppcloudr_rq.py`
- `wepppy/wepp/interchange/_utils.py`
- `wepppy/wepp/reports/return_periods.py`
- `wepppy/tools/migrations/parquet_paths.py`

### Secondary operational surfaces requiring alignment

- `wepppy/rq/run_sync_rq.py` root parquet normalization list
- `wepppy/nodb/skeletonize.py` run skeleton allowlist keeps root sidecars
- `wepppy/nodb/mods/omni/omni.py` sibling clone root sidecar cleanup/copy behavior
- `wepppy/rq/job-dependencies-catalog.md` sidecar note describing logical->root mapping

## Out-of-Scope for This Rehome Contract

These are not part of the NoDir root-sidecar compatibility contract and should not be added to this phase unless a real runtime fallback is discovered:
- WEPP interchange/report outputs such as `H.soil.parquet`, `H.wat.parquet`, `H.ebe.parquet`, `ebe_pw0.parquet`, `tc_out.parquet`
- Climate directory outputs already under `climate/` (for example `atlas14_intensity_pds_mean_metric.csv`)

## Comprehensive Scope Lock

Phase 7 implementation must treat the comprehensive in-scope set as:
1. `landuse.parquet`
2. `soils.parquet`
3. `climate.<name>.parquet` (including `climate.wepp_cli.parquet`)
4. `watershed.<name>.parquet` (including hillslopes/channels/flowpaths)
5. `wepp_cli_pds_mean_metric.csv`

If any additional WD-root fallback is found during implementation, it must be added to this artifact before code changes continue.
