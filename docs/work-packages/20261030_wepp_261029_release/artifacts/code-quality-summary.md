# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-10-30T16:24:03Z`
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
- Python runtime: `Python 3.14.6`
- Exception rules source: _none_
- Exception rules configured: `0`
- Exception rules applied: `0`

## Overall Baseline

| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python_prod_file_sloc` | 1114 | 133.0 | 309.0 | 680.4 | 964.45 | 2080.37 | 5416.0 |
| `python_prod_max_function_len` | 928 | 58.0 | 107.0 | 175.3 | 227.3 | 387.84 | 2249.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 236 | 241.0 | 547.25 | 1092.0 | 1549.25 | 2326.7 | 2840.0 |
| `js_source_max_cc` | 236 | 6.0 | 19.0 | 32.0 | 42.5 | 84.25 | 155.0 |

## Changed Files

- Files analyzed: `8`; highest severity red: `0`, yellow: `0`; worsened metric entries: `0` (exceptions: `0`, actionable: `0`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/tools/test_roads_buffer_drainage.py` | `python` | `green` | python_file_sloc n/a->34 (new, green)<br>python_function_len n/a->10 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_buffer_reconciliation.py` | `python` | `green` | python_file_sloc n/a->23 (new, green)<br>python_function_len n/a->7 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_drainage_runtime.py` | `python` | `green` | python_file_sloc n/a->47 (new, green)<br>python_function_len n/a->10 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_drainage_validation.py` | `python` | `green` | python_file_sloc n/a->38 (new, green)<br>python_function_len n/a->12 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_engineered_surface.py` | `python` | `green` | python_file_sloc n/a->36 (new, green)<br>python_function_len n/a->14 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_ofe_budget.py` | `python` | `green` | python_file_sloc n/a->89 (new, green)<br>python_function_len n/a->14 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_parameterization_score.py` | `python` | `green` | python_file_sloc n/a->45 (new, green)<br>python_function_len n/a->8 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/tools/test_roads_parameterization_screen.py` | `python` | `green` | python_file_sloc n/a->39 (new, green)<br>python_function_len n/a->18 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5416 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5349 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4643 |
| `tests/nodb/mods/test_features_export_service.py` | 3243 |
| `wepppy/nodb/mods/features_export/service.py` | 3139 |
| `tests/nodb/mods/test_roads_controller.py` | 3065 |
| `tests/nodb/mods/test_omni.py` | 2972 |
| `wepppy/rq/project_rq.py` | 2837 |
| `wepppy/wepp/management/managements.py` | 2623 |
| `wepppy/nodb/core/wepp.py` | 2433 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2249 |
| `wepppy/nodb/mods/roads/roads.py` | 2031 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 638 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 396 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2840 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2459 |
| `wepppy/weppcloud/controllers_js/project.js` | 2081 |
| `wepppy/weppcloud/controllers_js/ag_fields.js` | 1997 |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | 1915 |
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1873 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1751 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/subcatchment_delineation.js` | 1636 |

### `js_max_cc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js` | 155 |
| `wepppy/weppcloud/controllers_js/wepp.js` | 93 |
| `wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js` | 86 |
| `wepppy/weppcloud/static-src/tests/smoke/map-gl.spec.js` | 81 |
| `wepppy/weppcloud/controllers_js/postfire_debris_flow.js` | 74 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/controllers_js/project.js` | 52 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 48 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
