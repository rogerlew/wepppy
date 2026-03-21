# K Benchmark Comparison Summary

Date: 2026-03-21
Source: synthetic benchmark sanity check using the package comparison harness test fixture.
Reference mode: `gssurgo_kffact` (benchmark harness precedence default).
Thresholds: `abs_error_warn = 0.10`, `rel_error_warn = 0.40`.

## Summary Metrics

| Mode | Count | MAE | RMSE | Bias | Pearson r | Flagged Points |
|---|---:|---:|---:|---:|---:|---:|
| `polaris_nomograph` | 3 | 0.1100 | 0.1737 | 0.1033 | 0.4465 | 1 (`p2`) |
| `polaris_epic` | 3 | 0.0133 | 0.0141 | ~0.0000 | 0.9948 | 0 |

## Interpretation

- The implemented sanity-comparison harness is functioning and correctly flags outlier behavior (nomograph `p2` case).
- `polaris_epic` tracks the synthetic benchmark closely in this fixture.
- The artifact demonstrates expected workflow behavior: both POLARIS estimators are compared against the same reference points and thresholds, and flagged points are surfaced explicitly.

## Notes

This package artifact is a workflow-validation benchmark (synthetic fixture), not a scientific regional calibration claim.
