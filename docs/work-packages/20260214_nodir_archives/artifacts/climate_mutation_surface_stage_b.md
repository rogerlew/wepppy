# Climate Mutation Surface Stage B (Phase 6)

Scope: define and record canonical climate mutation ownership, lock/state boundaries, and read-path behavior.

## Canonical Mutation Entry Points

| Entry Point | File | Mutation Type | Requires Thaw | Lock Scope | State Transition | Failure Mode | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `build_climate_rq(runid)` | `wepppy/rq/project_rq.py` | Root producer (`WD/climate/*`) | Yes in archive form | `nodb-lock:<runid>:nodir/climate` via `mutate_root` | `archived -> thawing -> thawed -> freezing -> archived` (archive form) | Canonical NoDir `409`/`500`/`503`; callback errors propagate | implemented |
| `upload_cli_rq(runid, cli_filename)` | `wepppy/rq/project_rq.py` | Root producer (assign uploaded CLI to climate controller) | Yes in archive form | `nodb-lock:<runid>:nodir/climate` via `mutate_root` | Same archive-form transition sequence | Same canonical NoDir errors; callback failure preserves thawed dirty state | implemented |
| `POST /rq-engine/.../build-climate` | `wepppy/microservices/rq_engine/climate_routes.py` | Validation/enqueue boundary | No direct thaw/freeze | Route preflight with `nodir_resolve(..., view="effective")` | None at HTTP boundary | Canonical NoDir errors returned directly | implemented |
| `POST /rq-engine/.../tasks/upload-cli/` | `wepppy/microservices/rq_engine/upload_climate_routes.py` | Upload writer + enqueue | Yes for archive form through route callback wrapper | Route write callback executes under `mutate_root(..., "climate", ...)` | Archive form transitions during upload write callback | Canonical NoDir errors at route surface; upload callback errors propagate | implemented |

## Read-Path Classification

| Read Path | File | Expected Behavior | NoDir Contract |
| --- | --- | --- | --- |
| Browse/files/download | `wepppy/microservices/browse/*` | Archive-native pass-through reads; no thaw/freeze | `native` read surfaces |
| Climate report/interchange readers | `wepppy/weppcloud/routes/nodb_api/climate_bp.py`, `wepppy/wepp/interchange/*` | Consumer path usage for reports/datasets | Root mutation ownership remains in RQ + upload boundaries |
| WEPP/export climate consumers | `wepppy/nodb/core/wepp.py`, `wepppy/export/export.py` | FS-boundary consumer file access | Materialize/root-thaw behavior stays outside request-serving surfaces |

## Stage B Decision Summary

- Climate mutation ownership is centralized in `build_climate_rq` and `upload_cli_rq` with shared NoDir mutation orchestration.
- Upload route writes are now root-owner-safe in archive form (`mutate_root`), eliminating direct archive-form write drift.
- Build and upload routes enforce canonical NoDir preflight semantics before enqueue or mutation.

## Phase 9 Contract Transition Addendum (2026-02-18)

This Stage B artifact remains a historical record of Phase 6 climate mutation ownership under thaw/freeze semantics.

Forward contract update:
- Archive-form climate mutation ownership remains at the same RQ and upload-owned mutation boundaries.
- Archive-form mutation mechanism is superseded from `materialize(root)+freeze` to `projection(mode=mutate)+commit`.
- Read-only path-heavy climate consumers should migrate toward read-session projection before using per-file materialization fallback.

Interpretation guidance:
- `Requires Thaw` in this document should be treated as `Requires Mutation Session` for Phase 9+ implementation.
