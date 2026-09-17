# Post-fire debris-flow likelihood report

Status: implemented; saved M1/M3 development browser acceptance passed (2026-09-16 UTC).
The owner requested execution and explicitly authorized the successor package,
contract checkpoint and implementation commits. Scientific and publication
contracts remain unchanged. The reviewed ancestor checkpoint precedes code.
Checkpoint: `ac4deb681`. Validation and independent review are retained in the
[implementation package](../../work-packages/20260915_postfire_debris_flow_report_implementation/package.md).
No production deployment or model rerun is implied.

## Purpose and authority

Help an end-user answer: “For this watershed and its modeled post-fire conditions,
what debris-flow likelihood is associated with the rainfall shown?” Use familiar
WEPPcloud reports, not a new dashboard framework. Report one existing watershed
and outlet, with one accepted M1 or M3 assessment at a time.

Scientific/data authority is the module [specification](../../../wepppy/nodb/mods/postfire_debris_flow/specification.md),
[rainfall/results contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md),
[production M1](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md),
[M3 scientific support](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md),
and [production runtime](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3_runtime.md).
The [run control contract](postfire-debris-flow-control-contract.md) continues to
own uploads, model/source preferences, execution and status. This report does not
add controls to that workflow or reinterpret its freshness rules.

## Familiar layout and first-release boundary

Reuse the full-width Pure `reports/_base_report.htm` shell, run header, Unitizer,
compact striped tables, fixed units rows, and subtle CSV actions described in
[report conventions](../report-ui-conventions.md) and the
[base-shell note](../../dev-notes/weppcloud-base-report-shell.md).
Follow Geneva's keyboard-operable linked chart/table selection and Storm Event
Analyzer's event selection and explicit loading/empty/error states. Do not copy
their domain-specific filters, tolerance settings, or hidden-unavailable behavior.

The first release is a single page in this order:

1. **Assessment summary**: accepted model, completion time, currentness, full
   watershed area, valid/excluded input coverage, and a short interpretation note.
2. **Rainfall scenarios**: one duration selector (15, 30, 60 minutes; initially 15),
   saved 1/2/5/10-year design points and their linked four-row table. Show the saved
   frequency source as text, not an editable selector. All durations remain reachable.
3. **Rainfall associated with 50% modeled likelihood**: three duration rows from
   the existing inverse table. Keep these together for comparison; no target slider.
4. **Storm events**: paginated saved events at the selected duration; one row per
   event, with selected-event detail covering all three durations.
5. **Methods and downloads**: expandable provenance and limitations; visible
   actions for full artifacts and per-table CSV.

Do not add metric tiles, nested tabs, duplicate duration selectors, map controls,
arbitrary rainfall inputs, model/source switching, or threshold tuning in v1.
The chart displays saved scenario markers, not a smoothed probability curve;
the table is the complete usable alternative. A future continuous curve must
evaluate the accepted equation at explicitly bounded rainfall values, never
interpolate a scientific curve from four saved points. That enhancement needs
its own reviewed amendment. Coverage maps, Storm Event Analyzer deep links,
archived-model comparison, and custom inverse targets are also deferred.

Rationale: answer the rainfall question without making the user configure a
second assessment. The existing outputs are sufficient for a useful report;
continuous exploration and maps introduce extra data/interaction contracts.

The chart's x-axis is peak rainfall intensity in displayed units; its y-axis is
modeled likelihood on a fixed 0–100% scale. Never zoom that likelihood axis to
exaggerate differences among saturated probabilities. Include the selected
rainfall window in the chart heading. Accessible marker labels identify window,
recurrence interval, intensity, window rainfall and likelihood without requiring hover.

## Interpretation and visible language

Keep this short statement beside the first results, not only under Methods:

> Likelihood is conditional on the rainfall shown and the modeled post-fire
> conditions. It is not the annual chance of a debris flow and does not predict
> where debris will travel. This is not an official warning or evacuation threshold.

