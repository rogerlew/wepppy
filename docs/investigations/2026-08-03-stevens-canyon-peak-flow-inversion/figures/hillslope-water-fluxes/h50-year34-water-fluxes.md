# H50: Simulation-Year-34 Water Fluxes

![H50 paired water fluxes](h50-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H50. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=0.25, latqcc=0.00, Dp=0.00, Ep=5.76, Es=3.16, Er=0.00.
- Day 203 undisturbed: Q=6.10, latqcc=0.25, Dp=0.00, Ep=5.88, Es=0.05, Er=0.00.
- Day 203 high severity: Q=51.01, latqcc=0.00, Dp=0.00, Ep=1.20, Es=3.91, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=13.92, Es=7.35, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=9.12, Es=0.29, Er=0.00.
- Days 196-202 high severity: Q=12.53, latqcc=0.00, Dp=0.00, Ep=4.27, Es=8.14, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=48.90, Es=28.24, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=30.51, Es=1.32, Er=0.00.
- Days 173-202 high severity: Q=37.70, latqcc=0.00, Dp=0.00, Ep=16.08, Es=24.03, Er=0.00.
- Year 34 burned: Q=0.25, latqcc=0.12, Dp=23.07, Ep=338.14, Es=131.07, Er=0.00.
- Year 34 undisturbed: Q=6.10, latqcc=0.25, Dp=0.00, Ep=453.44, Es=7.98, Er=0.00.
- Year 34 high severity: Q=138.81, latqcc=2.87, Dp=29.60, Ep=142.05, Es=146.94, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=+5.85 mm, Es=-3.11 mm, latqcc=+0.25 mm.
The largest year-34 differences are Es=-123.09 mm, Ep=+115.30 mm, Dp=-23.07 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H50; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H50.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H50.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H50.wat.dat`
