# Combined release streamflow validation results

The combined `wepp_261007` recut at 10 cm preserves warming-championship
totalwatsed streamflow to numerical precision, but its routed outlet hydrographs
are not negligibly different from `wepp_260803` at 10 cm under the predeclared
screen. Whole-record agreement is strong, yet individual event volumes, peaks
and shapes change materially. The October 1994 sampled-volume deficit remains
unresolved.

**Assessment status**: Complete (2026-10-07 22:14 UTC). All 2,596 executions,
native conversions, seven-file observer parity, 18,168 raw-output hash checks
and independent daily metric recalculations pass. These execution checks do
not imply that the routed-flow negligibility hypothesis passed.

## Comparisons and fit

The reference for every score is `wepp_260803` at 10 cm. Each case covers all
8,766 days in 1980–2003, with 864 hillslopes, 1,904 OFEs and 371 channels.
Outlet element 1235 is channel 371. No calibration, time shift, rescaling or
warm-up removal was applied. Each outlet series has 1,262,304 samples at
600-second intervals; no daily-average expansion was needed.

| Flow quantity | Comparison | NSE | KGE 2009 | R² | Volume bias |
| --- | --- | ---: | ---: | ---: | ---: |
| Daily totalwatsed | 261007, 10 cm | 1.000000 | 1.000000 | 1.000000 | +0.000000024% |
| Daily totalwatsed | 260803, 17 cm | 0.999992 | 0.999009 | 0.999993 | −0.011016% |
| Daily mean outlet discharge | 261007, 10 cm | 0.995419 | 0.970290 | 0.996189 | −0.598043% |
| Daily mean outlet discharge | 260803, 17 cm | 0.999992 | 0.999006 | 0.999993 | −0.010678% |
| 600-second outlet discharge | 261007, 10 cm | 0.979740 | 0.977108 | 0.979859 | −0.598043% |
| 600-second outlet discharge | 260803, 17 cm | 0.999967 | 0.998630 | 0.999969 | −0.010678% |

Full precision, KGE components, annual scores, quartiles and greatest departures
are retained in [metrics.json](artifacts/analysis/metrics.json). R² is squared
Pearson correlation, not NSE. The methods and selection rules are in
[methods.md](methods.md).

The provisional daily screen was ≤0.1% absolute volume bias and NSE, KGE and
R² each ≥0.999. Combined-release totalwatsed passes; combined-release daily
outlet discharge fails. Both daily measures for legacy 17 cm pass, although
some individual peaks still change appreciably. This is a study-specific
screen, not a universal adequacy criterion or a user-ratified physical tolerance.

## Daily water yield is preserved

Legacy 10 cm totalwatsed volume is 1,267,735,665.288646 m³; the combined release
gives 1,267,735,665.593408 m³, a difference of only +0.304762 m³ over 24 years.
The maximum absolute daily-mean departure is 0.000002513 m³/s. None of the
8,766 daily totalwatsed values changes by 1%.

Legacy 17 cm reduces totalwatsed by 139,648.525934 m³ (0.011016%). Its greatest
daily departure is 0.325569 m³/s; only two days differ by more than 1%.
This is small in whole-watershed yield terms, but it is a different intervention
from correcting the estimator and channel representation.

## Routed discharge differs despite similar daily patterns

The combined-release sampled outlet integral is 1,258,874,978.04 m³, versus
1,266,448,890.30 m³ for the baseline: −7,573,912.26 m³, or −0.598043%.
Daily mean outlet flow differs by more than 1% on 1,600 days (18.3%). Its
maximum absolute daily departure is 5.119653 m³/s. Annual volume bias ranges
from −2.440% in 1996 to +0.169% in 1993.

The effect is not a uniform scaling. For days in the baseline's lowest daily
flow quartile, combined-release volume is 1.017% higher; in the highest
quartile it is 1.442% lower. The daily standard-deviation ratio is 0.970960
and mean ratio is 0.994020. Those systematic differences help explain why
KGE is lower than the near-unity correlation might suggest.

Daily sampled peaks have NSE 0.968021, KGE 0.958461 and R² 0.970542. Their
mean increases 2.046%, even though the largest peak in the entire record
falls from 50.5 to 42.9 m³/s and moves to a different event. Thus a reduction
in the record maximum does not imply every peak is reduced.

## Manual assessment of the figures

All six rendered PNGs were inspected for curve behaviour, units, labels,
legends and clipping; their supporting paired data were read back after saving.

[Figure 1](artifacts/analysis/figure-1-daily-hydrographs.png) shows almost
indistinguishable seasonal timing and daily totalwatsed curves. The residual
panels reveal what the long time axis obscures: the combined release leaves
totalwatsed virtually unchanged but introduces intermittent substantial
negative daily outlet departures. Legacy 17 cm residuals are much smaller.

[Figure 2](artifacts/analysis/figure-2-fit-flow-duration.png) shows near-overlap
of the flow-duration curves. The combined-release daily outlet scatter has
visible points below the 1:1 line at moderate and high flows. The duration
curves alone conceal event order, peak timing and compensating departures.

