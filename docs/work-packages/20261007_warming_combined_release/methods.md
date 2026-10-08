# Streamflow comparison methods

The baseline is `wepp_260803` at 10 cm. Both the combined recut of
`wepp_261007` at 10 cm and the legacy 17 cm case are compared directly with
that baseline, with no calibration, rescaling, lag correction or warm-up
exclusion. These are model-to-model agreement measures, not performance
against observed streamflow.

## Inputs and execution

The native input snapshot is the same one used in the preceding
warming-championship study, retained at
`/workdir/warming-rrinit-20261006/snapshot` on forest. All 864 hillslopes,
1,904 OFEs, 371 channels and 24 calendar years (1980–2003) are retained.
The original hourly water-balance configuration is retained in every case;
this site is not a standalone test of the estimator's non-hourly 24-hour rule.
Each watershed consumes fresh hillslope passes from its own binary family.
The 17 cm case changes only 1,885 initial-condition roughness records at
0.10 m; two 0.06 m and seventeen 0.008 m records remain unchanged. The normal
management parser checks these values after writing and before execution.
Inputs must match the preceding study byte for byte, including channel
output mode 3 and a 600-second interval. A new-release mode-1 replay checks
that output detail does not change canonical physical outputs.

## Two flow quantities

Totalwatsed streamflow is the sum of hillslope surface runoff, lateral flow
and postprocessed groundwater baseflow. Native PASS/WAT conversion precedes
the standard totalwatsed3 calculation, with initial groundwater storage zero,
baseflow coefficient 0.04/day and deep-seepage coefficient zero. The area is
19,258,143.09 m². Convert depth in mm/day to mean m³/s by multiplying by
area/1000/86400. All 8,766 dates, component sums and units are checked.

Routed outlet discharge is channel 371, element 1235 in `chan.out`. The
600-second right-end samples are integrated using the existing discrete
sum convention, then divided by 86,400 seconds for daily mean discharge.
If the model publishes one daily-average record instead, its weight is
86,400 seconds; constant expansion for subdaily comparison is labelled and
counted, not interpreted as measured subdaily behaviour. Daily channel
ledger volume comes independently from `chanwb.out` and is cross-checked
against event-by-event output. Totalwatsed and the outlet ledger are not
interchangeable quantities.

## Fit measures

For reference values x and comparison values y, NSE is
`1 − sum((y−x)²)/sum((x−mean(x))²)`. Original KGE (2009) is
`1 − sqrt((r−1)² + (α−1)² + (β−1)²)`, where r is Pearson correlation,
α is the standard-deviation ratio and β the mean ratio. R² here is r²,
not NSE or an uncentred regression statistic. KGE components, RMSE, bias,
absolute-departure quantiles and worst daily departures accompany the fit
scores. Constant or zero-reference cases return explicit undefined metrics,
not fabricated perfect scores. These definitions follow
[Knoben, Freer and Woods (2019)](https://hess.copernicus.org/articles/23/4323/2019/hess-23-4323-2019.html).

Scores are calculated for daily totalwatsed, daily mean routed discharge,
daily sampled outlet peaks and the equally spaced 600-second outlet series.
Annual scores expose differences that full-period pooling can obscure.
Baseline-flow quartiles are assessed separately without changing their
membership between cases; the ten greatest absolute daily departures are
retained for each flow quantity.
The provisional daily negligibility screen is absolute volume bias ≤0.1%
and NSE, KGE and R² ≥0.999. It was declared before fresh model execution;
it is study-specific, not a universal threshold or user-ratified tolerance.
Subdaily comparisons are diagnostic, with no retrofitted acceptance limit.

## Figures and event selection

The full-record hydrograph and residuals, scatter plots and flow-duration
curves show both daily quantities. Each event figure includes the largest
baseline event plus three smaller events. Baseline local peaks have at least
seven days between them and prominence ≥0.1 m³/s; smaller means the lower
half of those peak magnitudes. Rank smaller candidates by the largest
absolute relative departure of either comparison within three days of the
peak; require selected centres to be more than ten days apart. Show a
seven-day window from three days before to four days after each centre.
These examples deliberately target sensitivity, not typical behaviour.

Event records include volume, sampled peak, first maximum time and local
fit scores. A time shift between flat printed maxima is ambiguous at the
600-second sample interval and three-significant-digit printing precision.
The daily difference and cumulative difference between sampled outlet volume
and the channel ledger are plotted separately. A conservative bound sums
half a unit in the last printed discharge digit times its duration. This
bounds sample rounding only; it does not prove numerical routing continuity,
resolve all channel storage terms or validate the unresolved HV-02/HV-05
scientific contracts.

Three further five-day routed-flow windows centred on 27 October 1994,
21 November 1992 and 6 February 1996 reproduce the diagnostic windows in the
preceding investigation. These are historically selected controls, not newly
selected examples of favourable agreement.
