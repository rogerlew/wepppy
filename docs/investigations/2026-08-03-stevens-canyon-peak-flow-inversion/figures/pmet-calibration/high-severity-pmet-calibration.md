# High-Severity PMET Calibration

![High severity PMET response surfaces](high-severity-pmet-calibration.png)

## Caption

Median annual total-ET ratio and soil-evaporation fraction across 100 paired
climate years for the `kcb` and `rawp` grid. White contours mark the target
envelope boundaries. The red star is the minimum joint-distance candidate.

## Best Candidate

- `kcb=0.35`, `rawp=0.40`
- median ET ratio: `0.654`; target
  `0.40-0.60`
- median `Es/ET`: `0.617`; target
  `0.30-0.45`
- median annual `Ep=82.1 mm`,
  `Es=131.6 mm`, and
  `ET=211.8 mm`
- paired years inside both envelopes: `0%`

## Interpretation

None of the 42 candidates produced a paired year inside both envelopes. The surfaces test PMET coefficient sufficiency, not production
defaults. `kcb` and `rawp` remain physically provisional until independently
validated against observed post-fire ET components. Runoff was not included in
the score.

## Source Data

- [`pmet-calibration-summary.csv`](../../artifacts/pmet-calibration-summary.csv)
- [`pmet-calibration-annual.csv.gz`](../../artifacts/pmet-calibration-annual.csv.gz)
