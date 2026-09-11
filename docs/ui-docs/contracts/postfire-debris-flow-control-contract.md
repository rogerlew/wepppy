# Postfire debris-flow control contract

Status: accepted owner-directed contract; implemented and validated on the development stack.
Canonical domain: [production M1 workflow](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md).
The owner requested a simple interface for land managers and hydrologists,
with upload and model execution now and reports deferred. The contract checkpoints are `5c0a172ee` and `595816476`.

## Scope and layout

One existing Pure UI control named **Post-fire debris flow**, following project
control typography, spacing, form helpers and status patterns. No new dashboard,
wizard, card grid or tabs. Model is fixed to Staley M1; no model picker. Existing
project watershed/outlet supplies the assessment domain.

The control and its navigation link follow RUSLE, which supplies soil
erodibility. Selecting the mod inserts and initializes it without a page reload,
including on projects where it has never been enabled. Keep hidden navigation
and section placeholders when disabled; re-enabling binds a fresh controller
to the new form. This follows the registry’s usable-toggle contract and its
RUSLE-before-debris-flow order. Eligibility and execution prerequisites remain
server-authoritative.

Opening text: “Estimate debris-flow likelihood for this watershed using the
Staley model.” A single help link, “About this model”, explains Western US
intended use, recent-fire context, 0.2–8 km² study range, and guidance to isolate
suspected burned basins through project outlet selection. No mandatory modal or
acknowledgment checkbox. Show material applicability warnings inline when relevant.

Proposed layout (brackets describe controls, not literal rendered text):

    Post-fire debris flow
    Estimate debris-flow likelihood for this watershed using the Staley model.
    About this model

    Required project data
    Watershed                 Ready
    Soils                     Ready
    Soil burn severity        Ready
    Soil erodibility (K)       Needed — Prepare in RUSLE
    Climate                   Ready

    differenced Normalized Burn Ratio (dNBR)
    [Choose file]
    Single-band raster with integer or floating-point values.
    GeoTIFF (.tif/.tiff) preferred; self-contained .img or supported .vrt accepted.
    dNBR values [Auto ▾]
    [Upload dNBR]
    [Uploaded-map summary table: file, format, cell size, coverage, values, scale]

    Design storm rainfall
    (•) Project climate   ( ) NOAA Atlas 14
    Storm events always use the project climate.

    [Run debris-flow model]
    Prepare soil erodibility in RUSLE before running the model.

Required data is a compact list, not five cards or five duplicate descriptions.
Ready rows are plain text; missing rows link to the existing owner control.
Use “Prepare in RUSLE”, “Build soils”, “Set soil burn severity”, “Build climate”,
or “Delineate watershed” as applicable. Do not add rebuild actions here.
Drive these rows through the existing preflight stream and `preflight:update`
event. Update readiness, missing-data links, run-button explanation and NOAA
availability without reloading when upstream data change. Hydrate initial state
and reconcile on reconnect; do not retain a false live-ready indication while
disconnected. Use the existing preflight connection-status treatment.
Show “Ready” only from server prerequisite/freshness checks, never from controller-file
existence or a cached client assumption. Feature availability obeys WBT/CONUS
policy; an absent controller in an eligible new project is normal first use.

## dNBR field and copy

Label: **differenced Normalized Burn Ratio (dNBR)**. Help: “Upload a dNBR map for the same
fire assessment as the soil burn severity map. The map will be aligned to the
project watershed.” The control must not ask users for EPSG, resolution,
resampling, dtype, target grid, file paths, hashes, or backend tool choices.

Formats follow the accepted backend: .tif/.tiff, self-contained .img, restricted
identity .vrt with explicitly uploaded source raster. Always show the wireframe's
format and datatype hint beside the picker, plus the finalized upload size limit.
Additional help: “Shapefiles, geodatabases and ESRI GRID folders are not supported.
Export a single-band GeoTIFF.” Validate the actual raster, not just its extension.
No arbitrary companion paths or automatic URL downloads. For .vrt only,
show “Referenced raster” file input, with one allowed companion; no general
archive manager or asset table. Transport mapping must satisfy the backend's
explicit allowlist. Unsupported external IMG/VRT resources give actionable
format errors, not silent partial reads.

