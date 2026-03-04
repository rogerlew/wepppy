# OSM Roads Client with Persistent Server-Side Cache

**Status**: Open (2026-03-04)

## Overview
WEPPpy needs a production-grade OpenStreetMap roads client that can supply road vectors for terrain conditioning workflows without repeated Overpass fetches per run or per user. This package defines and delivers a server-wide persistent cache module with explicit contracts for query inputs, cache behavior, locking, failure semantics, and reproducibility metadata.

The package is designed to support `roads_source="osm"` flows used by terrain preparation and embankment synthesis, while keeping dependency and performance risk low.

## Objectives
- Define a clear concrete WEPPpy module contract for OSM road fetch + cache behavior.
- Implement a persistent server-side cache with deterministic keys and lock-safe population.
- Provide a stable API that returns roads clipped/reprojected to the target project CRS.
- Enforce explicit error contracts and observability for cache hit/miss, stale reuse, and Overpass failures.
- Add tests and docs so agents can implement and maintain the module end-to-end.

## Scope

### Included
- New OSM roads module contract specification (`module_contract.md`).
- Active ExecPlan with milestone-level implementation and validation guidance.
- Server-wide persistent cache design (metadata index + vector payload storage).
- Overpass query interface and response normalization pipeline.
- Integration seam for TerrainProcessor-style consumers (`roads_source="osm"`).
- Tests for keying, cache lifecycle, reprojection, clipping, locking, and error behavior.

### Explicitly Out of Scope
- Frontend map layer changes.
- Replacing existing route auth/session mechanisms.
- General-purpose OSM feature ingestion beyond road vectors.
- Full TerrainProcessor implementation itself (this package focuses on OSM roads module).

## Stakeholders
- **Primary**: WEPPpy terrain delineation maintainers and agents implementing TerrainProcessor Phase 1.
- **Reviewers**: maintainers of `wepppy/topo/*`, `wepppy/nodb/*`, and infrastructure owners of server storage/runtime config.
- **Informed**: users running watershed preprocessing with OSM roads as input.

## Success Criteria
- [ ] Concrete module contract is published and versioned in this package.
- [ ] OSM roads client supports deterministic query keying and persistent cache hit/miss semantics.
- [ ] Cache survives process restarts and is shared across runs/users on the same server.
- [ ] Roads are returned clipped to AOI and reprojected to requested target CRS.
- [ ] Concurrency controls prevent duplicate cache fills for the same key.
- [ ] Multi-tile AOIs use bounded batched Overpass queries (not per-tile query explosion).
- [ ] Expired cache entries are removable via module cleanup/eviction routine.
- [ ] Automated tests pass for cache correctness, reprojection, and error contracts.

## Dependencies

### Prerequisites
- Root guidance in `AGENTS.md` including dependency/performance discipline.
- Terrain-processing direction in `wepppy/topo/wbt/terrain_processor.concept.md` (`OSM Roads Module` section).
- Existing geospatial stack (`pyproj`, `shapely`, `geopandas`, `fiona/ogr` as already used by WEPPpy code paths).
- Deployment expectation: `/wc1` mount persists across production deploys, with cache root override available via env var.

### Blocks
- Production use of `roads_source="osm"` without redundant Overpass requests.
- Reliable multi-user OSM road acquisition for terrain embankment synthesis.

## Related Packages
- **Related**: [20260304_browse_parquet_quicklook_filters](../20260304_browse_parquet_quicklook_filters/package.md)
- **Related**: [20260303_raster_tools_crosswalk_benchmarks](../20260303_raster_tools_crosswalk_benchmarks/package.md)
- **Follow-up**: TerrainProcessor implementation package consuming this module contract.

## Timeline Estimate
- **Expected duration**: 1-2 weeks.
- **Complexity**: High.
- **Risk level**: Medium-High (network reliability, cache correctness, geospatial normalization).

## References
- `wepppy/topo/wbt/terrain_processor.concept.md` - OSM Roads Module requirements and cache intent.
- `docs/standards/dependency-evaluation-standard.md` - dependency and adoption gates.
- `AGENTS.md` - active ExecPlan and implementation guardrails.
- `docs/work-packages/20260304_osm_roads_client_cache/artifacts/osmnx_decision.md` - dependency decision record for not using OSMnx in v1.
- Overpass policy notes (for operational limits) captured in package artifacts during implementation.

## Deliverables
- `module_contract.md` with concrete API/cache contract.
- Active ExecPlan in `prompts/active/`.
- OSMnx dependency decision record in `artifacts/osmnx_decision.md`.
- Implementation PR(s) for OSM roads module + tests.
- Updated docs for consumer usage and runtime configuration.
- Cleanup/eviction policy notes and operational guidance for cache lifecycle.

## Follow-up Work
- Optional secondary cache backend (PostGIS) if file-backed cache proves insufficient at scale.
- Optional warm-cache prefetch for commonly used AOIs.
- Optional support for OSM snapshot pinning by date for strict reproducibility.
