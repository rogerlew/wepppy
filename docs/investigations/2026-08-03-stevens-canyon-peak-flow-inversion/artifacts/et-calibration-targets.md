# Post-Fire Annual ET Calibration Targets

## Purpose

These targets define a diagnostic calibration envelope for the paired Stevens
Canyon hillslopes. They are not production defaults. They constrain annual
soil evaporation (`Es`), plant-side evapotranspiration (`Ep`), and total
evapotranspiration together so a parameter set cannot appear successful merely
by moving water between components.

## Output Definitions

For this study, model total ET is:

    ETmodel = Ep + Es + Er

`Es` is soil evaporation. `Er` is evaporation from intercepted residue water.
Although the water-balance header calls `Ep` plant transpiration, the active
water-balance path also uses the `Ep` budget to evaporate live-canopy
interception. `Ep` must therefore be calibrated as **plant-side ET**, not as a
direct field measurement of transpiration alone.

The primary reference is the paired undisturbed hillslope under the identical
climate year. Ratios should first be calculated for each hillslope and year,
then summarized by severity using hillslope-area weights. This removes climate
differences and avoids treating simulation year 34 as a representative annual
water budget merely because it contains the focal event.

## First-Year-Equivalent Targets

The current fire management is repeated as a stationary condition through the
100-year climate realization. Each simulated year is therefore evaluated
against first-year-equivalent post-fire targets rather than interpreted as a
chronological recovery sequence.

| Severity | Burned total ET / undisturbed total ET | Burned `Es` / burned total ET | Central total-ET ratio | Central `Es/ET` |
| --- | ---: | ---: | ---: | ---: |
| Low | 0.65-0.80 | 0.15-0.30 | 0.70 | 0.22 |
| Moderate | 0.50-0.70 | 0.25-0.40 | 0.60 | 0.33 |

The total-ET envelope brackets the Sierra Nevada observation of a 31% first-
year reduction after low-severity fire and a 50% reduction after high-severity
fire. The moderate-severity envelope bridges those observations instead of
claiming a separately observed universal percentage. The soil-evaporation
fractions are anchored by a post-fire forest water-balance study in which soil
evaporation increased from 46 to 125-143 mm/year while total ET declined 33%.
That study's first post-fire `Es/ET` was approximately 0.36.

Sources:

- [Wildfire controls on evapotranspiration in California's Sierra Nevada](https://research.fs.usda.gov/treesearch/62600)
- [The effect of wildfire on the structure and water balance of a Hualo forest](https://doi.org/10.1016/j.foreco.2020.118219)

## Derived `Es`, `Ep`, and ET Targets

`Ep` is not assigned independently. It is derived so the three targets close:

    Ep_target = ET_target - Es_target - Er_target

Until residue evaporation is represented and validated, use `Er_target = 0`
for comparison with the present output. If `Er` becomes nonzero, reduce the
allowable `Ep` by the same amount rather than increasing total ET.

For an illustrative undisturbed annual ET of `474 mm`, close to the area-
weighted year-34 value over the treated contributing area, the targets become:

| Severity | Total ET range (mm) | `Es` range implied by joint envelope (mm) | Central `Es` (mm) | Central `Ep` if `Er=0` (mm) |
| --- | ---: | ---: | ---: | ---: |
| Low | 308-379 | 46-114 | 73 | 259 |
| Moderate | 237-332 | 59-133 | 94 | 190 |

The broad `Es` range reflects the joint ET and partition envelopes. Calibration
should minimize distance from the central targets while remaining inside every
envelope; it should not select incompatible extremes independently.

## Secondary Checks

The following checks are informative but are not primary optimization targets:

- After the undisturbed ET partition is independently judged credible, burned
  `Es` should generally be about 2-4 times the paired undisturbed `Es`, not the
  current area-weighted ratio near 24.
- Burned `Ep` should decline materially. A solution that obtains the ET target
  entirely by suppressing `Es` while retaining undisturbed plant-side ET is not
  acceptable.
- `Es` should be pulse-responsive and moisture-limited. Large values should
  concentrate after rain or melt rather than persist through dry periods.
- The calibration must preserve daily and annual water-balance closure and must
  not create compensating errors in runoff, deep percolation, lateral flow, or
  soil-water storage.

The ratio check is secondary because the current undisturbed year-34 `Es` is
only about `6 mm`. Multiplying that potentially biased denominator by three
would yield `18 mm`, far below the post-fire absolute soil evaporation observed
in the Hualo study. Both sides of the partition require validation.

## Acceptance Metrics

For each severity group, report the area-weighted median annual ratio and the
10th-90th percentile across 100 paired climate years. A candidate passes the ET
calibration gate only if:

1. median total-ET ratio is within the severity envelope;
2. median burned `Es/ET` is within its envelope;
3. derived `Ep + Es + Er` closes to reported total ET at output precision;
4. at least 80% of paired years remain within a wider tolerance of plus or
   minus 0.10 around the total-ET ratio envelope;
5. no material annual water-balance residual is introduced; and
6. focal-event runoff, antecedent storage, and downstream peak response are
   reported as consequences, not additional tuned targets.

These targets deliberately separate calibration from validation. At least one
parameter combination should be reserved from selection, and the preferred
candidate should be checked against external ET observations before any
production default changes.
