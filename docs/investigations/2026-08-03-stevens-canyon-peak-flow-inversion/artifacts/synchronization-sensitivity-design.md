# Hillslope Synchronization Sensitivity Design

## Objective

Test whether the large undisturbed peak on simulation year 34, Julian day 203
depends on unusually synchronized hillslope inflow to the channel network.
The first experiment should vary hillslope timing while holding each
hillslope's runoff volume and hydrograph magnitude/shape as nearly fixed as
possible. This separates synchronization sensitivity from runoff-generation
sensitivity.

This is a source review and experiment design, not an implemented WEPP change.
No production or local model outputs were mutated for this review.

## Source Provenance

The source reviewed is `/workdir/wepp-forest_260430_baseline` at clean commit
`2f65506d239b449bbb73c6820ff9cb949fa55158` (2026-07-28).

The authoritative path for hillslope surface inflow to a channel is:

1. `wshpas.f90` writes storm duration, computed hillslope time of
   concentration, runoff volume, and hillslope peak discharge to the pass
   record.
2. `wshred.for` reads those fields and assigns `watdur(i) = hildur(i)`.
3. `wshchr.f90` calls `chrqin` separately for left, right, and top hillslope
   contributors.
4. `chrqin.f90` constructs the discrete lateral-inflow hydrograph supplied to
   channel routing.

Relevant source locations are:

- [`wshpas.f90`](/workdir/wepp-forest_260430_baseline/src/wshpas.f90):
  hillslope pass fields and the `htcs` calculation;
- [`wshred.for`](/workdir/wepp-forest_260430_baseline/src/wshred.for): pass-field
  readback and `watdur` assignment;
- [`wshchr.f90`](/workdir/wepp-forest_260430_baseline/src/wshchr.f90): `chrqin`
  call sites;
- [`chrqin.f90`](/workdir/wepp-forest_260430_baseline/src/chrqin.f90): lateral
  hydrograph construction.

## Controlling Coefficient

For nonrectangular hillslope hydrographs, `chrqin` sets peak time as:

```text
td = watdur(hillslope)
tc = td / 2.67
```

Thus the active peak-time fraction is:

```text
f_peak = tc / td = 1 / 2.67 = 0.3745
```

The source contains the dormant alternative statement:

```fortran
! tc = htcs(ielmt)*3600.
tc = td / 2.67
```

Consequently, the computed hillslope time of concentration does **not** control
the timing of the lateral-inflow peak in this path. Because all 13 undisturbed
fixtures use the same climate, their day-203 `td` is the same 4,068 seconds and
their unperturbed nominal hillslope peak time is the same 1,524 seconds.

The dormant line must not simply be uncommented. In `chrqin`, `ielmt` is the
current channel element, while `iq` selects its left, right, or top hillslope.
The adjacent active statements correctly index `watdur` and `tmppkr` through
`nhleft(ielmt)`, `nhrght(ielmt)`, or `nhtop(ielmt)`. A valid `htcs` experiment
must use that same contributing-hillslope index, for example:

```fortran
ih = nhleft(ielmt)   ! or nhrght/nhtop according to iq
td = watdur(ih)
qp = tmppkr(ih)
tc = htcs(ih) * 3600.0
```

Using the literal commented expression risks reading the channel slot rather
than the hillslope whose hydrograph is being built.

The hydrograph rises and falls as a double exponential. Its shape parameter is
obtained from:

```text
a = volume / (peak discharge * td)
1 - exp(-u) = a * u
b = u / tc
d = u / (td - tc)
```

The cell-average branch rescales the sampled hydrograph to the supplied volume.
Varying `f_peak` therefore changes timing and asymmetry without intentionally
changing hillslope volume or supplied peak discharge.

If `volume >= peak discharge * td`, however, `chrqin` uses a rectangular
hydrograph and does not consult `tc`. A `2.67` perturbation cannot desynchronize
those contributors.

## Day-203 Branch Audit

The local undisturbed `H*.pass.dat` files show the following surface-runoff
events. The ratio `a` determines the `chrqin` branch.

| Hillslope | Duration (s) | Computed `htcs` (s) | Supplied peak (m3/s) | Runoff volume (m3) | `a` | Peak-time coefficient active? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| H50 | 4068 | 1887 | 0.92544 | 4884.0 | 1.2973 | No, rectangular |
| H51 | 4068 | 1506 | 3.32220 | 13515.0 | 1.0000 | No, boundary/rectangular |
| H52 | 4068 | 1481 | 19.18000 | 49542.0 | 0.6350 | Yes |
| H53 | 4068 | 1545 | 7.04330 | 19239.0 | 0.6715 | Yes |
| H54 | 4068 | 1542 | 1.66650 | 6779.4 | 1.0000 | No, boundary/rectangular |
| H55 | 4068 | 1916 | 1.70490 | 7760.7 | 1.1190 | No, rectangular |
| H57 | 4068 | 3499 | 1.93130 | 17204.0 | 2.1898 | No, rectangular |
| H59 | 4068 | 1489 | 7.51960 | 19555.0 | 0.6393 | Yes |
| H60 | 4068 | 892 | 0.03323 | 135.2 | 1.0000 | No, boundary/rectangular |
| H61 | 4068 | 1121 | 0.06862 | 279.2 | 1.0000 | No, boundary/rectangular |

