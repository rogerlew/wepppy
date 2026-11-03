# Roads settings editor contract

## Operator clarification: default settings and user overrides

Operator direction, 2026-11-03, supersedes the five-fallback-only proposal:
this is a **default settings harness**, not a calibration harness. Users need
explicit overrides of key model drivers so they can increase or decrease Roads
runoff and sediment toward observed data or their expectations. Observations and
user expectations are distinct comparison targets; matching either does not by
itself establish physical validity or field calibration.

Defaults provide a reproducible starting point, not a restriction on custom inputs.
The editor must expose effective runoff and erosion drivers, with clear units,
role/scope, validation and precedence. An intentional override must affect its
selected scope even when feature values or templates supply the baseline; a
fallback that is unused cannot satisfy this requirement. Preserve original source
values and make override enable/disable/reset explicit. Exact parameter keys,
precedence, bounds and native propagation remain to be specified and reviewed.
Do not silently reinterpret the existing fallback fields as overrides.

Characterize the native runoff/infiltration and erosion/detachment drivers before
selecting controls. Lack of a field-calibrated interval is not a reason to exclude
an otherwise useful, supported driver. Separate input validity from tested values
and calibration claims. Explain response direction and coupling honestly; no
universal monotonic response or independent runoff/sediment adjustment is promised.
Geometry/traffic fallbacks alone are insufficient: width changes footprint and
traffic response is nonmonotonic. Do not require users to misstate physical geometry
to adjust runoff or erosion behavior.

Acceptance requires save/reload/reset and visible effective-input provenance,
plus controlled rerun comparisons demonstrating increased and decreased runoff
and sediment through the selected overrides in declared representative contexts.
Retain baseline/custom results and distinguish total exports from area-normalized
quantities. Automatic optimization, new-default adoption and deployment are not
implied. Existing study results remain valid within their original scope.

The prior five-field specification/static layout and their reviews are historical
proposal evidence, not approval or sufficient coverage of this corrected objective.
Revise the concrete specification/layout and obtain independent review and explicit
human approval before production persistence/application/UI wiring.


