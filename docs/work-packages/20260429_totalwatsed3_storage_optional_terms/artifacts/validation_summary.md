# Validation Summary

Timestamp: 2026-04-30 04:09 UTC

## WEPPpy Required Tests

- `wctl run-pytest tests/wepp/interchange/test_hill_wat_interchange.py` - 4 passed.
- `wctl run-pytest tests/wepp/interchange/test_hill_soil_interchange.py` - 1 passed.
- `wctl run-pytest tests/wepp/interchange/test_hill_element_interchange.py` - 2 passed.
- `wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py` - 4 passed.
- `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py` - 2 passed.

## WEPP-Forest Build/Smoke

- `make wepp wepp_hill` from `/workdir/wepp-forest/src` - passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp` - p962 and p1 passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill` - p962 and p1 passed.

## Review Fix Coverage

- `totalwatsed3` element partition aggregation now joins production-shaped `H.element.parquet` rows to WAT on calendar keys and takes `sim_day_index` from WAT.
- `/workdir/wepp-forest/src/watbalprint.for` now appends all five optional WAT storage/capacity terms for the `ivers=3` watershed output path.
- The ExecPlan closure-audit command example now uses the tool's positional parquet-path argument.

## Production Closure Gate

Completed on wepp1 without container takedown.

- Regenerated: `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`
- Backup: `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet.bak.20260430T040509Z`
- New hash: `20f39d30280c9ccaf20754778e57c9e5595711ea334c8ffab82def2d89f68ca2`
- Backup hash: `d649088f1948c3f98de4f4c5868824aba920b8552bacc07da4cfaf40f37c8e73`
- Whole-run reconstructed closure with legacy storage: `-13,813.464759 mm`
- Closure as percent of rain + melt: `-16.855844%`
- Mean absolute daily closure with storage: `1.877172 mm`
- Max absolute daily closure: `541.600205 mm` on 1996-02-06
- Runoff consistency max absolute difference: `0.0 mm`

Hillslope findings:

- `H2637`: closure with storage `-119,246.654467 mm` (`-114.007900%` of rain + melt); top closure day 1996-02-06.
- `H2809`: closure with storage `-297,116.718881 mm` (`-278.295506%` of rain + melt); top closure day 1996-02-06.

Artifacts:

- `wepp1_uncapped_spectacular_20260430/daily_closure_audit_summary.json`
- `wepp1_uncapped_spectacular_20260430/daily_closure_audit_top_days.csv`
- `wepp1_uncapped_spectacular_20260430/hillslope_reconciliation_H2637_H2809.json`
- `wepp1_uncapped_spectacular_20260430/production_rollout_gate.md`