Use one compact interpretation note plus concise assessment-specific stale,
coverage and applicability notices near the results. Do not repeat the entire
warning block under each table. Put longer explanations and technical provenance
under Methods without hiding material assessment-specific limitations.

Use “Rainfall recurrence interval (years)” with help explaining the source's
partial-duration-series average recurrence interval (PDS ARI). Never relabel it
“debris-flow return period” or convert it into annual debris-flow probability.
NOAA is a design-frequency source, not the source of the storm event catalog.
Show the accepted snapshot's actual climate mode; do not assume CLIGEN. Label
`frequency.represented_years` as “Years represented,” with accepted `year_min`
and `year_max` labels where available. Do not infer a continuous complete record
from that span or consult current Climate for old results. Name `wet_years`
separately if shown; missing historical metadata is “Not recorded.”

Label intensity “Peak rainfall intensity” and accumulation “Rainfall in the
selected window”; total event precipitation is a separate field. For example,
24 mm/h over 15 minutes means 6 mm in that window, not 24 mm of total storm rain.
Different durations are separate model estimates, not probabilities to sum,
average, or combine. M1 and M3 are separate accepted model choices, not ensemble
members or uncertainty bounds.

The 50% table describes an equation-derived equality, not a safe/unsafe boundary
or recommended warning trigger. Explain that thresholds depend on the accepted
predictors/model, not the selected rainfall-frequency source. Read
`target_probability`; the inverse row's null `probability` is intentional.

Preserve model applicability warnings, including the published study-area range
of 0.2–8 km² and unresolved preprocessing equivalence. An area warning does not
invalidate otherwise available results. Input coverage describes usable spatial
support, **not confidence**; 100% coverage does not mean certainty. Do not invent
coverage cutoffs, confidence bands, severity classes, or green “safe” labels.
No volume, runout, inundation, damage, or official USGS assessment claims.

All catalog storms use the same fixed post-fire predictor snapshot. A long
simulated climate record is not a simulation of landscape recovery over that
many years. Explain this beside the event heading. Display `simulation_labels`
as “Simulation year / month / day,” never observed/calendar dates. Calendar
labels retain their actual climate provenance; `invalid_or_missing` dates remain
unavailable labels without dropping otherwise usable storms.

## Data authority, currentness and compatibility

The accepted production attempt and its validated bundle own model, assessment
identity, predictors, hashes, source, dates, coverage and values. A changed model
preference must never relabel saved M1 results as M3. Read accepted status and
currentness through the existing production contract, not filesystem existence
or the currently selected form values. Expose accepted attempt ID and assessment
ID in Methods/download metadata; show model/time/currentness in the summary.

Use `open_results` and its validated `ResultCatalog`, `list_events`, and
`get_event`; retain fixed names, hash/schema/semantic validation and resource
bounds. Existing validation includes scalar consistency checks and bounded decoding
of the fixed saved v2 `valid_mask.tif`; preserve those checks. No original-source
raster reads, new model scenarios/predictor computation, source acquisition,
Climate/Soils rebuild, result publication, or RQ enqueue on report reads. Unit
changes are presentation-only. Do not follow source paths embedded in manifests.

Current `ResultCatalog` retains manifest/events only: `open_results` validates
but discards design/inverse tables. The future adapter therefore needs a minimal
additive validated saved-table projection, not unchecked reopening of parquet.
Ratify that reader addition in the rainfall/results contract before code. Retain
all three tables from one validated immutable snapshot with unchanged existing
query behavior, hash/schema checks and bounded resource use; test compatibility,
corruption and publication races. This is a planned reader change, not a claim
that the current query interface already provides these two views.

Compatibility is additive: no changes to NoDb keys, schema-1 parquet columns,
published files, accepted attempt promotion, or existing control behavior.
Supported v1 M1 bundles retain independent-support semantics; do not invent a
common-valid fraction/mask. v2 uses accepted common-valid counts and mask metadata.
When older provenance lacks a summary field, show “Not recorded,” not a guessed
value. Unsupported or inconsistent bundles are not silently upgraded.

