# H51: Simulation-Year-34 Water Fluxes

![H51 paired water fluxes](h51-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H51. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: Q=10.00, latqcc=0.00, Dp=0.00, Ep=4.31, Es=4.61, Er=0.00.
- Day 203 undisturbed: Q=9.64, latqcc=0.52, Dp=0.00, Ep=5.41, Es=0.05, Er=0.00.
- Day 203 high severity: Q=49.80, latqcc=0.00, Dp=0.24, Ep=1.20, Es=4.52, Er=0.00.
- Days 196-202 burned: Q=0.00, latqcc=0.00, Dp=0.00, Ep=11.81, Es=10.31, Er=0.00.
- Days 196-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=15.62, Es=0.29, Er=0.00.
- Days 196-202 high severity: Q=11.92, latqcc=0.00, Dp=1.71, Ep=3.87, Es=8.44, Er=0.00.
- Days 173-202 burned: Q=0.00, latqcc=0.00, Dp=0.60, Ep=44.75, Es=33.35, Er=0.00.
- Days 173-202 undisturbed: Q=0.00, latqcc=0.00, Dp=0.00, Ep=46.93, Es=1.29, Er=0.00.
- Days 173-202 high severity: Q=36.73, latqcc=0.00, Dp=7.32, Ep=18.67, Es=24.51, Er=0.00.
- Year 34 burned: Q=10.00, latqcc=0.93, Dp=42.70, Ep=281.01, Es=156.49, Er=0.00.
- Year 34 undisturbed: Q=9.64, latqcc=0.52, Dp=0.00, Ep=474.57, Es=7.40, Er=0.00.
- Year 34 high severity: Q=115.34, latqcc=2.04, Dp=49.19, Ep=139.16, Es=160.43, Er=0.00.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are Es=-4.56 mm, Ep=+1.10 mm, latqcc=+0.52 mm.
The largest year-34 differences are Ep=+193.56 mm, Es=-149.09 mm, Dp=-42.70 mm. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H51; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/burned/wepp/output/H51.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/undisturbed/wepp/output/H51.wat.dat`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/high_severity/wepp/output/H51.wat.dat`
