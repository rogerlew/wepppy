# H56: Simulation-Year-34 Water Fluxes

![H56 paired water fluxes](h56-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H56. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=6.08, latqcc=0.00, Dp=0.03, Ep=5.82, Es=3.16, Er=0.00.
- Day 203 undisturbed: Q=0.00, latqcc=0.01, Dp=0.00, Ep=9.48, Es=0.05, Er=0.00.
- Day 203 high severity: Q=53.60, latqcc=0.00, Dp=0.03, Ep=1.20, Es=2.61, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.24, Ep=15.92, Es=8.54, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=17.67, Es=0.21, Er=0.00.
- Days 196-202 high severity: Q=14.65, latqcc=0.00, Dp=0.24, Ep=3.62, Es=7.08, Er=0.00.
- Days 173-202 burned: Q=0.01, latqcc=0.02, Dp=1.04, Ep=50.82, Es=29.62, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=72.73, Es=1.00, Er=0.00.
- Days 173-202 high severity: Q=40.85, latqcc=0.34, Dp=1.04, Ep=17.68, Es=22.46, Er=0.00.
- Year 34 burned: Q=6.09, latqcc=32.63, Dp=12.68, Ep=304.00, Es=128.13, Er=0.00.
- Year 34 undisturbed: Q=0.00, latqcc=3.28, Dp=2.33, Ep=479.19, Es=4.07, Er=0.00.
- Year 34 high severity: Q=156.54, latqcc=39.28, Dp=12.53, Ep=118.80, Es=136.44, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=-6.08 mm, Ep=+3.66 mm, Es=-3.11 mm.
The largest year-34 differences are Ep=+175.19 mm, Es=-124.06 mm, latqcc=-29.35 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H56; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H56.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H56.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H56.wat.dat`