Pin summary, table, detail and downloads to one accepted assessment identity.
If the accepted attempt changes between requests, discard the obsolete response
and ask the user to reload the report; never mix models or assessment versions.
Ignore out-of-order filter responses using one controller-owned request generation.

## Fields and interactions

Design identity is assessment + source + duration + recurrence interval; event
identity is the exact `event_id` (source hash plus row ordinal), not date. A chart
marker and its table row share selection; Enter/Space and native row controls
work without a pointer. Initialize with no scenario or event selected. Selecting
a scenario only highlights its marker/row; selecting an event exposes its three
duration rows inline immediately after that event row, not below the entire page.
Use an existing disclosure pattern with an event-labeled detail and explicit
expanded/controlled relationship. Keep keyboard focus on the activating control;
first and last page rows must expose discoverable details equally. No new modal
or side panel. These are independent selections with distinct labels.

Label the duration selector “Rainfall window” and explain that it changes rainfall
scenarios and storm events. Repeat the selected window as read-only text in both
section headings so it stays clear when the control is off-screen. It does not
filter the threshold table, labeled “All three rainfall windows.” Changing duration clears scenario selection,
resets event pagination, and preserves a selected event ID if it still matches
the filters. Otherwise clear its detail with a brief explanation. Unit changes
preserve all selections, ordering, filters and probability values.

Design columns: rainfall recurrence interval, peak intensity, window rainfall,
modeled likelihood, availability/reason. Threshold columns: duration, intensity,
window rainfall, availability/reason. Status/reason can share a cell with an
unavailable value; no full extra status column is needed for all-valid tables.

Event columns: date label, peak intensity, window rainfall, total event rainfall,
modeled likelihood. Selected detail adds all three duration rows and availability
reasons. Start in original event order, 100 rows per page. Offer a clearly labeled
minimum likelihood filter (blank means all) and year filter (original year label),
with Reset filters. Backend filtering remains on canonical probabilities 0–1;
the UI field is percent 0–100. Sort only by existing supported keys
`row_ordinal`, `rainfall_mm`, `probability`, with deterministic ordinal ties and
nulls last. Do not imply date/intensity/total-rainfall sorting is supported.
Respect existing limit 1–1000 and offset 0–200000 bounds; no unbounded browser load.

Always state “Showing X–Y of N matching storm events” with N for the selected
duration and filters, not parquet duration-row count. Unfiltered totals count
unique events, not three copies. Unavailable likelihoods remain visible with
their reason when no likelihood filter is applied. A numeric likelihood filter
excludes unavailable values; explain this beside the filter and retain the
unfiltered event total so the user can see the denominator changed.

All numeric values use existing Unitizer categories/precision contracts; charts,
tables and selected details update together. Likelihood display uses percent
with at most one decimal; positive values rounding to zero show `<0.1%`, values
below one rounding to 100% show `>99.9%`. True endpoints remain distinguishable.
Raw exports preserve exact canonical values. Null is “Unavailable” or an em dash
with a textual reason, never zero. Color is supplementary, not the only status
or selection cue. Use textual likelihood, no invented low/medium/high bands.

## Valid states and error behavior

| Runtime state | User outcome |
| --- | --- |
| Never run / optional state absent | Normal empty report: “No completed assessment”; link to existing run control, no automatic creation or execution. |
| Complete but no wet events | Summary, design/threshold results if available; “No storm events in this climate record.” |
| Current accepted results | All available sections for that exact accepted assessment. |
| Partial support / unavailable rows | Available values remain usable; counts, warnings and per-row reasons remain visible. No new coverage rejection. |
| New attempt running or failed, prior accepted bundle exists | Display prior accepted model/time with currentness and newer-attempt notice; never label it the newer result. |
| Stale accepted bundle | Persistent “Inputs have changed; these are previous results” notice; allow inspection/download with stale identity, no current-result claim. |
| Supported legacy v1 M1 | Read through existing validator, label missing/common-support information accurately; no forced migration. |
| Filter matches nothing | “No storms match these filters”; Reset filters, retain summary and other sections. |
| Missing/corrupt/unsupported accepted bundle | Explicit results-unavailable error and safe recovery guidance; no unchecked parquet fallback or numeric zero. |
| Assessment replaced during read | Stop mixed-version rendering and offer reload; retain no misleading current detail. |
| Malformed query / unauthorized run | Existing validated-input/access error behavior; no disclosure of other runs or arbitrary local paths. |
| Archive/restore | Same accepted identity and readable artifacts after normal restore; original failed/intermediate records remain browsable. |

