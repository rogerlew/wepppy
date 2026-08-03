# H61: Simulation-Year-34 Water Fluxes

![H61 paired water fluxes](h61-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H61. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=5.77, Es=3.16, Er=0.00.
- Day 203 undisturbed: Q=5.96, latqcc=0.39, Dp=0.00, Ep=5.88, Es=0.05, Er=0.00.
- Day 203 high severity: Q=41.70, latqcc=0.00, Dp=0.00, Ep=1.30, Es=7.51, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=13.92, Es=7.35, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=9.12, Es=0.29, Er=0.00.
- Days 196-202 high severity: Q=0.00, latqcc=0.00, Dp=0.00, Ep=4.79, Es=13.96, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=48.90, Es=28.24, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=30.50, Es=1.32, Er=0.00.
- Days 173-202 high severity: Q=14.06, latqcc=0.00, Dp=0.00, Ep=17.10, Es=35.22, Er=0.00.
- Year 34 burned: Q=0.00, latqcc=0.21, Dp=23.01, Ep=338.36, Es=130.94, Er=0.00.
- Year 34 undisturbed: Q=5.96, latqcc=0.39, Dp=0.00, Ep=453.44, Es=7.98, Er=0.00.
- Year 34 high severity: Q=74.16, latqcc=4.78, Dp=33.90, Ep=167.56, Es=176.99, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=+5.96 mm, Es=-3.11 mm, latqcc=+0.39 mm.
The largest year-34 differences are Es=-122.96 mm, Ep=+115.08 mm, Dp=-23.01 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H61; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H61.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H61.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H61.wat.dat`
