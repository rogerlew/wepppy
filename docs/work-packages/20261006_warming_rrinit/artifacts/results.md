# Warming-championship initial roughness experiment

**Completed 2026-10-06. Research comparison, not a deployment or calibration.**

Increasing initial random roughness from 10 cm to 17 or 60 cm has a small effect
on the modeled watershed outlet in this Cedar Creek run. Whole-period runoff
changes by less than 0.022%, and the maximum daily peak falls by less than 1%.
The effects are event-dependent, not uniform attenuation or a consistent delay.

These comparisons use the corrected surface-return build for all cases and all
24 years, 1980–2003. Only the 1,885 initial roughness records originally at 10 cm
change; the other 19 stay at their original values. This is not a comparison with
an unpatched executable or with the source run's previously saved outputs.

## Outlet peaks and volume

| Initial rrinit on targeted OFEs | Reported runoff volume over 24 years (m³) | Volume change | Maximum daily peak (m³/s) | Maximum peak change | Days with peak change over 1% |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10 cm | 1,272,337,712.21 | baseline | 43.06409 | baseline | 0 |
| 17 cm | 1,272,198,063.87 | −0.01098% | 42.77490 | −0.67153% | 2 |
| 60 cm | 1,272,069,776.86 | −0.02106% | 42.67082 | −0.91322% | 3 |

All three record maxima occur on April 27, 1990. The 1% count uses days with
baseline peak greater than 0.01 m³/s; all 8,766 days meet that threshold here.

At report precision, 8,109 daily peaks are unchanged for 17 cm and 8,038 for
60 cm. The 17 cm case has 244 lower and 413 higher daily peaks; the 60 cm case
has 277 lower and 451 higher peaks. These counts include very small changes.
The largest relative daily peak reductions are 1.600% and 2.505%, respectively;
the largest increases are 0.452% and 0.567%.

## Hydrograph shape and timing

The three largest separated baseline events show nearly overlapping hydrographs.
Difference panels reveal changes that are hard to see at the full discharge scale.
Higher roughness does not always produce a larger reduction: on March 7, 2003,
the daily peaks are 40.07583, 39.79060, and 39.91690 m³/s for 10, 17, and 60 cm.
On November 25, 1999, the 60 cm peak is slightly higher than baseline.
For March 7, 2003, reported daily volume falls from 2,194,050 m³ to 2,165,918 m³
at 17 cm and 2,145,738 m³ at 60 cm, approximately 1.28% and 2.20% reductions.
Thus the small whole-period total does not imply that every event-day volume is
equally insensitive; the ledger-versus-hydrograph caveat below also applies.

No large, consistent timing shift is resolved in those selected events. The
five-day discharge-centroid changes range from approximately −0.04 to +1.65
minutes, smaller than the conservative paired rounding bounds of about
2.46–2.94 minutes. Printed peak plateaus overlap between cases. The series uses
10-minute samples and three significant digits of discharge, so an exact
subtle peak-time shift should not be inferred from its first printed maximum.
Across days with a unique printed maximum in both compared cases, the median
peak-time shift is zero; that subset contains 1,190 days for 17 cm and 1,183
for 60 cm, not all days.

## Figures

- [Figure 1 — full-period peaks and cumulative reported runoff](analysis/figure-1.png)
- [Figure 2 — selected hydrographs and discharge differences](analysis/figure-2.png)
- [Figure 3 — peak distribution and annual volume changes](analysis/figure-3.png)

Figure 2 uses the three largest baseline peaks separated by more than seven days,
not the events with the largest treatment differences. Small steps in its
difference panels can reflect the three-significant-digit output precision.

## Interpretation and limits

There is a separate output-consistency caveat: integrating the printed 10-minute
hydrographs gives totals 1.3212%, 1.3138%, and 1.3037% below the reported volume
ledger for 10, 17, and 60 cm. This is larger than the roughness-induced change in
reported total volume and exceeds what three-significant-digit rounding alone
can explain. The code computes reported channel volume from inflow plus change
in storage (`wshchr.for`, chvol), separately from the sampled routed discharge
array (q1). The source of the measured discrepancy is not resolved here.
Accordingly, volume totals above come from the agreeing EBE/channel ledgers,
not hydrograph integration; ledger agreement is not proof that the plotted
hydrograph conserves that volume. No routing change was made to reconcile them.

For this corrected-build watershed, even the 60 cm intervention does not produce
a large outlet hydrograph change. It is nevertheless not numerically neutral:
individual peaks, event volumes, and parts of the hydrograph change, sometimes
in different directions. This experiment neither establishes 17 or 60 cm as
physically appropriate nor justifies changing roughness to repair a routing defect.

The conclusion is specific to this run and its existing channel parameterization.
It does not establish small hillslope-scale effects, transfer to the 6 cm shrub
Palisades case, or show that initial roughness is unimportant elsewhere. Dynamic
roughness, infiltration, and rill-width feedback remain active. No separate
warm-up interval was discarded.

## Validation and reproducibility

All 2,592 hillslope executions and the three experimental watershed executions
succeeded. Each outlet output contains all 8,766 days and 1,262,304 ten-minute
samples, with no missing event-report days. Daily reported volume agrees exactly
between the event report and channel water-balance report at printed precision.
The maximum absolute printed outlet water-balance residual is 0.31 m³ in each case.
The original-output-mode control also succeeded, with byte-identical results in
all seven canonical watershed files. The post-execution audit confirmed only the
intended 1,885 rrinit token changes per treatment, unchanged consumed inputs after
execution, and identical 98-file output sets for the 14 untouched hillslopes.
No stderr errors or warning lines were found. Source-input and binary hashes
remain unchanged. See the [validation review](validation-review.md).

[Methods](methods.md), [machine-readable summary](analysis/summary.json), and
[execution and input evidence](evidence/) accompany the figures. Raw logs, input
snapshots, hillslope pass files, and watershed outputs remain on forest at
`/workdir/warming-rrinit-20261006`. Two staging-only attempts are retained separately
and excluded; neither produced model results. The original run is not modified.
