# GL dashboard flow-duration panel contract

Status: Accepted, 2026-10-10. Checkpoint c63f2cc52; implementation and forest
integration validated. Rain-on-snow classification remains explicitly unavailable.

## Requested behavior

The GL dashboard shall offer a Flow duration curve panel with radio choices for
hillslope streamflow from totalwatsed and channel outlet discharge. Users shall
be able to select a linear or logarithmic x-axis for exceedance probabilities.
The graph shall support Omni scenarios and use the same labels and colors as
other dashboard Omni graphs, including Undisturbed/Burned baseline naming.
Rationale: compare flow distributions between scenarios while retaining familiar
source, scenario and graph presentation conventions.

Daily sampling is required. Year selection shall offer All years included,
Exclude first year, Exclude first two years (default), and Exclude first five
years, matching the return-period report. Exclusions refer to zero-based sorted
year groups, not fixed day counts. Honor explicit selection across redraws.
There shall be no seasonal filters or CSV export. Hover shall expose discharge
and exceedance probability with scenario identity and units. Provide equivalent
value access for keyboard/touch users.

Rain-on-snow exclusion is omitted because a verified event classifier is not
available. The operator requested removal of the disabled checkbox and explanation
on 2026-10-10. Do not show a control that cannot perform the requested filtering.
A future filter requires a verified classification contract; no proxy or arbitrary
threshold is accepted by this delivery.

This composes the [controller contract](../controller-contract.md), the
[dashboard spec](../gl-dashboard.md), module contracts in
`wepppy/weppcloud/static/js/gl-dashboard/README.md`, and the
[output-scope contract](../../schemas/output-scope-contract.md).

## Daily sources

Daily sources are totalwatsed3 `Streamflow` and channel-ledger chanwb
`Outflow (m^3)` for the verified watershed outlet. Daily mean discharge is the
presentation; existing annual outlet summaries, channel water-balance
depth, event peaks and ranked return-period samples are not substitutes.

## Accepted calculation and interaction decisions

Use daily mean discharge in fixed m³/s. Each scenario uses its own available
eligible record and denominator N; display its period and sample count. Do not
intersect valid-flow dates across scenarios. Rationale: the operator explicitly
prioritized performance and independent records over a common-date comparison.
Warm-up applies independently to each original year inventory.

Rank eligible daily flows descending, m = 1..N, using Weibull
P = 100m/(N+1). Preserve tied daily values at consecutive ranks and retain zeros.
For flows [4, 2, 2, 0], probabilities are [20, 40, 60, 80] percent. Missing days
and null/NaN values are omitted and counted, never filled. Negative/infinite or
nonnumeric flows, malformed dates, invalid conversion area and duplicate daily
records invalidate the affected curve with an explanation. Keep other valid
curves visible. Report zero-flow fraction. Axis switching changes presentation
only; it does not change ranked values or N.

Default to hillslope streamflow and linear x; y remains linear. Include baseline
plus available Omni scenarios with existing legend/visibility behavior and stable
colors. Use baseline output scope for both baseline and child runs; Roads is out
of scope. Preserve selections through graph/layout changes and reuse existing
reload persistence where available, without a new storage mechanism. Map
scenario selection must not implicitly restrict multi-scenario comparisons.
Rationale: reuse familiar dashboard behavior and keep first delivery bounded.

## Verification and deferred classification

Outlet identity, source lineage and conversions are verified against the retained
source oracle; formulas/defaults are governed by ADR-0085. Define rain-on-snow classification,
shared-mask construction, and event-day versus recession-window exclusion.
The shared event mask does not require intersecting valid-flow records. Keep
classification stable across legend visibility changes. Verify query limits,
cache boundaries, rendering performance and hover/accessibility semantics.

Source-readiness policy preserves valid curves while explaining missing
scenario data, never silently reading the baseline as an absent child's result.
Readonly is not a completion predicate. Expected absent/empty data must be
separate from malformed/unauthorized states. Query authorization, containment,
input schemas, existing graphs, and model outputs remain unchanged.

## Required acceptance specification before checkpoint

Promote accepted decisions from the [requirements register](../../work-packages/20261010_gl_dashboard_flow_duration/notes/requirements.md)
into this document, including the exact population/ranking equations and a small
hand-calculated oracle. Specify source lineage, unit metadata, axis endpoints,
state/cache behavior, missing-source responses and bounds on any approximation.
Keep rejected alternatives and their rationale concise and explicit.

