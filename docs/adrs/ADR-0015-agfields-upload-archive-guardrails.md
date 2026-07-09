# ADR: AgFields Backend Readiness and Upload Guardrails

Status: Accepted  
Date: 2026-07-09

## Context

The AgFields backend-readiness package adds two authenticated rq-engine uploads and server-derived stage gating. Both uploads reach run-scoped filesystem and parser boundaries. The state snapshot must also decide which climate modes satisfy observed-year scheduling and how to classify historical sub-field/WEPP artifacts that lack new provenance signatures. Repository policy requires an ADR for the upload limits, readiness classification, and conservative historical fallback.

## Decision

Use existing WEPPcloud upload precedents rather than introduce AgFields-specific scaling assumptions. Boundary uploads accept `.geojson` and `.json` through the shared non-ZIP upload helper with a 10 MB file-size limit. Plant archives use the shared ZIP validator with a 100 MB compressed limit, 600 MB uncompressed limit, 200-member limit, and `.man`-only member policy. Archive path, encryption, compression-method, name-length, and depth checks remain owned by `validate_and_extract_zip_archive()`.

Observed-climate readiness requires integer start/end bounds with `end_year >= start_year` and a mode in `Observed`, `ObservedPRISM`, `ObservedDb`, `PRISM`, `EOBS`, `AGDC`, `GridMetPRISM`, or `DepNexrad`. Watershed readiness requires `dem/wbt/flovec.tif`; parent-WEPP readiness requires both `p<wepp_id>.sol` and `.cli` for every current sub-field parent. Historical sub-fields/runs without the new source signatures are reported stale until rebuilt.

Queue submission uses a 30-second run-scoped Redis submit lock and rejects enqueue while any AgFields build, plant, or WEPP job is queued/started/deferred/scheduled. The lock closes concurrent submission races; the active-job check prevents overlapping mutable workers after the short submit lock is released. Synchronous boundary/schema/mapping mutations, plant-file delete, and artifact clear also return HTTP 409 while a job is active.

The canonical rq-engine OpenAPI size budget increases from 118,500 to 130,000 bytes for the 13 new internal AgFields operations. The measured schema is 129,217 bytes. These routes remain outside the frozen 97-route agent inventory until the successor UI package promotes AgFields from `internal` maturity and explicitly classifies that surface.

## Decision Provenance

Decision Venue: AgFields backend-readiness work-package execution session, 2026-07-09 15:20 PDT  
Participants Present: WEPPpy requesting maintainer, Codex  
Decision Owner(s): WEPPpy maintainers through the repository upload contract and parameterization policy  
Implementer(s): Codex

## Change Summary

Previously, AgFields had no HTTP upload surface and therefore no route-level caps, server-side readiness/staleness contract, async single-flight guard, or OpenAPI allocation. The new boundary endpoint uses 10 MB and the new plant endpoint uses 100 MB compressed, 600 MB uncompressed, and 200 members. Readiness uses the explicit historical modes and artifact checks above. Missing provenance defaults to stale rather than current. A 30-second submit lock plus live RQ status check rejects overlapping AgFields jobs. The OpenAPI ceiling changes from 118,500 to 130,000 bytes. These choices do not change WEPP formulas, units, or scientific results for accepted/current data.

## Rationale

Ten megabytes is already the canonical run-scoped GeoJSON limit for Batch Runner and Roads. The shared ZIP defaults provide decompression-bomb and member-count protection while accommodating plant databases that contain many text management files. Reusing these values keeps operator expectations and security behavior consistent across services. Explicit mode/artifact checks keep UI gating honest, and treating unprovable historical provenance as stale avoids silently running against mismatched boundaries or mappings.

## Alternatives Considered

1. No explicit limits - rejected because it permits unbounded request memory, scratch use, and decompression expansion.
2. The 500 MB raster-upload limit - rejected because text GeoJSON and management archives do not need the raster ingestion allowance.
3. A new configurable AgFields limit - rejected for v1 because there is no workload evidence that existing canonical limits are insufficient; configuration would add unsupported policy surface.
4. Treat any climate with year bounds as observed - rejected because future/user-defined modes can also carry years but do not satisfy the AgFields observed-schedule contract.
5. Treat historical artifacts without signatures as current - rejected because the backend cannot prove which boundary/schema/mapping produced them.
6. Hide AgFields operations from OpenAPI - rejected because the implemented HTTP contract should remain discoverable even before feature-maturity promotion.

## Consequences

Oversize inputs receive HTTP 413 before controller/RQ processing. ZIPs containing non-`.man` files, unsafe paths, encrypted members, unsupported compression, or excess expansion/member counts receive a specific HTTP 400/413 error. A user with a legitimate larger archive must split or reduce it before upload. Historical AgFields projects show stale downstream stages until the user confirms schema and rebuilds; this is intentional and does not delete historical files.

## Evidence

- `docs/work-packages/20260709_ag_fields_backend_readiness/`
- `docs/schemas/upload-endpoint-contract.md`
- `tests/microservices/test_rq_engine_ag_fields_routes.py`

## Risk and Rollback Notes

The primary risks are rejecting an unusually large legitimate farm dataset or omitting a historical observed climate mode. Repeated legitimate 413 responses or a supported observed-mode run blocked despite valid integer bounds are review signals. Changing a limit, readiness mode, or historical fallback requires updating code, contracts, tests, and this ADR in one change. Removing upload limits or defaulting unproven artifacts to current are not acceptable rollbacks.

## Implementation Notes

Boundary content is validated into staged GeoJSON/Parquet artifacts before canonical replacement. Plant archives are validated in scratch space, stored under a unique server-generated filename, and removed by the worker after terminal success or failure.
