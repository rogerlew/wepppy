# Climate Touchpoints Stage A (Phase 6)

Scope: reconcile `climate` mutation/read touchpoints and classify NoDir readiness for archive-form mutation adoption.

| Touchpoint | File | Class | Current Behavior | NoDir Readiness | Notes |
| --- | --- | --- | --- | --- | --- |
| Climate controller bootstrap (`cli_dir`) | `wepppy/nodb/core/climate.py` | producer | Constructor no longer eagerly creates `WD/climate`; writes create path on demand. | archive-ready | Phase 6 Wave 1 blocker removed. |
| Climate build pipeline | `wepppy/nodb/core/climate.py` | producer, FS-boundary | `build()` writes `.cli`, reports, and climate-sidecar datasets. | thaw-required | Archive form must run under root thaw/freeze ownership. |
| Climate RQ mutation owner | `wepppy/rq/project_rq.py` (`build_climate_rq`) | producer | Root mutation now wrapped by `mutate_root(wd, "climate", ...)`. | archive-ready | Behavior-matrix `materialize(root)+freeze` requirement enforced. |
| Upload CLI RQ mutation owner | `wepppy/rq/project_rq.py` (`upload_cli_rq`) | producer | CLI assignment now wrapped by `mutate_root(wd, "climate", ...)`. | archive-ready | Upload mutation path now archive-safe. |
| Climate RQ-engine build route | `wepppy/microservices/rq_engine/climate_routes.py` | producer | Route now preflights `nodir_resolve(..., "climate", view="effective")` and propagates canonical NoDir errors. | archive-ready | Rejects mixed/invalid/transitional states before enqueue. |
| Upload CLI route write path | `wepppy/microservices/rq_engine/upload_climate_routes.py` | producer, FS-boundary | Uploaded file save now executes inside `mutate_root(..., "climate", ...)`. | archive-ready | Archive-form upload now follows thaw/modify/freeze contract. |
| Climate API routes/reporting | `wepppy/weppcloud/routes/nodb_api/climate_bp.py` | consumer | Read/report operations via controller data and climate report files. | thaw-required | Not a root mutation owner; relies on producer boundaries. |
| WEPP climate prep consumers | `wepppy/nodb/core/wepp.py` | consumer, FS-boundary | Copies/uses climate files for WEPP run prep. | thaw-required | FS-boundary consumer behavior unchanged in this phase. |
| Climate interchange helpers | `wepppy/wepp/interchange/_utils.py`, `wepppy/wepp/interchange/_rust_interchange.py` | consumer, FS-boundary | Reads climate assets/sidecars for interchange and analysis. | thaw-required | Consumer boundary handled separately from route mutation ownership. |
| WinWEPP export climate copy | `wepppy/export/export.py` | consumer, FS-boundary | Export pipeline copies climate tree when needed. | thaw-required | Consumer boundary remains outside request-serving mutation path. |
| Climate sidecar readers | `wepppy/query_engine/*`, `wepppy/nodb/duckdb_agents.py` | consumer | Sidecar-first logical climate dataset handling. | archive-ready | Compatible with NoDir sidecar contract. |
| Browse/files/download surfaces | `wepppy/microservices/browse/*` | consumer | Archive-native list/stat/read without root thaw/freeze. | archive-ready | Behavior matrix preserved. |

## Stage A Totals

### Counts by Class
- `producer`: 7
- `consumer`: 8
- `FS-boundary`: 6
- `serialized-path hazard`: 0

### Counts by Readiness
- `archive-ready`: 8
- `thaw-required`: 4
- `blocked`: 0

### Stage A Verdict
- `ready`: yes
- Climate mutation entry points (`build-climate`, `upload-cli`) now have explicit root-owner orchestration and route-level canonical preflight.
