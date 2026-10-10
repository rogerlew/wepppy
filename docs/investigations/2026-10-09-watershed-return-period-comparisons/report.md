# Rattlesnake and Topanga Return-Period Comparisons

Recorded 2026-10-09, before investigating the January 18, 1993 Topanga anomaly.

Subsequent inquiry: [January 1993 event-outlier investigation](../../work-packages/20261009_topanga_jan1993_outlier/package.md),
opened at Roger's request with no presumed defect. The comparisons and frozen
snapshots below remain the before-investigation record.
Owner: Roger Lew. Scope: preserve and compare existing results, not diagnose or
change model behavior. No simulations, project mutations, release or deployment
were performed for this record.

## Findings

- Rattlesnake's 2- and 5-year runoff and peak estimates are nearly unchanged
  between `wepp_260803` and `wepp_261009`. Burned values exceed undisturbed
  values in both versions. Larger reductions occur in rare undisturbed peaks,
  with essentially unchanged corresponding event volumes.
- Fresh Topanga simulations with synthetic climate have higher burned peaks
  at every reported interval. With GridMET 1980-2024, burned peaks remain
  higher at 2, 5, 10 and 20 years under the saved report settings.
- One GridMET undisturbed peak, 707.6391 m3/s on January 18, 1993, dominates
  the upper tail and reverses the 25-year comparison. This remains an open
  finding. The more frequent-event results are encouraging, but the entire
  peak response must not be described as resolved.

Roger judged the frequent-event comparisons encouraging and requested that
these results be documented before investigating that isolated anomaly.

## Projects and Provenance

Each parent below is the burned scenario; its corresponding undisturbed run
is under `_pups/omni/scenarios/undisturbed`.