Transport errors retain the last coherent view only when explicitly labeled
“Could not update results”; offer Retry. Loading replaces neither a valid value
with zero nor a stale response with a current label. Expected empty states are
not corruption. Unknown reason codes retain a safe generic explanation and a
support reference, not raw exceptions or host paths.

## Read boundary and exports

Proposed additive page: `/runs/<runid>/<config>/report/postfire_debris_flow/`.
Before implementation, bind its report/query/download adapters to existing
run authorization and approved query/error contracts in the checkpoint; a run
ID is not authorization. All reads are GET-only and side-effect free. Preserve
private/public run rules and existing error sanitization. Do not introduce a
generic SQL, file-path, remote-URL, or arbitrary attempt reader.

Use one safely serialized bootstrap payload and one controller initializer.
Query inputs are typed/allowlisted (duration, finite filter values, supported
sort, bounded page, validated event ID); render source strings as text, not HTML.
Use existing authorized artifact browsing/download routes with fixed validated
artifact mappings. Never include credentials or raw host paths in browser data.
Revalidate access on query and download, not just initial page rendering. Proposed
report HTML, query/detail and CSV responses use `Cache-Control: no-store`;
controller memory is limited to the coherent in-page snapshot, not persistent
browser storage. Verify existing authorized artifact-download cache behavior
against privacy/freshness requirements before reusing it; do not silently change
shared download behavior. Retain response-header and unauthorized-repeat tests.

Label the table action “Download displayed rows (CSV)” so pagination scope is
unambiguous. Use the existing report CSV convention and displayed units. Full
parquet links are explicitly “All saved events/design scenarios/thresholds
(canonical units).” Include accepted model/assessment, duration/filter/page and
units in an accompanying export context; never silently call a single page the
full filtered dataset. Explicitly neutralize spreadsheet formula interpretation
in exported text cells (including untrusted labels/reasons beginning with formula
prefixes); CSV quoting alone is insufficient. Preserve numeric scientific fields
as numbers and test hostile text fixtures. Existing `report_csv`/`to_csv` helpers
do not by themselves prove this protection. The manifest and supported validity mask are discoverable alongside
normal module files; do not create hidden copies or alter archive inclusion.

## Exact read interface — 2026-09-15

The authorized implementation uses a new `postfire_report` Flask blueprint,
registered with the existing run-context preprocessing. It composes the local
validated reader, not the query-engine service. Every endpoint uses existing
run authorization, including public/read-only access, and no-store headers on
success and error. Feature enablement is not authority to read a private run.
Disabled mods do not prevent authorized inspection of retained assessments.

Paths below are relative to `/runs/<runid>/<config>`; application URL helpers
retain the deployment prefix. All endpoints are GET-only:

| Path | Inputs | Result |
| --- | --- | --- |
| `/report/postfire_debris_flow/` | No query arguments | Pure report shell with one JSON seed and links. |
| `/query/postfire_debris_flow/` | Required `attempt_id`; optional event-query fields below | JSON view for that accepted attempt. |
| `/query/postfire_debris_flow/event` | Required `attempt_id`, `event_id` | JSON `{attempt_id, rows}` with all saved durations. |
| `/report/postfire_debris_flow/files/<name>` | Required `attempt_id` | Verified fixed saved artifact attachment. |

