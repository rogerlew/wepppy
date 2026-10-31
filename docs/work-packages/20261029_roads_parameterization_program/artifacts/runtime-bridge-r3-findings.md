# Revision-3 runtime bridge

The predeclared 16-input panel contains 11 distinct remaining legacy-soil misses
and five passing climate controls. Seven new sidecar combinations per input give
112 new executions; 16 retained all-present baselines complete 128 cells. All
use the exact revision-3 binary and unchanged soil/climate/management/geometry.
Bits below represent hourly mode, PMET and snow sidecar presence, respectively.

| Configuration | Residual within criteria /11 | Residual physical /11 | Passing controls within /5 | Controls physical /5 |
| --- | ---: | ---: | ---: | ---: |
| 000 | 8 | 11 | 5 | 5 |
| 001 | 8 | 11 | 5 | 5 |
| 010 | 10 | 11 | 5 | 5 |
| 011 | 10 | 11 | 5 | 5 |
| 100 | 1 | 9 | 4 | 4 |
| 101 | 1 | 9 | 5 | 5 |
| 110 | 0 | 11 | 5 | 5 |
| 111 (retained baseline) | 0 | 11 | 5 | 5 |

Fresh verification rehashed every recorded input/output, checked exact retained
input bytes and PMET activation, and recomputed completed native physical audits
and magnitude scores for all 128 cells. There are **107/112 new physical passes**
and **123/128 overall physical passes**, with five native failures retained.
`runtime-bridge-r3-effects.json` contains the full paired contrasts and failures.

## Interpretation

Hourly mode is the dominant residual distinction in this selected same-soil panel.
Daily mode with PMET recovers 10/11 residuals and retains all five passing controls.
Removing PMET in daily mode recovers only 8/11. Snow presence does not alter those
pass counts, which does not mean that all hydrological outputs are unchanged.
PMET absence selects original Penman; snow absence changes the default threshold.
Neither absence is a regional calibration or automatic production recommendation.

The remaining daily/PMET miss is Flagstaff loam, outunrut, gravel/high: 7.50031
kg/year versus a 0.560368 kg/year reference (allowed maximum 5.60368 kg/year).
Year 4 contributes 116.600 kg of the 119.962 kg summed annual records. This is a retained event-scale
mismatch, not evidence for a universal erosion multiplier.

## Failed alternatives

All five native stops occur with hourly mode and PMET absent. Four are Denver
clay outunrut gravel high/none with snow absent/present; one is a Denver sand
inbare passing control with snow absent. The guard reports negative demands
between approximately -9.70e-12 and -2.43e-12 at zero available water. This repeats
the previously observed negative-demand signature; it does not establish a new
causal diagnosis. Preserve the guard, failed outputs and rejected configurations.
No failed run is counted as zero sediment or a passing magnitude comparison.

## Conditional next validation

These results use legacy soil templates. Complete generated/legacy × hourly/daily
with PMET and snow retained on the same 116-case panel before selecting generated
hydraulic parameters. The exact-input inventory requires 196 unique new runs:
116 generated and 80 legacy. Reuse 232 hourly baseline cells and 22 labeled cells
from this runtime bridge; 14 other labels share newly executed legacy inputs.
All 464 labeled cells remain in the analysis; aliases are not independent material.
This isolates whether the runtime effect transfers to generated soils, rather
than adopting a global switch from this deliberately selected diagnostic panel.

No production defaults, magnitude thresholds, withheld outcomes or UI change.
The fixed-site PMET/snow bundle across climates remains a limitation, and broader
climate/geometry validation remains necessary before scientific acceptance.
