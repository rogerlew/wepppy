# Single User-Defined landuse and soil inputs

Status: intended behavior approved through the operator's 2026-09-25 execution
instruction; independent design reviews approved2026-09-25; implementation conformance pending.
Amendment: SUDI-01. This contract composes Builder, landuse, soil, watershed,
feature activation and WEPP preparation only; it does not advance their unrelated
work packages. See [ADR-0075](../adrs/ADR-0075-single-user-defined-inputs.md).

## Creation policy and compatibility

Builder exposes the unchecked checkbox “Enable single landuse and soils upload”.
`BuilderSelections.single_user_defined_uploads` is a strict JSON boolean, omitted
means false. Review, create and manifest selections serialize it consistently.
The generated `[nodb] single_user_defined_uploads` value is immutable through run
forms and config refresh. Runtime policy reads effective project configuration,
never submitted flags. Existing/unchecked projects retain current behavior.
Only opted-in projects expose `LanduseMode.SingleUserDefined = 5` and
`SoilsMode.SingleUserDefined = 5`, with label “Single User-Defined”. Existing enum
values and aliases are unchanged. Checking the box changes neither selected dataset
nor default input mode. Landuse and soil choices remain independent.

The selected capability graph adds `single-user-defined` to landuse methods and
soil builders, including each selected dataset relation and both single/multiple
OFE representations; default methods remain unchanged. New capability IDs must
not leak into legacy, preset or unchecked authority. Refresh preserves the flag,
source metadata and policy, including graph relations and config congruence.
No existing-project conversion or runtime flag-toggle interface is introduced.

