# M1/M3 selection and workflow increment

Status: owner-directed UI intent recorded 2026-09-11; implementation pending.
The accepted request and state intent below requires the contract-first checkpoint
before runtime edits. Production currently executes M1 only. This increment
prepares UI and rq-engine wiring; full M3 predictor integration follows.

## Accepted presentation

Keep the existing control below RUSLE and use canonical Pure UI macros, theme
styles, tables, radio groups, uploaded-file display, job ID, Status and Details.
Do not introduce tabs, cards, custom components or a separate model control.

Inside `wc-control__header`, describe both models and show this table using
the established table presentation:

| Input | M1 | M3 |
| --- | --- | --- |
| Terrain | Fraction of watershed both at least 23° slope and moderately/highly burned | Basin ruggedness: vertical relief divided by square root of watershed area |
| Fire | Mean differenced Normalized Burn Ratio (dNBR) | Fraction of watershed moderately/highly burned |
| Soil | Mean soil erodibility (K), prepared through RUSLE | Mean soil thickness, using SSURGO first and STATSGO as fallback |
| Rainfall | Rainfall over 15, 30 or 60 minutes | Rainfall over 15, 30 or 60 minutes |

Proposed header copy: “Estimate debris-flow likelihood for recently burned
watersheds in the Western United States. Staley et al. (2017) recommend M1;
it performed most consistently against regional rainfall thresholds in their
test dataset. M3 provides an alternative when dNBR is unavailable and requires
soil thickness and basin ruggedness.” Retain the existing About this model link.
The M1 recommendation is supported by section 5.2 of the retained manuscript
(DOI 10.1016/j.geomorph.2016.10.019). The data-availability description of M3 is
our workflow guidance, not a claim that the authors recommend M3 over M1.

Immediately below the header, provide one labeled model radio group with
side-by-side choices “M1 (recommended)” and “M3”. M1 remains the default.
Use normal responsive wrapping on narrow screens. Then show Required project
data, the applicable upload section, rainfall selection and the existing run
action/status/downloads in that order.

| Required project data or input | M1 | M3 |
| --- | --- | --- |
| Watershed | Show and require | Show and require |
| Soil burn severity | Show and require | Show and require |
| Soil erodibility (K) | Show and require current RUSLE Nomograph K | Hide; not a dependency |
| Soils | Hide; no independent WEPP soils prerequisite | Show; built WEPP soils for wiring, usable thickness at full integration |
| Climate | Show and require | Show and require |
| dNBR upload and its map/scale summary | Show and require accepted dNBR to run | Hide; not a dependency |

Removing M1's independent Soils prerequisite changes backend admission and
freshness as well as presentation. Required K provenance remains authoritative;
this does not weaken RUSLE's own input requirements. Both models use SBS, for
different predictors. M3 does not need the M1 slope/SBS intersection.

Preflight remains server-authoritative and updates for the selected model in
real time, on initial load and reconnect. NOAA remains disabled when unavailable.
Model changes preserve uploaded maps and completed/failed attempts. Hiding the
dNBR fields must not hide existing job failures or retained project artifacts.
No automatic model substitution. Reports/dashboard remain deferred.

## Request, state and result compatibility

- Add a model-aware run endpoint accepting explicit `model: M1|M3` and the
  existing `frequency_source`. Preserve `run-m1` for existing clients, pinned to
  M1. Reject unknown models and contradictory payloads before queue admission.
- Persist selection separately from immutable attempt/result model identity.
  Legacy attempts/results without model identity mean M1. Changing selection
  does not relabel or delete a prior result; downloads identify their model.
- Include model identity in duplicate-admission comparisons, predictor reuse,
  source snapshots and publication checks. Preserve queued receipt before
  admission, worker ownership, locks, authorization, CSRF and bounded bodies.
- Exclude unrelated model inputs from freshness: dNBR/K changes do not stale
  M3; WEPP soil-thickness changes alone do not stale M1. Shared DEM/domain/SBS/
  climate dependencies still apply. K's actual provenance remains checked.
- M3 is wired through the real run endpoint into a dedicated `run_m3_rq` task
  now. Enable Run when its model-specific project prerequisites are ready; do
  not disable it merely because scientific composition is deferred. The task
  receives the immutable M3 attempt and uses the existing job/status/error
  lifecycle. Until scientific composition is implemented, it fails explicitly
  with `integration_pending` and “M3 soil and terrain integration is not
  implemented yet.” Retain job ID, failure and visible attempt/error records
  across reload. No placeholder probabilities, successful no-op or M1 dispatch.
  This is a wired task boundary, not a claim of implemented M3 calculations.
  Completing composition later must not require another selector/API change.
- Keep the existing latest accepted result publication in the module directory
  and all earlier attempts visible. Separate persistent current bundles per
  model are not assumed by this proposal.

Validation must cover never-used/empty/legacy/populated state; model switching
and reload; missing inputs for either model; stale preflight replies; active
jobs while selection changes; duplicate/different-model submissions; failed
replacement and result identity; unauthorized/malformed requests; normal
browse/download/archive observability. Validate the actual browser and queue
handoff under existing development service identities before claiming completion.

## Exact wiring boundary

This section supersedes the earlier fixed-M1 UI/transport intent for this
increment. Implementation remains pending the reviewed checkpoint ancestor.