The implementation checkpoint must include operator decisions, an ADR where
required, two independent contract reviews and their disposition, and a committed
ancestor before production edits. The operator has authorized execution after the checkpoint commit.

## Execution boundary and valid states

Implementation and forest integration conform to this contract. Daily conversions
are governed by [ADR-0085](../../adrs/ADR-0085-gl-dashboard-flow-duration.md).
Expose additive readiness/outlet metadata in the existing authorized dashboard
bootstrap. For each scenario resolve expected daily file paths inside that exact
scenario root, reject escaping symlinks, and validate any existing catalog entry
points to that same file. An absent catalog can use existing Query Engine
activation; an existing stale/mismatched catalog is explicitly unavailable.
No new query endpoint or authorization behavior is introduced. Request all daily
rows (no result limit) and verify returned row_count; query only the verified
outlet channel. Cache raw data by scenario/source within the page, recompute
ranks for year selection, and do not refetch for x-scale or legend changes.
Do not cache failed requests; retry reloads the metadata and failed data.

Valid states: no Omni still shows baseline; completed writable and readonly
sources are readable; missing daily outputs or unresolved outlet metadata explain
unavailability without fabricated curves; present-empty or warm-up-exhausted
records show empty status; legacy runs missing chanwb can still show hillslope
curves; one invalid scenario leaves valid curves visible. Each scenario has its
own year inventory, N, missing count and probability coordinates. Malformed paths,
symlinks or mismatched catalogs are unavailable, never read as another scenario.
Normal authorization and Query Engine restrictions still apply. Archived outputs
must be restored through existing workflows before this reader can consume them.

Rain-on-snow classification cannot currently be established from a verified flag.
The control and unavailable explanation are omitted, per the operator's final
interaction decision. A future enabled filter requires a verified definition and
shared excluded-date policy.

Outlet resolution is read-only: use a registered outlet_top_id if available;
otherwise a sole registered channel, or the unique network.txt channel absent
from upstream-channel references. Ambiguous/missing topology means unavailable.
Translate that Topaz ID using chn_enum for Chan_ID and wepp for Elmt_ID; filter
both ledger columns. Do not call a structure accessor that may persist files.
For existing catalogs require catalog.root equals the exact resolved scenario
root as well as canonical entry ownership. Bootstrap provenance is a snapshot;
outputs/catalog must not be replaced during the page session. Reload after model
regeneration. This does not add a query-time filesystem race guarantee.

Quality accounting uses the source's original first/last calendar dates. Warm-up
indices address sorted source year groups before value filtering, matching the
return-period report; no fixed 365/730-day cutoff. Coverage counts calendar days
inside that horizon whose year is not excluded, including leap days and absent
dates. Report absent days plus null/NaN values as missing; retained N counts valid
daily values. Entirely absent source years cannot be reconstructed as simulation
inventory, but their dates count as missing within the horizon. Do not renumber
years after excluding missing values. Disclose coverage rather than filling gaps.
Invalid dates and duplicates invalidate the source before filters; invalid flow
or area invalidates the curve only on eligible non-warm-up dates. Query projections transport flow and area as VARCHAR so NaN and infinity retain
explicit tokens without invalid JSON. The loader treats null/NaN as missing and
flags infinity, negative/nonnumeric values or invalid area before conversion; do
not rely on JSON serialization of nonfinite floats. Synthetic years 1–99 retain their numeric year
(no JavaScript Date.UTC 1900 offset). Check daily dates against Gregorian month/day
and julian consistency. Metadata and hover include valid N, period and missing
count; all-zero and one-point curves are valid, N=0 has an explanatory empty state.

On a dashboard opened with output_scope=roads, FDC is unavailable with an
explanation; never silently display baseline curves under a Roads context.

Standalone Omni-child views preserve the same ownership rules. Shared topology
may resolve to the established parent project only for canonical
`_pups/omni/scenarios/<name>` lineage. A parent URL with a pup selector passes the
child scenario to Query Engine; a terminal `;;omni;;<name>` URL already names the
child endpoint. Labels use the exact child name. Batch-map dashboards do not
expose this run-specific panel.
