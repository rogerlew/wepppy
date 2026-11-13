# Raster upload format and driver boundary

Status: proposed contract checkpoint; implementation pending.

## Authority and classification

- **Starting implementation revision:** `419fa0b320d83456cbbd6fc7ad3b6119108da015`
- **Operator decision:** Roger Lew directed implementation on 2026-11-13 UTC.
- **Remediation ID:** `F6-RU-01`
- **Classification:** bounded cross-owner security remediation for the confirmed
  shared assumption that a raster filename extension is sufficient before an
  unrestricted GDAL open.
- **Security impact:** high because authenticated users can supply hostile raster
  bytes to native parsers.

## Canonical authority and discrepancy

The primary affected canonical contract is
`docs/schemas/upload-endpoint-contract.md`. It currently records extension
allowlists and route-specific semantic validators, but it does not require the
uploaded bytes to match the extension or restrict the first native open to the
declared driver. Several routes accept VRT even though their ordinary upload
transport cannot safely package and prove referenced files.

Applicable unchanged contracts are `docs/schemas/rq-response-contract.md` and
the failed-mutation/composite-operation requirements in
`docs/schemas/nodb-persistence-concurrency-contract.md`.

The intended behavior is now explicit:

- `.tif` and `.tiff` mean a GeoTIFF opened only by `GTiff`;
- `.img` means a self-contained ERDAS Imagine raster opened only by `HFA`;
- private scratch bytes must open only with the extension-selected driver,
  report that exact driver and no dependent file, and survive a full-band read
  before any route-specific parser, metadata reader, raster stacker, or NoDb
  validator receives the same immutable snapshot;
- general raster upload routes no longer accept VRT; the separately contracted
  postfire dNBR identity-VRT decoder is outside this remediation;
- the uploaded-DEM route accepts both GeoTIFF and self-contained IMG, matching
  the repository's established user-facing raster formats;
- every raster part must pass scratch validation before any part is published or
  controller state changes; validation failure removes request scratch files and
  returns the canonical explicit 400 upload error without enqueueing work.

## Scope

The implementation covers the rq-engine DEM, SBS, HUC-fire SBS, batch SBS,
landuse, treatments, ash, and Omni SBS upload/consume boundaries listed in the
canonical contract. Shared non-ZIP boundary implementation belongs in
`wepppy/microservices/upload_boundary.py`; rq-engine's `upload_helpers.py`
translates boundary errors into the canonical API contract. Routes must stage
and validate every request raster before mutation/publication, then use the
existing `post_save` promotion boundary. Previously stored user raster reuse
must resolve from server-authoritative run state under its approved root, reject
path/symlink escape, and prove unchanged bytes immediately before consumption.

For Omni, client-supplied `sbs_file_path` is never path authority. Reuse resolves
only the server-owned scenario upload beneath that run's `omni/_limbo/{index}`
root; ambiguous, missing, escaped, legacy VRT, or mismatched content requires a
new upload.

Excluded behavior is archive ingestion, GeoJSON, climate files, shape-converter,
trusted generated rasters, the postfire dNBR identity-VRT contract, scientific
value/class rules, reprojection, queue topology, authentication, and deployment.

## Valid-state and input matrix

| Input/state | Valid | Required result |
| --- | --- | --- |
| New `.tif`/`.tiff` containing self-contained GTiff | yes | Restricted open succeeds; existing semantic validation continues |
| New `.img` containing self-contained HFA | yes | Restricted open succeeds; existing semantic validation continues |
| Extension and actual driver differ | no | Explicit 400 rejection; staged file removed; no mutation/enqueue |
| Malformed, empty, truncated, or unsupported raster | no | Explicit 400 rejection; staged file removed; no mutation/enqueue |
| VRT submitted to a general raster upload route | no | Extension rejection before native open |
| Optional upload absent where the route permits reuse | conditional | Validate the persisted raster before its next native consumer |
| Previously stored valid GTiff/HFA | yes | Preserve the established workflow after restricted validation |
| Previously stored VRT or mismatched content | no | Explicit re-upload guidance; never pass it to an unrestricted native open |
| Client attempts to select a persisted pathname | no | Ignore a legacy absolute-path value as a non-authoritative reuse signal and derive the sole candidate from server state; reject traversal, symlink escape, missing, or ambiguous server state |
| Multi-raster request has a valid first file and invalid later file | no | Reject all parts; preserve prior destinations and controller state |

## Compatibility and regression plan

This is intentionally incompatible with new or reused general-purpose VRT
uploads. Roger's direction to implement `.tif`/`.img` content-to-extension and
driver enforcement authorizes removing VRT from the named general routes, which
did not collect a referenced-file set capable of proving a safe VRT graph.
Generated/internal VRT and the postfire dNBR identity-VRT contract remain
unchanged. `.tif`, `.tiff`, and self-contained `.img` remain supported. DEM gains
`.img` support. Existing scientific and dimensional validation remains unchanged
after the new format boundary.

Regression evidence must use real GDAL/rasterio drivers, not a mocked open:

1. Generate small valid GTiff and self-contained HFA fixtures and prove both are
   accepted with exact detected drivers.
2. Rename each valid file to the opposite extension and prove rejection before
   route-specific validation.
3. Create a real companion-dependent HFA (for example `.img` plus `.ige`), omit
   the companion, and prove rejection during a forced band read.
4. Prove malformed TIFF/IMG and VRT inputs fail with cleanup and no mutation.
5. Prove an invalid second Ash/Omni raster leaves no first-file publication or
   controller mutation.
6. Prove persisted reuse rejects absolute paths, traversal, symlink escape,
   client path substitution, byte replacement, legacy VRT, and mismatched bytes.
7. Exercise DEM and representative shared SBS/landuse route boundaries using the
   real validator.
8. Instrument direct GDAL opens touched by the remediation and prove only the
   selected driver is enabled until the exact validated snapshot is published.
9. Run focused microservice tests, frontend controller tests for `.img` DEM
   admission, documentation lint, broad-exception enforcement, and the full
   Python/frontend gates required by F6.

## Rationale

Compiling and maintaining a private GDAL/Rasterio stack is not an acceptable
routine dependency-update burden. Restricting untrusted inputs at the existing
upload boundary is smaller, preserves the documented TIFF/IMG workflows, and
prevents extension spoofing from selecting unrelated GDAL drivers. The control
does not claim the accepted GTiff/HFA parsers are vulnerability-free; the exact
image advisory gate and final deployment review remain required.

## Review gate

Two independent read-only contract reviews approved authority, compatibility,
security containment, and the regression plan after findings were corrected.
Their records are `20261113_raster_upload_correctness_review.md` and
`20261113_raster_upload_security_review.md`. This standalone checkpoint is the
required implementation ancestor. Implementation conformance is pending.
