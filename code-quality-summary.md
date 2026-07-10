# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-07-10T21:51:44Z`
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

- `radon` available: `False`
- `eslint` available: `True`
- Python runtime: `Python 3.12.3`
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 908 | 124.0 | 294.5 | 661.2 | 960.6 | 1969.92 | 5697.0 |
| `python_prod_max_function_len` | 728 | 60.0 | 108.25 | 175.3 | 225.65 | 345.14 | 2126.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 181 | 282.0 | 582.0 | 1238.0 | 1617.0 | 2458.8 | 2835.0 |
| `js_source_max_cc` | 181 | 7.0 | 22.0 | 33.0 | 45.0 | 87.4 | 155.0 |

## Changed Files

_No changed-file analysis available (base ref missing or no analyzable files changed)._

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 4232 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `tests/nodb/mods/test_features_export_service.py` | 3043 |
| `wepppy/nodb/mods/features_export/service.py` | 2998 |
| `tests/nodb/mods/test_omni.py` | 2895 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/nodb/core/wepp.py` | 2430 |
| `wepppy/climates/cligen/cligen.py` | 2248 |
| `wepppy/nodb/base.py` | 2213 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2063 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 631 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 460 |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/rq/wepp_rq_pipeline.py` | 352 |
| `wepppy/nodb/core/landuse.py` | 350 |
| `wepppy/export/arc_export.py` | 332 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2401 |
| `wepppy/weppcloud/controllers_js/project.js` | 2040 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1911 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1782 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1659 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1617 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 93 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 86 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/controllers_js/project.js` | 52 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |
| `wepppy/weppcloud/controllers_js/utils.js` | 45 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
