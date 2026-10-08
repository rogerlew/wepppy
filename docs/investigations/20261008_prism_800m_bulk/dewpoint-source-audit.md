# WEPP dewpoint lower-bound source audit

Follow-up: the [paired WEPP/OpenET study](../../work-packages/20261008_dewpoint_openet/artifacts/results.md)
completed nine hillslopes and supports retaining the existing clipping policy
for the tested parameterization. It does not change this source-level finding
that the engine accepts dewpoint below Tmin.

Date: 2026-10-08. Scope: read-only source trace in `/workdir/wepp-forest` at
commit `375ccc296ed1ea491f599ff1b1a25b415d494a2a`. The checkout has unrelated
README/configuration/smoke-tool changes and release artifacts; none of the
inspected production source files is modified. No WEPP source, binary, or
production climate behavior was changed. This is source/formula evidence,
not a comparative watershed simulation.

## Correction and retained requirement

The operator reports that Anurag specified `dewpoint >= tmin` as necessary.
The initial PRISM investigation's recommendation to remove the lower clipping
was premature: atmospheric plausibility alone cannot establish model suitability.
Preserve unmodified source observations in the cache, and retain the established
lower bound in model preparation unless explicitly authorized to change it after
model-level evaluation. Document derived adjustments rather than overwriting
source data. The durable requirement is in
[client design: required validation](../../dev-notes/prism-800m-client-design.md#required-validation-before-publishing-a-cache-entry).

## Engine requirement versus preprocessing policy

All active references to `tdpt` (daily dewpoint), `xtdpt` (buffered climate
dewpoint), and `hrdewp` were traced through `src/`. No comparison requiring
`tdpt >= tmin`, lower clamp to `tmin`, or rejection triggered by `tdpt < tmin`
was found. Ordinary finite values below `tmin` are accepted by the inspected
code and alter calculations. This does not establish why Anurag selected the
preprocessing rule or prove that removing it preserves calibrated behavior.

| Source and lines | Observed behavior |
| --- | --- |
| `src/cclim.inc:34` | Defines `tdpt` as mean daily dewpoint in C. |
| `src/stmget.for:185-194,223-229` | Loads daily/breakpoint dewpoint directly; NaN observation only, no comparison with minimum temperature. |
| `src/watbal.for:524-529`, `src/watbal_hourly.for:628-632` | Dispatches between legacy evaporation and FAO Penman-Monteith paths. |
| `src/evappm.for:191-211,224-228,263-268,280-289` | Dewpoint determines actual vapor pressure, net longwave radiation, vapor-pressure deficit, and humidity adjustment of crop coefficients. No lower-bound assumption. |
| `src/evap.for:291-300`, `src/impeo.for:138-148` | Derives relative humidity from dewpoint and mean air temperature; caps RH above 1, with no lower clip to minimum temperature. |
| `src/melt.for:215-228,254-275` | Uses daily dewpoint in the wind-related snowmelt term and warm-rain heat contribution. |
| `src/melt.for:281-292`, `src/winter.for:421-460` | Allows negative hourly melt terms, then reconciles positive and negative melt at the daily boundary. |
| `src/stmtim.for:67-103,112-135` | Dewpoint-based rain/snow partitioning is commented out; active partition uses hourly air temperature and `rst`. |
| `src/hrtmp.for:60-68` | Hourly dewpoint reconstruction is commented out, explicitly described as incorrect. |

## What happens when dewpoint is below minimum temperature?

There is no branch discontinuity or error simply on crossing that boundary.
For ordinary climate temperatures, the FAO formula
`ed = 0.6108 * exp(17.27 * tdpt / (tdpt + 237.3))` remains positive and finite.
Lower dewpoint lowers actual vapor pressure and increases `ee - ed`, the vapor
pressure deficit driving the aerodynamic ET term. It also changes longwave
radiation and crop coefficients; total ET is not guaranteed to change
monotonically under every combination of inputs or water limitations.

Formula-level example, evaluated directly from the source equations with
`tmin=10 C`, `tmax=25 C`, and mean temperature `17.5 C`:

| Quantity | Raw dewpoint 0 C | Raised to tmin, 10 C |
| --- | --- | --- |
| Actual vapor pressure `ed` (kPa), FAO path | 0.610800 | 1.227963 |
| Vapor-pressure deficit `ee-ed` (kPa), FAO path | 1.587070 | 0.969908 |
| Relative humidity fraction, legacy mean-temperature formula | 0.305402 | 0.613985 |

These are formula evaluations, not simulated daily ET or runoff results. NaN
dewpoint or pathological temperatures near the formula singularity at -237.3 C
are separate numerical problems, not consequences of `tdpt < tmin` itself.

In the snowmelt code, `hrdtf = 1.8 * tdpt` enters the wind term as
`0.22 * hrtef + 0.78 * hrdtf`. With other inputs fixed and positive wind,
lowering dewpoint lowers this contribution and can make it negative. Negative
hourly melt is explicitly supported; daily reconciliation can reduce or zero
melt and change subsequent snow storage/runoff timing. Rain heat uses dewpoint
when it is positive and hourly air temperature otherwise, so crossing zero can
switch that branch. These are meaningful modeling consequences even without
an input error or floating-point failure.

## Existing application policy and remaining uncertainty

The lower clip is present in PRISM, GridMET single/multiple-location, and Daymet
single/daily-interpolation clients. PRISM introduced it in commit
`04640bd647ad3e0882736119d4b508d60c951ba7` (2023-11-27); that diff does not explain
the scientific or operational rationale. The evidence supports calling it an
established application preprocessing policy, not an engine-enforced invariant.

To reconsider it, recover Anurag's rationale and compare raw versus clipped
inputs through the deployed WEPP version, including water balance, ET, snowmelt,
and runoff. This audit does not supersede that instruction or authorize a
behavior change. No new numerical defaults or formulas were implemented.

## CLIGEN stochastic generation follow-up

Inspected `/workdir/jimf-cligen532` at clean commit
`8b9619b68c78f52d3bac778be19dc8436cac7d51`. Stochastic generation does not enforce
`dewpoint >= tmin`. In `cligen532/cligen.f:1416-1447`, dewpoint is generated
jointly with minimum and maximum temperature, without that lower bound. Lines
1466-1469 apply two sequential adjustments in internal Fahrenheit units:

    if (tdp .gt. .99*(tmxg+tmng)/2.) tdp=((tmxg+tmng)/2.)*0.99
    if(tdp.lt.-10.) tdp=1.1*tmng

The first is an upper adjustment relative to the daily mean; the second is a
cold-weather adjustment triggered below -10 F (about -23.3 C). Neither
guarantees dewpoint at or above minimum temperature, and the upper condition is
not rechecked after the cold adjustment. Celsius conversion occurs later at
lines 3111-3114. These checks also follow the observed-temperature branch.

Verified generated output with an unmodified fresh build in a temporary
directory, using `/usr/bin/gfortran -O0 -I <source-dir> <source-dir>/cligen.f
-o <temporary-binary>`. Station `or354811.par` (Leaburg 1 SW, Oregon), stochastic
type 5, years 2000-2009, seed 12345, interpolation 2:

    cligen -istation.par -ooutput.cli -t5 -y10 -b2000 -r12345 -I2 -F

The process completed normally. Parsed all 3,653 output records: 1,400 (38.3%)
had dewpoint below minimum temperature, 91 were equal, and 2,162 were above.
Maximum shortfall was 9.8 C. On 2000-01-01, minimum temperature was -1.3 C and
dewpoint was -1.6 C. Comparisons use the written CLI precision. This is a direct
counterexample to a universal stochastic-generation lower bound, not a
multi-station assessment or a WEPP simulation.

Retained [build/input/output provenance](evidence/cligen_stochastic_probe.json)
and [generated CLI](evidence/cligen_stochastic_probe.cli.gz). No files in the
CLIGEN repository were modified. This finding does not authorize changing
Anurag's application preprocessing instruction.
