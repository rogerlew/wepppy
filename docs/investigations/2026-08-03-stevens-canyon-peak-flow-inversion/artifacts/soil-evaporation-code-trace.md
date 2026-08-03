# Soil-Evaporation Code Trace

## Finding

The approximately 24-fold area-weighted increase in burned year-34 soil
evaporation is primarily produced by the active Penman-Monteith partitioning
dynamics acting on the fire-management leaf area index (LAI). It is not caused
by daily soil evaporation of 10-15 mm, and it is not primarily a soil hydraulic
parameter effect.

The required `pmetpara.txt` file sets `iflget=2` in `infile.for`, so
`watbal_hourly.for` calls `evappm`, not the older `evap` routine. The active
routine computes:

    kcbcon = kcbadj * (1 - exp(-0.45 * LAI))
    etke   = kcbadj * exp(-0.45 * LAI)

`kcbcon` controls potential plant transpiration and `etke` controls potential
soil evaporation. Before stress and surface constraints,
`kcbcon + etke = kcbadj`. Reducing LAI therefore transfers potential ET almost
one-for-one from transpiration to soil evaporation instead of necessarily
reducing total ET.

## H59 Example

The generated year-34 element output reports these approximate states:

| State | Burned | Undisturbed |
| --- | ---: | ---: |
| LAI | 1.466 | 11.875 |
| Canopy height (m) | 0.050 | 7.789 |
| Canopy cover | 0.600 | 0.900 |
| Interrill and rill cover | 0.603 | 0.999 |

Both crop names receive `kcb=0.95` and `rawp=0.8` from `pmetpara.txt`. Ignoring
the small daily climate adjustment to `kcbadj`, their LAI terms are:

| Coefficient | Burned | Undisturbed |
| --- | ---: | ---: |
| `exp(-0.45 * LAI)` | 0.517 | 0.00477 |
| `etke / kcbadj` | 0.517 | 0.00477 |
| `kcbcon / kcbadj` | 0.483 | 0.99523 |

The potential soil-evaporation share is therefore about 108 times larger in
the burned parameterization before water, residue, and exposed-area limits.
Those limits reduce the realized year-34 contrast to approximately 24-fold
when area-weighted over treated H49-H61 hillslopes.

## Secondary Controls

`evappm.for` limits realized soil evaporation through four additional paths:

1. `etkr` represents drying of the upper 0.1 m and is derived from field
   capacity, wilting point, current available water, and daily infiltration.
2. `eaj = exp(-0.5 * (cv + 0.1))` uses standing and flat residue mass, not
   canopy cover, to estimate exposed soil.
3. `kecon = min(etke * etkr, eaj * kcmax)` applies the water-reduction and
   exposed-area limits.
4. The final loop removes evaporation from available water in the upper 0.1 m
   and reduces reported evaporation if insufficient water remains.

Burned H59 also has substantially less dead and standing biomass than
undisturbed H59. This raises `eaj` and reinforces the LAI effect. Canopy cover
does not directly attenuate soil evaporation in these equations. It affects
other model processes, while `canhgt` enters only the `kcmax` climate
adjustment in this soil-evaporation block.

## Parameter-to-Dynamics Chain

The H59 management file changes maximum LAI from 14 to 4, maximum canopy
height from 20 m to about 0.28 m, maximum root depth from 2.0 m to 0.3 m, and
initial canopy/residue states. The simulated state settles near LAI 1.47 and
canopy height 0.05 m for the moderate-fire case versus LAI 11.88 and canopy
height 7.79 m undisturbed. The active dynamics then follow this chain:

    fire management parameters
      -> much lower LAI and residue mass
      -> lower transpiration coefficient and higher soil coefficient
      -> greater exposed-soil limit
      -> potential ET largely reassigned from Ep to Es
      -> only a small decline in total ET

This is a parameter-driven response mediated by an important structural model
assumption: the dual crop coefficients partition nearly the same `kcbadj`
between plant and soil as LAI changes. Whether that assumption is appropriate
for recently burned conifer forest is the central validation question.

## Code Risks Worth Separating

The source contains a suspicious assignment in the root-zone water loop:

    wftrp = wfevp + st(i,iplane) * 1000 * (...)

The expected accumulator form appears to be `wftrp = wftrp + ...`; using
`wfevp` can mix evaporative-layer water into the transpiration water-stress
calculation when the root-depth boundary falls within a layer. This could alter
`etks` and transpiration, but it does not explain the exponential LAI control
on `etke` or the first-order soil-evaporation contrast. It requires a separate
instrumented test before being classified as a defect.

## Next Diagnostic

Before mutating parameters, instrument `evappm` for a representative moderate,
low, and undisturbed hillslope and record `etorc`, `kcbadj`, `LAI`, `kcbcon`,
`etke`, `etkr`, `eaj`, `kcmax`, `kecon`, `wfevp`, `etks`, `Ep`, and `Es`.
Counterfactual calculations can then hold climate and soil water fixed while
swapping only LAI, residue, or soil parameters. This separates the structural
partition identity from water limitation and identifies which parameter family
is responsible for the realized flux.

## Source Locations

- `/workdir/wepp-forest_260430_baseline/src/infile.for`: selects
  Penman-Monteith when `pmetpara.txt` exists.
- `/workdir/wepp-forest_260430_baseline/src/watbal_hourly.for`: builds residue
  mass `cv` and calls `evappm` once per day.
- `/workdir/wepp-forest_260430_baseline/src/evappm.for`: computes the dual crop
  coefficients, soil-water limits, and final fluxes.
- Paired H59 management and output files under
  `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes`.
