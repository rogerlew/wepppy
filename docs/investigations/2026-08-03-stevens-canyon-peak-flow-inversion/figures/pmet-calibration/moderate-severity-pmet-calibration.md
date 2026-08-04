# Moderate-Severity PMET Calibration

![Moderate severity PMET response surfaces](moderate-severity-pmet-calibration.png)

## Caption

Median annual total-ET ratio and soil-evaporation fraction across 100 paired
climate years for the `kcb` and `rawp` grid. White contours mark the target
envelope boundaries. The red star is the minimum joint-distance candidate.

## Best Candidate

- `kcb=0.35`, `rawp=0.30`
- median ET ratio: `0.839`; target
  `0.50-0.70`
- median `Es/ET`: `0.400`; target
  `0.25-0.40`
- median annual `Ep=162.6 mm`,
  `Es=108.8 mm`, and
  `ET=266.7 mm`
- paired years inside both envelopes: `3%`

## Interpretation

7 of 42 candidates produced at least one paired year inside both envelopes. The surfaces test PMET coefficient sufficiency, not production
defaults. `kcb` and `rawp` remain physically provisional until independently
validated against observed post-fire ET components. Runoff was not included in
the score.

## Source Data

- [`pmet-calibration-summary.csv`](../../artifacts/pmet-calibration-summary.csv)
- [`pmet-calibration-annual.csv.gz`](../../artifacts/pmet-calibration-annual.csv.gz)
