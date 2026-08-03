# H55: Simulation-Year-34 Water Fluxes

![H55 paired water fluxes](h55-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H55. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=3.16, latqcc=0.03, Dp=0.02, Ep=4.31, Es=4.61, Er=0.00.
- Day 203 undisturbed: Q=10.57, latqcc=0.13, Dp=0.00, Ep=9.48, Es=0.05, Er=0.00.
- Day 203 high severity: Q=39.12, latqcc=0.01, Dp=0.02, Ep=1.26, Es=7.51, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.15, Ep=11.81, Es=10.16, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=17.13, Es=0.19, Er=0.00.
- Days 196-202 high severity: Q=0.17, latqcc=0.11, Dp=0.15, Ep=5.90, Es=13.73, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.11, Dp=0.65, Ep=44.29, Es=33.67, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=72.30, Es=0.95, Er=0.00.
- Days 173-202 high severity: Q=12.91, latqcc=0.78, Dp=0.65, Ep=24.18, Es=35.41, Er=0.00.
- Year 34 burned: Q=3.16, latqcc=23.58, Dp=7.94, Ep=294.54, Es=156.62, Er=0.00.
- Year 34 undisturbed: Q=10.57, latqcc=0.13, Dp=0.00, Ep=482.07, Es=4.01, Er=0.00.
- Year 34 high severity: Q=55.59, latqcc=38.53, Dp=7.94, Ep=172.43, Es=181.75, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=+7.41 mm, Ep=+5.17 mm, Es=-4.56 mm.
The largest year-34 differences are Ep=+187.53 mm, Es=-152.61 mm, latqcc=-23.45 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H55; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H55.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H55.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H55.wat.dat`
