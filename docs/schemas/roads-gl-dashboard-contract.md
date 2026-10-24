# Roads detachment layer for GL Dashboard

Status: operator decisions D1–D4 accepted (2026-10-23), including an explicit
dashboard output-scope switch. Independent contract reviews and dispositions
complete (2026-10-24 UTC); not implemented. The standalone implementation
checkpoint remains uncommitted. See the
[review disposition](../work-packages/20261023_roads_gl_dashboard/artifacts/review_disposition.md).

## Intent and settled meaning

Roger requested a spatial view of Roads erosion per area and selected detachment
rather than sediment export (task conversation, 2026-10-22). Show a segment layer
named **Roads soil detachment**, with legend **Mean annual detachment (t/ha/year)**.
For an individual profile, display `soil_loss_density_kg_m2 * 10`, equivalent to
`soil_loss_kg / modeled_area_m2 * 10`. Mass is already mean annual: do not divide
by simulation duration again. One kg/m² equals ten metric tonnes/hectare.

The [segment summary contract](roads-segment-loss-summary-contract.md) governs
source selection, annualization and full modeled OFE area. Use the full modeled
area for mixed profiles too; do not infer a road-prism denominator from line
length/width or perform geographic-overlap correction. Detachment is neither
sediment export nor incremental road impact. Retain signed native values.
Display aggregation and defaults are recorded in
[ADR-0105](../adrs/ADR-0105-roads-dashboard-detachment-display.md).

## Decision register

The operator accepted the recommendations below, with road-centerline-only
geometry and the existing sediment/erosion palette, and required an in-dashboard
Baseline/Roads scope switch. These are accepted requirements, not implementation
or independent-review evidence.

| ID | Decision | Accepted first version | Alternative and consequence |
| --- | --- | --- | --- |
| D1 | What constitutes one colored feature when one prepared segment has multiple modeled profiles? | One prepared road line, colored by `10 * sum(soil_loss_kg) / sum(modeled_area_m2)` over its distinct completed profiles; details list every profile. | Restrict coloring to one-to-one joins; multi-profile lines get an explicit unavailable state. Profile-specific spatial colors require persisted subsegment geometry that is not established by the current outputs. |
| D2 | Include mixed profiles and replacement remainders? | Include mixed profiles, visibly labeled full-profile values. Exclude replacement remainders from the road layer and report their count separately. | Road-only layer is scientifically narrower but leaves valid mixed-profile Roads runs uncolored. Remainders would need a separate hillslope layer. |
| D3 | Where is the layer discoverable and initially visible? | Available in both baseline and Roads dashboard views for the current run when valid Roads artifacts exist; initially off in general dashboard, on from the Roads results link. | Roads-scope-only entry is simpler but harder to discover; automatic activation in every dashboard changes existing initial views. |
| D4 | Color scaling and cross-project comparability? | Existing sediment/erosion palette (`jet2`), linear 0-to-project-maximum with numeric legend and existing maximum override pattern. | Shared fixed breaks improve cross-project comparison but need agreed thresholds. Log scaling improves low-end contrast but needs explicit zero handling and a labeled transformation. No automatic percentile clipping. |

D2 geometry decision (operator feedback, 2026-10-23): draw road centerlines only.
Do not display MOFE fill, buffer or land-use areas as mapped footprints, inferred
polygons or strips scaled by distance to a channel. Those areas are rectangular
model abstractions; drawing them geographically would imply unsupported spatial
precision. The subsequent instruction to proceed with the remaining recommendations
accepts coloring the road line with the labeled full-profile rate, including mixed
profiles, without drawing their off-road modeled areas.

D4 palette decision (operator feedback, 2026-10-23): reuse the dashboard's existing
sediment/erosion palette, `jet2`, through the shared color helpers. This preserves
visual consistency with soil loss and sediment layers; do not introduce a separate
Roads palette. Numeric legends, text status and the accessible tabular equivalent
remain required. The subsequent acceptance of the remaining recommendations
settles the linear project-specific range and existing maximum override pattern.

D1's aggregation is an area-weighted diagnostic across modeled profiles,
not a spatial integration over the drawn line. Never sum or take an unweighted
mean of densities. All contributing rows must share the same annual duration;
keep row IDs distinct and do not multiply mass/area by inclusion ratios again.

## Inputs, identity and provenance

- Geometry: `wepp/roads/segments/roads.inslope.monotonic.geojson`; use its generated
  `properties.segment_id`, not uploaded IDs or target hillslope IDs.
