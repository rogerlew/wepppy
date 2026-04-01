# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-03-28T04:20:39Z`
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
| `python_prod_file_sloc` | 819 | 105.0 | 252.0 | 522.2 | 845.2 | 1569.18 | 3225.0 |
| `python_prod_max_function_len` | 646 | 56.0 | 104.0 | 149.5 | 216.75 | 293.35 | 850.0 |
| `python_prod_max_cc` | 659 | 10.0 | 18.0 | 28.0 | 38.0 | 55.42 | 66.0 |
| `js_source_file_sloc` | 159 | 275.0 | 560.5 | 1230.8 | 1469.0 | 2365.52 | 2500.0 |
| `js_source_max_cc` | 159 | 7.0 | 22.5 | 33.2 | 42.3 | 78.68 | 155.0 |

## Changed Files

_No changed-file analysis available (base ref missing or no analyzable files changed)._

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 3225 |
| `tests/nodb/mods/test_omni.py` | 2467 |
| `wepppy/wepp/management/managements.py` | 2214 |
| `wepppy/nodb/core/wepp.py` | 2100 |
| `wepppy/climates/cligen/cligen.py` | 2091 |
| `wepppy/nodb/base.py` | 1884 |
| `tests/microservices/test_browse_auth_routes.py` | 1779 |
| `wepppy/soils/ssurgo/ssurgo.py` | 1778 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 1770 |
| `wepppy/topo/wbt/terrain_processor.py` | 1671 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 850 |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 368 |
| `wepppy/rq/wepp_rq_pipeline.py` | 352 |
| `wepppy/export/arc_export.py` | 332 |
| `wepppy/tools/migrations/unroll_root_resources_batch.py` | 309 |
| `wepppy/nodb/mods/ash_transport/ashpost.py` | 301 |
| `wepppy/export/ermit_input.py` | 284 |
| `wepppy/climates/cligen/cligen.py` | 276 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 276 |

### `python_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 66 |
| `wepppy/export/gpkg_export.py` | 65 |
| `wepppy/export/arc_export.py` | 61 |
| `wepppy/nodb/core/wepp_prep_service.py` | 58 |
| `tools/code_quality_observability.py` | 57 |
| `wepppy/nodb/mods/path_ce/path_ce_solver.py` | 56 |
| `wepppy/nodb/mods/roads/roads.py` | 56 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 55 |
| `wepppy/nodb/mods/ash_transport/ashpost.py` | 53 |
| `wepppy/climates/cligen/cligen.py` | 51 |

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2500 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2398 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2342 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1911 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1780 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1642 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |
| `wepppy/weppcloud/controllers_js/subcatchments_gl.js` | 1586 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js` | 1456 |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 1339 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 77 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 75 |
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
