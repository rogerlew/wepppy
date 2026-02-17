# Soils Touchpoints Stage A (Phase 6)

Scope: reconcile `soils` mutation/read touchpoints and classify NoDir readiness for archive-form mutation adoption.

| Touchpoint | File | Class | Current Behavior | NoDir Readiness | Notes |
| --- | --- | --- | --- | --- | --- |
| Soils controller bootstrap (`soils_dir`) | `wepppy/nodb/core/soils.py` | producer | Constructor no longer eagerly creates `WD/soils`; build/clean paths create on demand. | archive-ready | Phase 6 Wave 1 blocker removed. |
| Soils build pipeline | `wepppy/nodb/core/soils.py` | producer, FS-boundary | `build()` writes map artifacts and `.sol` outputs under `WD/soils`; parquet is sidecar (`WD/soils.parquet`). | thaw-required | Archive form must run under root thaw/freeze orchestration. |
| Soils RQ mutation owner | `wepppy/rq/project_rq.py` (`build_soils_rq`) | producer | Root mutation now wrapped by `mutate_root(wd, "soils", ...)`. | archive-ready | Contract-aligned `materialize(root)+freeze` behavior for archive form. |
| Treatments cross-root mutation | `wepppy/rq/project_rq.py` (`build_treatments_rq`) | producer | Multi-root mutation now wrapped by `mutate_roots(wd, ("landuse", "soils"), ...)`. | archive-ready | Deterministic lock order and shared failure semantics. |
| Soils RQ-engine route | `wepppy/microservices/rq_engine/soils_routes.py` | producer | Route now preflights `nodir_resolve(..., "soils", view="effective")` and propagates canonical NoDir errors. | archive-ready | Rejects mixed/invalid/transitional states before enqueue. |
| Soils API routes (mode/report) | `wepppy/weppcloud/routes/nodb_api/soils_bp.py` | consumer | Reads/writes controller settings and reports via run context. | thaw-required | Not a root-thaw owner; depends on producer boundary correctness. |
| WEPP prep soils consumers | `wepppy/nodb/core/wepp.py` | consumer, FS-boundary | Reads `WD/soils/*.sol` for run prep flows. | thaw-required | Covered by existing FS-boundary/materialization contract work. |
| WinWEPP export soils copy | `wepppy/export/export.py` | consumer, FS-boundary | Uses soils directory copy behavior in export pipeline. | thaw-required | Remains a consumer boundary; no route-surface thaw logic added. |
| Soils parquet consumers | `wepppy/nodb/duckdb_agents.py`, `wepppy/export/prep_details.py`, `wepppy/export/gpkg_export.py` | consumer | Sidecar-first parquet reads (`soils/soils.parquet` logical id). | archive-ready | Already compatible with NoDir sidecar mapping. |
| Soils mods writers | `wepppy/nodb/mods/*` (disturbed/baer/rred/treatments/omni) | producer | Root writers run through existing mutation flows and controller APIs. | thaw-required | Root mutation ownership centralized in RQ owners for Phase 6. |
| Soils migrations | `wepppy/tools/migrations/soils.py`, `wepppy/tools/migrations/migrate_soils_parquet.py` | producer | Sidecar normalization and logical catalog updates. | archive-ready | Logical-id behavior unchanged by Phase 6 mutation cutover. |
| Browse/files/download surfaces | `wepppy/microservices/browse/*` | consumer | Native archive listing/stat/read for allowlisted roots. | archive-ready | No thaw/freeze from request-serving code. |

## Stage A Totals

### Counts by Class
- `producer`: 7
- `consumer`: 8
- `FS-boundary`: 4
- `serialized-path hazard`: 0

### Counts by Readiness
- `archive-ready`: 8
- `thaw-required`: 4
- `blocked`: 0

### Stage A Verdict
- `ready`: yes
- Root mutation ownership is explicit (`build_soils_rq`, `build_treatments_rq`) and route preflight now enforces canonical NoDir status/code behavior before enqueue.