- Results: `wepp/roads/output/interchange/roads_segment_loss_summary.parquet`,
  policy `roads_segment_pass_v1`, with `segment_run_id` unique per modeled profile.
- Manifest: `wepp/roads/segments/roads.segment.pass.manifest.json`, for completed,
  skipped and failed states and attribution context.
- Prepare summary: `wepp/roads/segments/roads.inslope.summary.json`, using effective
  `input_crs` for prepared coordinates and preparation provenance. Original
  `source_crs` or `configured_input_crs` may differ after inference/fallback and
  must not override the effective field.

A prepared segment can join multiple result rows by `segment_id`. A replacement
remainder has a synthetic ID such as `h<topaz>::remainder`, not road geometry.
Do not coerce those rows onto a nearby road. Duplicate geometry IDs, duplicate
profile IDs, or unmapped completed non-remainder rows are explicit integrity
errors; no first-row-wins behavior. Geometry without completed results remains
visible as neutral **No results**, with reason when known. Distinguish zero.
If some profiles on a line fail/skip while others complete, mark the line partial
and leave it uncolored; details can show successful diagnostics without implying
complete results or overriding the existing whole-run failure policy.

Prepared coordinates remain in the preparation input CRS. Deck.gl requires
longitude/latitude: reuse established server/native transformation facilities
when needed; do not assume all GeoJSON is WGS84. Reject unresolved CRS explicitly.
Use longitude/latitude axis order for rendered coordinates and reject conflicting
prepared-geometry CRS declarations rather than guessing. Validate inferred and
fallback effective CRS as well as explicitly configured projected CRS.
Display line width is a screen-space visibility aid, not modeled width or area.
Do not infer fill, buffer or land-use polygons or channel-distance-scaled strips
from a one-dimensional simulation footprint. The Roads layer draws only the
prepared road centerlines; existing independent hillslope layers are unchanged.

Current-result eligibility follows the upstream
[Roads preparation lifecycle](roads-preparation-lifecycle-contract.md).
Preparation replaces the segment set and invalidates previous Roads results
across all consumers. Only a fresh successful Roads run can publish new current
results. Join IDs are unique within that set; there is no stable-ID reconciliation,
cross-preparation matching, geometry-fingerprint subsystem or legacy admission path.
Display uploaded road names/IDs where available rather than implying generated
keys are durable road identities. Existing source-integrity checks remain.

## Display and interaction

Render a pickable colored-line GeoJsonLayer above hillslope fills,
with a minimum visible stroke and adequate hit target for short segments. Preserve
pan/zoom and independent channel visibility. Use an independent Roads visibility
control; never share hillslope or channel radio groups. Selecting Roads alone
must not open a graph or introduce a year slider: this source is mean annual.

Hover shows segment label, detachment rate and profile scope. Click opens persistent
details: prepared/source identifier where available, rate, annual detachment mass,
modeled area, design, scope, simulation years and profile count. Show available
per-profile `segment_length_m` as **Modeled source road-segment length**, not
surveyed length; missing values remain unavailable. Uploaded source length may
appear separately as source-provided, never substituted for a prepared segment's
length. For multiple profiles show constituent IDs, lengths, masses, areas and
rates. Do not sum repeated road lengths or infer a single line length from them.
Provide an accessible tabular equivalent/keyboard selection, explicit units and
text status so color is not the only way to retrieve a result.

Mixed-profile details say **Includes modeled road/fill/buffer or land-use OFEs**;
use **Unclassified profile** when scope is unknown. Remainder counts explain their
exclusion. Finite negative detachment is shown as a signed value with a distinct
negative-result state; never silently clamp it to zero or include it in the
positive-value color range. All-zero and constant-valued datasets get a nondegenerate legend.
Unavailable and negative states have separate labeled legend entries.

The Roads layer belongs to the current run root, not automatically to an Omni
scenario. Until scenario-specific Roads lineage is supported, hide/deactivate it
when an Omni scenario or comparison is active, explaining that limitation inline;
never display parent-run Roads as if they were scenario differences. Preserve
normal base Roads visibility when returning. Child runs use their own artifacts,
with no parent fallback. Baseline hillslope results retain their existing meaning.

### Dashboard output-scope switch

Provide a visible, keyboard-accessible **Output scope** control with **Baseline**
and **Roads** choices, identifying the current choice. Users must be able to
switch in either direction without editing the URL or returning to the run page.
Use the existing `output_scope=baseline|roads` URL contract so reloads, bookmarks
and shared links retain scope. Baseline remains the default when omitted.