The added run route is POST `/postfire-debris-flow/run` beneath the existing
run/config API prefix. Require `model` exactly `M1` or `M3`; `frequency_source`
retains `cli` default or `noaa`. The old `/run-m1` payload stays unchanged and
always dispatches M1. Both return the existing job_id/result.attempt_id envelope.

POST `/postfire-debris-flow/selection` accepts required `model` and
`frequency_source` only and persists selection without enqueue or invalidating
accepted outputs. Return the selected model's public state in `result`. This
mutation uses existing rq:enqueue scope, config/readonly/feature/locale checks,
4 KiB JSON limit, duplicate/unknown-key rejection and NoDb lock/refresh behavior.
Serialize it with the existing admission lease. GET `/state` remains read-only;
it returns persisted selection (legacy default M1) and its requirements.
Browser radio changes save selection, then apply the returned state. Discard
obsolete responses, and serialize preference writes so an older server request
cannot overwrite the newest choice. Disable Run during that pending save.

Add top-level state/public key `model`; additive legacy default is M1 without
GET persistence. Attempt records carry immutable `model` and `frequency_source`;
legacy model attempts resolve M1 and their recorded snapshot frequency. Workers
never derive either from a subsequent UI selection. Expose model on public run
and result summaries. A different selected model is displayed as a different
model, not as proof that an old result's dependencies changed. Test changing
model/frequency while a job runs and during readback. Preserve the single-active-
model-job admission policy; duplicate identity includes model/frequency/sources.
Reconciliation maps M1 to run_m1_rq and M3 to run_m3_rq with existing exact args.

For this scaffold stage only, M3 Soils readiness checks the existing completed
WEPP soils inventory and ownership; it does not claim thickness has been
prepared. The eventual scientific integration adds thickness acquisition/
coverage validation to this backend readiness key without changing UI structure.
M3 watershed readiness also requires the effective 10 m ned13/2022 settings and
returns an actionable reason when they differ. Actual M3 worker admission checks
those settings and its captured inputs before the explicit integration_pending
failure. No scientific artifact is created by that scaffold failure.

## Owner decisions (2026-09-11)

M3's initial accepted DEM configuration is `[general] cellsize = 10` and
`dem_db = "ned13/2022"`. Check effective Ron.cellsize and Ron.dem_db at admission
and in the worker snapshot; full terrain integration also checks the actual
raster grid. Do not impose this requirement on M1 or expand to other sources
without a subsequent decision. This is the owner's selected source contract,
not a new provenance survey or custom-DEM inference system.

Assess the existing `wepppy/soils/ssurgo/ssurgo.py` horizon validity rules before
implementing thickness preparation. Reuse adequate rules; do not create another
soil validity policy merely because this is a new module. Source priority remains
SSURGO first, original STATSGO THICK fallback. The assessment is recorded in
[SSURGO validity assessment](ssurgo_validity_assessment.md); production material,
component and fallback details remain the next scientific integration milestone.

Calculate scalar probabilities using non-masked support. Show **Valid coverage**
as a percentage of the original project watershed, explain that the estimate
represents the area with usable inputs, and provide a GeoTIFF validity mask for
download through the ordinary project browser and results links. No uncertainty
interval UI or report/dashboard map is required. Never turn missing observations
into zeros. Zero valid support yields unavailable probabilities and explicit
coverage diagnostics, not a fabricated scalar. ADR-0066 records this change in
scientific intent; calculation implementation follows the UI/task wiring.

Keep the existing automatic POLARIS and RUSLE enablement for both selections.
For M1 the user manually runs RUSLE to build the K layer before submitting the
postfire model. Selecting M3 neither disables these mods nor requires their K
output. No feature-registry dependency redesign is part of this increment.

## Coverage integration details

The next numerical milestone must use one declared analysis support and publish
its exact mask, numerator/denominator counts and grid. Proposed M1 support is
in-watershed cells with determined slope/SBS intersection, valid normalized
dNBR and valid K; all three predictors aggregate over that same support. This
preserves the owned tool's Horn and three-state diagnostics while replacing the
production all-or-nothing point estimate. Retain the original watershed area
for applicability warnings. M3 needs a separate support definition for SBS and
thickness; its basin-scale relief is not a local surface roughness raster.
Do not silently substitute masked pixel count into the accepted full-upstream
ruggedness formula. Ratify that exact aggregation contract at the scientific
integration checkpoint.

Planned coverage output is `valid_mask.tif`, aligned to the project grid, UInt8:
1 used, 0 excluded inside the watershed, 255 NoData outside. `coverage` metadata
records total/valid/excluded cells and unrounded `valid_fraction`; display
percentage to enough precision to reveal a nonzero exclusion, with counts
available in the summary. Legacy results without this artifact must say coverage
was not recorded, never claim 100%. Existing files are not retrospectively
rewritten. The UI/task wiring must accommodate the additive coverage summary and
file link when present, without inventing values before calculation supplies them.

Retain accepted rainfall choices: project climate events; CLI or available NOAA
design storms; 15/30/60 minutes; 1/2/5/10-year intervals; 50% inverse threshold.
Keep project watershed/outlet scope, continental-US eligibility, Western-US
guidance, study-area warnings and project SI/English display preferences.
