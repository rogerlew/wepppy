# Peridot centroid coordinate projection

## Status

Accepted, 2026-09-09 UTC.

## Decision provenance

Decision venue: this repository task conversation, 2026-09-09 UTC (exact meeting time not recorded). Participants: requesting user and Codex. Decision owner: requesting user. Implementer: Codex.

## Context and change

Peridot approximated longitude and latitude using two opposite raster corners. On seductive-sabra that displaces sampling coordinates by hundreds of meters and changes bedrock conductivity classes. Export each integer pixel centroid through all six raster affine coefficients and then the source CRS to WGS84 using existing PROJ. Preserve the existing pixel-corner convention (no new half-cell offset), coordinate column names/types, IDs, and parameter maps. Initialize one transformer per metadata writer and report invalid CRS/conversion as explicit errors.

## Rationale and alternatives

Pointwise projection restores spatial correctness. A different pure Rust dependency is unnecessary because PROJ is already linked. Retaining the approximation or changing conductivity classes hides the cause. Pixel-center shifts, sampler rounding changes, and area aggregation are separate decisions and are not included.

## Evidence

See ../work-packages/20260909_peridot_centroid_projection/package.md and its validation artifacts. Peridot docs/contracts/watershed-output-contract.md is the canonical centroid contract.

## Risk and rollback

Corrected coordinates may change all location-based downstream parameterization, not only kslast. Existing runs are not automatically rewritten. Regenerate affected metadata and dependent inputs through normal authorized workflows; keep prior run outputs for comparison. Roll back the source/binary commits if projection or schema parity fails. No model default or raster class changes.
