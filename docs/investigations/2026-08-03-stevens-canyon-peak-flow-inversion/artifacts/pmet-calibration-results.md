# PMET Fire-Severity Calibration Results

## Result

The 924-run grid does not identify a physically persuasive `kcb` and `rawp`
pair that jointly matches post-fire total ET and `Es/ET` for all three forest
fire severities. Low severity comes within a narrow screening margin at the
lowest tested `kcb`; moderate and high severity do not. The negative result is
structural: `kcb` largely scales total demand, while `rawp` weakly changes plant
water stress and cannot independently suppress soil evaporation.

## Experiment

The grid evaluated seven `kcb` values (`0.35-0.95`) and six `rawp` values
(`0.30-0.80`) for each severity. Low severity used H50, H56, H58, H60, and H61;
moderate used H51-H55 and H59; high used all eleven treated forest hillslopes.
Each candidate was run for 100 paired climate years with hillslope-area
weighting. Runoff was excluded from the objective.

| Severity | Best `kcb` | Best `rawp` | Median ET ratio | ET target | Median `Es/ET` | `Es/ET` target | Joint-pass years |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Low | 0.35 | 0.80 | 0.837 | 0.65-0.80 | 0.317 | 0.15-0.30 | 4% |
| Moderate | 0.35 | 0.30 | 0.839 | 0.50-0.70 | 0.400 | 0.25-0.40 | 3% |
| High | 0.35 | 0.40 | 0.654 | 0.40-0.60 | 0.617 | 0.30-0.45 | 0% |

All best candidates occur at the lower `kcb` boundary. This means the grid did
not locate an interior optimum and the values should not be promoted as
calibrated production coefficients.

## Magnitudes

| Severity | Median undisturbed ET (mm/year) | Best Ep (mm/year) | Best Es (mm/year) | Best total ET (mm/year) |
| --- | ---: | ---: | ---: | ---: |
| Low | 320.9 | 181.1 | 84.9 | 267.7 |
| Moderate | 323.4 | 162.6 | 108.8 | 266.7 |
| High | 322.2 | 82.1 | 131.6 | 211.8 |

The high-severity candidate gets total ET into the approximate absolute range
but does so with too much soil evaporation and too little plant-side ET. That
is not a successful calibration. The low candidate is the only combination
reasonably described as within “spitting distance,” missing the upper ET-ratio
bound by `0.037` and the upper `Es/ET` bound by `0.017`. Even there, only four
paired years satisfy both envelopes.

## Sensitivity and Identifiability

At fixed `kcb`, changing `rawp` across its entire tested range moves median ET
ratio by only `0.01-0.03`. Its effect on `Es/ET` is similarly small and often
opposes improvement in total ET. `rawp` is therefore weakly identifiable from
annual ET component targets in this fixture.

Lowering `kcb` reduces total ET, but its effect on the partition is not
independent. In high severity, median `Es/ET` is `0.611-0.626` at `kcb=0.35`
and remains `0.528-0.544` even at `kcb=0.95`; the entire response surface lies
above the target. Extending `kcb` below `0.35` could lower total ET further but
would move the already excessive soil fraction in the wrong direction and
would be difficult to defend for low- or moderate-severity forest.

## Interpretation

The grid supports a low-severity screening value near `kcb=0.35` and
`rawp=0.80` only as a provisional edge case. It rejects the proposition that
severity-specific `kcb` and `rawp` alone can calibrate the full target matrix.
The next calibration control must act on the `Ep`/`Es` partition itself—for
example, the LAI exposure relationship or a separately justified post-fire
soil-evaporation availability term—before further refinement of `kcb` or
`rawp` is meaningful.

## Artifacts

- [Calibration figure index](../figures/pmet-calibration/README.md)
- [`pmet-calibration-summary.csv`](pmet-calibration-summary.csv)
- [`pmet-calibration-annual.csv.gz`](pmet-calibration-annual.csv.gz)
- [`run_pmet_calibration.py`](run_pmet_calibration.py)
