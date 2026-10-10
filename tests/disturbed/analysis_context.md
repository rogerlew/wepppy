# Disturbed Parameterization: Current Canonical Results

Reviewed: **2026-10-10**. Model: **wepp_261010**, hourly hillslope mode.
Parameterization: **adopted low-severity forest RRINIT of 6 cm**, including
young, deciduous and mixed forest through the shared burned templates.
See [ADR-0083](../../docs/adrs/ADR-0083-low-severity-forest-initial-random-roughness.md).

## What to Expect

These 96 canonical cases describe how the current parameterization behaves
under one common climate and slope. They are a reproducible model comparison,
not observations, watershed outlet predictions, or a promise that every burned
event exceeds its unburned counterpart. Here, an event comparison matches an
output date; it does not necessarily isolate a complete multi-day storm.

Across the 24 soil/vegetation combinations, the full-record severity sequence
unburned <= low <= moderate <= high is ordered for:

| Metric | Ordered combinations |
| --- | ---: |
| Cumulative hillslope surface runoff (EBE) | 23 of 24 |
| Delivered hillslope sediment (PASS) | 24 of 24 |
| Largest event peak (PASS) | 18 of 24 |

The runoff exception is sandy-loam tall grass, where moderate burn gives
slightly less runoff than low burn. Peak exceptions are the four clay-loam
forest types, clay-loam tall grass and sandy-loam tall grass. These are findings
to understand, not automatic failures or evidence that a real site is wrong.
Nor do ordered totals establish physically correct absolute magnitudes.

For example, the sandy-loam mature-forest sequence with the adopted defaults is:

| Measure | Unburned | Low burn | Moderate burn | High burn |
| --- | ---: | ---: | ---: | ---: |
| Mean annual surface runoff, mm | 92.7 | 119.8 | 121.3 | 376.4 |
| Mean annual delivered sediment, kg/ha | 0 | 7.51 | 27.76 | 4,027 |
| Largest peak, m3/s | 0.0201 | 0.1704 | 0.1734 | 0.3135 |

The low-burn roughness correction removes 17 low-over-moderate same-date
sediment inversions in this sandy-loam forest comparison. It fixes a
parameterization inconsistency; the associated sediment decrease is not
classified as a degradation. Roughness still has soil-state-dependent effects,
including an existing interrill-delivery cutoff. A reported zero does not
establish that natural sediment production is absent.

## Reading the Tables

- Runoff is hillslope surface runoff, not total streamflow or routed discharge.
- Sediment is delivered hillslope sediment, not gross detachment or channel
  erosion. Detailed EBE tables use rounded kg/m values; the summary above uses
  PASS concentration-derived mass normalized by area and 100 years.
- Burned/unburned event tables use matched dates. Read the one-sided-event
  counts and independent full-record totals as well; unmatched events matter.
- Sums of event peaks in the directionality diagnostic are not water volumes,
  record maximum peaks, or complete hydrographs.
- Weak ordering permits equal values at output precision. Shared forest burn
  templates are reused across vegetation labels, not independent calibrations.
- Zero-denominator ratios do not provide evidence of a quantified relative
  increase. Inspect the underlying absolute outputs when zero delivery occurs.

## Evidence and Scope

The 100-year synthetic McKenzie Bridge climate, four canonical soils and
87.9 m steep profile are common across these cases. All 96 cases were freshly
generated and run with the released 261010 hillslope binary in the development
container. Standard outputs match the validated candidate matrix byte-for-byte.
Prepared inputs and output hashes are retained; no cross-build PASS reuse or
parameter changes are included. Historical 261009 reports remain archived.

The hillslope binary SHA256 is
`d8ea3a07a29ef1e754c5362bd7931cc3a93486d75faa32df5c5f2e821c22d698`.
Forest source commit is `7471bb5e9`; adopted WEPPpy parameter files remain
unchanged from `bae734d71`. Current harness and source identities are pinned
in the report sidecar.
The repository sidecar `analysis_results_current.provenance.json` records
case selection and identities. The
[targeted assessment](../../docs/work-packages/20261009_rrinit_parameter_review/low-forest-4v6-results.md)
and [broader sensitivity study](../../docs/work-packages/20261009_rrinit_parameter_review/sensitivity-results.md)
retain the numerical evidence and limitations.

These results do not establish behavior on gentler slopes, other climates,
other soil states, independent watersheds or against field observations.
Use them to set expectations and investigate departures, not as universal
acceptance thresholds or a substitute for site-specific judgment.

This is the maintained current report. The
[older 80-case report](analysis_results.md) remains historical, with its
climate and geometry limitations explicitly recorded. Developers must follow
the [refresh procedure](PLAN.md#report-refresh-contract) when changing the
binary, relevant defaults or canonical fixtures.
