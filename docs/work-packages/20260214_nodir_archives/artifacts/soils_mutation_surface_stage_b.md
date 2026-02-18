# Soils Mutation Surface Stage B (Phase 6)

Scope: define and record canonical soils mutation ownership, lock/state boundaries, and read-path behavior.

## Canonical Mutation Entry Points

| Entry Point | File | Mutation Type | Requires Thaw | Lock Scope | State Transition | Failure Mode | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `build_soils_rq(runid)` | `wepppy/rq/project_rq.py` | Root producer (`WD/soils/*`) | Yes in archive form | `nodb-lock:<runid>:nodir/soils` via `mutate_root` | `archived -> thawing -> thawed -> freezing -> archived` (archive form) | `409`/`500`/`503` canonical NoDir errors, callback failures propagate | implemented |
| `build_treatments_rq(runid)` (soils participation) | `wepppy/rq/project_rq.py` | Cross-root producer (`landuse` + `soils`) | Yes for any archive-form root in set | Deterministic lock order via `mutate_roots` | Per-root archive transitions; dir-form no transition | Same canonical NoDir errors; callback failure leaves thawed dirty roots | implemented |
| `Soils.build()` | `wepppy/nodb/core/soils.py` | Controller root writer | Yes when called for archive form | Must execute inside `mutate_root` owner boundary | Inherited from wrapper | Underlying filesystem/runtime errors propagate | implemented via RQ owners |
| `POST /rq-engine/.../build-soils` | `wepppy/microservices/rq_engine/soils_routes.py` | Validation/enqueue boundary | No direct thaw/freeze | Route preflight: `nodir_resolve(..., view="effective")` | None at HTTP boundary | Canonical NoDir errors returned directly | implemented |

## Read-Path Classification

| Read Path | File | Expected Behavior | NoDir Contract |
| --- | --- | --- | --- |
| Browse/files/download | `wepppy/microservices/browse/*` | Archive-native pass-through reads; no thaw/freeze | `native` surfaces remain extraction-free |
| Soils parquet reads | `wepppy/nodb/duckdb_agents.py`, `wepppy/export/prep_details.py`, `wepppy/export/gpkg_export.py` | Sidecar-first parquet resolution | WD-level sidecar mapping preserved |
| FS-boundary consumers (`.sol` and export copytree) | `wepppy/nodb/core/wepp.py`, `wepppy/export/export.py` | Consumer-level path usage; no route-surface thaw | Materialize/root-thaw ownership remains outside request-serving surfaces |

## Stage B Decision Summary

- Soils root mutation ownership is centralized in RQ mutation owners (`build_soils_rq`, `build_treatments_rq`) through shared `mutate_root`/`mutate_roots`.
- Route layer stays preflight/enqueue only; it does not own thaw/freeze.
- Callback failures after thaw intentionally preserve thawed/dirty state for deterministic recovery and forensics.

## Phase 9 Contract Transition Addendum (2026-02-18)

This Stage B artifact remains a historical record of Phase 6 soils mutation ownership under thaw/freeze semantics.

Forward contract update:
- Archive-form soils mutation ownership remains at the same RQ boundaries.
- Archive-form mutation mechanism is superseded from `materialize(root)+freeze` to `projection(mode=mutate)+commit`.
- Read-only path-heavy soils consumers should migrate toward read-session projection before using per-file materialization fallback.

Interpretation guidance:
- `Requires Thaw` in this document should be treated as `Requires Mutation Session` for Phase 9+ implementation.
