# Code Review - Roads Point-Source Inslope Non-Channel Routing (2026-03-27)

## Scope Reviewed

- `/workdir/wepppy/wepppy/nodb/mods/roads/monotonic_segments.py`
- `/workdir/wepppy/wepppy/nodb/mods/roads/roads.py`
- `/workdir/wepppy/wepppy/nodb/mods/roads/specification.md`
- `/workdir/wepppy/tests/nodb/mods/test_roads_monotonic_segments.py`
- `/workdir/wepppy/tests/nodb/mods/test_roads_controller.py`
- `/workdir/wepppy/docs/work-packages/20260327_roads_point_source_inslope_non_channel/package.md`
- `/workdir/wepppy/docs/work-packages/20260327_roads_point_source_inslope_non_channel/tracker.md`
- `/workdir/wepppy/docs/work-packages/20260327_roads_point_source_inslope_non_channel/prompts/active/roads_point_source_inslope_non_channel_execplan.md`

## Findings

| ID | Severity | Finding | Status | Resolution |
|---|---|---|---|---|
| CR-01 | Medium | Non-channel routed segments needed explicit receiving-hillslope resolution after trace completion to avoid ambiguous pass merge targets. | Resolved | Run-stage now derives receiving hillslope from traced pre-channel `subwta` cell (`suffix 1|2|3`) and skips with explicit diagnostics when unresolved. |
| CR-02 | Low | Prepare summary lacked explicit routing eligibility counts for non-channel routable segments. | Resolved | Added `eligible_routing_eligibility_counts` and routed/non-routed counters in `last_prepare_summary`. |
| CR-03 | Low | Routed contributor builders (`road + buffer`) were untested directly. | Resolved | Added targeted controller tests for routed two-OFE soil and management file assembly. |
| CR-04 | High | Routed two-OFE management transform removed fill scenario but left yearly FOREST `itype=3`, yielding WEPP parser failure (`ntype` out of range) in live run `ed22a800-e4d1-452a-b09e-cf8cd031060f`. | Resolved | `_build_routed_two_ofe_management_file` now remaps yearly FOREST `itype` (`3 -> 2`) when scenarios are reduced; controller regression test now asserts no `itype=3` remains and `itype=2` is present for FOREST. |

## Medium/High Closure

- Unresolved medium findings: **0**
- Unresolved high findings: **0**

## Reviewer Verdict

- Step-2 objectives are implemented with explicit, test-backed behavior for prepare classification, trace execution, routed contributor assembly, and merge diagnostics.
- Channel-associated inslope behavior remains intact while non-channel routing paths are isolated behind explicit metadata gates.
- Live-run parser regression is closed by explicit `itype` cardinality remap in routed two-OFE management generation.
