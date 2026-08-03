# H53: Simulation-Year-34 Water Fluxes

![H53 paired water fluxes](h53-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H53. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=0.34, latqcc=0.05, Dp=0.00, Ep=4.31, Es=4.61, Er=0.00.
- Day 203 undisturbed: Q=23.49, latqcc=0.51, Dp=0.00, Ep=5.44, Es=0.05, Er=0.00.
- Day 203 high severity: Q=44.38, latqcc=0.00, Dp=0.00, Ep=1.21, Es=7.22, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=11.40, Es=10.01, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=11.77, Es=0.29, Er=0.00.
- Days 196-202 high severity: Q=2.33, latqcc=0.00, Dp=0.00, Ep=5.06, Es=12.95, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=43.86, Es=33.53, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=37.24, Es=1.32, Er=0.00.
- Days 173-202 high severity: Q=20.03, latqcc=0.00, Dp=0.01, Ep=21.47, Es=32.58, Er=0.00.
- Year 34 burned: Q=0.34, latqcc=1.08, Dp=35.84, Ep=296.92, Es=161.38, Er=0.00.
- Year 34 undisturbed: Q=23.49, latqcc=0.51, Dp=0.00, Ep=454.63, Es=7.70, Er=0.00.
- Year 34 high severity: Q=78.90, latqcc=2.10, Dp=40.30, Ep=161.81, Es=179.89, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=+23.15 mm, Es=-4.56 mm, Ep=+1.13 mm.
The largest year-34 differences are Ep=+157.71 mm, Es=-153.68 mm, Dp=-35.84 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H53; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H53.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H53.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H53.wat.dat`
