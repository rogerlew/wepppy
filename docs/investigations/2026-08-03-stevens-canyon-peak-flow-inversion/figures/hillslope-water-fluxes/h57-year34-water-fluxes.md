# H57: Simulation-Year-34 Water Fluxes

![H57 paired water fluxes](h57-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H57. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=9.72, latqcc=0.08, Dp=0.00, Ep=7.95, Es=1.16, Er=0.00.
- Day 203 undisturbed: Q=9.72, latqcc=0.08, Dp=0.00, Ep=7.95, Es=1.16, Er=0.00.
- Day 203 high severity: Q=9.72, latqcc=0.08, Dp=0.00, Ep=7.95, Es=1.16, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=15.72, Es=1.67, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=15.72, Es=1.67, Er=0.00.
- Days 196-202 high severity: Q=0.00, latqcc=0.00, Dp=0.00, Ep=15.72, Es=1.67, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=56.55, Es=5.63, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=56.55, Es=5.63, Er=0.00.
- Days 173-202 high severity: Q=0.00, latqcc=0.00, Dp=0.00, Ep=56.55, Es=5.63, Er=0.00.
- Year 34 burned: Q=9.72, latqcc=0.08, Dp=0.00, Ep=472.54, Es=16.17, Er=0.00.
- Year 34 undisturbed: Q=9.72, latqcc=0.08, Dp=0.00, Ep=472.54, Es=16.17, Er=0.00.
- Year 34 high severity: Q=9.72, latqcc=0.08, Dp=0.00, Ep=472.54, Es=16.17, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=+0.00 mm, latqcc=+0.00 mm, Dp=+0.00 mm.
The largest year-34 differences are Q=+0.00 mm, latqcc=+0.00 mm, Dp=+0.00 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H57; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H57.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H57.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H57.wat.dat`
