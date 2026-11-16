# Culvert per-run stream selection

Status: accepted direction; implementation pending contract checkpoint commit.

## Authority and purpose

Operator decision, 2026-11-16: prefer simpler networks for performance, selecting
finer networks per run when required to retain culvert connections. The supplied
DEM, stream network, watershed polygons, and producer-snapped culvert points
remain authoritative inputs. Do not resample DEMs, re-extract streams, or move
points during production selection.

## Starting pass count

Map mode retains `effective_cellsize = cellsize_m * sqrt(threshold / 100)`;
missing/nonpositive threshold uses 100. Starting counts are:

| Effective resolution | Starting passes |
| --- | ---: |
| <= 1.5 m | 4 |
| > 1.5 through 3 m | 3 |
| > 3 through 6 m | 2 |
| > 6 m | 1 |

These bins give nominal 1/2/4/8/10 m starts of 4/3/2/1/1. They are bounded
performance-first heuristics based on Santee, not universally calibrated values.
The old twofold count target is diagnostic, not a lower-bound requirement:
a simpler connected network is acceptable. The coarse 4 m diagnostic TOPAZ
failure remains unresolved and must not be represented as calibrated success.

Precedence is explicit payload `order_reduction_passes`, then a valid map result
when mode is `map`, then the configured count. Missing/nonpositive cell size
uses the configured count as before; fixed mode uses the configured count. The
chosen count means a maximum pruning level subject to per-run connection preservation.
A zero override selects supplied unpruned streams directly.

## Candidate generation and selection

Generate immutable batch-level binary networks for every pass from the starting
count through one, using the existing short-stream pruning and Strahler process.
Pass zero is the original supplied `streams.tif`, without short-stream pruning.
Every candidate requires its matching junction raster. Retain a versioned batch
manifest identifying pass number, raster paths, grid, and generation policy.
Do not overwrite one candidate while a run is consuming it.

For each Point_ID, examine candidates in descending pass order. A candidate is
eligible only when the containing raster cell of the supplied culvert point is
a valid positive stream cell AND the supplied watershed mask has positive
stream coverage. Do not snap to a nearby channel or accept polygon coverage
alone. Preserve existing point-in-watershed validation and its configured buffer.
The selected network subsequently drives the existing outlet-finding workflow;
no new outlet snapping or outlet-finding algorithm is authorized. Validate the
resolved outlet and generated topology during acceptance testing.

Stop at the first eligible candidate. If pass zero fails, fail that run explicitly
with Point_ID and rejection reasons; never substitute an unrelated network.
Missing candidate rasters, invalid grid alignment, or malformed manifests are
explicit errors, not reasons to silently step down. Normal candidate rejection
is limited to valid-but-insufficient channel coverage/intersection.

## Persistence and compatibility

Additive manifests/selection receipts record policy version, starting/selected
passes, every examined candidate and rejection reason, selected raster identities,
and the supplied point coordinates/grid cell. Publish a receipt only after its
artifacts are valid. Log selected passes and reason; retain existing summary keys.
Use canonical NoDb locking/cache rules if saved controller state changes.

New batch admission writes `stream_selection_policy.json` with version1 before
preparation or child enqueue. This durable intent marker is independent of the
completed candidate manifest. Existing batches without this marker retain their
legacy network-selection behavior; do not silently regenerate retained runs or
change their topology when opened or resumed. A manifest or receipt present with an absent/malformed policy marker is an
integrity error, not legacy. Genuine legacy means no new-policy evidence; cover
this inconsistent-state case in regression and archive/restore tests.
New-policy resumed runs must reuse
or deterministically reproduce the recorded selection with verified artifact
identity. Partial generation is an explicit incomplete-preparation error.
No client payload schema, queue dependency, auth, or runtime identity changes
are needed. The upload boundary adds only this internal policy marker.

## Validation and rationale

Santee at 1 m gives 783 hillslopes/313 channels at four passes for Point_ID1040,
but seven other supplied outlets disappear; all seven polygons then have zero
stream coverage. Three passes retains all39. A descending candidate ladder
retains simplification where possible without forcing small watersheds back to
the densest network unnecessarily. Changing extraction thresholds or resampling
was rejected here because those treatments move drainage relationships.

Validate real rasters for 4->3 and multi-level fallback, direct zero override,
point-miss despite polygon coverage, terminal zero-pass miss, missing artifacts,
legacy replay, and idempotent new-policy resume. Validate each candidate's
junction/network consistency and parsed per-run generated/consumed topology.
Use forest RQ submissions for a large retained outlet and a small fallback case;
unit tests or parent-job completion alone cannot establish acceptance.

## Artifact lifecycle and observability

At batch root, `stream_selection_policy.json` records version and intent;
`stream_candidates.json` records state `preparing`, `ready`, or `failed`, with
candidate paths/hashes and bounded error details. Candidate binaries and junctions
live under `topo/stream_candidates/pass_<N>/`; pass0 references original supplied
streams and their matching junction artifact. Per-run `stream_selection.json`
records `selected` or `failed`, attempted candidates, reasons and verified identities.
These artifacts are visible through existing authorized browse/download surfaces;
no new endpoint or secret-bearing content is introduced.

Write JSON atomically via same-directory temporary file and replace. Publish
`ready` only after every required candidate and junction is readable and validated;
children cannot run against partial preparation. A marker with absent/not-ready
manifest is an explicit incomplete-preparation state, never legacy. Retry under
the existing orchestration/locking rules may rebuild incomplete artifacts before
children start; a ready set referenced by receipts is immutable. Resume verifies
receipt identities and errors on missing or altered candidates instead of selecting
a different topology silently.

Archive/export/restore operations that retain batch/run topology must retain the
policy marker, manifest, candidates, and selection receipts together with resolvable
relative references. Do not advertise standalone run archives as self-contained
unless their referenced topology is included or materialized. Cover retained
artifacts through browse/download and an archive/restore readback test; partial
or failed state must remain visible rather than appearing as a successful run.
