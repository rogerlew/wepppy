# Probability and data-quality guidance

Research date: 2026-10-10. Ranking/data-quality recommendations were accepted by the operator. They are
local implementation policies, not claims that every agency mandates them. Daily
resolution and the filter/interaction scope in the requirements register are
operator decisions. Formula/default/conversion decisions need an ADR before code.

## Probability and ties

HEC-SSP prefers ranking all observations in descending order and offers both
Weibull `P = 100 m / (N + 1)` and `P = 100 m / N`. Here m starts at 1 for the
largest flow and N counts eligible daily observations. See the
[HEC duration-analysis manual](https://www.hec.usace.army.mil/confluence/sspdocs/sspum/2.2/duration-analysis/duration-analysis-general-settings-and-options).
Its probability-paper x-axis is not the logarithmic x-axis requested here.

Recommend Weibull without a formula selector. It supplies strictly positive
probabilities below 100%, usable unchanged on either requested x scale. These
are plotting positions, not exact observed fractions of days. An alternative
empirical survival curve uses `100 * count(Q >= q) / N`, assigning a tied value
the cumulative probability through the entire tie group. That convention also
works with log x; choose based on interpretation, not a claim that Weibull is
mathematically necessary. The older repository midpoint research plot is not a
binding dashboard convention.

Our proposed tie policy retains every daily observation at consecutive ranks;
equal discharges form horizontal segments. Do not deduplicate, jitter flows,
round before ranking, or average away the plateau. HEC's rank-all guidance
supports preserving the population; this specific tie/hover policy is our design
recommendation, not a separately documented agency mandate. Use straight
segments between ranked points, without smoothing or extrapolation. Hover snaps
to an actual ranked point and may additionally report its tied probability range.
No fitted distribution or interpolated discharge is implied by hover.

Hand-calculated oracle (arbitrary consistent discharge units):

| Rank m | Flow | Weibull P (%) |
| --- | --- | --- |
| 1 | 4 | 20 |
| 2 | 2 | 40 |
| 3 | 2 | 60 |
| 4 | 0 | 80 |

The zero-flow fraction is 25%, independently of these plotting positions.
N=1 yields a point at 50%; N=0 yields an empty state. An all-zero series remains
visible at zero on a linear y-axis. No invented observations at 0% or 100%; log
x uses a positive bound covering all plotted probabilities. Axis ticks may
include 100%, but the curve does not extrapolate to it.

## Zeros, missing days and invalid records

Proposed policies for these modeled, nonnegative daily discharge sources:

- Keep true zeros in N, including signed zero. Show zero-day count/fraction.
  A logarithmic x-axis needs no modification of zero discharge on linear y.
- Omit absent days and null/NaN flows from N, disclose missing counts and coverage,
  and never replace them with zero or interpolate a continuous hydrograph.
  Missingness can bias the distribution; report it visibly without claiming
  that omission eliminates that bias.
- Reject the affected scenario/source for negative or infinite flows, nonnumeric
  values, invalid dates, invalid required conversion area, or duplicate daily
  outlet records. Explain the problem while retaining other valid curves.
  Do not clamp or silently deduplicate. A future signed-flow source would need
  its own contract; negative values can be physical in other settings.
- Retain finite nonnegative extremes without an arbitrary outlier filter.
  Validate dates and conversion inputs before ranking; distinguish missing data
  from malformed schema and query failure.
- Count actual calendar days, including leap days. Track warm-up exclusions,
  rain-on-snow exclusions, missing days and retained days separately. Recompute
  N after all accepted filters. Do not drop incomplete years automatically or
  invent a universal allowed-missing-days threshold.

A [USGS regional streamflow dataset](https://www.usgs.gov/data/summary-streamflow-statistics-usgs-streamgages-southeastern-united-states-1950-2010)
reports zero-flow counts and applies study-specific record-completeness criteria.
That supports making zeros and coverage visible, not importing its eligibility
threshold as a universal FDC rule. The stricter malformed-record handling above
is a local engineering recommendation for generated model outputs.

Operator decision: use each scenario’s own available eligible record, for
performance. Show its period and N; do not intersect valid-flow dates across
scenarios. Apply warm-up against each original sorted year inventory. Missing
entire years must not silently renumber warm-up; verify the original simulation
year inventory when implementing. Different periods are disclosed, not corrected
by padding or truncation to a shared record.

## Rain-on-snow feasibility

A recent [rain-on-snow study, section 4.2](https://hess.copernicus.org/articles/29/4199/2025/hess-29-4199-2025.html)
reports that definitions and thresholds vary and affect event counts. No single
published threshold can be adopted as a universal WEPP classifier.

Existing totalwatsed3 fields include Precipitation, Rain+Melt, Snow-Water, QRain
and QSnow. Rain+Melt includes rainfall, irrigation and snowmelt; QRain/QSnow are
runoff partitions. They do not establish a verified rain-on-snow event flag.
Snowmelt alone is not rain-on-snow, and end-of-day snow can be zero after an event
melts the pack. Watershed-average rain and snow can also occur on different
hillslopes. Inspect native producer semantics before claiming classification.

Requested direction: optional checkbox. Accepted default: unchecked. Before
implementation, define liquid-rain and antecedent-snow inputs, spatial overlap,
thresholds, calendar mapping and how the shared mask is constructed. The operator
accepted excluding the same dates across scenarios. Whether the mask is a union
of classified events across a fixed catalog or another reference remains to be
verified; changing legend visibility must not silently change the mask. Each
scenario removes only masked dates present in its own eligible record. This
optional event mask is separate from a common valid-flow-date intersection.

Propose excluding identified event days from both numerator and denominator,
with removed-day counts and a clear filtered-population label. Do not zero the
flow, subtract QSnow, or claim that this removes all delayed snow-related channel
flow. Event-day removal versus a multi-day event/recession window is an open
scientific choice. If required inputs are absent, explain unavailability rather
than quietly applying a proxy or ignoring an enabled filter.

## Validation additions

Use the oracle above plus constant/all-zero/one-day populations, tied maxima and
minima, leap years, missing dates/nulls, duplicate dates, negative/infinite flows,
invalid conversion areas, short records exhausted by warm-up, and mismatched
scenario periods. Exercise every Year selection option, preserving explicit All
years. Verify identical values and N under both x scales and correct inverse-log
hover selection. Verify rain-on-snow counts and mask semantics once defined.
Validate visible values and accessible inspection; no CSV export is in scope.