| Watershed | Project | Executed build | Climate |
| --- | --- | --- | --- |
| Rattlesnake | [ascending-mourner](https://wc.bearhive.duckdns.org/weppcloud/runs/ascending-mourner/disturbed9002_wbt/) | wepp_260803 | 100 synthetic years |
| Rattlesnake | [anisotropic-sassafras](https://wc.bearhive.duckdns.org/weppcloud/runs/anisotropic-sassafras/disturbed9002_wbt/) | wepp_261009 | Same 100-year synthetic record |
| Topanga/Palisades | [phylogenetic-folly](https://wc.bearhive.duckdns.org/weppcloud/runs/phylogenetic-folly/disturbed9002_wbt/) | wepp_261009 | 100 synthetic years |
| Topanga/Palisades | [scrawny-relay](https://wc.bearhive.duckdns.org/weppcloud/runs/scrawny-relay/disturbed9002_wbt/) | wepp_261009 | GridMET 1980-2024, 45 years |

All eight watershed execution logs contain successful completion markers and
record the expected executable identity. Watershed binary SHA256 values:

- `wepp_260803`: `4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`
- `wepp_261009`: `e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc`

The comparison was read from local run files, not inferred from project labels.
Corresponding Rattlesnake managements, climate, geometry and effective soil
inputs match across builds. Differences in undisturbed soil files are timestamp
and source-path comments, not their non-comment contents. Burned and undisturbed
daily precipitation sequences match within each project. Vegetation/soil
parameterization intentionally differs between burned and undisturbed states.

## Definitions and Settings

Runoff is watershed-outlet daily event volume expressed as equivalent depth
using the report's normalization area: 673.745301 ha for Rattlesnake and
972.029631 ha for Topanga. It is not hillslope totalwatsed yield. Peak discharge
is the watershed EBE peak, not a sum of hillslope peaks or the canonical
matrix's matched-event peak-sum diagnostic.

These are WEPPcloud CTA order-statistic selections using its existing
`weibull_series` helper, not fitted annual-maximum flood curves. Each measure
and each scenario is independently ranked; equal return intervals need not
refer to the same storm. At the upper end of a short record, the selected rank
may represent a recurrence longer than the requested label. The 25-year
GridMET row selects the record maximum under these settings.

Two settings are retained separately in the machine-readable evidence:

1. Full record with Gringorten correction, matching the saved default reports.
2. First two simulation years excluded, no Gringorten correction, matching
   the prior Rattlesnake comparison: 98 synthetic years or 1982-2024 (43 years).

Do not mix these settings across scenarios or versions. Small displayed
differences between tables can be different selected ranks, not model changes.

Snapshot readback found two records labeled synthetic year 100, December 22,
in each of the six synthetic scenario series. The GridMET series have no
duplicate dates. All original rows are retained in the order-statistic analysis,
without silently deduplicating or changing the live reporting population.
The cause of the synthetic date-label duplication is not investigated here.
This caveat is separate from the 1993 GridMET peak finding.

## Rattlesnake Across Builds

The following retains the earlier comparison's settings: **98 years, first
two years excluded, CTA without Gringorten correction**.

| Measure | Interval | 260803 burned | 261009 burned | 260803 undisturbed | 261009 undisturbed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Runoff, mm | 2 | 5.4363 | 5.4363 | 3.7719 | 3.7719 |
| Runoff, mm | 5 | 7.0984 | 7.0984 | 4.7431 | 4.7431 |
| Runoff, mm | 10 | 8.3922 | 8.3901 | 5.2008 | 5.2008 |
| Runoff, mm | 20 | 18.7523 | 18.7524 | 15.2576 | 15.2576 |
| Runoff, mm | 25 | 24.1666 | 24.1666 | 19.2190 | 19.2190 |
| Runoff, mm | 50 | 37.9540 | 37.9540 | 31.2158 | 31.2158 |
| Peak, m3/s | 2 | 9.84958 | 9.84958 | 0.30898 | 0.30653 |
| Peak, m3/s | 5 | 15.38192 | 15.34344 | 0.39513 | 0.39428 |
| Peak, m3/s | 10 | 19.57450 | 19.57450 | 0.45179 | 0.43941 |
| Peak, m3/s | 20 | 27.84298 | 27.71073 | 3.67237 | 2.29556 |
| Peak, m3/s | 25 | 28.58797 | 28.58797 | 3.74594 | 2.92180 |
| Peak, m3/s | 50 | 44.54780 | 44.54780 | 5.63202 | 4.33284 |

At 2 and 5 years, burned runoff is approximately 44% and 50% above undisturbed;
with `261009`, burned peaks are approximately 32 and 39 times undisturbed.
Version changes in those peak estimates are 0%/-0.25% burned and
-0.79%/-0.22% undisturbed. This does not show a frequent-event inversion.

Undisturbed 20-, 25- and 50-year peak estimates decrease approximately 37.5%,
22.0% and 23.1%. On the same event, simulation year 84 December 5,
undisturbed peak decreases 5.63202 -> 2.92180 m3/s while runoff volume changes
102,797.39 -> 102,797.41 m3. This illustrates a peak change without meaningful
volume loss; it does not isolate which individual release patch caused it.

For the full-100-year Gringorten variant, burned 2-/5-year runoff is approximately
5.439/6.448 mm and undisturbed 3.833/4.934 mm. The same overall ordering and
small version differences hold. Full values and selected dates are archived.

## Topanga With Synthetic Climate

Settings: **100 years, CTA with Gringorten correction**, `wepp_261009`.

| Interval | Burned runoff, mm | Undisturbed runoff, mm | Burned peak, m3/s | Undisturbed peak, m3/s |
| --- | ---: | ---: | ---: | ---: |
| 2 | 28.01 | 24.98 | 48.31 | 14.75 |
| 5 | 55.02 | 51.05 | 92.68 | 38.95 |
| 10 | 69.73 | 68.73 | 118.14 | 57.06 |
| 20 | 87.54 | 88.03 | 168.86 | 79.03 |
| 25 | 91.62 | 90.57 | 170.58 | 111.49 |
| 50 | 106.11 | 108.54 | 208.36 | 129.23 |

Burned peaks are 3.28 times undisturbed at 2 years and 2.38 times at 5 years;
burned runoff is approximately 12% and 8% higher. Rare runoff-depth estimates
can be slightly higher in the undisturbed case while peak estimates stay lower.
The alternative 98-year/no-Gringorten comparison preserves this conclusion:
2-year peaks 48.71404/15.16712 and 5-year peaks 93.44060/39.76041 m3/s,
burned/undisturbed respectively.

## Topanga With GridMET

Settings: **1980-2024, 45 years, CTA with Gringorten correction**,
`wepp_261009`.

| Interval | Burned runoff, mm | Undisturbed runoff, mm | Burned peak, m3/s | Undisturbed peak, m3/s |
| --- | ---: | ---: | ---: | ---: |
| 2 | 70.70 | 65.84 | 168.93 | 118.85 |
| 5 | 88.10 | 85.14 | 218.14 | 170.68 |
| 10 | 127.64 | 117.46 | 243.79 | 211.64 |
| 20 | 136.93 | 135.05 | 259.95 | 249.91 |
| 25 | 148.12 | 139.86 | 293.56 | 707.64 |

At 2 and 5 years, burned runoff is 7.4% and 3.5% higher; burned peaks are
42.1% and 27.8% higher. Excluding the first two years and using the uncorrected
Weibull setting leaves these particular 2-/5-year values unchanged, but does
change some higher-interval selections. The 1993 maximum remains.

This fresh observed-climate comparison does not reproduce the historical
low-return-period inversion. It is not yet a controlled rerun of the historical
projects with only the executable changed. The
[earlier investigation](../2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md)
includes different working configurations. Its initial 43-year description
must not obscure that the working GridMET climate spans 1980-2024, 45 years.
The synthetic/GridMET contrast likewise is not a model-version experiment.

## Open Finding: January 18, 1993

No cause has been adjudicated, and no repair is proposed in this record.

| GridMET date | Precipitation, mm | Burned volume, m3 | Undisturbed volume, m3 | Burned peak, m3/s | Undisturbed peak, m3/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1993-01-16 | 47.2 | 432,728.50 | 443,488.47 | 21.26492 | 18.11747 |
| 1993-01-17 | 59.7 | 587,654.44 | 564,070.81 | 106.43185 | 71.88370 |
| 1993-01-18 | 15.7 | 213,282.16 | 218,608.19 | 76.03957 | 707.63910 |
| 1993-01-19 | 0.0 | 110,156.74 | 132,228.16 | 1.62068 | 3.54204 |
| 1993-01-20 | 0.0 | 81,801.86 | 93,600.05 | 1.26435 | 2.25298 |

On January 18, the undisturbed peak is approximately 9.3 times the burned
peak for only 2.5% more daily volume. The next-largest undisturbed record peak
is 249.90948 m3/s, versus 707.63910 for this date. The separate channel output
also reports approximately 708 m3/s (outlet Topaz 412/channel 128), at its
reported time of 1,200 s; the burned output reports 76 m3/s at 1,800 s.
The time-origin interpretation and upstream source of the spike are not
investigated here. Agreement between the two outputs rules out a
return-period-table-only artifact, not a model or upstream data defect.

This is not an initialization-year event. Neither removing early years nor
the encouraging 2-/5-year ordering explains it. Preserve it for a bounded
future diagnosis; do not generalize it into a routing rewrite or imply that
the surface-return correction is fully validated by the other comparisons.

## Evidence and Reproduction

`artifacts/snapshot/` contains byte-preserved watershed EBE Parquet files for
all eight scenarios, both GridMET channel-output Parquet files, available
cached return-period reports, and a provenance manifest with executable and
prepared-input hashes. Logs are represented by their execution headers,
success assertion at capture and whole-file hashes; full NoDb state is not
copied. The live run folders are provenance sources, not required replay gates.

`artifacts/results/return-periods.csv` records both settings, values, selected
ranks and dates. `january-1993-window.csv` preserves the daily context above.
Snapshot hashes, finite outputs, daily date-label checks, paired precipitation
and agreement with the available matching cached reports are verified by the
analysis command. This checks reporting, not physical validity.

Validation completed for eight scenarios and 184 return-period rows across
the two settings. All 82 available matching cached-report values agree with
the recomputed values. The first validation attempt assumed unique date labels;
the synthetic duplicates above were then identified and explicitly retained,
not repaired. No source outputs were changed.

Recompute from the repository snapshot without touching live projects:

```bash
.venv/bin/python docs/investigations/2026-10-09-watershed-return-period-comparisons/capture.py analyze --out /tmp/watershed-return-period-recheck
```

Use a new output directory; the script refuses to overwrite existing evidence.
The `capture` mode is for explicit future snapshots of the named live runs;
do not replace this pre-investigation snapshot after a rerun. No new model
execution or anomaly investigation is authorized by these reproduction steps.
