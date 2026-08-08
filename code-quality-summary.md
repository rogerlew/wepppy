# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-08-07T19:13:21Z`
- Base ref: `7ce0cf524d9e7f4d2be6270ca220b574f04e91ed`

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
| `python_prod_file_sloc` | 933 | 126.0 | 303.0 | 683.2 | 984.8 | 2010.56 | 5697.0 |
| `python_prod_max_function_len` | 752 | 59.0 | 109.25 | 183.8 | 241.45 | 356.9 | 2126.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 201 | 252.0 | 572.0 | 1238.0 | 1586.0 | 2426.0 | 2835.0 |
| `js_source_max_cc` | 201 | 6.0 | 21.0 | 33.0 | 44.0 | 86.0 | 155.0 |

## Changed Files

- Files analyzed: `4`; highest severity red: `1`, yellow: `0`; worsened metric entries: `3` (exceptions: `0`, actionable: `3`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_jobinfo.py` | `python` | `green` | python_file_sloc 494->554 (worsened, green)<br>python_function_len 37->37 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_job_info.py` | `python` | `green` | python_file_sloc 336->336 (unchanged, green)<br>python_function_len 64->64 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/rq/test_job_queue_rank.py` | `python` | `green` | python_file_sloc n/a->235 (new, green)<br>python_function_len n/a->21 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/rq/job_info.py` | `python` | `red` | python_file_sloc 377->473 (worsened, green)<br>python_function_len 153->162 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 4242 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 3549 |
| `tests/nodb/mods/test_features_export_service.py` | 3251 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `wepppy/nodb/mods/features_export/service.py` | 3022 |
| `tests/nodb/mods/test_omni.py` | 2929 |
| `wepppy/rq/project_rq.py` | 2689 |
| `wepppy/wepp/management/managements.py` | 2548 |
| `wepppy/nodb/core/wepp.py` | 2430 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2073 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 631 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 460 |
| `wepppy/nodb/mods/ash_transport/neris_ash_model.py` | 381 |
| `wepppy/nodb/core/landuse.py` | 362 |
| `wepppy/rq/wepp_rq_pipeline.py` | 352 |

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
| `wepppy/weppcloud/controllers_js/channel_gl.js` | 1873 |
| `wepppy/weppcloud/controllers_js/geneva_summary_report.js` | 1747 |
| `wepppy/weppcloud/controllers_js/control_base.js` | 1727 |
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
