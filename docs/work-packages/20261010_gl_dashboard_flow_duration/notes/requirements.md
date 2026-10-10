# Requirements and decision register

Updated: 2026-10-10. Daily sampling and filter/interaction scope are confirmed.
Operator accepted the recommendations below, except date alignment: use each
scenario’s own available record for performance. Scientific source verification,
rain-on-snow classification, ADR and independent review remain outstanding.

## Confirmed

| ID | Requirement | Acceptance |
| --- | --- | --- |
| FDC-01 | Flow duration curve panel in GL dashboard | Discoverable graph with existing minimize/split/fullscreen behavior |
| FDC-02 | Source radio options: hillslope streamflow (totalwatsed), channel outlet discharge | One source selected; title, units and data agree |
| FDC-03 | Linear or logarithmic x-axis for exceedance probability | Same ranked data under either transform; probability ticks and tooltip |
| FDC-04 | Omni scenarios and existing label/color conventions | Undisturbed/Burned baseline; exact child names; stable palette identity |
| FDC-05 | Daily population | One daily flow observation per eligible day |
| FDC-06 | Year selection matching return periods; default exclude first two years | All years included; Exclude first year; Exclude first two years; Exclude first five years |
| FDC-07 | No seasonal filters or CSV export | Neither control is included |
| FDC-08 | Hover information | Discharge value and exceedance probability; include scenario and units |
| FDC-09 | Optional rain-on-snow exclusion checkbox | Requested direction; detection definition and available inputs must be resolved before wiring |


## Accepted decisions and remaining verification

| ID | Decision | Decision and rationale |
| --- | --- | --- |
| D-01 | Daily population (resolution accepted) | Daily mean flows including true zeros; verify source definitions below. |
| D-02 | Hillslope flow definition | Watershed-total `Streamflow` from totalwatsed3; retain its modeled baseflow contribution. Not surface runoff alone and not per-hillslope curves. |
| D-03 | Outlet definition | Daily `Outflow (m^3)` from chanwb for the watershed outlet. Prove ID mapping with the established watershed translator; do not sum channels or pick max ID by guess. |
| D-04 | Flow units | Use fixed m³/s for consistency with the dashboard’s fixed metric units. GL dashboard currently has no Unitizer integration; honoring project preferences or offering ft³/s would be additional scope. Source depths and volumes require different conversions. |
| D-05 | Date coverage | Use each scenario’s own available eligible record, with its date range and sample count shown. Operator chose this for performance; no cross-scenario date intersection or padding. |
| D-06 | Warm-up (accepted) | Default excludes first two years; reuse return-period Year selection options. No seasonal filters. See year semantics below. |
| D-07 | Exceedance formula and ties | Use Weibull `100 * m / (N + 1)`, descending consecutive daily ranks, retaining tied values. See [research](probability-and-data-quality.md) for alternatives and oracle. |
| D-08 | Initial controls | Default hillslope source and linear x-axis. Y-axis stays linear in first delivery, so zero flow is representable. A log-y option is a separate decision. |
| D-09 | Scenario visibility | Baseline plus available Omni scenarios; reuse existing graph legend/visibility behavior. Map scenario selection must not silently restrict graph comparisons. |
| D-10 | Output scope | Baseline output scope only for first delivery, for baseline and Omni runs. Roads is excluded pending separately verified daily sources. |
| D-11 | Export (resolved) | No CSV export, per operator. Provide hover and an accessible way to inspect values. |
| D-12 | Persistence | Preserve source/x-scale/scenario choices across graph layout changes; use existing dashboard reload persistence where available. Do not introduce a separate storage mechanism. |

## Year selection semantics

Match `templates/reports/wepp/return_periods.htm` and the zero-based sorted-year
exclusions in `wepp/reports/return_periods.py`. Exclude year groups, not a fixed
730 days. Preserve an explicit All years selection across redraws. The existing
report shows a conditional Custom option for an already supplied nonstandard
index list; it has no custom editor. Preserve that display if the panel accepts
such state; do not add a custom editor. Apply exclusions to each scenario’s original year inventory independently.
Do not select the first two surviving years after missing-value filtering.
A record exhausted by warm-up yields an explicit empty state, not relaxed filters.

## Rain-on-snow definition to resolve

Checkbox initially unchecked. Use a shared set of excluded dates across scenarios;
this optional mask does not require a common valid-flow record. Define precipitation
phase, antecedent snow, thresholds, spatial aggregation, mask membership and
event-day versus recession-window handling before wiring.
Do not silently use QSnow > 0 or Rain+Melt > Precipitation as a classifier. Removing
days makes a conditional distribution; it does not subtract snow-derived flow
or remove delayed routed effects. Missing classification inputs need an explicit
unavailable state. See [research and feasibility](probability-and-data-quality.md).

## Supporting requirements

**Data quality.** Include true zero flows in N. Separate missing, nonfinite and
negative values from zeros; disclose counts and define exclusion/failure rules.
Do not clamp negatives without an accepted scientific policy. Verify unique
scenario/day/outlet records; duplicate rows cannot silently inflate N. Calendar
and simulation-year records, leap days, partial years, one-day/all-zero/constant
series and independently empty records need explicit outcomes.

**Axis semantics.** Label x as Exceedance probability (%), increasing left to
right. Log x cannot contain 0%; choose the lower bound from the accepted finite
probabilities, with no fabricated epsilon observation. Changing scale must not
change N, ranking, zeros or flow values. Use inverse log mapping for
pointer/tooltip hit testing. Do not label probabilities as years or dates.

**Scenario identity.** Reuse `scenarioDisplayName` and named/palette colors with
stable full-catalog index, not filtered selection index. Resolve the current
baseline display label before choosing its named color. Burned is red and
Undisturbed green; toggling a scenario must not recolor others. Legends provide
text identification and visibility state; color alone is insufficient.

**Availability and errors.** Distinguish no Omni, no source data, valid empty
filtered data, missing one scenario/source, malformed schema, and failed query.
Keep valid curves visible with a named explanation for unavailable ones. Do not
invent zero curves or reuse base files for absent scenario outputs. Loading and
retry UI must not show stale curves as current. Readonly data remains readable.

**Interaction and performance.** Reuse the graph host and existing control
styles. Hide the year/month playback controls for an all-period distribution.
Rapid source/axis/selection changes must discard late responses. Cache keys
include run, scenario identity, source, scope, period/filter and units as needed;
presentation-only x-scale changes should not refetch identical source data.
Verify query row limits/pagination against actual N. Benchmark 45-year records,
long synthetic records and many scenarios. If rendering is reduced, rank the
full population first and retain extrema and scientifically important tails.

**Accessibility and hover.** Label radio groups and axes; keyboard-accessible
controls, readable legend/focus states, informative loading/no-data text, and
responsive/fullscreen layout. Provide keyboard/touch access to values and an accessible text equivalent
for the canvas; CSV is excluded. Tooltip should name scenario, source, exceedance and flow with
units; dates are optional provenance because the curve discards temporal order.
