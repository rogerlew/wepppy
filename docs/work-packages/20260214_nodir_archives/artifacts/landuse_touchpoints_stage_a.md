# Landuse Touchpoints Stage A (Phase 6)

Scope: reconcile `landuse` mutation/read touchpoints and classify NoDir readiness for archive-form mutation adoption.

| Touchpoint | File | Class | Current Behavior | NoDir Readiness | Notes |
| --- | --- | --- | --- | --- | --- |
| Landuse controller bootstrap (`lc_dir`) | `wepppy/nodb/core/landuse.py` | producer | Constructor no longer eagerly creates `WD/landuse`; root is created only when map assets are actually materialized. | archive-ready | Phase 6 Wave 1 blocker removed. |
| Landuse build pipeline | `wepppy/nodb/core/landuse.py` | producer, FS-boundary | `build()` writes landuse map products and sidecar parquet (`WD/landuse.parquet`). | thaw-required | Archive form requires root thaw/freeze owner boundary. |
| Landuse RQ mutation owner | `wepppy/rq/project_rq.py` (`build_landuse_rq`) | producer | Root mutation now wrapped by `mutate_root(wd, "landuse", ...)`. | archive-ready | Behavior-matrix `materialize(root)+freeze` requirement enforced. |
| Treatments cross-root mutation | `wepppy/rq/project_rq.py` (`build_treatments_rq`) | producer | Multi-root mutation now wrapped by `mutate_roots(wd, ("landuse", "soils"), ...)`. | archive-ready | Lock ordering and post-thaw failure semantics shared across roots. |
| Landuse RQ-engine route (build) | `wepppy/microservices/rq_engine/landuse_routes.py` | producer | Route preflights `nodir_resolve(..., "landuse", view="effective")` and propagates canonical NoDir errors. | archive-ready | Rejects mixed/invalid/transitional states before enqueue. |
| Landuse UserDefined upload/raster stack writes | `wepppy/microservices/rq_engine/landuse_routes.py` | producer, FS-boundary | User-defined map write path now executes inside `mutate_root(..., "landuse", ...)`. | archive-ready | Upload + stacker writes are archive-safe and root-owned. |
| Treatments mod writer (`*.man`) | `wepppy/nodb/mods/treatments/treatments.py` | producer | Writes management files under `WD/landuse`. | thaw-required | Phase 6 ownership moved to `build_treatments_rq` wrapper. |
| Omni clone/copy behavior | `wepppy/nodb/mods/omni/omni.py` | producer, consumer | Handles root-form copy/link semantics across scenarios/contrasts. | archive-ready | Existing root-form awareness retained. |
| Landuse API routes (`landuse_bp`) | `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` | consumer | Controller-mode/report mutation endpoints remain logical-run operations. | thaw-required | Root mutation ownership remains in RQ flows. |
| WEPP management-dir consumers | `wepppy/nodb/core/wepp.py` | consumer, FS-boundary | Uses landuse assets/templates for WEPP run prep. | thaw-required | Consumer boundary unchanged in this phase. |
| Landuse parquet consumers | `wepppy/nodb/duckdb_agents.py`, `wepppy/export/prep_details.py`, `wepppy/export/gpkg_export.py` | consumer | Sidecar-first logical dataset reads (`landuse/landuse.parquet`). | archive-ready | NoDir sidecar mapping already contract-compliant. |
| Browse/files/download surfaces | `wepppy/microservices/browse/*` | consumer | Archive-native list/stat/read; no root thaw/freeze from requests. | archive-ready | Behavior matrix maintained. |

## Stage A Totals

### Counts by Class
- `producer`: 8
- `consumer`: 7
- `FS-boundary`: 4
- `serialized-path hazard`: 0

### Counts by Readiness
- `archive-ready`: 8
- `thaw-required`: 4
- `blocked`: 0

### Stage A Verdict
- `ready`: yes
- Landuse mutation owners and high-risk user-defined write paths are now explicitly routed through shared NoDir mutation orchestration.
