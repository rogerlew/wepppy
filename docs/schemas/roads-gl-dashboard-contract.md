# Roads detachment layer for GL Dashboard

Status: proposed, static evaluation only (2026-10-22). Not implemented or ratified
for implementation. Resolve D1–D4 before the independent contract checkpoint.

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

## Decision register

Recommendations below are proposals, not operator decisions.

| ID | Decision | Recommended first version | Alternative and consequence |
| --- | --- | --- | --- |
| D1 | What constitutes one colored feature when one prepared segment has multiple modeled profiles? | One prepared road line, colored by `10 * sum(soil_loss_kg) / sum(modeled_area_m2)` over its distinct completed profiles; details list every profile. | Restrict coloring to one-to-one joins; multi-profile lines get an explicit unavailable state. Profile-specific spatial colors require persisted subsegment geometry that is not established by the current outputs. |
| D2 | Include mixed profiles and replacement remainders? | Include mixed profiles, visibly labeled full-profile values. Exclude replacement remainders from the road layer and report their count separately. | Road-only layer is scientifically narrower but leaves valid mixed-profile Roads runs uncolored. Remainders would need a separate hillslope layer. |
| D3 | Where is the layer discoverable and initially visible? | Available in both baseline and Roads dashboard views for the current run when valid Roads artifacts exist; initially off in general dashboard, on from the Roads results link. | Roads-scope-only entry is simpler but harder to discover; automatic activation in every dashboard changes existing initial views. |
| D4 | Color scaling and cross-project comparability? | Sequential accessible palette, linear 0-to-project-maximum default with numeric legend and existing maximum override pattern. | Shared fixed breaks improve cross-project comparison but need agreed thresholds. Log scaling improves low-end contrast but needs explicit zero handling and a labeled transformation. No automatic percentile clipping. |

D1's recommendation is an area-weighted diagnostic across modeled profiles,
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
- Prepare summary: `wepp/roads/segments/roads.inslope.summary.json`, for source CRS
  and preparation provenance; confirm the recorded CRS field in implementation.

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
Display line width is a screen-space visibility aid, not modeled width or area.
No buffer polygons are inferred from a one-dimensional simulation footprint.

Current-result eligibility follows the upstream
[Roads preparation lifecycle](roads-preparation-lifecycle-contract.md).
Preparation replaces the segment set and invalidates previous Roads results
across all consumers. Only a fresh successful Roads run can publish new current
results. Join IDs are unique within that set; there is no stable-ID reconciliation,
cross-preparation matching, geometry-fingerprint subsystem or legacy admission path.
Display uploaded road names/IDs where available rather than implying generated
keys are durable road identities. Existing source-integrity checks remain.

## Display and interaction

Subject to D1–D4, render a pickable colored-line GeoJsonLayer above hillslope fills,
with a minimum visible stroke and adequate hit target for short segments. Preserve
pan/zoom and independent channel visibility. Use an independent Roads visibility
control; never share hillslope or channel radio groups. Selecting Roads alone
must not open a graph or introduce a year slider: this source is mean annual.

Hover shows segment label, detachment rate and profile scope. Click opens persistent
details: prepared/source identifier where available, rate, annual detachment mass,
modeled area, road length, design, scope, simulation years and profile count.
For multiple profiles show constituent IDs, masses, areas and rates. Do not sum
repeated road lengths or label modeled profile length as surveyed road length.
Provide an accessible tabular equivalent/keyboard selection, explicit units and
text status so color is not the only way to retrieve a result.

Mixed-profile details say **Includes modeled road/fill/buffer or land-use OFEs**;
use **Unclassified profile** when scope is unknown. Remainder counts explain their
exclusion. Finite negative detachment is shown as a signed value with a distinct
negative-result state; never silently clamp it to zero or include it in a positive
sequential range. All-zero and constant-valued datasets get a nondegenerate legend.
Unavailable and negative states have separate labeled legend entries.

The Roads layer belongs to the current run root, not automatically to an Omni
scenario. Until scenario-specific Roads lineage is supported, hide/deactivate it
when an Omni scenario or comparison is active, explaining that limitation inline;
never display parent-run Roads as if they were scenario differences. Preserve
normal base Roads visibility when returning. Child runs use their own artifacts,
with no parent fallback. Baseline hillslope results retain their existing meaning.

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
browse/query-engine access. Queries name the Roads summary explicitly; do not
substitute `loss_pw0.hill.parquet`. Honor browse sitePrefix and the separate
root-scoped query-engine URL contract. Prefer existing transport to a new API.
Only select necessary columns; do not load daily PASS/WAT into the browser.
Cache within the current run/result lifecycle, invalidate on preparation/scope/data changes and
ignore stale asynchronous responses. Keep geometry identity stable on color updates.
Any generated transformed geometry must remain visible and archivable under the
existing artifact standards. No new service, dependency or hidden CSV copy.

Before implementation: settle D1–D4, establish a work package/ExecPlan and obtain
the required independent contract checkpoint. Add an ADR for any newly selected
aggregation/threshold/default policy under the parameterization standard.
Validation must include one-to-one and multi-profile joins, mixed/unclassified
scope, remainder exclusion, partial/empty/historic-beta/stale states, projected CRS,
zero/negative/outlier values, unit conversion and scenario transitions. Verify
real producer-to-map identity after re-preparation, actual browser selection,
legend/keyboard details, route authorization, downloads and archive/restore.
UM1 proves only the one-to-one inslope case; it cannot validate mixed-profile
geography. No implementation, runtime mutation or deployment is authorized by
this static specification alone.
