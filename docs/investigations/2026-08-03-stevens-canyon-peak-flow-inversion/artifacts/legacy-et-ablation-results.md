# Legacy-ET Burn-Matrix Results

## Result

Running both treatment and reference hillslopes without `pmetpara.txt` does not
produce a credible post-fire ET response. No severity has any of its 100 paired
climate years inside both the total-ET-ratio and `Es/ET` target envelopes.
Legacy ET changes the component partition, but low- and moderate-severity total
ET remains almost identical to undisturbed ET. High-severity total ET declines
only to a median ratio of `0.862`, well above the `0.40-0.60` target.

| Severity | Legacy ET ratio | ET target | Legacy `Es/ET` | `Es/ET` target | Joint-pass years |
| --- | ---: | ---: | ---: | ---: | ---: |
| Low | 0.990 | 0.65-0.80 | 0.106 | 0.15-0.30 | 0% |
| Moderate | 0.997 | 0.50-0.70 | 0.308 | 0.25-0.40 | 0% |
| High | 0.862 | 0.40-0.60 | 0.501 | 0.30-0.45 | 0% |

## Absolute Magnitudes

| Severity | Reference Ep | Reference Es | Reference Er | Reference ET | Burned Ep | Burned Es | Burned Er | Burned ET |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Low | 324.9 | 0.0 | 0.0 | 324.9 | 235.3 | 34.1 | 50.1 | 324.0 |
| Moderate | 321.6 | 0.0 | 0.0 | 321.6 | 190.1 | 99.1 | 32.5 | 324.2 |
| High | 324.4 | 0.0 | 0.0 | 324.4 | 128.8 | 136.9 | 8.0 | 274.5 |

All depths are median annual millimeters across 100 years and are
hillslope-area weighted within each severity class. The undisturbed reference
differs slightly among rows because each row uses the matching treated
hillslope subset.

The zero undisturbed `Es` and `Er` values are a model result, not a measurement
or a missing-data substitution. Under the legacy routine, dense forest canopy
places all modeled ET in `Ep`. Fire-reduced canopy and ground cover then move
ET into `Es` and `Er`, but the potential demand remains almost fully consumed
for low and moderate severity.

## Comparison with the Existing PMET Fixture

| Severity | PMET ET ratio | Legacy ET ratio | PMET `Es/ET` | Legacy `Es/ET` |
| --- | ---: | ---: | ---: | ---: |
| Low | 0.985 | 0.990 | 0.354 | 0.106 |
| Moderate | 0.983 | 0.997 | 0.408 | 0.308 |
| High | 0.849 | 0.862 | 0.528 | 0.501 |

The original fixture PMET values and the newly executed legacy values give
nearly the same total-ET ratios. The largest difference is partitioning: legacy
ET strongly reduces low-severity soil evaporation and shifts evaporation to
`Er`, but does not generate the expected decline in total ET. At high severity,
where little residue remains, the methods are especially similar.

## Interpretation

This is a negative model-form result. Turning PMET off is not an adequate fire
parameterization and should not be adopted as a production workaround. The
broad excessive-ET response is not specific to PMET coefficients: both ET
paths primarily redistribute atmospheric demand after canopy loss instead of
reducing realized total ET by the amount implied by the target matrix.

The legacy result also exposes a separate forest-model limitation. Assigning
zero annual soil and residue evaporation to undisturbed forest is not a
physically complete ET partition. Consequently, legacy ET cannot serve as a
credible baseline partition even where its post-fire `Es/ET` happens to fall
inside one severity envelope.

The next model investigation should instrument daily potential ET and each
limiting step in both `evap` and `evappm`, then introduce a forest-specific
canopy/interception and exposed-soil availability formulation. Calibration
should require nonzero undisturbed `Es` and `Er`, a severity-dependent decline
in total ET, and plausible post-fire `Es/ET` simultaneously. Runoff should be
revisited only after that ET contract is satisfied.

## Execution and Controls

The experiment ran 33 isolated hillslope simulations: eleven undisturbed,
eleven burned, and eleven high-severity. Each produced 36,525 finite daily
water-balance rows. `pmetpara.txt` was absent in every lane, model stdout did
not contain the PMET announcement, and `wepp_ui.txt`, `gwcoeff.txt`, `snow.txt`,
`chntyp.txt`, `tc.txt`, and `chan.inp` were retained. Temporary lanes were
removed and `/workdir/wepp-forest_260430_baseline` remained clean.

## Artifacts

- [Figure and extended sidecar](../figures/legacy-et-ablation/legacy-et-burn-matrix.md)
- [`legacy-et-ablation-summary.csv`](legacy-et-ablation-summary.csv)
- [`legacy-et-ablation-annual.csv.gz`](legacy-et-ablation-annual.csv.gz)
- [`run_legacy_et_ablation.py`](run_legacy_et_ablation.py)
- [`plot_legacy_et_ablation.py`](plot_legacy_et_ablation.py)

