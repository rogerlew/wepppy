# Selected-hillslope landuse modification contract

## Authority and status

The operator requested on 2026-09-11 that clicking **Modify Landuse** regenerate
MOFE management files and include the modified class in the landuse summary.
Implementation conformance is pending. This contract governs the selected-Topaz-ID
`modify-landuse` operation, not the separate class-to-class mapping operation.

## Required outcome

For a built multi-OFE project, apply the requested management class to the selected
hillslopes and their existing OFE assignments. Preserve hillslope IDs, OFE IDs,
segment geometry, and unselected hillslope assignments. Preserve the configured
MOFE buffer rule: a designated buffer segment retains its configured buffer class.
Use the effective management map and existing management parameterization.

Regenerate `landuse/hill_<topaz_id>.mofe.man` from the updated assignments before
returning success. Rebuild management summaries and `landuse/landuse.parquet`
from the resulting OFE assignments so modified classes have their actual area
and coverage and appear on summary reload. Existing single-OFE behavior remains.
This action prepares landuse; it does not run WEPP or refresh simulation results.

Do not rebuild assignments from the original landcover raster in a way that
discards the explicit selection. Repeated identical edits must retain the same
assignments. Existing burn remapping is governed separately by
[the Disturbed MOFE contract](disturbed-mofe-mapping-contract.md); do not reinterpret
an explicitly selected treatment as an instruction to reapply burn severity.

## State, compatibility, and errors

Keep request fields, response shape, NoDb keys, parquet columns, and paths unchanged.
Maintain existing authentication and run access. Follow the
[NoDb persistence contract](nodb-persistence-concurrency-contract.md) and
[RQ response contract](rq-response-contract.md).
Validate selected IDs and the requested management class before mutation.
For single-OFE projects, absent or empty MOFE state remains valid and unused.
For multi-OFE projects, absent, empty, or incomplete OFE assignments cannot establish
a treatment result: return an explicit existing-contract error requiring landuse
to be built first. Malformed assignments and writer failures must not return success.

The input matrix includes one or multiple selected valid IDs, repeated identical
edits, an empty selection under the existing route policy, unknown IDs, and unknown
classes. The runtime-state matrix is:

| State | Required behavior |
| --- | --- |
| Single-OFE; MOFE state absent or empty | Preserve existing single-OFE edit behavior. |
| Built MOFE; complete assignments | Regenerate and summarize the resulting assignments. |
| Supported legacy built MOFE; existing nested ID/class representation | Accept through existing builder normalization; do not migrate schemas or mapping namespaces. |
| MOFE never built, or legacy project without required segment assignments | Explicit build-first error; segment treatment cannot be inferred safely from hillslope dominance. |
| MOFE assignments empty, incomplete, or malformed | Explicit error before mutation; preserve diagnostic evidence. |
| Optional Disturbed controller or SBS absent; SBS present-empty | Apply explicit classes without requiring burn data; no new burn remap. |
| Populated SBS or configured buffer | Preserve explicit treatment and existing buffer precedence. |
| Working regeneration | Existing request remains pending; visible files are not success evidence. |
| Failed regeneration | Return existing error; retain visible partial artifacts and diagnostics. |
| Completed regeneration and reload | Files and OFE-area summary agree with the applied treatment. |
| Archived/restored completed or failed project | Preserve artifact bytes and diagnostics through normal archive paths; restoration does not certify failed output as complete. |

## Artifacts and verification

Reuse the existing landuse builder's visible project layout. Inputs are
`landuse.nodb`, the effective management map, and existing watershed OFE data;
outputs are `landuse/hill_*.mofe.man`, `landuse/landuse.parquet`, and updated
`landuse.nodb`. Diagnostics remain in `landuse.log` and existing error/status paths.
Working and failed artifacts remain browsable; a failed request does not certify
partially regenerated files as complete. Keep these project records in normal
archive/restore paths, with no hidden alternatives or new exclusions.

The synchronous route's error response and existing controller error/status panel
must expose regeneration failure; `landuse.log` must identify the failed attempt.
After failure, users must treat management files as potentially mixed-generation
until a successful retry. Retry the same selection to regenerate from its explicit
assignments; never infer completion from file existence. Verify this failure and
retry behavior with a real writer failure. Validation errors are expected request
errors; malformed required project state and writer failures are exceptional and
use the existing route's canonical error envelope, without new response fields.

Regression evidence must cover populated assignments, missing/empty/malformed
state, invalid selections, buffers, repeated edits, unselected hillslopes,
single-OFE behavior, summary reload, real management-file contents and writer
failure. Verify generated management propagation into WEPP preparation on a
disposable project, plus browser/download and byte-preserving archive restoration.

## Rationale

The upraised-seventeen incident saved thinning class 424 on 434 hillslopes while
all 1,065 OFEs retained forest classes. Updating only the hillslope dictionary
produces a misleading treatment selection and zero treatment area in MOFE summaries.
Regenerating from explicit OFE assignments makes the button's success represent
usable management inputs without changing geometry or model formulas.
