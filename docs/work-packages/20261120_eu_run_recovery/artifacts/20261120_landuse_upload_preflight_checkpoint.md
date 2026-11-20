# Uploaded land-use raster compatibility draft

Starting implementation `af514e39c`. The operator requested that the
incompatible raster and management-map failures be corrected and that the
original workflow be replayed on forest. The controlled forest fixture
used a retained CORINE raster as the submitted data with the plain ESDAC
selection. It confirmed worker failure and a healthy retry page. That result
exercises the known mismatch. The uploaded original `LandCover25m.tif` is
still unavailable.

The [upload compatibility contract](../../../schemas/european-landuse-mapping-contract.md#uploaded-raster-compatibility)
defines the proposed correction. Currently the route sets the mapping and
writes the active raw and aligned rasters before RQ admission, then validates
only the table's ability to load. Normal non-single-input EU admission does
not use the single-input serialization guard. The build uses a separate
per-OFE assignment function in MOFE, and Disturbed derives all nine required
destinations from every row even without an SBS map. Reuse those actual
classification and lookup boundaries during preflight and bind admitted
inputs to the queued job. The first invalid build leaves a retryable empty
project. Rejected replacements preserve the previous build's accepted files.
Standalone browser mode and dataset selections persist independently.

Required controls include an unused row missing `DisturbedClass`, a table
missing one severity with no SBS, a code dominant only in one OFE, readback
from a valid uploaded CORINE raster, exact raw and aligned file identity,
a near-simultaneous same-name attempt, a custom map edit before worker
publication, and a gridded transition back to CORINE. Confirm absent,
legacy, unsupported, malformed and hostile inputs. Keep the normal
authenticated batch selection and existing worker argument compatibility.

## Reviewed boundaries

Preserve independently persisted selections from before request entry. Prepare
the private clipped candidate after confirming ordinary upload authorization
and active-job eligibility. Publish through the worker only after the
tracked admission and dependency checks. Use ordered functional mapping
identity, including custom record order, and exact current raw/aligned inputs.
A definite admission failure must preserve prior state. An ambiguous
dispatch retains private evidence and permits only the current tracked
job to progress once authority can be verified. No directory or raster
symlink is trusted solely because its filename matches.

A retained source must pass the same checks as a new source. A valid MOFE
segment set and complete model units are prerequisites to the final check.
Validate an effective persisted buffer even when absent from the request.
Exercise an existing VRT-to-upload transition, a watershed or OFE change,
and a same-number upload-to-upload schema change using the real assignment,
Disturbed and native preparation paths. Include a retained-source retry and
a no-delineation batch admission. Validate canonical route JSON and rendered
Landuse feedback, prior files and timestamps under concurrency, and normal
archive/fork behavior without activating superseded attempts.

The operator requested actionable upload failure correction and preservation
of the European run workflow. This draft chooses private staging and named
worker receipts to apply that request with the existing upload authorization
and queue contracts. It changes neither accepted user inputs nor provider
class numbering. No implementation authority is claimed before review and
the standalone contract commit.

## Independent review disposition

The first reviewer cleared the revised contract and identified the direct
`BatchRunner` caller of `Landuse.build()` as required coverage. The second
cleared the earlier findings and required authoritative expected unit IDs
and the protected watershed read lifetime through consumption. Both are
explicit in the amended contract. The raster upload, RQ state and response
contracts cross-reference the slice. Existing authentication, route access,
format restrictions, and selected-input authority apply. Test imprecise,
malformed and symlinked paths through the established boundary.

Implement and validate table checks first, including normal UI feedback for
plain ESDAC in a Disturbed project. Then add the aligned-raster and admitted
worker evidence path. A table rejection alone is partial conformance.
