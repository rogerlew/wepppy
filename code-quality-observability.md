# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-02-21T18:00:59Z`
- Base ref: `origin/master`

## Threshold Bands

| Metric | Yellow | Red |
| --- | ---: | ---: |
| `python_file_sloc` | 650 | 1200 |
| `python_function_len` | 80 | 150 |
| `python_cc` | 15 | 30 |
| `js_file_sloc` | 1500 | 2500 |
| `js_cc` | 15 | 30 |

## Tooling

- `radon` available: `True`
- `eslint` available: `True`
- Python runtime: `Python 3.12.3`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 746 | 98.0 | 234.75 | 497.0 | 763.0 | 1747.1 | 2244.0 |
| `python_prod_max_function_len` | 581 | 56.0 | 102.0 | 154.0 | 213.0 | 287.4 | 381.0 |
| `python_prod_max_cc` | 590 | 10.0 | 18.0 | 29.0 | 37.55 | 57.44 | 81.0 |
| `js_source_file_sloc` | 147 | 257.0 | 554.0 | 1150.6 | 1324.8 | 2229.06 | 3222.0 |
| `js_source_max_cc` | 147 | 7.0 | 22.5 | 33.4 | 44.1 | 75.94 | 155.0 |

## Changed Files

_No changed-file analysis available (base ref missing or no analyzable files changed)._

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `tests/nodb/mods/test_omni.py` | 2296 |
| `wepppy/nodb/mods/swat/swat.py` | 2244 |
| `wepppy/wepp/management/managements.py` | 2214 |
| `wepppy/nodb/core/wepp.py` | 2024 |
| `tests/microservices/test_files_routes.py` | 2003 |
| `wepppy/climates/cligen/cligen.py` | 1994 |
| `wepppy/nodb/core/watershed.py` | 1845 |
| `wepppy/nodb/mods/omni/omni.py` | 1806 |
| `wepppy/nodb/core/climate.py` | 1784 |
| `wepppy/soils/ssurgo/ssurgo.py` | 1784 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 368 |
| `wepppy/rq/wepp_rq_pipeline.py` | 365 |
| `wepppy/nodb/mods/path_ce_model.py` | 342 |
| `wepppy/export/arc_export.py` | 332 |
| `wepppy/nodb/mods/ash_transport/ashpost.py` | 301 |
| `wepppy/export/ermit_input.py` | 284 |
| `wepppy/nodb/mods/omni/omni_build_router.py` | 283 |
| `wepppy/climates/cligen/cligen.py` | 276 |
| `wepppy/nodb/mods/ash_transport/ash_multi_year_model_alex.py` | 272 |

### `python_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/omni/omni_build_router.py` | 81 |
| `wepppy/nodb/mods/path_ce_model.py` | 81 |
| `wepppy/nodb/core/wepp_prep_service.py` | 67 |
| `wepppy/export/gpkg_export.py` | 65 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 64 |
| `wepppy/export/arc_export.py` | 61 |
| `wepppy/weppcloud/utils/helpers.py` | 57 |
| `wepppy/nodb/mods/path_ce/path_ce_solver.py` | 56 |
| `wepppy/nodb/mods/ash_transport/ashpost.py` | 53 |
| `wepppy/climates/cligen/cligen.py` | 51 |

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 3222 |
| `wepppy/weppcloud/controllers_js/omni.js` | 2500 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1911 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1780 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1736 |
| `wepppy/weppcloud/controllers_js/subcatchments_gl.js` | 1586 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1458 |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 1338 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js` | 1294 |
| `wepppy/weppcloud/controllers_js/climate.js` | 1278 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 70 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 64 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/utils.js` | 45 |
| `wepppy/weppcloud/controllers_js/omni.js` | 42 |
| `wepppy/weppcloud/controllers_js/climate.js` | 40 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
