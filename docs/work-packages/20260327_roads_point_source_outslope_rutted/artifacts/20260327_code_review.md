# Code Review - Roads Point-Source Outslope Rutted with Fill OFE (2026-04-07)

## Scope Reviewed

- `/workdir/wepppy/wepppy/nodb/mods/roads/roads.py`
- `/workdir/wepppy/wepppy/nodb/mods/roads/monotonic_segments.py`
- `/workdir/wepppy/wepppy/nodb/mods/roads/specification.md`
- `/workdir/wepppy/wepppy/weppcloud/templates/reports/roads/segment_summary.htm`
- `/workdir/wepppy/tests/nodb/mods/test_roads_controller.py`
- `/workdir/wepppy/tests/nodb/mods/test_roads_monotonic_segments.py`
- `/workdir/wepppy/docs/work-packages/20260327_roads_point_source_outslope_rutted/package.md`
- `/workdir/wepppy/docs/work-packages/20260327_roads_point_source_outslope_rutted/tracker.md`
- `/workdir/wepppy/docs/work-packages/20260327_roads_point_source_outslope_rutted/prompts/active/roads_point_source_outslope_rutted_execplan.md`

## Findings

| ID | Severity | Finding | Status | Resolution |
|---|---|---|---|---|
| CR-01 | Medium | `outslope_rutted` required a distinct execution branch to prevent fallback into inslope routed-two-OFE assembly. | Resolved | Added explicit design branch in `run_roads_wepp()` using routed three-OFE soil/slope/man builders for `outslope_rutted`. |
| CR-02 | Low | `outslope_rutted` fill defaults needed explicit telemetry to avoid silent overuse. | Resolved | Added `fill_default_usage_counts` plus per-segment fill values in execution records and run summary payloads. |
| CR-03 | Low | Roads spec still described step-2 as current boundary and listed `outslope_rutted` as follow-on only. | Resolved | Updated `wepppy/nodb/mods/roads/specification.md` to step-3 current-state contract and follow-on ordering. |

## Medium/High Closure

- Unresolved medium findings: **0**
- Unresolved high findings: **0**

## Reviewer Verdict

- Step-3 implementation is complete and consistent with package scope.
- `outslope_rutted` now executes as point-source `road -> fill -> buffer` with branch-specific behavior for channel-associated vs non-channel routed segments.
- Added tests and summaries make fill/default/routing diagnostics explicit without regressing inslope behavior.
