# ADR-0065: Require native SBS raster processing

## Status and provenance

Accepted by project operator on 2026-09-10 in this development conversation
(America/Los_Angeles). Participants: operator and Codex; implementer: Codex.
Owner instruction: “remove the python fallback. i don't want the fast rust path
to break and go unnoticed. it's also annoying to maintain updates in both.”

## Decision

Require existing wepppyo3 SBS native raster operations. Before: missing/broken
native helpers could silently select Python raster implementations. After:
fail explicitly using existing route error contracts. Preserve numerical and
NoData behavior; no classification recalibration. Remove duplicate fallback
code, retaining scalar summary/custom-color-map helpers and GDAL display exports.

## Rationale and alternatives

Wallow four-class export took 55.55 seconds in Python and 0.35 seconds using Rust
with complete NoData masking. Keeping a fallback or merely logging it conceals
native installation defects and duplicates maintenance. Increasing proxy timeouts
does not fix the accidental slow path.

## Risk, compatibility and rollback

Installations missing native APIs will now fail explicitly instead of continuing
slowly. Validate actual installed native APIs and output parity before release.
Restore the known working native installation if it fails; do not silently
restore a Python fallback. Existing public outputs/classes and upload payloads
remain stable. See [package](../work-packages/20260910_sbs_native_upload/package.md)
and [raster contract](../schemas/sbs-raster-contract.md).