The page seed and query share `{schema_version: 1, status, attempt_id, summary,
design, inverse, events, query, urls}`. `status` is `absent` or `available`;
absent has null attempt/summary, empty scenario rows and an empty event page.
An available summary contains only `model`, `completed_at`, `assessment_id`,
`current`, `newer_attempt` (id/model/phase), `climate_mode`, `date_semantics`,
`frequency_source`, `frequency` (represented_years/year_min/year_max/wet_years),
`area_km2`, `coverage`, `warnings`, and `predictors` (name/value/unit/reason).
Missing optional provenance is null, never inferred. Coverage and warnings are
safe projections of accepted metadata; do not serialize arbitrary nested paths.
`design` is an array of all saved schema-1 design rows (normally 12), not
duration-filtered; the browser shows the selected four. `inverse` is an array
of all saved duration rows restricted to target 0.5 (normally three).
`newer_attempt` is null or `{id, model, phase}` only when the latest attempt
differs from the accepted attempt. `predictors` is an array of
`{name, value, unit, reason}` records with string name/unit, nullable numeric
value and nullable safe reason code. `warnings` is an array of safe warning
codes. Unknown codes become `unrecorded_warning`, not raw source strings.
`coverage` is null for v1 or `{total_cells, valid_cells, excluded_cells,
valid_fraction}` for v2, with integer counts and fraction 0–1. Legacy independent
support is identified in Methods without inventing common coverage. `frequency`
has exactly the four nullable numeric keys above. `events` is
`{rows, total, unfiltered_total}` with schema-1 event
rows and unique-event counts. Query context is not copied from local
`list_events` because it contains upstream provenance paths.

Event-query fields: `duration_minutes` integer 15/30/60, default 15;
`min_probability` optional finite fraction 0–1; `year` optional finite integral
original label; `sort` row_ordinal/rainfall_mm/probability, default row_ordinal;
`descending` exactly true/false, default false; `limit` integer 1–1000, default
100; `offset` integer 0–200000, default 0. Empty optional filters mean absent.
Reject unknown or repeated keys and malformed values with 400 `invalid_input`.
The query object echoes these normalized values. Attempt IDs are exactly 32
lowercase hexadecimal characters. Event IDs use the existing
64-lowercase-hex hash, colon, canonical decimal ordinal syntax.

`urls` provides query, event, control and fixed artifact URLs generated by the
server, never from source metadata. Artifact names are events.parquet,
design.parquet, inverse.parquet, manifest.json and v2 valid_mask.tif only.
Normal project browsing/archive continues unchanged. The existing rq-engine
download requires bearer export auth and lacks an explicit no-store header;
therefore this report uses a bounded session-authorized attachment adapter,
not changes to that shared transport. Verify the opened descriptor against the
accepted artifact signature/hash and recheck accepted identity before serving.

Read `state_at` before/after validation, pin the accepted manifest hash from
its artifact record, and verify manifest model agrees with acceptance. M1's
assessment ID must match the accepted snapshot's dNBR ID; M3's matches the model
attempt ID. Keep displayed assessment ID separate from accepted attempt ID.
Use `get_state(..., reconcile=False)` for currentness; do not reconcile jobs,
initialize optional module state, or expose its raw payload. A changed accepted
record at either boundary is 409 `assessment_replaced`, not a mixed snapshot.
No accepted attempt on a query is also 409; on an initial page it is normal
absence. Unknown valid event IDs or disallowed artifact names are 404
`not_found`; invalid attempt syntax is 400. Missing, malformed, hash-inconsistent
or unsupported accepted files produce 409 `results_unavailable`. Unavailable
infrastructure produces 503 `results_unavailable`. Use sanitized canonical
`error: {code, message}` responses; never return raw exception details/paths.
Call existing `authorize()` inside a deliberate local report boundary rather
than leaking the shared exception decorator's stacktrace response. Unexpected
exceptions are logged server-side and return sanitized 500 `results_unavailable`.
Use existing `rainfall_io.open_local` for bounded, regular-file descriptor
confinement; retain descriptor ownership until response close, including early
disconnect. Test unexpected-error responses, symlink races and closure.
HTML unavailable states must retain an explicit readable error/reload action.
If only live currentness dependencies are unavailable while the accepted bundle
validates, preserve its values with `current: null` and “Currentness could not be
checked” (user-facing: “Could not check whether these results match the current
inputs”); this is not corruption and never implies current. Log the failure
server-side. Existing run-context `pup` selection is accepted as a shared query
key and preserved by server URL helpers on all reads; it is not a file path
interpreted by this report and retains existing run-context authorization.

