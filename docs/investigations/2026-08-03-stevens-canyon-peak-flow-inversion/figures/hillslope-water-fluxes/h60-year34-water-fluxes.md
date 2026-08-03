# H60: Simulation-Year-34 Water Fluxes

![H60 paired water fluxes](h60-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H60. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=0.08, latqcc=0.00, Dp=0.00, Ep=5.77, Es=3.16, Er=0.00.
- Day 203 undisturbed: Q=5.78, latqcc=0.57, Dp=0.00, Ep=5.88, Es=0.05, Er=0.00.
- Day 203 high severity: Q=44.48, latqcc=0.00, Dp=0.00, Ep=1.25, Es=7.18, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=13.92, Es=7.35, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=9.12, Es=0.29, Er=0.00.
- Days 196-202 high severity: Q=1.78, latqcc=0.00, Dp=0.00, Ep=4.68, Es=13.25, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=48.90, Es=28.24, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=30.47, Es=1.32, Er=0.00.
- Days 173-202 high severity: Q=19.53, latqcc=0.00, Dp=0.00, Ep=16.73, Es=32.86, Er=0.00.
- Year 34 burned: Q=0.08, latqcc=0.36, Dp=22.94, Ep=338.46, Es=130.79, Er=0.00.
- Year 34 undisturbed: Q=5.78, latqcc=0.57, Dp=0.00, Ep=453.48, Es=7.98, Er=0.00.
- Year 34 high severity: Q=86.08, latqcc=5.37, Dp=31.27, Ep=161.42, Es=172.85, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=+5.70 mm, Es=-3.11 mm, latqcc=+0.57 mm.
The largest year-34 differences are Es=-122.81 mm, Ep=+115.02 mm, Dp=-22.94 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H60; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H60.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H60.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H60.wat.dat`