H49 and H56 have subsurface-only events, and H58 has no runoff event. The
existing `2.67` coefficient can therefore alter day-203 timing directly for
only H52, H53, and H59. Those are substantial contributors, but this limitation
means a `2.67`-only experiment is not a complete synchronization test.

## Recommended Experimental Lanes

### Lane 1: volume-preserving timing dispersion

This is the primary synchronization test. Add an experimental, hillslope-fixed
time offset after `chrqin` constructs each contributor hydrograph and before it
is added to `qin` or `qlat`. Apply the same offset to the whole hydrograph,
including rectangular hydrographs, and preserve its time-integrated volume.

There is no existing WEPP input coefficient for this operation. It should be an
explicit ablation control, disabled by default, rather than disguised as a soil
or management parameter.

Use a deterministic random deviate per hillslope that remains fixed across all
events and replicates a persistent natural landscape difference. Center the
deviates by contributing area so the perturbation has no systematic watershed
timing shift. Because negative model time is unavailable, compare each
heterogeneous realization with a control having the same common positive
offset; only the between-hillslope dispersion should differ.

Suggested standard deviations are:

| Condition | Timing standard deviation | Day-203 fraction of duration | Purpose |
| --- | ---: | ---: | --- |
| Low | 300 s | 0.074 | Sub-timestep/near-resolution sensitivity |
| Medium | 600 s | 0.147 | One channel-routing output interval |
| High | 1200 s | 0.295 | Strong natural heterogeneity stress test |

Run at least 100 deterministic seeds per condition. Reuse the same seed set for
all evaluated events and scenarios. Record peak discharge, peak time, and
routed volume at WEPP_IDs 169, 172, 173, and 193. The principal response is the
distribution of peak-discharge change relative to the equal-delay control.

### Lane 2: active peak-shape coefficient

Perturb the active `f_peak = 1 / 2.67` coefficient by hillslope. Vary `f_peak`
rather than `2.67` itself so random variation is symmetric in peak time. Use
fixed, area-centered normal deviates and bound the result away from zero and
`td`:

```text
f_peak,i = clip(0.3745 + sigma_f * z_i, 0.05, 0.95)
tc_i = f_peak,i * td_i
```

Suggested `sigma_f` values are `0.075`, `0.15`, and `0.30`, corresponding on
day 203 to approximately 305, 610, and 1,220 seconds of one-standard-deviation
timing variation. This lane probes hydrograph asymmetry for H52, H53, and H59,
but it must not be interpreted as covering the rectangular contributors.

### Lane 3: physically linked time of concentration

Treat the dormant computed `htcs` field as a leading alternative model-form
hypothesis. Use the contributing hillslope's `htcs`, not the literal dormant
`htcs(ielmt)` indexing:

```text
tc_i = clip(htcs_i * 3600 * multiplier_i, epsilon, td_i - epsilon)
```

This must not be mixed into Lane 1 or described as restoration of known-correct
behavior. The source deliberately uses `td / 2.67`, and day-203 `htcs` ranges
from 892 to 3,499 seconds; unbounded substitution can approach or exceed the
storm duration and invalidate the falling-limb denominator.

For the three day-203 contributors on which `tc` is active, the evidence is
more constrained: H52, H53, and H59 have computed `htcs` values of 1,481,
1,545, and 1,489 seconds. These closely bracket the fixed 1,524-second value.
A direct `htcs` substitution is therefore unlikely by itself to materially
desynchronize those three hillslopes on this event. The wider 892-3,499-second
range belongs mostly to rectangular contributors, for which current `chrqin`
does not use `tc` at all. That branch interaction must be reported explicitly.

Use multipliers centered on 1.0 with low, medium, and high coefficients of
variation of 0.10, 0.25, and 0.50. This lane asks whether a physically derived,
landscape-varying travel time changes the result, while Lane 1 asks the cleaner
causal question about synchronization alone.

## Landscape Parameters Not Recommended for the First Test

`wshpas` computes hillslope time of concentration as proportional to:

```text
(hillslope length * Manning n)^0.75 /
(runoff intensity^0.25 * slope^0.375)
```

The Manning value is derived from hydraulic radius and surface friction.
Management and cover variables including random roughness, residue cover,
rill/interrill cover, basal cover, and canopy cover feed that friction through
`frcfac.for`. They are physically meaningful sources of natural variation.

They are poor first choices for this hypothesis test for two reasons:

1. their resulting `htcs` does not feed `chrqin` peak timing in the active
   path; and
2. they also change hillslope runoff production and peak discharge, confounding
   timing dispersion with magnitude and antecedent-state effects.

Slope and hillslope length do feed computed `htcs`, but mutating them would
alter the observed watershed geometry rather than represent uncertainty in
routing. Channel Manning coefficients should also remain fixed because the
question is sensitivity to hillslope synchronization, not channel-parameter
uncertainty.

## Decision

Use the post-`chrqin`, volume-preserving timing offset as the primary causal
test. Use `1 / 2.67` as the source-native secondary coefficient, with the clear
qualification that it affects only nonrectangular hydrographs. Use computed
`htcs` and its roughness controls only in a separately labeled model-form lane.

Do not begin by randomly perturbing soil conductivity, cover, roughness, slope,
or channel Manning values. Those changes cannot isolate synchronization and
would make a peak reduction impossible to attribute uniquely to timing.