Initial checked-project binary support is `wepp_260803`, the current Builder
default, with both vendored roles identified by their release sidecars (source
commit `f24c957e3633898e0fd4cbbea5ae08c781f29dba`). Checked review/create rejects
other binaries with supported-binary guidance; the stored graph and runtime
selection gates preserve this restriction. Unchecked/legacy binary choices are
unchanged. Additional binaries require equivalent native-reader certification,
not name/date inference. Validate that each prepared hillslope has at most32
OFEs (this hillslope role's mxplan); report unsupported topology before execution
without silently merging/truncating OFEs. Preserve supported non-buffer geometry.

Checked projects exclude `disturbed`, SBS upload/removal/uniform severity,
`treatments`, `omni`, `omni_contrasts`, `path_ce`, `debris_flow`, `rusle`,
`postfire_debris_flow`, and fire/revegetation parameterization. Dependency closure
must be checked before any module mutation, backup restoration or controller
initialization. Menus, sections, reports, direct APIs and worker execution enforce
this policy even when neither input currently uses upload. Compatible RAP analysis,
Ash, Geneva and other independent modifiers remain available. Legacy BAER
alternatives and ordinary Disturbed projects retain their existing rules.

Resolved `watershed.mofe_buffer` is false. Hide or disable buffer geometry and
buffer-management controls with an explanation. Reject requests enabling buffers
before mutation/enqueue; reject inconsistent saved enabled-buffer state before
build/preparation. Do not silently change topology. Other multi-OFE remains enabled.
No excluded controller or buffer can be restored by changing either input mode.

## Upload interface and validation

Use existing build-landuse/build-soils endpoints, existing run authorization,
session-token/CSRF transport and RQ jobs. Multipart fields are
`input_upload_single_landuse` and `input_upload_single_soil`. Mode fields remain
`landuse_mode` and `soil_mode` (existing `mode` aliases retain their rules).
An upload is accepted only for its selected mode 5 and opted-in project. An empty
chooser reuses a valid accepted source; never-used mode 5 requires an upload.
Multiple files or unexpected single-source fields are validation errors, not
silent first-file selection. Existing form and JSON requests remain supported
when not uploading. Validation precedes changes to mode or other submitted settings.

Before generic payload parsing, multipart requests use bounded streaming parsing
without request.json/body buffering. At most one file, 64 scalar fields, 16KiB
per scalar field, and 70-byte boundary are accepted. Bound aggregate wire bytes
to501MiB for landuse (preserving the existing500MiB raster upload) and6MiB for
soil. Single-source file parts are capped at5MiB incrementally by field name,
regardless of part order; existing raster file retains its500MiB limit. Reject
unknown file fields and duplicate single-source fields, including file/scalar
collisions. Enforce counted-stream limits with absent or false Content-Length,
close partial spools on success/failure/disconnect, and bound part headers to16KiB.
Enforce file limits inside multipart part-data callbacks, not only UploadFile.read
or Starlette max_part_size. The UI omits inactive and empty file inputs from
FormData so normal submissions contain at most one actual file; reuse of an
accepted source is a file-free request.
Existing non-upload JSON/form compatibility remains unchanged; the new mode
cannot be selected through an unbounded alternate file transport.

Allow plain-text `.man`/`.MAN` and `.sol`/`.SOL` extensions case-insensitively.
Names are display-only basenames, at most 255 UTF-8 bytes, with no control
characters; reject path components. HTML displays are escaped text in `<code>`.
MIME is not authority. No shell, eval, deserialization or referenced-file loading
is permitted. Maximum source size is 5 MiB per file (existing management-upload
precedent); enforce a bounded read before decoding. Reject empty, NUL/binary or
invalid UTF-8 input; accept UTF-8 BOM and CRLF. Maximum 100,000 physical lines,
16,384 bytes per line, and 64 characters per numeric token bound parsing work.
Validation must use the exact bytes later published.

Supported formats are management 98.4 and soils 2006, 2006.2, 7778, and 9002.
Soil-format amendment SUDI-02 is operator-approved; implementation conformance
is pending until its native artifact acceptance passes. Reject management
2016.3: the pinned native reader ignores modern rcc/usinrco/usrilco fields even
though the Python parser supports them. Future expansion requires native semantic
preservation evidence, not merely parsing or successful WEPP execution. Each source
must contain exactly one OFE. Require finite numbers, complete structural
consumption (comments/whitespace excepted), valid section/reference/count bounds,
and supported parser/writer content; parser success alone is insufficient.
Reject unsupported versions/content with actionable format guidance. Management
must be compatible with owned management summaries and synthesis; initial
conditions and yearly scenarios use supported cropland-format landuse 1 records.
Do not infer eligibility from description words or apply disturbed classes.
Management rotations/scenarios/section counts must be positively bounded before
count-driven allocation and validated against actual available records; source
simulation/rotation years are limited to 1–1000. Admission caps are 20 plant
scenarios (owned rotation-stack limit), 32 yearly scenarios (owned MOFE limit),
30 surface/tillage sequences, and 32 each for initial-condition, operation, contour
and drainage scenarios. Event caps are 20 tillage operations per sequence, 10 grazing
cycles, 25 cuttings and 6 crops per year. Validate source and synthesized output
separately against selected-binary limits; deduplicate repeated scenarios before
checking combined counts. Boundary fixtures must prove accepted maxima and
rejected maxima+1 rather than assuming a universal 32-scenario limit.

Checked projects use native contour and drainage section references at admission,
summary reload, synthesis, and final preparation. Legacy parser defaults remain
unchanged. This avoids accepting a valid source that later resolves against the
wrong scenario table. No negative references or unresolved
cross-section indexes are permitted; mandatory references cannot be zero and
scenario names must be unique within a section. Explicit zero-count optional sections remain
valid where the owned format permits them.

All soil versions require one OFE, `ksflag` 0 or 1, 1–10 layers,
increasing positive cumulative depths, nonnegative erodibility/shear values,
surface fractions in [0,1], nonnegative CEC, percentages in [0,100], and sand+clay <=100.
Versions 2006 and 2006.2 require exactly nine soil-header fields including explicit
nonnegative `avke`, six fields per layer (depth, sand, clay, organic matter, CEC,
rock), and a three-field restrictive record (flag, anisotropy, conductivity).
The pinned native reader consumes `avke` for both versions; eight-field 2006.2
headers are rejected rather than guessing the missing value.

Versions 7778 and 9002 require eight soil-header fields and eleven base layer
fields, including positive density, nonnegative conductivity/anisotropy,
0 <= wilting point <= field capacity <= 1, and nonnegative CEC.
Version 9002 additionally requires its five-field adjustment header (flag 0/1,
quoted landuse and texture labels, positive conductivity factor and recovery),
and seven appended layer values: residual/saturated water fractions satisfying
0 <= residual < saturated <= 1, positive alpha, exponent n > 1, positive
conductivity, and 0 < wilting point < field capacity <= 1. Its supplied native
adjustment flag/parameters remain active as authored; WEPPcloud adds no Disturbed
parameterization and does not infer a class from those labels.
Versions 7778 and 9002 have a three-field restrictive record (flag, bedrock
thickness, conductivity). Restrictive flags are 0/1, remaining values nonnegative.

Text fields must have unambiguous native list-directed token syntax: quoted
labels without embedded quotes/backslashes, or single unquoted labels without
native separators/control punctuation. Reject Python-only quoting/escape syntax.
Derived soil copies remove standalone comments and blank lines (retaining the
required free-text comment record); immutable accepted source bytes retain them.
This prevents comments between records from disrupting native reads that do not
skip comments. Prepared files put modifier provenance comments before the
required free-text comment record, where the native reader skips comments.
Reject missing/extra fields, four-field restrictive records, trailing content,
non-finite or nonrepresentable values and inputs invoking silent numeric repair.
Preserve source version, `avke`, `ksflag`, explicit restrictive values and all
9002 hydraulic values through synthesis and preparation, except fields changed by
explicit compatible modifiers. Do not estimate missing values, convert versions,
or recalculate uploaded 9002 values with Rosetta. Native calculations inherent
to the chosen file format remain native behavior. Use an explicit upload-only
preservation path; ordinary catalog/Disturbed serialization stays unchanged.
For preserved uploads, explicit kslast overrides apply even when the 9002 label
contains "developed"; labels do not select WEPPcloud modifier policy. Depth
clipping at an existing horizon ends there without adding a duplicate depth.
Existing reporting/management bulk-density derivation from older soil formats
remains unchanged; it must not convert or populate the generated soil file.
Metadata `version` records the actual admitted version as a canonical string;
existing 7778 metadata remains valid. Format bounds are admission/resource limits,
not scientific defaults.

## Source state, publication and recovery

Optional controller `_single_user_defined_source` metadata contains `filename`,
`sha256`, `size_bytes`, `version` and `relative_path`, plus optional
`previous_relative_path` for generation retention. Absent metadata is the
legacy/never-used state. Publish immutable hash-named files under visible
`landuse/single-user-defined/<sha256>.man` or
`soils/single-user-defined/<sha256>.sol`; use summary key `single-user-defined`.
Keep generated management/soil filenames distinct. Expose accepted name and source
through normal run browse/download/archive paths; raw source bytes never receive
cover/soil modifiers. Clean/rebuild/mode switching preserves accepted inputs.

Use canonical NoDir materialization and scoped mutation for legitimate projected
module roots. Reject child symlinks, traversal and non-regular files; anchor
operations to the authorized materialized module directory. Fresh directories
must be created normally rather than rejected as corrupt. Staging uses exclusively
created temporary files within that boundary, then atomic publication; do not
follow attacker-selected names. Validate existing immutable source hashes before
reuse. A malformed/missing populated source is an explicit repair/re-upload error,
never a silent database fallback.

Publication and metadata use canonical NoDb locking/fresh hydration/cache rules.
Serialize source acceptance and build access using the module lock and existing
run submission coordination: a build consumes one source generation, and active
conflicts return 409. Idle checks include normal build/descendant receipts, the
archive/restore receipt, and the source fork receipt. Checked archive/restore
admission checks source work under the shared lifecycle lease; checked forks
lease source and destination in run-id order through receipt/enqueue publication.
This prevents a copied or restored project from racing accepted-source publication.
Immutable previous generations survive failed metadata
publication; remove an unreferenced candidate on failure. After successful
acceptance retain current and immediately previous accepted generation, prune only
unreferenced older generations when no build can consume them. Do not retain
rejected hostile bytes. Temporary files are cleaned on expected failure; interrupted
staging is identifiable for normal bounded cleanup. Disk failure preserves the
previous active source. Enqueue failure after acceptance leaves the accepted source
visible/reusable and returns an explicit submission error; retry does not require
re-upload. Build failure retains source and normal job diagnostics, and cannot
claim completed outputs. No queue topology changes are introduced.

## Generated inputs and modifiers

On each mode5 build, assign the chosen source to every hillslope and every actual
non-buffer OFE. Subsequent explicit selected-hillslope class changes and global
class mappings retain existing behavior, including summary and combined-file
regeneration; these user edits may replace individual assignments. They do not
activate Disturbed/Treatments or modify the accepted source. Rebuilding mode5
restores uniform source assignments. Guidance distinguishes initial replication
from later explicit modifications; no new restriction on compatible modifiers.
Replicate management rotations and soil profiles with owned synthesis utilities;
match slope, management and soil OFE counts/order. Ordinary-soil plus uploaded
landuse, uploaded-soil plus ordinary-landuse, both and neither are supported in
opted-in projects, including non-disturbed MOFE soil assembly. Dataset/locale
branches must not override selected upload modes. Soil saturation, kslast/depth
and compatible management cover overrides continue on generated copies under
their existing contracts. Preserve raw accepted bytes and modifier provenance.
Summary rebuilds, edits and configured defaults must regenerate combined files
as required by the MOFE management contract. Do not enable Disturbed from uploaded
descriptions, mappings, retained controllers or missing generated state.

## UI, state and errors

Use Pure `file_upload` and `text_display` macros with labels “Current landuse file”
and “Current soil file”, matching the SBS label/display/code hierarchy. Guidance
states versions/extensions, one-OFE source, replication across all hillslopes and
OFEs, no disturbed parameterization, and excluded buffer/features. Show accepted
filename after reload, successful upload and failed replacement; never pretend to
rehydrate the native file chooser. Read-only views display but cannot mutate.
Working/failed/completed states use existing request/RQ status and errors.

| Valid or hostile state | Outcome |
| --- | --- |
| Fresh opted-in, ordinary modes, absent optional source | Ordinary build, no Disturbed/buffers; source UI empty |
| Fresh opted-in, mode 5, valid first file | Create directory/source/metadata and build |
| Mode 5, no file and no accepted metadata | 400 `single_input_required`, field guidance |
| Populated valid source, chooser empty | Reuse and display accepted source |
| Mode switch away/back; rebuild; refresh; clone/archive/restore | Retain independent sources and policy |
| Invalid bytes/type/count/semantics/name | 400 `invalid_single_input`; preserve prior state, no enqueue |
| Oversize input | 413 `single_input_too_large`; preserve prior state |
| Populated missing/hash-mismatched/nonregular source | 409 `single_input_unavailable`; re-upload guidance |
| Concurrent mutation/active build | 409 `job_active`; retry guidance, no state loss |
| Excluded feature/SBS/buffer or mode5 without opt-in | 400 `unsupported_capability` before mutation/enqueue |
| Malformed policy or inconsistent saved buffer/modules | Explicit conflict before build, no controller restoration |
| Accepted upload then enqueue failure | Existing canonical 5xx submission error; source retained |
| Valid legacy/unchecked | Unchanged source modes/Disturbed/BAER/buffers; no new upload capability |

Expected absence creates/no-ops as specified; malformed populated state fails.
Errors use the canonical RQ envelope and bounded diagnostics without uploaded
contents, internal paths or parser tracebacks. Auth errors retain existing codes.

## Acceptance and rollback

Direct unmocked tests must cover parser, filesystem, NoDb publication and all four
input combinations. Read generated module files and consumed `wepp/runs/*` inputs
for all hillslopes/OFE counts, repeated builds and modifier propagation. Compare
source hashes before/after; inspect real browse/download/archive restore and
fresh WEPP execution under representative service identities/mounts/umask.
Check unchecked/legacy control projects and valid empty/projected-root states.
Security review proves containment and noninterference; separate correctness review
proves user outcomes. Deployment remains separate. Reverting code does not migrate
opted-in projects; retain their source/config archives and restore compatible code
before processing them. Do not silently reinterpret mode5 as an older mode.

User, operator, and developer usage guidance: [Single User-Defined inputs](../dev-notes/single-user-defined-inputs.md).