The read-only guarantee prohibits scientific/project NoDb and artifact writes,
model jobs, acquisition, rebuilds and job reconciliation. Existing authorized
session handling and ordinary read-through Redis caches retain their existing
contracts. Currentness may inspect bounded local provenance metadata and source
stat/hash identities, never decode original rasters or prepare inputs. Do not
introduce a replacement cache/read layer to claim zero Redis writes.
Before invoking currentness, require existing `redisprep.dump`; RedisPrep's
constructor otherwise creates that project file. Missing currentness state is
`current: null`, not permission to initialize it. Cover this with an actual
saved bundle lacking redisprep.dump and assert the file remains absent. Shell
context readers likewise must not create missing optional project state.

Displayed-row CSV is generated in the browser from the last coherent validated
page, using the same displayed Unitizer values, with full numeric precision.
There is no CSV endpoint or second query. Each export includes repeated context
columns for model, assessment/attempt, window/filter/page and units; text cells
neutralize spreadsheet formula prefixes (including leading control/whitespace),
numeric scientific cells remain numeric. Disable export on assessment replacement;
on a transient failure label retained values and their export as previous view.
Use a short-lived object URL, revoke it after download, and do not persist data.
Export help states “Current page and displayed units; numeric values retain
full precision.”
This narrows the previously proposed server CSV surface without changing scope.

Discoverability: add one always-reachable **View likelihood report** link inside
the existing eligible postfire control, including before a first assessment.
Do not introduce a new Mods-menu option or change feature roles/prerequisites.
The empty report links back to that control. The accepted source/model remain
read-only; no report interaction changes scientific defaults or model/source
preferences. Explicit user changes through the shared Unitizer retain existing
presentation-preference persistence; passive report reads do not change them.

## Acceptance and UX review

The dedicated UX reviewer must walk through opening the report, interpreting
one design scenario, comparing duration, finding a storm, changing units, and
recognizing stale/unavailable data without reading developer documentation.
Challenge duplicate controls, jargon, unnecessary clicks, hidden caveats and
misleading emphasis. Prefer removing a control to adding a new configuration
system. UX simplification cannot conceal scientific limitations or valid states.

Implementation acceptance requires route/authorization and real-file boundary
tests, controller selection/filter/race/Unitizer tests, and human browser checks
at desktop and narrow widths, keyboard-only, and supported themes. Verify saved
M1 and M3, both design sources, simulation/calendar/invalid dates, v1/v2,
empty/partial/stale/failed/replaced states, exact artifact values and no writes
or new jobs from report use. A basin-specific example is never a runtime default.

## Evidence and rationale

