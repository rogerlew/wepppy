# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-07-30T14:55:54Z`
- Base ref: `d35586d30`

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
- Python runtime: `Python 3.14.6`
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 932 | 124.0 | 300.5 | 676.4 | 972.45 | 2010.73 | 5697.0 |
| `python_prod_max_function_len` | 751 | 59.0 | 109.0 | 185.0 | 238.5 | 351.0 | 2126.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 200 | 252.5 | 573.0 | 1231.7 | 1588.5 | 2428.64 | 2835.0 |
| `js_source_max_cc` | 200 | 6.0 | 21.0 | 32.1 | 44.05 | 86.07 | 155.0 |

## Changed Files

- Files analyzed: `6`; highest severity red: `1`, yellow: `2`; worsened metric entries: `7` (exceptions: `0`, actionable: `7`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/weppcloud/routes/test_command_bar_mcp_token.py` | `python` | `green` | python_file_sloc 141->187 (worsened, green)<br>python_function_len 39->42 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_project_bp.py` | `python` | `yellow` | python_file_sloc 678->693 (worsened, yellow)<br>python_function_len 107->107 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `red` | python_file_sloc 3513->3539 (worsened, red)<br>python_function_len 118->118 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/command_bar.test.js` | `javascript` | `green` | js_file_sloc n/a->159 (new, green)<br>js_cc n/a->10 (new, green) |
| `wepppy/weppcloud/routes/command_bar/command_bar.py` | `python` | `yellow` | python_file_sloc 248->269 (worsened, green)<br>python_function_len 78->81 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/nodb_api/project_bp.py` | `python` | `green` | python_file_sloc 548->549 (worsened, green)<br>python_function_len 70->70 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 4238 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 3539 |
| `tests/nodb/mods/test_features_export_service.py` | 3251 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `wepppy/nodb/mods/features_export/service.py` | 3022 |
| `tests/nodb/mods/test_omni.py` | 2906 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/nodb/core/wepp.py` | 2430 |
| `wepppy/rq/project_rq.py` | 2375 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2069 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 631 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 460 |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/rq/wepp_rq_pipeline.py` | 352 |
| `wepppy/nodb/core/landuse.py` | 350 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2426 |
| `wepppy/weppcloud/controllers_js/project.js` | 2071 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1997 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1911 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1782 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1659 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |

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