[Figure 3](artifacts/analysis/figure-3-events.png) confirms that both 10 cm
totalwatsed curves overlap even in sensitivity-selected smaller events. The
17 cm differences are visible mainly in the magnified residual panels.

[Figure 4](artifacts/analysis/figure-4-events.png) shows much stronger changes
in routed event shape. The 1994 peak is lower and later, while several smaller
events acquire narrower, higher peaks or additional pulses. The two legacy
roughness curves mostly overlap in these selected windows.

| Smaller-event centre | Baseline sampled peak | Combined sampled peak | First printed maximum |
| --- | ---: | ---: | --- |
| 21 October 1990 | 1.42 m³/s | 3.07 m³/s | 05:20 in both cases |
| 25 October 1991 | 0.220 m³/s | 0.293 m³/s | 13:50 → 05:40 |
| 18 September 1998 | 2.45 m³/s | 4.95 m³/s | 05:10 → 05:30 |

These are deliberately sensitivity-selected examples, not typical-event
estimates. Their seven-day combined-release volumes are also larger than the
baseline. The 1991 curve has repeated pulses above a comparatively flat
legacy background. First-maximum times are subject to 600-second sampling
and ambiguity among equal rounded values; they are not exact physical lags.

[Figure 5](artifacts/analysis/figure-5-channel-ledger.png) shows a persistently
growing integral/ledger deficit in all cases, with larger downward steps in
the combined release. This is not merely redistribution between adjacent days
that disappears over the full record.

[Figure 6](artifacts/analysis/figure-6-retained-windows.png) shows that changes
are event-dependent. October 1994 loses a substantial part of the main pulse;
November 1992 and February 1996 have higher, more pronounced peaks and
changed recessions, with far smaller integrated-volume changes.

## Channel ledger agreement remains unresolved

| Case | Channel ledger volume | Sampled outlet integral | Integral minus ledger | Sample-printing bound |
| --- | ---: | ---: | ---: | ---: |
| 260803, 10 cm | 1,272.337716 million m³ | 1,266.448890 million m³ | −0.462835% | 2.879069 million m³ |
| 261007, 10 cm | 1,272.337752 million m³ | 1,258.874978 million m³ | −1.058113% | 2.880085 million m³ |
| 260803, 17 cm | 1,272.198069 million m³ | 1,266.313662 million m³ | −0.462539% | 2.879183 million m³ |

The combined-release full-record discrepancy is −13.462774 million m³,
well beyond the conservative three-significant-digit sample-printing bound.
The two 10 cm channel ledgers themselves differ by only +35.09 m³. Hence
ledger-volume agreement does not establish agreement in the published
discharge curve. The bound addresses decimal printing only, not every
quadrature, routing or storage term.

In the five-day window 25–29 October 1994, the combined-release integral is
2,080,721.40 m³ against a 2,539,873.36 m³ ledger, a deficit of 18.07775%.
The baseline deficit is 0.82986%. The combined-release sample-printing bound
is only 4,307.85 m³, compared with a 459,151.96 m³ discrepancy. Its peak drops
from 50.5 to 35.4 m³/s, with the first printed maximum moving from 04:40 to
06:00. Its integrated volume is 17.392% below the legacy baseline despite
nearly identical ledgers. This window does not support a conservation-closure
claim.

The earlier estimator-only candidate had a 1.321206% full-record discrepancy
and 18.297911% in this window, as retained in the immutable
[preceding comparison](../20261006_warming_rrinit_legacy/package.md).
The combined recut improves those particular discrepancies but does not
eliminate them. That historical comparison is context, not a fourth fresh
case in this validation.

## Disposition and limits

The daily hillslope-derived yield-preservation hypothesis is supported.
The broader assertion that the combined release is negligibly different in
routed streamflow is not supported by the predeclared screen or selected
event behaviour. Similar seasonal patterns, high R² and overlapping duration
curves are insufficient to make that claim.

Legacy output is not observational truth. Some differences may be intended
corrections, so failure of equivalence is not by itself proof that the new
model is physically less accurate. This paired comparison also does not
separate estimator effects from channel-repair effects. HV-02/HV-05 and the
October 1994 source/support/routing reconciliation remain scientific
follow-ups; no additional model fix or release modification is made here.

The study is limited to this watershed, forcing, geometry and period. No
production deployment, live-project mutation or universal validation claim
is included.

## Reproduction and retained evidence

The exact runner, assessment and independent verification scripts are in
[artifacts](artifacts/). Raw inputs, frozen binaries, all logs and raw outputs
remain on forest at `/workdir/warming-combined-release-20261007`.
Compact manifests and release sidecars are in [evidence](artifacts/evidence/);
paired daily data, event curves, conversion records, scores and six figures
are in [analysis](artifacts/analysis/). The binary hashes identify the corrected
recut, not the superseded same-name release.
