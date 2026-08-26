# Topanga Peak-Flow Stratum Cluster Analysis

## Purpose

This artifact makes the burned-versus-unburned peak-response cluster analysis
repeatable. It quantifies the visual displacement in the split peak-flow
scatter and pairs corresponding event rows across strata. It does not assign a
duration, forcing-mode, or solver mechanism to individual clusters.

## Population and Rules

The source is the frozen Topanga `event-pairs.parquet` ledger under plan
`b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`.
The plotted-positive population requires the event on both sides, baseline
peak of at least `1e-7 m/s`, and positive mutant peak.

A response is congruent when a plus mutation lowers peak or a minus mutation
raises peak. Every other response, including an exact tie, is incongruent. The
central band includes ratios from 0.5 through 2.0. The 25% magnitude criterion
uses the census convention:

```text
abs(mutant peak - baseline peak) / max(abs(baseline peak), 1e-7 m/s) > 0.25
```

Cross-stratum matching uses hillslope, mutation family, mutation direction,
year, day, OFE, and solver-call ordinal. Both matched rows must lie in the
central band for the matched-cluster table.

## Results

Among incongruent Ksat rows in the central band, baseline peaks cluster at a
median of 73.89 mm/h in the unburned stratum and 39.17 mm/h in the burned
stratum. Their interquartile ranges are 49.58–102.92 and 25.94–50.88 mm/h,
respectively.

The independent 25% magnitude criterion gives the same displacement: 832
unburned rows have a median baseline peak of 37.06 mm/h, while 1,500 burned
rows have a median of 10.42 mm/h. These values supersede the earlier ad hoc
44 and 14 mm/h estimates, which used a symmetric log-ratio threshold rather
than the census absolute-fractional-change convention.

The cross-stratum match contains 43,944 central-band Ksat rows:

| Classification | Rows | Unburned median (mm/h) | Burned median (mm/h) | Median burned/unburned ratio |
|---|---:|---:|---:|---:|
| Neither incongruent | 32,578 | 5.37 | 23.00 | 1.08 |
| Both incongruent | 1,164 | 81.46 | 46.49 | 0.74 |
| Burned only incongruent | 7,204 | 8.82 | 38.14 | 4.11 |
| Unburned only incongruent | 2,998 | 71.90 | 43.79 | 0.67 |

Because the strata share climate files, the displacement cannot be attributed
to different storm forcing. The evidence supports the interpretation that
soil, vegetation, cover, and burn-severity parameterization shift the modeled
hydrologic state at which the unstable peak response is expressed. It does not
by itself identify which state variable or implementation boundary causes an
individual event response.

## Durable Outputs

- [`analyze_peakflow_stratum_clusters.py`](analyze_peakflow_stratum_clusters.py)
  performs the complete calculation.
- [`topanga-peakflow-stratum-cluster-bins.csv`](topanga-peakflow-stratum-cluster-bins.csv)
  records bin-level counts and shares by scenario and mutation family.
- [`topanga-peakflow-stratum-cluster-summary.csv`](topanga-peakflow-stratum-cluster-summary.csv)
  records cluster quantiles for the two primary definitions.
- [`topanga-peakflow-stratum-matched-clusters.csv`](topanga-peakflow-stratum-matched-clusters.csv)
  records the matched-event classification summary.
- [`topanga-peakflow-stratum-cluster-manifest.json`](topanga-peakflow-stratum-cluster-manifest.json)
  records the source hash, population filter, thresholds, matching keys, and
  output names.

Run from the repository root with:

```bash
.venv/bin/python \
  docs/work-packages/20260809_peakflow_topanga_census_execution/artifacts/\
analyze_peakflow_stratum_clusters.py
```

The script overwrites only its four named derived outputs. The frozen source
ledger is read-only.