Changing scope selects the corresponding WEPP datasets and refreshes their
layers, legends and reports; never show cached baseline values as Roads results
or silently fall back. Preserve map position and compatible display choices.
The scope control is separate from the **Roads soil detachment** visibility
control: selecting Roads output does not itself redefine the road-line metric
or force its visibility. The accepted Roads-results-link initial visibility
still applies.

Enable Roads only when current Roads results satisfy the existing lifecycle
and resource requirements. Otherwise show the unavailable choice with an
actionable reason; do not imply that another successful run is needed when the
failure is authorization or a transient read error. Baseline remains reachable
from a Roads-scoped view whose results become unavailable. Scope eligibility
always satisfies the upstream mode-specific mandatory resource set. Continuous
mode requires the segment summary: missing it makes Roads scope unavailable,
not merely the overlay. Valid single-storm output can enable Roads scope while
mean-annual detachment is unavailable; a valid typed-empty continuous summary
can admit scope while reporting no completed profiles. These are the supported
differences between scope and detachment availability.

Roads scope uses the current run's own outputs. Entering it from an Omni
scenario/comparison view clears that incompatible selection explicitly; no
parent fallback or scenario-difference labeling is permitted. While Roads scope
is selected, disable incompatible map scenario/comparison controls with an inline
reason, and reject incompatible restored/hash selections before queries start.
Re-enable those controls on returning to Baseline. Apply the same
current-run boundary to child runs. Combined/batch views gain no new scope
semantics from this change.

Clear an active graph that is not supported in the destination scope and explain
why, rather than leaving a stale plot. Flow Duration remains baseline-only.
Preserve supported graph choices and their existing graph-specific scenario
rules; this feature does not redefine all graph scenario selectors. Neither a
scope change nor selecting the Roads line overlay invents a year-slider context.

If initial Roads-page admission fails, preserve the lifecycle HTTP status and
code while rendering an actionable unavailable view with a Baseline navigation
link. Do not serve a successful empty Roads dashboard. Authorization is checked
first; unauthorized users receive the existing denial, not project details.

Rationale: the existing scoped URL is supported but undiscoverable from the
dashboard. A familiar scope control exposes it while retaining separate layer
visibility and avoiding confusion between baseline and Roads model results.

## Availability and error states

| Artifact state | User behavior |
| --- | --- |
| Roads never used or no prepared geometry | No Roads result layer; ordinary dashboard works. |
| Prepared but no completed output, including single-storm without this summary | No detachment coloring; selected Roads context explains unavailable mean-annual results. |
| Valid empty summary | Explicit no completed profiles; no invented zero values. |
| Valid populated current summary | Enable layer; neutral geometry for unmatched noncompleted segments. |
| Historic beta outputs without established current eligibility | Offer Prepare and run Roads again; no compatibility admission path. |
| Re-prepared segments, failed run, or stale results | No current detachment coloring until a fresh successful Roads run; retained historical files do not enable the layer. |
| Malformed IDs, nonfinite metrics, nonpositive areas, inconsistent duration or CRS | Layer-specific actionable error; keep other dashboard layers usable. |
| Unauthorized read or transient fetch failure | Respect existing auth/error behavior; do not report absence or fall back to baseline. |

## Integration and acceptance boundary

Reuse existing GL data/detector/state/layer/legend modules and existing authorized
browse/query-engine access. The segment layer must consume a coherent server-side
materialization of geometry, prepare CRS, manifest and summary under one existing
Roads shared read/admission guard, held through validation and materialization.
Separate successful fetches are insufficient: another session can prepare and
rerun between them, reusing segment IDs. Client cancellation alone cannot detect
that mismatch. Do not introduce persistent generations, geometry fingerprints
or a new lock. A response completed before another session invalidates may remain
visible until a subsequent read, matching the upstream cross-session guarantee.

Use an additive opt-in detachment view on the existing authorized Roads map
resource (`resources/roads.json?view=detachment`); preserve ordinary prepared-geometry
consumers and their response shape when `view` is absent. An unsupported explicit
view returns 400 after authorization. Read only the required summary
columns and existing manifest/geometry metadata; never stream daily PASS/WAT to
the browser. Existing query-backed WEPP layers keep the root-scoped query-engine
URL and freshness contract; do not substitute receiving-hillslope loss for segment
detachment. Honor the site prefix and current-run authorization on the map view.