“dNBR values” is a select: “Auto” (default), “Scaled by 1,000” (factor 0.001),
“NBR difference” (factor 1), “Custom scale”. Auto is a valid upload choice;
users need not prepare encoding metadata before submitting a file.
Help: “Auto estimates the scale from the map values.” Custom reveals only
“Multiply values by” and “Add offset”, numeric fields validated server-side.
Presets use offset 0. Auto must examine the valid source-value distribution,
including when scale metadata is absent. Compare the standard encodings (factor
1 or 0.001, offset 0) using robust distribution statistics, not just dtype or
one extreme pixel. Treat explicit encoding metadata as evidence and check for
conflict; do not silently override conflicting metadata or scale twice.

The detection algorithm must define its sample domain, deterministic sampling,
NoData/mask exclusion, quantiles, outlier treatment, minimum evidence and selection
criteria before implementation. Include both source-wide and watershed-overlap
diagnostics so unrelated areas cannot silently dominate an unrepresentative
sample. The distribution-v1 criteria and initial fixture evidence are recorded in
[ADR-0063](../../adrs/ADR-0063-dnbr-auto-scale.md); distribution-based detection
itself is owner-directed. Preserve negative/zero values and never clip source
values to force a candidate fit. Do not infer arbitrary custom factors/offsets.
Pass the selected factor/offset explicitly to the existing normalizer and record
the distribution evidence, detection version and selection method.

Auto may proceed without a confirmation click when evidence supports a standard
encoding. If evidence is ambiguous (for example all-zero or low integer-valued
maps), retain the staged candidate for a bounded retry and show “Could not
determine the dNBR value scale. Choose the scale used by your map.” Users choose
a preset/custom value and retry with the same Upload dNBR button without
retransferring the file. Permit the same correction after a successful Auto
upload, reprocessing the retained source as a new attempt; accepted replacement
marks model results stale. No normalized map becomes accepted until encoding is
resolved. Freeze safe candidate/source identity, expiry and retry authorization
in the transport checkpoint.

No image-date fields or disclosure. Dates are not needed for this upload/run
interaction. Preserve source imagery metadata when available under the existing
backend contract, without asking users to enter dates or making missing dates a
prerequisite. Do not carry dates from a replaced map into a new upload.

Button: **Upload dNBR**. Disabled only without required file/encoding, for read-
only users, during this upload, or when the required project grid is unavailable.
Unrelated missing soils/K/climate must not block dNBR upload. During operation:
“Uploading dNBR…” then “Preparing dNBR…”. Browser transfer completion alone
must not show success; wait for normalized-artifact publication.

After successful preparation, render one two-column table inside the existing
`wc-control__panel-summary` region. Use semantic row headers; no cards, tabs or
separate confirmation step. These are upload details, not the deferred model
report. Example values below are illustrative, not fixture measurements:

| Detail | Example value |
| --- | --- |
| File | wallow_dnbr.tif |
| Format / data type | GeoTIFF / Int16 |
| Prepared cell size | 10 m × 10 m |
| Watershed coverage | 94% |
| Uploaded values | −120 to 850 |
| Applied scale | Divide by 1,000 (Auto — value distribution) |
| Prepared dNBR values | −0.120 to 0.850 |

The filename, format/type and uploaded range describe the original source;
prepared cell size, coverage and prepared range describe the normalized project
map. Ranges exclude NoData/masked/nonfinite cells; prepared range uses valid
watershed cells. Label a custom factor/offset explicitly and distinguish Auto
from a user-selected scale or metadata-based resolution. Use Unitizer for cell
size; dNBR values and scaling are dimensionless. Keep detailed quantiles and
algorithm diagnostics in provenance, not extra user-facing rows.

Persist the table across reloads and escape the original filename as text.
The native file picker shows a new selection, not proof of upload. Retain the
accepted summary during a pending/failed replacement, identifying the candidate
separately. Display the uploaded filename using the shared `ui.text_display`
macro: label **Uploaded dNBR map**, standard `wc-field--display` /
`wc-text-display` classes, and the filename alone in a `<code>` element populated
as text. Match the SBS filename field rather than using an inline prose sentence.
On initial failure show the actionable error without a ready summary.
Show partial coverage as “The dNBR map covers only part of the watershed.
Calculations will use the available dNBR values.” Keep replacement available
through the same picker/button; no separate destructive remove/reset workflow.
On failure retain the previously accepted map and identify the failed attempt.
Example no-overlap message: “The dNBR map has no usable data inside this
watershed. Check the file and its location.” Details may expand in the job log.

