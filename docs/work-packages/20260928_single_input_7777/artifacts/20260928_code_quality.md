# Code Quality Observability Report

- Mode: `observe-only` (non-blocking)
- Generated (UTC): `2026-09-28T19:43:40Z`
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
| `python_prod_file_sloc` | 1043 | 132.0 | 324.0 | 686.8 | 971.9 | 2092.8 | 5697.0 |
| `python_prod_max_function_len` | 859 | 60.0 | 109.0 | 176.0 | 236.1 | 397.82 | 2243.0 |
| `python_prod_max_cc` | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `js_source_file_sloc` | 214 | 256.0 | 567.0 | 1206.7 | 1592.3 | 2406.48 | 2840.0 |
| `js_source_max_cc` | 214 | 6.0 | 19.75 | 33.0 | 44.35 | 85.35 | 155.0 |

## Changed Files

- Files analyzed: `5`; highest severity red: `1`, yellow: `0`; worsened metric entries: `5` (exceptions: `0`, actionable: `5`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/nodb/test_single_input_artifacts.py` | `python` | `green` | python_file_sloc 144->150 (worsened, green)<br>python_function_len 65->65 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_single_input_sources.py` | `python` | `green` | python_file_sloc 165->165 (unchanged, green)<br>python_function_len 15->15 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp/test_single_input_soil_formats.py` | `python` | `green` | python_file_sloc 160->185 (worsened, green)<br>python_function_len 33->33 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/single_input.py` | `python` | `green` | python_file_sloc 190->195 (worsened, green)<br>python_function_len 60->65 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/wepp/soils/utils/wepp_soil_util.py` | `python` | `red` | python_file_sloc 1115->1116 (worsened, yellow)<br>python_function_len 202->202 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |

## Hotspots (Current Tree)

### `python_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/nodb/mods/roads/roads.py` | 5697 |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 5282 |
| `tests/weppcloud/routes/test_pure_controls_render.py` | 4458 |
| `tests/nodb/mods/test_roads_controller.py` | 3240 |
| `tests/nodb/mods/test_features_export_service.py` | 3209 |
| `wepppy/nodb/mods/features_export/service.py` | 3099 |
| `tests/nodb/mods/test_omni.py` | 2933 |
| `wepppy/rq/project_rq.py` | 2818 |
| `wepppy/wepp/management/managements.py` | 2623 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 2430 |

### `python_max_function_len_top20`

| Path | Value |
| --- | ---: |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | 2243 |
| `wepppy/nodb/mods/roads/roads.py` | 2126 |
| `tests/nodb/mods/disturbed/live_e2e/runbook.py` | 768 |
| `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` | 641 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 631 |
| `wepppy/nodb/mods/path_ce/data_prep.py` | 541 |
| `wepppy/wepp/fuzzing/single_ofe_stratified_campaign.py` | 528 |
| `wepppy/microservices/rq_engine/orchestration_read_routes.py` | 470 |
| `wepppy/microservices/rq_engine/project_routes.py` | 412 |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | 410 |

### `python_max_cc_top20`

_No entries._

### `js_file_sloc_top20`

| Path | Value |
| --- | ---: |
| `wepppy/weppcloud/controllers_js/omni.js` | 2840 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 2690 |
| `wepppy/weppcloud/controllers_js/map_gl.js` | 2459 |
| `wepppy/weppcloud/controllers_js/project.js` | 2055 |
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
| `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js` | 47 |
| `wepppy/weppcloud/controllers_js/features_export.js` | 46 |

## Review Guidance

- This report is observe-only: it does not block merges.
- Use changed-file deltas to spot opportunistic cleanup candidates.
- Prefer incremental reductions when touching hotspot files.

## Amendment disposition

The existing WSU parser hotspot is unchanged; the preserving writer adds one
field-order branch. Validator growth is five lines for explicit 7777 hydraulics.
Keep these localized branches rather than refactor unrelated parsing. Radon is
unavailable on the host; complexity observations are partial and non-blocking.
