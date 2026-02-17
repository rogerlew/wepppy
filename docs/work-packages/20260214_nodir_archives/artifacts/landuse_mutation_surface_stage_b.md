# Landuse Mutation Surface Stage B (Phase 6)

Scope: define and record canonical landuse mutation ownership, lock/state boundaries, and read-path behavior.

## Canonical Mutation Entry Points

| Entry Point | File | Mutation Type | Requires Thaw | Lock Scope | State Transition | Failure Mode | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `build_landuse_rq(runid)` | `wepppy/rq/project_rq.py` | Root producer (`WD/landuse/*`) | Yes in archive form | `nodb-lock:<runid>:nodir/landuse` via `mutate_root` | `archived -> thawing -> thawed -> freezing -> archived` (archive form) | Canonical NoDir `409`/`500`/`503`; callback errors propagate | implemented |
| `build_treatments_rq(runid)` (landuse participation) | `wepppy/rq/project_rq.py` | Cross-root producer (`landuse` + `soils`) | Yes for any archive-form root in set | Deterministic lock ordering via `mutate_roots` | Per-root transitions as needed | Same canonical NoDir errors; failure preserves thawed dirty roots | implemented |
| `POST /rq-engine/.../build-landuse` | `wepppy/microservices/rq_engine/landuse_routes.py` | Validation/enqueue + optional user-defined root write | No direct thaw/freeze for enqueue; user-defined file writes run inside `mutate_root` | Route preflight with `nodir_resolve(..., view="effective")`; write callback in root lock | No state transition at route level unless user-defined write callback runs in archive form | Canonical NoDir errors at route surface | implemented |
| `Landuse.build()` and UserDefined map stack writes | `wepppy/nodb/core/landuse.py`, `wepppy/microservices/rq_engine/landuse_routes.py` | Controller root writers | Yes in archive form | Caller-owned root lock through shared mutation wrapper | Inherited from wrapper | Underlying filesystem/runtime errors propagate | implemented via owner boundaries |

## Read-Path Classification

| Read Path | File | Expected Behavior | NoDir Contract |
| --- | --- | --- | --- |
| Browse/files/download | `wepppy/microservices/browse/*` | Archive-native pass-through, no thaw/freeze | `native` read surfaces |
| Landuse parquet readers | `wepppy/nodb/duckdb_agents.py`, `wepppy/export/*` | Sidecar-first parquet reads | WD-level sidecar mapping remains authoritative |
| WEPP + mod consumers | `wepppy/nodb/core/wepp.py`, `wepppy/nodb/mods/treatments/*`, `wepppy/nodb/mods/omni/*` | Consumer path usage; no request-layer thaw | Mutation ownership stays at RQ boundary |

## Stage B Decision Summary

- Landuse mutation ownership is centralized in `build_landuse_rq` and `build_treatments_rq` through the shared `mutate_root`/`mutate_roots` contract.
- User-defined landuse upload + raster stack writes now execute in the same root mutation boundary to prevent archive-form drift.
- Route handlers remain strict preflight/enqueue boundaries with canonical NoDir error propagation.
