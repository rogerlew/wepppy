# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-15T20:13:00Z`
- Base ref: `e8c40adda`

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
| `python_prod_file_sloc` | 1026 | 129.0 | 325.25 | 686.5 | 973.75 | 2079.25 | 5697.0 |
| `python_prod_max_function_len` | 842 | 61.0 | 110.0 | 175.9 | 235.75 | 396.67 | 2233.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 212 | 254.0 | 568.25 | 1212.9 | 1594.1 | 2414.67 | 2835.0 |
| `js_source_max_cc` | 212 | 6.0 | 20.25 | 33.0 | 44.45 | 85.45 | 155.0 |

## Changed Files

- Files analyzed: `5`; highest severity red: `0`, yellow: `1`; worsened metric entries: `4` (exceptions: `0`, actionable: `4`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/nodb/mods/test_postfire_debris_flow_run_preparation.py` | `python` | `green` | python_file_sloc n/a->48 (new, green)<br>python_function_len n/a->20 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py` | `python` | `green` | python_file_sloc 173->279 (worsened, green)<br>python_function_len 45->44 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/production.py` | `python` | `yellow` | python_file_sloc 559->563 (worsened, green)<br>python_function_len 92->92 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/production_soils.py` | `python` | `green` | python_file_sloc 59->61 (worsened, green)<br>python_function_len 29->31 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/mods/postfire_debris_flow/run_preparation.py` | `python` | `green` | python_file_sloc n/a->54 (new, green)<br>python_function_len n/a->44 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5274 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4392 |
| `tests/nodb/mods/test_features_export_service.py` | 3251 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `wepppy/nodb/mods/features_export/service.py` | 3026 |
| `tests/nodb/mods/test_omni.py` | 2929 |
| `wepppy/rq/project_rq.py` | 2809 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 2421 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2233 |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 613 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 402 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2835 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2459 |
| `wepppy/weppcloud/controllers_js/project.js` | 2056 |
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
| `wepppy/weppcloud/controllers_js/postfire_debris_flow.js` | 75 |
| `wepppy/weppcloud/controllers_js/dss_export.js` | 58 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 57 |
| `wepppy/weppcloud/controllers_js/project.js` | 52 |
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.
