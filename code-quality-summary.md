# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-03-22T02:16:28Z`
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
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 785 | 104.0 | 248.0 | 507.6 | 813.0 | 1325.6 | 2214.0 |
| `python_prod_max_function_len` | 617 | 56.0 | 102.0 | 148.4 | 215.2 | 282.72 | 381.0 |
| `python_prod_max_cc` | 627 | 10.0 | 18.0 | 28.0 | 37.7 | 52.48 | 67.0 |
| `js_source_file_sloc` | 151 | 257.0 | 553.0 | 1113.0 | 1334.5 | 2126.5 | 2500.0 |
| `js_source_max_cc` | 151 | 7.0 | 21.0 | 33.0 | 43.5 | 78.0 | 155.0 |

## Changed Files

_No changed-file analysis available (base ref missing or no analyzable files changed)._

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `tests/nodb/mods/test_omni.py` | 2467 |
| `wepppy/wepp/management/managements.py` | 2214 |
| `wepppy/nodb/core/wepp.py` | 2098 |
| `wepppy/climates/cligen/cligen.py` | 2091 |
| `wepppy/nodb/base.py` | 1884 |
| `tests/microservices/test_browse_auth_routes.py` | 1779 |
| `wepppy/soils/ssurgo/ssurgo.py` | 1776 |
| `wepppy/topo/wbt/terrain_processor.py` | 1670 |
| `tests/microservices/test_files_routes.py` | 1537 |
| `wepppy/rq/culvert_rq.py` | 1488 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 368 |
| `wepppy/rq/wepp_rq_pipeline.py` | 352 |
| `wepppy/export/arc_export.py` | 332 |
| `wepppy/tools/migrations/unroll_root_resources_batch.py` | 309 |
| `wepppy/nodb/mods/ash_transport/ashpost.py` | 301 |
| `wepppy/export/ermit_input.py` | 284 |
| `wepppy/climates/cligen/cligen.py` | 276 |
| `wepppy/nodb/mods/ash_transport/ash_multi_year_model_alex.py` | 272 |
| `wepppy/wepp/management/utils/downgrade_to_98_4_format.py` | 262 |

### `python_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/core/wepp_prep_service.py` | 67 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 66 |
| `wepppy/export/gpkg_export.py` | 65 |
| `wepppy/export/arc_export.py` | 61 |
| `tools/code_quality_observability.py` | 57 |
| `wepppy/nodb/mods/path_ce/path_ce_solver.py` | 56 |
| `wepppy/nodb/mods/ash_transport/ashpost.py` | 53 |
| `wepppy/climates/cligen/cligen.py` | 51 |
| `wepppy/weppcloud/utils/helpers.py` | 51 |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 48 |

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2500 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2342 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1911 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1780 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |
| `wepppy/weppcloud/controllers_js/subcatchments_gl.js` | 1586 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1532 |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 1338 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 1331 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js` | 1294 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 75 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 70 |
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
