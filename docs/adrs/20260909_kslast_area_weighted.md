# Area-weighted bedrock conductivity on the project grid

## Status and provenance

Accepted design, 2026-09-09 UTC; not yet implemented. Decision venue: repository task conversation (exact meeting time not recorded). Participants: requesting user and Codex. Decision owner: requesting user. Implementer: executing Codex session. [Canonical contract](../schemas/kslast-map-contract.md); [execution package](../work-packages/20260909_kslast_area_weighted/package.md).

## Change and rationale

Replace nearest raster sampling at one hillslope centroid with the arithmetic mean over all hillslope pixels in aligned run-local `soils/kslast.tif`. Missing area receives configured scalar kslast; no default plus missing area fails explicitly. Keep map nodata visible and audit fallback coverage. A generic Rust kernel owns statistics and finite/nodata handling; WEPPpy owns positive conductivity validation and run persistence. Patch raster_stacker to explicitly initialize uncovered destination pixels as nodata.

The source map can contain several conductivity classes within a hillslope; a single point is not representative. Ignoring missing pixels overstates mapped coverage. Filling the saved raster with the default loses provenance and makes scalar changes harder to audit. No new dependency is needed. Preserve current source units (mm/h), positive-only map rule, and hillslope-level assignment to MOFE OFEs.

## Alternatives and limits

Rejected: centroid fallback, mode/median substitution, averaging only covered area without disclosure, and a kslast-specific Rust API. No arbitrary minimum coverage threshold or upper conductivity cap. Nearest-neighbor warp plus project-grid aggregation is deliberate; exact fractional source-pixel overlap, geographic-cell area weighting, and per-OFE aggregation are separate scope. Existing no-map and developed-soil behavior remain unchanged.

## Validation and rollback

Build/install the actual py312 release, restart local forest Compose with `wctl down` then `wctl up -d`, verify new extension imports in web/workers, then complete the full local seductive-sabra WEPP workflow. Unit-only or prep-only evidence cannot close the package. Preserve external run/artifact and native-library backups before execution. On failure, stop submission, capture RQ/model errors, and restore a compatible source/native pair and saved run state through canonical procedures; never hot-overwrite a mapped shared object. The request authorizes local validation, not production deployment. Both repository branches must be committed and pushed at completion.
