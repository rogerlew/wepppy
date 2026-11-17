# Roads refactor baseline

Observed 2026-11-17 22:37 UTC at `96555f2f95326350d2d7007c19327378ea831ab0`.
Source: `wepppy/nodb/mods/roads/roads.py`, unchanged in the inspected checkout.

## Measurement

`tools/code_quality_observability.py:analyze_python_text` reports 5,907 SLOC and a maximum function length of 2,069. SLOC counts nonblank, non-comment lines (including docstrings); physical length is 6,447 lines. AST inspection counts 150 functions. Cyclomatic complexity is unavailable in the host Python environment (`cc_visit is None`); do not describe it as zero or passing. Obtain the existing CI/runtime measurement before implementation closure; no new production dependency is justified.

The user's 5,834-SLOC observation differs from the current checkout; retain this exact revision as the comparison base rather than assuming the earlier count still applies.

| Function | Start line | Physical span |
| --- | ---: | ---: |
| `run_roads_wepp` | 4316 | 2069 |
| `prepare_segments` | 1613 | 223 |
| `set_uploaded_geojson` | 1106 | 166 |
| `_regenerate_roads_report_resources` | 4131 | 163 |
| `query_segment_detail` | 1454 | 157 |
| `_resolve_segment_run_inputs` | 2092 | 140 |
| `_validated_params_payload` | 896 | 128 |
| `_last_parameterization_readback` | 3517 | 120 |
| `_build_routed_three_ofe_soil_file` | 3092 | 106 |
| `_select_outslope_unrutted_hillslope_segments` | 2361 | 103 |

## Extraction map

| Responsibility | Existing anchors | Proposed private home |
| --- | --- | --- |
| Input normalization and mapping | `_validated_params_payload`, `_build_attribute_catalog`, `_resolve_segment_run_inputs` | `_inputs.py` |
| Preparation orchestration and spatial selection | `prepare_segments`, `_resolve_prepare_raster_paths`, `_select_outslope_unrutted_hillslope_segments` | `_prepare.py`, existing `_unrutted.py` where cohesive |
| Native profiles | `_write_routed_*`, `_build_routed_*`, `_build_single_ofe_*` | `_slope_inputs.py`, `_soil_inputs.py`, `_management_inputs.py` |
| Execution stages and design branches | `run_roads_wepp`, `_run_segment_hillslope` | `_execution.py`, `_point_source.py`, `_unrutted_execution.py` |
| PASS combination and workspace assembly | `_normalize_road_pass_header_climate_tokens`, `_combine_target_hillslope_pass`, `_prepare_roads_runs_workspace` | `_pass_routing.py` |
| Accounting and publication | `_prepare_modeled_area_accounting`, `_regenerate_roads_report_resources` | `_reporting.py`; reuse existing loss-summary helper |
| Inspection and parameterization views | `query_segment_detail`, `_last_parameterization_readback`, `query_parameterization` | `_queries.py`; reuse parameterization helpers |

Names are a starting map, not permission to create empty scaffolding. Inspect call dependencies before each extraction. Keep runtime collaborators out of serialized instance state. Avoid mixins, dynamic method installation, `__getattr__` proxies, and cyclic facade imports. Preserve module-level monkeypatch seams deliberately; do not move a dependency and quietly bypass its existing test/control seam.

## Risk inventory

There are 19 broad-handler sites including two `BaseException` upload rollback boundaries. Inventory each by intent before moving it: validation translation, raster/geometry errors, segment-level continuation, final run status, and cancellation rollback have different contracts. Narrow only when characterized failure behavior is preserved; do not accidentally remove rollback for cancellation or let telemetry mask the original failure.

`run_roads_wepp` owns status transitions, retained prior results, workspace staging, runtime template/readback state, design-specific native execution, accounting, report generation, and failure summaries. Its extraction needs explicit stage data and ordered side effects, not a catch-all dictionary or copies of mutable controller state.

The latest unrutted contract includes top placement and policy-marker admission, including failed and zero-contributor attempts. `tests/roads/README.md` still describes older non-positive-upstream negative cases; reconcile fixture expectations against current contracts and actual baseline before using those cases as an oracle. This is a local documentation discrepancy, not evidence of a production defect.

## Existing test anchors

Use `tests/nodb/mods/test_roads_*.py`, `tests/rq/test_roads_rq.py`, `tests/microservices/test_rq_engine_roads_routes.py`, `tests/weppcloud/routes/test_roads_bp.py`, and `tests/wepp/interchange/test_roads_*.py`. Native validation lives in `tests/roads/` with `roads_matrix.py`, `roads_project.py`, and the sensitivity helpers. Its full-project tests are opt-in; a skipped suite is not project parity evidence.

No runtime tests were run for the documentation scaffold. Before implementation retain the full quality report in `/tmp`, source-qualified test receipts, and a baseline generated-artifact manifest. Capture a concise durable metric summary here; do not commit large native runs or sensitive project state.
