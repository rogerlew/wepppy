# GDAL residual-risk exception decision

## Decision

Roger explicitly accepts the residual risk for the affected installed PyPI GDAL
finding instead of compiling and maintaining a custom GDAL/Rasterio stack. The
accepted advisory aliases are `GHSA-r5m4-5vww-w9f5` and `CVE-2026-8212`. This
decision is limited to the exact GDAL installation reported in each final
candidate image and does not cover Debian GDAL packages, another version, a
different path, another advisory, or an unmatched native-coverage item.

The machine-readable private disposition must bind the final Grype finding key,
image ID, source revision, static lock hash, installed GDAL version and reported
path after fresh evidence collection. It may not be prepared from an earlier
candidate or by weakening the evaluator. The evaluator must reject any stale or
unmatched disposition.

## Exception fields

- **Disposition:** `accepted-risk`
- **Owner and approver:** Roger, WEPPcloud production operator
- **Created:** `2026-11-13T22:16:59Z`
- **Expires:** `2026-12-13T22:16:59Z`
- **Rationale:** compiling a private GDAL toolchain creates disproportionate
  maintenance and scientific compatibility risk; a supported packaged upgrade
  was explicitly deferred.
- **Compensating control:** `F6-RU-01` admits uploaded `.tif/.tiff` only as
  self-contained `GTiff` and `.img` only as self-contained `HFA`, rejects
  mismatched drivers and companions, performs full-band decode before
  publication, and reasserts locked file identity before asynchronous reuse.
- **Evidence:**
  `20261113_raster_upload_contract_decision.md`,
  `20261113_raster_upload_correctness_review.md`,
  `20261113_raster_upload_security_review.md`, and
  `20261113_gdal_qualification.md`.
- **Review trigger:** any new or changed advisory, GDAL/Rasterio version or
  package path, candidate image, source revision, evidence bundle, scanner or
  database, raster admission behavior, Compose configuration, or compensating
  control; renewal also requires fresh review.

## Release boundary

This is the operator authorization needed to create an exact, private
machine-readable exception after final candidate scanning. It is not a blanket
waiver, does not approve an image before its evidence passes, and does not by
itself authorize service interruption or activation. Production readiness still
requires fresh host-bound retained candidates, imported evidence, exact
dispositions, protected approvals, and green deployment preflights.
