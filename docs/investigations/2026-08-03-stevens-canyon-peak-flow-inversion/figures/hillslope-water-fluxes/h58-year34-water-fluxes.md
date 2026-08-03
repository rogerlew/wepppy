# H58: Simulation-Year-34 Water Fluxes

![H58 paired water fluxes](h58-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H58. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=4.71, latqcc=0.00, Dp=0.09, Ep=5.82, Es=3.16, Er=0.00.
- Day 203 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=9.48, Es=0.05, Er=0.00.
- Day 203 high severity: Q=45.85, latqcc=0.00, Dp=0.09, Ep=1.23, Es=6.49, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.62, Ep=15.92, Es=8.40, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=17.36, Es=0.21, Er=0.00.
- Days 196-202 high severity: Q=4.47, latqcc=0.00, Dp=0.62, Ep=4.38, Es=12.08, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=2.64, Ep=50.80, Es=29.51, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=72.14, Es=1.02, Er=0.00.
- Days 173-202 high severity: Q=23.80, latqcc=0.00, Dp=2.64, Ep=20.71, Es=30.90, Er=0.00.
- Year 34 burned: Q=4.71, latqcc=18.20, Dp=22.35, Ep=310.99, Es=129.62, Er=0.00.
- Year 34 undisturbed: Q=0.00, latqcc=0.06, Dp=5.03, Ep=482.59, Es=4.31, Er=0.00.
- Year 34 high severity: Q=91.89, latqcc=37.28, Dp=24.92, Ep=145.14, Es=161.96, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Q=-4.71 mm, Ep=+3.66 mm, Es=-3.11 mm.
The largest year-34 differences are Ep=+171.60 mm, Es=-125.31 mm, latqcc=-18.14 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H58; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H58.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H58.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H58.wat.dat`
