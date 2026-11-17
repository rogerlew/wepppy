# Culvert per-run stream selection

Status: amended 2026-11-17 by operator direction; implemented locally; production deployment pending.

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

For new admissions with `selection_basis: original_outlet_v1`, resolve each
watershed's modeled outlet BEFORE any short-stream or Strahler pruning. Use the
existing native WBT FindOutlet with the supplied original streams, D8 pointer,
and watershed polygon raster mask. Supplied culvert coordinates remain road-constrained
input locations and may be off-stream; do not move them or use nearest-channel
snapping. Persist original input identities and a per-Point_ID resolved outlet
(cell-center coordinates, CRS and global grid cell), separately from the supplied
point. A valid network with no resolvable outlet records an explicit per-run failure;
missing/invalid shared inputs fail preparation. Never seed a substitute stream for
this policy. Preserve existing point-in-watershed validation and configured buffer.

Examine pruning candidates in descending pass order. A candidate qualifies only
if it retains the resolved original outlet cell as a positive stream cell AND has
stream coverage in the supplied watershed mask. Use that same fixed outlet during
run delineation, translating global coordinates to cropped run grid indices; do
not rerun outlet finding on the pruned network. Validate the installed outlet and
consumed/generated topology. Preserve the existing single-cell mask inclusion
when FindOutlet resolves just downstream of the supplied polygon (incident1751);
this includes the already-resolved outlet without seeding or moving streams.
Bind the original outlet artifact hash into the candidate manifest and verify it
on selection/resume, including when input hashes have not changed. This separates road location from hydrologic outlet,
as described by the integration developer guide's Outlet Finding Algorithm.

Stop at the first eligible candidate. If pass zero fails, fail that run explicitly
with Point_ID and rejection reasons; never substitute an unrelated network.
Missing candidate rasters, invalid grid alignment, or malformed manifests are
explicit errors, not reasons to silently step down. Normal candidate rejection
is limited to valid-but-insufficient channel coverage/intersection.

## Persistence and compatibility

Additive manifests/selection receipts record policy version, starting/selected
passes, every examined candidate and rejection reason, selected raster identities,
and the supplied point coordinates/grid cell, plus the resolved outlet used for selection. Publish a receipt only after its
artifacts are valid. Log selected passes and reason; retain existing summary keys.
Use canonical NoDb locking/cache rules if saved controller state changes.

New batch admission writes `stream_selection_policy.json` with version1 and `selection_basis: original_outlet_v1` before
preparation or child enqueue. This durable intent marker is independent of the
completed candidate manifest. Existing batches without this marker retain their
legacy network-selection behavior; do not silently regenerate retained runs or
change their topology when opened or resumed. A manifest or receipt present with an absent/malformed policy marker is an
integrity error, not legacy. Genuine legacy means no new-policy evidence; cover
this inconsistent-state case in regression and archive/restore tests.
Retained version-1 policies without selection_basis retain their supplied-point
intersection semantics; never reinterpret their receipts. Unknown bases fail
explicitly. A fresh submission is required to apply the correction to an old batch.
The new basis requires `original_outlets.json`, with atomic preparing/ready/failed
state, input hashes (DEM, pointer, original streams, points and watersheds), and
per-ID resolved/failed records. Generate it before pruning; ready records are
immutable and must match the inputs on resume. Include it in reserved upload
artifacts, browse/download and skeleton/archive retention. Missing or altered
records cannot silently fall back to supplied-point behavior.

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
off-stream supplied points with valid original outlets, terminal unresolved outlet, missing artifacts,
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
policy marker, original outlet records, manifest, candidates, and selection receipts together with resolvable
relative references. Do not advertise standalone run archives as self-contained
unless their referenced topology is included or materialized. Cover retained
artifacts through browse/download and an archive/restore readback test; partial
or failed state must remain visible rather than appearing as a successful run.