- [USGS assessment guidance](https://landslides.usgs.gov/hazards/postfire_debrisflow/)
  separates debris-flow generation from downstream runout/inundation. This
  supports explicit limits, not a new operational-warning product.
- [NOAA frequency FAQ](https://www.weather.gov/owp/hdsc_faqs) distinguishes PDS ARI
  from annual exceedance probability, especially at short intervals. Preserve
  rainfall source/duration terminology instead of annualizing debris-flow odds.
- [USGS hazard assessment FAQ](https://www.usgs.gov/programs/landslide-hazards/hazard-assessment-faq-frequently-asked-questions)
  explains rainfall scenarios and changing post-fire conditions. The report
  therefore distinguishes a rainfall window from total rain and static snapshots
  from recovery simulation.
- [Staley et al. (2017)](https://pubs.usgs.gov/publication/70188478) provides the
  model context for rainfall intensity-duration thresholds. Numerical authority
  remains the independently implemented, accepted local scientific contracts.
- [Barnhart et al. (2023), USGS user-needs study](https://pubs.usgs.gov/publication/ofr20231025)
  motivates understandable scenarios, uncertainty communication and decision
  context. Applying its inundation-product findings to this likelihood report
  is a design inference, not evidence that this proposed interface is validated.

Local precedents: [Storm Event Analyzer design](../storm-event-analyzer.md),
Geneva [specification](../../../wepppy/nodb/mods/geneva/specification.md)
sections 12.3–12.4 and 14, and the return-period report's compact tables. Unlike
the Analyzer's combined draft/implementation history, this document owns the
proposed durable report behavior; work-package plans/reviews own execution history.

## Kf, response curve and rainfall provenance amendment — 2026-09-16

Status: accepted 2026-09-16 after two independent reviews; implementation
conformance verified on forest, 2026-09-16. This amendment supersedes the earlier prohibition on
computed response curves. It does not authorize writes during report reads.
The [Kf contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/kf_source.md)
owns source identity and legacy/new freshness dispatch. Display the accepted
soil source: NRCS-derived STATSGO Kf for v3 M1, recorded POLARIS/RUSLE K for
legacy M1, and recorded thickness provenance for M3. Do not infer source from
current controls or label every accepted M1 as Kf-backed.

### Curve payload and bounded calculation

The existing page/query payload gains `response_curve` for the selected rainfall
window. No endpoint or request parameter is added. Use only T/F/S, model and
source identity from the validated accepted manifest; scalar evaluation does
not prepare predictors or modify saved scenario tables. Supported legacy M1
and current M3 remain eligible. Query attempt pinning, no-store, authentication,
input limits and out-of-order response handling remain unchanged.

The object contains `status` (available/unavailable), `reason`,
`duration_minutes`, `direction` (increasing/constant/decreasing),
`intensity_units: mm/hour`, `probability_units: fraction`, `range_max`, `points`
(each intensity_mm_per_hour/rainfall_mm/probability), `p50` (existing scalar
status/reason and equality intensity, or null), and `design_markers` from the
validated saved design rows. Missing predictors return unavailable with no
points. Direction follows the sign of the scalar rainfall response coefficient;
never assume monotonic increase or manufacture a P50 for a nonunique equality.

Deterministic presentation policy `response_curve_v1`: set the nonnegative
intensity range to [0, max(1, available finite saved design intensities,
available finite P50 intensity, available finite 99%-equality intensity)].
The 1 mm/hour floor gives degenerate/no-marker models a visible axis; the 99%
equality exposes the increasing transition. These are display choices, not
scientific thresholds or new design storms. Discard unavailable inverse values,
not errors or negative forward probabilities. Evaluate 101 evenly spaced values,
plus deduplicated exact available design intensities and P50. With at most four
design rows, this produces at most 106 points per duration. Use overflow-safe
sampling and the existing scalar engine. Arithmetic failure returns an explicit
unavailable curve while preserving valid saved tables; do not clamp a failing
calculation or silently rescale it. Probability stays in [0,1].

Draw one curve in the existing rainfall-scenarios section using existing plotting
conventions, fixed 0–100% y-axis, the current duration selector and Unitizer.
Keep saved design markers and add a labeled P50 marker only for a unique,
nonnegative finite equality. Label the line as equation response, distinct from
design markers. Marker/row selection and keyboard operation remain intact.
An ordinary expandable numeric table contains every sampled point with units,
window and likelihood, and a displayed-unit CSV action. The curve table provides
a complete usable alternative; no hover-only information or new advanced panel.
Unit changes alter presentation only. Duration changes replace curve and markers
from the same accepted snapshot and preserve the existing event behavior.

### Rainfall provenance and exports

NOAA Atlas 14 points are statistical design rainfall, not dated observations.
Project Climate supplies event peaks. For a recorded GridMetPRISM/CLIGEN
pipeline label subdaily intensities “Modeled/disaggregated rainfall”; calendar
labels alone never imply measured 15/30/60-minute rainfall. Retain actual date
semantics and climate mode separately. Do not mark every possible climate source
synthetic; unsupported/missing historical subdaily origin is “Not recorded.”
Only recorded pipeline provenance can establish measured versus modeled origin.

Add summary `rainfall_provenance` with `design_origin`, `event_origin`,
`climate_mode`, `date_semantics`, and `subdaily_origin` (modeled_disaggregated,
measured, or not_recorded). Populate from the accepted snapshot, never current
Climate. New result manifests retain this object in context; old manifests may
be projected from sufficient recorded provenance or report not_recorded.
Do not alter old parquet files, introduce guessed provenance, or infer an
observation claim from a calendar date.

All displayed-row CSVs, including curve CSV, carry accepted source/model,
attempt/assessment, provenance labels, duration and displayed units. Full saved
parquet downloads remain unchanged and link to their provenance manifest;
legacy missing provenance is explicitly identified. Formula-injection defenses
apply to new textual context fields. Fixed-postfire/no-recovery, conditional
probability, coverage-not-confidence and no-runout explanations remain visible.

Acceptance includes independent curve/scalar/P50 calculations at all durations,
English/SI equivalence, negative/zero rainfall response, legacy missing provenance,
real browser keyboard/numeric-table use, export and reload, and proof that reads
leave scientific state and artifacts unchanged.

## 2026-09-17 presentation refinement

Status: implemented and authenticated browser acceptance passed (2026-09-17).

Render **Assessment summary** as the shared `wc-summary-pane` definition-list
component. Give model/time/area, currentness, input coverage and notices explicit
terms and definitions. Keep the conditional-likelihood interpretation immediately
after the pane. Missing legacy values remain “Not recorded”; the pane does not
change result authority or invent metadata. When there are no assessment-specific
notices, the Notices definition reads “None recorded.” rather than remaining
empty.

Chart text must paint after response lines, P50 and scenario markers so data
marks cannot obscure it. Use a shared chart-label class whose fill is
`--wc-color-text`, stroke is `--wc-color-surface`, and `paint-order` draws the
stroke before the fill. Use a 3-pixel stroke with rounded joins, and make the
final label layer pointer-transparent so it cannot intercept marker activation.
The contrasting halo must follow theme tokens; do not hard-code a light or dark
outline. Preserve fixed likelihood scale, accessible marker names, pointer and
keyboard selection and the tabular alternative.

Build the **Storm events** filter with canonical shared numeric/select fields,
checkbox and button row. Place fields in a responsive grid or stack with at
least `--wc-space-md` of row gap and bounded field widths; inputs must not stretch
to the full report width or overflow at narrow viewports. Separate the canonical
button row from the fields by at least `--wc-space-md`. Preserve field IDs,
`data-pfr-field` selectors, value ranges, blank semantics, query encoding, focus
order, Apply/Reset behavior, pagination and event selection. Acceptance covers
all four filter hooks, decimal 0–100 minimum-likelihood bounds, integral year
step, every sort option, descending checked and unchecked submissions,
Apply-before-Reset order and unchanged query encoding. This amendment is
presentation and accessibility only; no report API or scientific value changes.

Event-date link buttons in striped result rows use a theme token that meets the
AA text-contrast threshold against the row backgrounds in the default, light
high-contrast and AA dark validation themes.

Rationale: these changes align the report with familiar WEPPcloud components,
keep dense plot labels readable across themes and restore predictable form
spacing without introducing a new visual system.

## 2026-09-17 control summary placement

Implemented and browser-verified on forest, 2026-09-17 (ancestor ca3d58471). The [control layout amendment](postfire-debris-flow-control-contract.md#2026-09-17-control-summary-layout-amendment) governs help placement, section spacing and the accepted-only Summary card/report link. It supersedes earlier direct control download/placement language. Report endpoints, empty direct-report behavior, saved artifacts and download authorization remain unchanged.