Status: **proposed; explicit human specification/layout approval absent**.
Implementation conformance is pending. This document records the reviewable proposal;
it does not authorize production view or persistence/application implementation.
The retained study evidence and independent reviews support this bounded proposal;
explicit human approval is still required under [Roads adjudication](roads-parameterization-adjudication-contract.md#end-user-workflow-and-closure).

## Scope and rationale

Expose five existing Roads fallback settings through the existing Roads panel,
using familiar Edit, Save, Cancel and Reset actions. A user can change supported
model inputs without editing CSV or native files. Preserve existing template soil
assembly, uploaded feature precedence, routing and preparation. The conditioned
generated-soil `erosion_road_cap` research lane is not a production selectable policy
and is not adopted by this editor. Neither default nor custom values are field-calibrated by this program.

Applicable authorities remain the Roads NoDb
[specification](../../wepppy/nodb/mods/roads/specification.md),
[preparation lifecycle](roads-preparation-lifecycle-contract.md),
[water accounting](roads-water-accounting-contract.md),
[output scope](output-scope-contract.md),
[NoDb persistence/concurrency](nodb-persistence-concurrency-contract.md),
[CSRF](weppcloud-csrf-contract.md), shared
[controller contract](../ui-docs/controller-contract.md), and
[artifact observability](../standards/artifact-observability-standard.md).
No new endpoint, queue, native formula, global attribute override, segment identity
scheme or preparation version is introduced. See
[proposed ADR-0135](../adrs/ADR-0135-roads-settings-controls.md).

## Fields and sources

| Label / submitted and persisted key | Unit / choices | Baseline value | Validity limits | Applicability |
| --- | --- | --- | --- | --- |
| Surface fallback / `surface_default` | gravel, paved | gravel | Existing canonical enums and API aliases | Road soil/template choice; recognized mapped or legacy feature value wins |
| Traffic fallback / `traffic_default` | high, low, none | low | Existing canonical enums and API aliases | Road management/erosion package; recognized mapped or legacy feature value wins |
| Road width fallback / `road_width_m_default` | m | 4.0 | Finite, 0.3–100 inclusive | Existing designs, subject to their feature/geometry rules; valid feature width wins |
| Fill length fallback / `fill_length_default_m` | m | 30.0 | Finite, 0.3–100 inclusive | Outslope rutted; valid feature fill length wins |
| Fill slope fallback / `fill_slope_default_pct` | % | 10.0 | Finite, 0.1–150 inclusive | Outslope rutted; valid feature fill slope wins |

The baseline identifier is `roads_legacy_templates_v1`. It identifies precisely
these five existing fallback values and their meanings, not a new scientific
parameter set or a binary identity. No values, units or formulas change. Existing
unrelated Roads parameters remain authoritative and unchanged when these five are
saved or reset. Current API partial updates and ordinary accepted aliases remain supported,
subject to the explicit five-field validation delta below.

The UI submits canonical enum tokens and JSON numbers, never formatted unit strings.
Numeric strings accepted by the existing API remain accepted when finite and within
these limits. Booleans are not numbers for these five fields. Missing keys in an API
partial update preserve saved values; explicit null/empty values for these five
fields are invalid. Validation applies atomically to every supplied known field.
This is an intentional proposed API validation change for these five fields:
JSON booleans previously accepted by numeric coercion are rejected; JSON null that
previously normalized to traffic `none` is rejected. The string `none` remains a
valid traffic choice. Existing finite numeric strings, enum aliases and omitted-key
partial updates retain their behavior. This delta needs the same human approval
as the editor; it must not be described as wholly unchanged API behavior.
The editor sends exactly the five listed keys. Do not reinterpret unknown existing
API keys as an editor schema or tighten unrelated API behavior in this change.

Fill fallbacks do not create a fill OFE in inslope designs. Outslope unrutted keeps
its required explicit geometry contract; these fallbacks cannot satisfy missing
unrutted geometry. A mixed upload may contain applicable and inapplicable segments.
Keep the field available before design applicability is known, with this explanation;
never claim all saved values affect all profiles.

Width can alter the modeled road/fill/buffer strip footprint and unrutted geometry
transforms; it is not exclusively a road erosion coefficient. Surface and traffic
select coupled template/management behavior, not measured armor or vehicle counts.
Low and none can share soil coefficients while their management differs. Model
response need not be monotonic. Buffer geometry, road DEM grade/length, texture and
profile fragments remain inspectable through existing details; this editor adds no
editable control for them. Profile fragments must never be labeled surface armor.

Validity limits are distinct from study values and calibrated ranges. The
[47-profile study](../work-packages/20261029_roads_parameterization_program/artifacts/revised-sensitivity-results.md)
characterizes width 2/4/8 m, fill length 10/30/60 m, fill slope 2/10/30%, and
high/low/none traffic in the declared production-template contexts. A separate
conditioned generated-material context retains its own baseline and geometry
contrasts; it does not authorize generated-policy adoption. The
[four-project study](../work-packages/20261029_roads_parameterization_program/artifacts/revised-project-sensitivity-results.md)
verifies width/fill save/reload, native propagation and baseline preservation.
Surface remains an existing supported categorical field; this new panel does not
isolate its sensitivity from texture/context differences. See the
[independent scientific review](../work-packages/20261029_roads_parameterization_program/artifacts/revised-sensitivity-science-review.md)
for exact coverage and limitations.

Width primarily scales the whole modeled strip in these studies. Fill changes
both area and process extent; longer fill is not guaranteed to reduce total
sediment. Traffic response is context-dependent and nonmonotonic, so present
actual modeled condition choices, never an erosion-reduction slider. These
finite study values are not recommended intervals or validation of every value
inside the existing limits. No field-calibrated range is established for either
default or custom settings. PASS particle export and native terminal sediment
have different non-EVENT support; the study retains both rather than claiming
complete particle/storage closure.

## Presentation and actions

Reuse the Roads `control_shell`, shared field/button macros, status and Details
patterns. Place Roads settings after Attribute Mapping and before Prepare/Run.
Move the existing surface/traffic fallback fields into this single editor while
retaining their mapping semantics; do not duplicate them in separate forms.
The accompanying [static layout](../work-packages/20261029_roads_parameterization_program/artifacts/revised-settings-layout-draft.html)
is a review artifact, not an implemented view.

View mode shows saved values, units, baseline/default or custom status, applicability
and an **Edit settings** button for authorized mutable runs. “Default” means equal
to the five baseline values; it does not mean calibrated or newly adopted. An
unknown legacy provenance record must not be labeled verified merely because its
numbers match. Custom status reflects a difference in any of the five values.

Edit mode holds an unsaved local draft. **Save settings** submits the five values
once. **Cancel** discards the draft and re-reads saved values without a mutation request.
**Reset to defaults** fills the draft with the five baseline values and marks it
unsaved; Save commits the reset. Reset preserves upload, attribute mapping and all
other parameters. Show this scope adjacent to Reset. Reload discards an unsaved
draft and loads authoritative saved values. Do not store drafts in local storage.

Disable Save when canonicalized draft values equal the server-loaded five values.
This is a UI request omission, not a new server no-op contract: a direct accepted
same-value `set_params` call retains existing lifecycle invalidation behavior.
A successful Save reloads the response state and shows “Settings saved. Prepare
and run Roads to generate results.” A field error preserves the draft and focuses
the first invalid field. Announce errors and success with existing accessible
status patterns. Busy/conflict responses preserve the draft without automatic
retry or client-side mutation. A later explicit accepted Save can replace another
session's earlier values under existing last-accepted-write semantics; this design
does not promise cross-session draft conflict detection or automatic merging.

### Adjacent actions and draft ownership

The current `applyAttributeMapping` action reads surface/traffic fallbacks from the
form. The approved implementation must separate these actions: **Apply Attribute
Mapping submits only `attribute_field_map`**; **Save settings submits only the five
settings keys**. The mapping route/API may retain support for existing broader
payloads from other clients; this is a change to the Roads panel action, not removal
of API keys. Neither action implicitly saves the other's draft.

A dirty settings draft disables Upload, Apply Attribute Mapping, Prepare and Run
with the inline explanation “Save or Cancel your settings changes before uploading,
applying mappings, preparing or running Roads.” Keep Save, Cancel and Reset available;
no confirmation modal is needed. Upload file selection may remain visible, but no
upload request can start while the draft is dirty. Recheck dirty state in action
handlers as well as disabling controls so stale click handlers cannot submit.
Existing operation/readonly restrictions still apply and cannot be relaxed by this
rule. When clean, these adjacent actions retain their existing workflow.

A passive summary, mapping or job-status response may update status but must not
replace a dirty settings draft or its saved comparison snapshot. Successful settings
Save owns its submitted snapshot: disable field editing, Save, Cancel, Reset and
adjacent mutations while that request is pending; Cancel is not a rollback of an
in-flight server mutation. Hydrate only from the matching current request's
success response. Ignore responses from a superseded request or detached controller
instance. On failure retain the submitted draft and restore allowed editing/actions.
Cancel never mutates state: discard the draft, re-read authoritative settings through
the existing query path and then re-enable adjacent actions; while reloading, show
“Loading saved settings” and keep mutations unavailable. A failed reload is explicit
and cannot authorize Prepare/Run using a guessed form state. This is local request
ownership, not a new server version/conflict protocol or cross-session merge promise.

Required controller/render/browser checks: dirty edit + Apply Mapping attempt sends
no request; clean mapping request contains mapping only; Save contains five settings
only; passive/late mapping and summary responses preserve draft; double Save is
suppressed; matching success hydrates the server result; failed Save keeps values;
Cancel rereads without mutation; readonly/busy restrictions remain in force.

## Transport, persistence and concurrency

Reuse POST `/runs/<runid>/<config>/tasks/roads/set_params` (existing optional
trailing slash), existing request parsing and success/error envelopes. Use shared
`WCHttp`, run URL and CSRF helpers. Preserve run authorization, readonly and enabled
state checks on the server; disabling a browser control is not authorization.
No new reset endpoint is needed: Reset plus Save submits the same five keys.

Validate and normalize the entire supplied payload before retaining old artifacts
or changing NoDb. Invalid requests leave saved values and current-result eligibility
unchanged. Use the existing query-catalog/ Roads lifecycle mutation guards and
NoDb lock/cache contract; rehydrate authoritative saved state as that contract
requires. Do not introduce optimistic revision tokens or a new lock order.
Concurrent accepted mutations retain existing serialization semantics; no new
cross-session live update guarantee is claimed.

A successful accepted save retains existing invalidation of preparation/current
Roads results and preserves historical diagnostics under the lifecycle contract.
Baseline outputs/readiness remain independent. Rejected preflight or validation
preserves a prior coherent result. If accepted invalidation or persistence fails,
return the actual error and follow existing fail-closed admission and NoDb recovery;
do not claim a distributed rollback or silently re-admit old reports.

## Additive metadata and visible provenance

Add optional server-owned NoDb metadata `_roads_settings_metadata` with exactly
`schema_version: 1` and `baseline_id: "roads_legacy_templates_v1"`. It records that
the saved five-field configuration was handled by this editor-era contract, not
scientific validation, an engine version or policy adoption. It contains no second
copy of parameter values. Clients cannot select a baseline or write this metadata.
Set it in the same NoDb transaction as a successful `set_params` call supplying at
least one of the five fields. Other partial parameter updates preserve it.

Missing metadata on an existing project means legacy provenance. Read operations,
page loads and forks do not synthesize a metadata write or replace existing saved
values. Existing effective defaults for absent legacy keys remain unchanged under
normal Roads hydration. Unsupported/malformed metadata is displayed explicitly;
it cannot authorize a guessed conversion or different parameter policy. A later
explicit successful Save of the supported five-field configuration can establish
version-1 metadata while preserving unrelated settings. This is metadata enrollment,
not adoption of a new parameter set.

Present malformed saved settings are distinct from absent legacy keys. A present
invalid enum, boolean/null numeric, nonfinite or out-of-range value in these five
fields must not be silently replaced by a baseline for editor display or native
execution. Preserve its saved representation and surface a field-specific diagnostic;
withhold Default/Custom status and disable Prepare/Run until the settings are
repaired. Existing absent-key legacy defaulting remains supported. The editor shows
an explicit repair state and allows an authorized user to intentionally submit a
complete valid five-field Save (or Reset then Save); do not fill corrupt fields
silently. A partial API update leaving malformed fields unresolved fails before
invalidation. The complete repair applies atomically, preserves unrelated settings
and uses normal lifecycle retention. Render persisted values/diagnostics as text,
never executable markup. Validate raw saved fields before normalization can erase
this distinction; do not broaden the work to unrelated NoDb keys.

Expose metadata and the current five values via the existing Roads query payload
and successful Save response using additive `settings_provenance`; preserve existing
`roads_params` and other response keys. That object has `schema_version` and
`baseline_id` from valid metadata, `metadata_status` of `recorded`, `legacy` or
`unsupported`, and `values` containing the five effective saved settings. For malformed saved
fields, return null for the invalid field in `values`, plus additive `field_errors`
keyed by that field with a display-safe diagnostic; do not return nonfinite JSON
or pretend the null is a valid saved choice. Valid configurations use empty
`field_errors`. Preserve original saved bytes until explicit repair. For
legacy/unsupported metadata, schema/baseline are null rather than fabricated.
The UI computes display equality against the server-supplied baseline values,
provided additively as `baseline_values` in the same object. These are the existing
canonical defaults, not an independent source of builder formulas.

Copy the configuration `settings_provenance` object into existing visible preparation
summary `wepp/roads/segments/roads.inslope.summary.json`. Preparation provenance
records saved intent only. Preserve the execution manifest
`wepp/roads/segments/roads.segment.pass.manifest.json` as a JSON **list** with its
existing rows and keys. Add `settings_provenance` to each new row; do not wrap the
list in an object or reinterpret historical rows. This row object contains the
same configuration snapshot plus `segments`, a list of source-segment resolutions:

- `segment_id`: original preparation-local road segment ID. A combined profile
  may have several entries; a synthetic remainder has an empty list.
- `fields`: object keyed by the five saved parameter keys. Each entry contains
  `applicable` (boolean or null when failure prevented resolution), `source`
  (the canonical resolver's source label, `not_applicable` or `unresolved`),
  `resolved_value` (canonical enum/finite number, or null when not applicable or
  unresolved), and `reason` (null or existing applicability/failure reason).
  Capture resolver output at assembly; do not reconstruct sources from raw presence.
- `emitted_geometry`: list of actual slope-file readbacks, each with `input_relpath`,
  `ofe_index` (1-based), `role`, `width_m`, `length_m` and ordered `slope_points`,
  each point containing `distance_fraction` and `slope_fraction`. Preserve every
  serialized transition point in native order, not a single nominal slope.
  Preserve actual serialized units and values. List all modeled OFEs for that
  segment's profile; duplication across shared profiles is explicit, not summed.
- `input_files`: actual prepared slope, soil and management paths and SHA256 hashes,
  each represented by `relpath` and `sha256`. These bind categorical choices to
  the complete emitted artifacts without inventing one native scalar for a coupled
  surface/traffic package. Missing inputs after failure produce an empty or partial
  list, never invented hashes or values.

All paths are project-relative paths to existing Roads artifacts. A failure before
segment identification has `segments: []` and the row's existing failure reason;
it is not silently classified as a no-op. Do not infer internal native clamp values
from saved settings. Runtime consumer validation uses actual inputs, source mapping
and native outputs as separately retained evidence. These additive records do not
change builder formulas or scalar values. Existing rows without this object remain
legacy evidence, not fabricated current provenance. Retain complete and partial
records with historical/failed attempts under existing lifecycle rules and ordinary
authorized browse/download/archive paths. No new hidden file is needed.

Add `settings_usage` to the existing successful run summary (`_last_run_summary`,
returned query summary and normal run-summary log). It is keyed by the five fields;
each value has nonnegative integer `applicable_segments`, `feature_segments`,
`fallback_segments`, `skipped_segments` and `unresolved_segments`. Compute it from
source segment identities/resolutions captured for that execution, not a second
preparation formula. `feature_segments` groups actual mapped/legacy attribute source
labels; `fallback_segments` groups actual configured fallback source labels.
Unrutted explicit fill geometry is not counted as use of rutted fill fallbacks.
Preserve existing skipped/failed reason records. Count each original segment once
per field; combined/multiple profiles must not inflate counts. Conflicting source
records put that segment in unresolved, with a diagnostic, rather than arbitrarily
choosing a source. Synthetic remainders are excluded. Only current completed-run
summaries are displayed as actual use; failed attempts remain diagnostic evidence.

Label this “Settings used in the last completed run”. Before it exists, say “Run
Roads to see actual settings use”. Zero fallback use means applicable segments used
feature values, or that no applicable segments executed; distinguish those cases.
It does not establish a physical no-op for other fields. Old records missing
provenance show “Usage unavailable for this run”, not zero. Never show old-run
counts as describing edited settings.

## Compatibility, fork and restore

Existing projects keep saved values and existing template policy. No automatic
migration, default adoption, source-soil regeneration or native rerun occurs on
read. Adding metadata does not certify old outputs. Fork carries saved settings and
metadata with normal project state. Archive/restore retains NoDb, visible summaries,
execution manifests and history, preserving bytes and permissions under existing
archive rules. A legacy archive remains legacy; restoring a new archive does not
mix its metadata with old prepared inputs or fabricate current-result receipts.
Preparation-local IDs and readiness remain governed solely by the lifecycle
contract. All old API parameters and schema keys are preserved.

## Required validation and valid states

| State or operation | Required outcome and evidence |
| --- | --- |
| Roads absent / never used | Baseline UI and reports remain usable; render defaults without hidden writes |
| Present-empty, no upload | Authorized settings Save works; Prepare explains missing upload; no results fabricated |
| Populated/prepared/completed | Save invalidates Roads admission, retains history and baseline bytes; rerun reads saved values |
| Legacy saved values | Reload/fork preserve values and label missing provenance; explicit Save creates metadata only with that mutation |
| Malformed present saved setting | Explicit field diagnostic, no guessed default; Prepare/Run disabled; authorized complete five-field repair Save only |
| Unsupported metadata | Explicit provenance status; no guessed conversion, policy adoption or silent read-time replacement |
| Invalid/null/nonfinite/boolean/out-of-range input | Atomic validation failure before invalidation; all old values and current receipt preserved |
| Readonly/unauthorized/CSRF failure | Existing access/error contract; real server denial and no mutation |
| Dirty draft plus mapping/upload/Prepare/Run | Adjacent actions disabled with Save/Cancel explanation; passive refresh preserves draft; matching Save response only may hydrate |
| Concurrent run or mutation | Existing busy/lock behavior; local draft retained; no stale response revives reports |
| Reset/Cancel/reload | Reset is draft-only until Save; Cancel/reload restore server values; unrelated params/map retained |
| Failed preparation/native run | Error and partial artifacts inspectable, no current result receipt; saved intent remains identifiable |
| Fork/archive/restore | Saved values/provenance and archive payloads survive actual canonical operations; currentness remains coherent |
| Zero applicable/fallback segments | Honest applicability/no-use message; no silent global override or fabricated sensitivity |

After human approval and the required contract-first ancestor, validate actual
browser -> request -> persisted reload -> prepared executable inputs -> native
execution -> fresh Roads report artifacts. Read actual role values and areas,
not merely response codes or NoDb equality. Exercise production-equivalent service
identities, groups, mounts, umask and orchestration at each process boundary.
Include direct unmocked persistence/filesystem/restore checks, controller render
and JS tests, focused backend gates, full repository sanity and independent final
workflow reviews. Retained controller-only studies do not certify this browser/RQ
chain. No deployment is authorized by this proposal.