This bounded extension is required because independent existing reads fail the
concurrent-repreparation acceptance case. It adds one guarded materialization to
an existing route, not a service or background operation. Keep source diagnostics
visible through their established artifact paths and preserve existing map users.

Treat uploaded names, source IDs and diagnostic strings as untrusted text in
hover, persistent details and accessible tables. Use text nodes or equivalent
escaping, never raw HTML interpolation; source labels must not create links or
executable URLs. Links to project artifacts use existing authorized route builders
and validated project-relative paths, never a path/URL supplied by a label.

### Coherent detachment view payload

The opt-in response is a GeoJSON FeatureCollection with longitude/latitude line
coordinates. Existing source properties are preserved as data, never HTML.
A top-level `roads_detachment` object contains `state` (`available`,
`no_completed_profiles`, or `unavailable_mean_annual`), `units` (`t/ha/year`),
`remainder_profile_count` (nonnegative integer), and nullable text `reason`.
Single-storm absence uses `unavailable_mean_annual`; a valid empty continuous
summary uses `no_completed_profiles`. Neither state admits invalid lifecycle data.

Each feature adds `properties.roads_detachment` with `state` (`complete`,
`partial`, or `no_results`), nullable `reason`, `rate_t_ha_year`,
`annual_detachment_kg`, `modeled_area_m2`, integer `profile_count`, and `profiles`.
Aggregates are numeric only for complete lines; otherwise null, never fabricated
zero. `profiles` contains distinct completed summary rows using the existing
fields `segment_run_id`, `profile_scope`, `soil_loss_kg`, `modeled_area_m2`,
`soil_loss_density_kg_m2`, `simulation_years`, and nullable `design` where absent.
Include nullable `segment_length_m` from the existing summary; preserve it per
profile without summation or replacement by uploaded unsplit source length.
The count is the number of these constituent rows; no numeric conversion or
annualization is applied to their original fields. Partial lines can expose
those diagnostics but not an aggregate. Whole-run failed/currentness policy
still takes precedence over any per-line partial state. Replacement remainder
profiles contribute only to the top-level count, never to a line or its rate.

Reserve the added namespace: uploaded `roads_detachment` properties cannot
override computed result metadata. Retain required source identifiers/descriptions
from the existing prepared map resource; no absolute paths, tokens or raw stack
traces are added. Derive legend, hover, persistent details and accessible table
from this one response, not independent late profile queries keyed by reusable IDs.

### Error isolation and cache behavior

Keep optional Roads layer request/error state separate from baseline WEPP queries.
Distinguish auth denial, lifecycle 409, confirmed absence and transport/server
failure; do not turn every non-OK result into absent data. A failed Roads-layer
read clears/withholds only Roads coloring and result details and shows its reason;
baseline layers and scope-back navigation remain usable. Do not reuse a global
Roads-unavailable latch or automatic page reload that poisons unrelated queries
or creates a reload loop. A new scope/context resets its own request state.
Cache within the current run/result lifecycle, invalidate on preparation/scope/data changes and
ignore stale asynchronous responses. Keep geometry identity stable on color updates.
Any generated transformed geometry must remain visible and archivable under the
existing artifact standards. No new service, dependency or hidden CSV copy.

Before implementation: establish a work package/ExecPlan and obtain
the required independent contract checkpoint. Add an ADR for any newly selected
aggregation/threshold/default policy under the parameterization standard.
Validation must confirm that no MOFE fill, buffer or land-use footprint is drawn,
including geometry inferred from channel distance. It must include one-to-one
and multi-profile joins, mixed/unclassified
scope, remainder exclusion, partial/empty/historic-beta/stale states, projected CRS,
zero/negative/outlier values, unit conversion and scenario transitions. Verify
real producer-to-map identity after re-preparation, actual browser selection,
legend/keyboard details, route authorization, downloads and archive/restore.
Verify Baseline-to-Roads and Roads-to-Baseline switching, reload/bookmark scope,
unavailable/stale Roads states, independent road-layer visibility, compatible
view preservation and Omni scenario/comparison exit without stale results.
Interleave a real reprepare/rerun between attempted component reads and verify no
mixed-set response; test malicious labels as literal text, optional-layer 401/403,
409 and 5xx isolation, and an unavailable Roads entry retaining its status and
Baseline escape. These boundary checks must exercise actual readers and UI,
not mocked readiness or a fabricated coherent response alone.
UM1 proves only the one-to-one inslope case; it cannot validate mixed-profile
geography. No implementation, runtime mutation or deployment is authorized by
this static specification alone.