## Run action and completion

Render **Design storm rainfall** with the shared `ui.fieldset` macro so its
legend and border use theme colors, as in the Bootstrap control.

The only run option is **Design storm rainfall**: “Project climate” or
“NOAA Atlas 14”. Proposed default: Project climate. NOAA is disabled when its
artifact is unavailable or stale, with “NOAA rainfall estimates are not available for
this project.” Do not silently change a persisted NOAA selection to project
climate; show its unavailable state until the user changes it. Preflight drives
availability in realtime; the server rechecks at submission and execution. This selection
affects design comparisons only. Actual climate mode is retained in outputs;
“Project climate” does not assert all project data came from CLIGEN.

Fixed calculations: project wet events at 15/30/60 minutes,
1/2/5/10-year design storms for those durations, and 50% inverse thresholds.
No duration, recurrence, confidence-target, coefficient, coverage cutoff or
advanced algorithm controls in this first UI. These defaults are recorded in ADR-0063 and the execution checkpoint; report configuration can be added
later under its own contract. About/help may describe fixed calculations.

Button: **Run debris-flow model**. Validate all prerequisites server-side even
if the browser enables it. Missing prerequisite text appears immediately below
the disabled button and points to the relevant existing control. Once prerequisites
are available, one click prepares predictors and rainfall results through RQ.
No separate “build predictors”, “publish”, “refresh manifest” or confirmation
button. Duplicate clicks return/show the active run, not duplicate jobs.

Normal progress: “Waiting to run…”, “Preparing watershed data…”,
“Calculating debris-flow likelihood…”. Use the existing control status/log
pattern with an accessible live status region. No separate toast-only feedback.
On success: “Run complete.” Show completion time and an authorized **Download
model files** link. This is access to generated files, not a report. The download
must be a fixed allowlisted artifact set; no arbitrary path/archive request.
On valid partial output: “Run complete. Some probabilities could not be
calculated.” Follow with a concise reason such as “Soil erodibility data are
missing for part of the watershed.” Preserve downloads and diagnostics; never
show unavailable probabilities as zero. No charts, probability tables, maps,
summary cards or report-template implementation in this package.

Changed inputs: “Inputs changed. Run the model again.” Retain prior output and
its completion time, clearly marked “Previous run”; it must not appear current.
Failure: “The model could not finish. [specific corrective action when known]”.
Preserve previous successful output and offer the same run button after failure.
Technical errors stay in the expandable job log; ordinary messages omit RQ,
NoDb, hashes, stencils, schema versions and filenames of internal artifacts.

## Reload, access and accessibility

Server-rendered/hydrated state is authoritative after reload, including upload
preparation, queued/running jobs, previous success, failure and changed inputs.
Restore the latest attempt's linked job ID using the shared `ui.job_hint`,
separate from the ordinary workflow message. Reattach terminal jobs on reload so
`controlBase` restores failure Details and status/timestamps. Preserve its escaped
HTML layout, including separate status and timeline blocks; flattening HTML to
text concatenates labels. Clear old status/Details before retrying, retain the
accepted map summary, and ignore late responses from an older tracked job.
A unit preference change must not rebuild or mark results stale. Use project
Unitizer for dimensional status/help values; percent coverage and likelihood
retain explicit labels. Show dates/times using existing project conventions.
Read-only access follows existing run authorization: viewing status does not
create state or permit upload/run. Keyboard labels, error associations, focus
and disabled explanations follow existing Pure UI macros and accessibility rules.
Do not introduce a custom interaction widget for standard file/select/buttons.

Before approval, render a static reviewable preview of this exact control in
realistic empty/ready/partial/running/failed/stale states. Owner approval covers
layout, labels and normal messages, not permission for unreviewed UI additions.
Prototype artifacts are non-runtime; do not modify controllers/templates before
the required contract ancestor commit exists.
