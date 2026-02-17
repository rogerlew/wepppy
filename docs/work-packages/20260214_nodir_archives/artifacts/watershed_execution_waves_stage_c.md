# Watershed Execution Waves Stage C (Phase 6a)

Scope: implementation-ready rollout waves for watershed NoDir adoption, derived from Stage A touchpoints and Stage B mutation-surface rules.

## Wave Overview

| Wave | Objective | In-Scope Code Areas | Excluded Code Areas | Expected Behavior Changes | Dependencies and Ordering Rationale |
| --- | --- | --- | --- | --- | --- |
| Wave 1 | Foundation and migration-safe watershed adoption | `wepppy/nodb/core/watershed.py` (constructor/root-form guard only); `wepppy/topo/peridot/peridot_runner.py` (`migrate_watershed_outputs`); `wepppy/tools/migrations/watershed.py`; `wepppy/query_engine/activate.py`; `wepppy/nodb/duckdb_agents.py` | `wepppy/rq/project_rq.py`; `wepppy/microservices/rq_engine/watershed_routes.py`; `wepppy/export/*`; `wepppy/nodb/mods/*`; browse/files/download handlers | Archive-form migration/tooling paths can operate without creating mixed state; sidecar parquet consumers remain stable in both forms | First wave removes blockers (`Watershed.__init__` mixed-state side effect) and establishes low-risk groundwork required by mutation waves |
| Wave 2 | Core watershed mutation producers (RQ + abstraction) | `wepppy/rq/project_rq.py`; `wepppy/microservices/rq_engine/watershed_routes.py`; `wepppy/nodb/core/watershed.py` (`abstract_watershed`, `_peridot_post_abstract_watershed`, `_topaz_abstract_watershed`); `wepppy/topo/peridot/peridot_runner.py` (`post_abstract_watershed`); `wepppy/topo/watershed_abstraction/` | `wepppy/export/*`; `wepppy/nodb/mods/*`; `wepppy/rq/wepp_rq.py`; browse/files/download/dtale/gdalinfo surfaces | Canonical watershed mutation entry points run with NoDir preflight + lock + conditional thaw/freeze for archive form; directory form remains pass-through | Depends on Wave 1 blocker removal and migration-safe baseline before enabling high-impact producer paths |
| Wave 3 | Watershed consumer integration (exports, mods, WEPP prep) | `wepppy/rq/wepp_rq.py`; `wepppy/nodb/core/wepp.py`; `wepppy/export/prep_details.py`; `wepppy/export/gpkg_export.py`; `wepppy/export/ermit_input.py`; `wepppy/export/export.py`; `wepppy/nodb/mods/swat/swat.py`; `wepppy/nodb/mods/rhem/rhem.py`; `wepppy/nodb/mods/path_ce/data_loader.py`; `wepppy/nodb/mods/omni/omni.py`; `wepppy/nodb/mods/salvage_logging/flowpaths.py` | `wepppy/microservices/browse/browse.py`; `wepppy/microservices/browse/files_api.py`; `wepppy/microservices/browse/_download.py`; serialized-path cleanup internals | Watershed consumers stop assuming direct `wat_dir` availability in archive form; FS-boundary consumers use file-level materialization and preserve canonical NoDir errors | Depends on Wave 2 producers generating stable watershed outputs under thaw/freeze semantics |
| Wave 4 | Legacy serialized-path cleanup and consistency hardening | `wepppy/nodb/core/watershed.py` (`_structure`/`structure.json` semantics); `wepppy/microservices/browse/browse.py`; `wepppy/microservices/browse/files_api.py`; `wepppy/microservices/browse/_download.py`; `wepppy/microservices/browse/dtale.py`; `wepppy/microservices/_gdalinfo.py`; watershed docs/artifacts sync | New producer features; non-watershed roots (`landuse`, `soils`, `climate`); broad refactors outside touched call sites | Remove serialized-path hazard and close remaining behavior-matrix gaps across read surfaces; final watershed consistency pass for mixed/invalid/locked semantics | Depends on Waves 1-3 so hardening validates final behavior, not shifting implementation targets |

## Wave Assignments

| Touchpoint | File | Stage A Readiness | Assigned Wave | Cut Line / Reason |
| --- | --- | --- | --- | --- |
| Watershed controller bootstrap (`wat_dir` mkdir) | `wepppy/nodb/core/watershed.py` | blocked | Wave 1 | Foundational blocker removal required before archive-form controller use in later waves. |
| Watershed abstraction orchestration | `wepppy/nodb/core/watershed.py` | thaw-required | Wave 2 | Primary producer mutation boundary under thaw/modify/freeze. |
| Legacy TOPAZ abstraction writes | `wepppy/nodb/core/watershed.py` | thaw-required | Wave 2 | High-impact root mutation path grouped with abstraction producers. |
| Structure persistence and `_structure` serialization | `wepppy/nodb/core/watershed.py` | blocked | Wave 4 | Serialized-path hazard cleanup is final hardening scope. |
| Network reads from `wat_dir` | `wepppy/nodb/core/watershed.py` | thaw-required | Wave 3 | Consumer read coupling handled with export/mod/WEPP consumer integration. |
| Parquet-backed watershed summaries | `wepppy/nodb/core/watershed.py` | archive-ready | Wave 1 | Low-risk sidecar-first baseline verification with migration/tooling groundwork. |
| Slope path helpers | `wepppy/nodb/core/watershed.py` | thaw-required | Wave 3 | Direct slope-path consumers are export/mod/WEPP integration scope. |
| Peridot post-processing outputs | `wepppy/topo/peridot/peridot_runner.py` | thaw-required | Wave 2 | Producer post-processing sits on mutation critical path. |
| Peridot watershed migration | `wepppy/topo/peridot/peridot_runner.py` | blocked | Wave 1 | Migration unblocked early to de-risk later producer waves. |
| Watershed abstraction engine (`WatershedAbstraction`) | `wepppy/topo/watershed_abstraction/watershed_abstraction.py` | thaw-required | Wave 2 | Core producer engine coupled to abstraction mutation flow. |
| Project bootstrap orchestration | `wepppy/rq/project_rq.py` | thaw-required | Wave 2 | Queue owner for watershed mutation sequence, including direct/smoke `test_run_rq` flow. |
| Watershed RQ mutation jobs | `wepppy/rq/project_rq.py` | thaw-required | Wave 2 | Canonical entry points for mutation orchestration rollout. |
| RQ-engine watershed routes | `wepppy/microservices/rq_engine/watershed_routes.py` | thaw-required | Wave 2 | Route-to-job mutation boundary requires consistent cutover. |
| WEPP watershed prep/run queue flow | `wepppy/rq/wepp_rq.py` | thaw-required | Wave 3 | Consumer integration with slope/network dependencies. |
| Prep-details export | `wepppy/export/prep_details.py` | archive-ready | Wave 3 | Export surface grouped with consumer integration wave. |
| GeoPackage export | `wepppy/export/gpkg_export.py` | archive-ready | Wave 3 | FS-boundary export handling with materialization conventions. |
| ERMiT export | `wepppy/export/ermit_input.py` | blocked | Wave 3 | Blocked consumer path tied to export/mod integration fixes. |
| WinWEPP export | `wepppy/export/export.py` | thaw-required | Wave 3 | Watershed-dependent export coupling handled with other exports. |
| Browse HTML handler | `wepppy/microservices/browse/browse.py` | archive-ready | Wave 4 | Final consistency pass against behavior matrix and mixed-state semantics. |
| Files JSON API | `wepppy/microservices/browse/files_api.py` | archive-ready | Wave 4 | Same as browse HTML: hardening/consistency, not early mutation work. |
| Download API | `wepppy/microservices/browse/_download.py` | archive-ready | Wave 4 | Final audit of admin/non-admin mixed-state and invalid-archive behavior. |
| D-Tale bridge | `wepppy/microservices/browse/dtale.py` | archive-ready | Wave 4 | Hardening pass for transition-state lock/error behavior. |
| GDAL info endpoint | `wepppy/microservices/_gdalinfo.py` | archive-ready | Wave 4 | Hardening pass for FS-boundary materialization error semantics. |
| Query-engine watershed cataloging | `wepppy/query_engine/activate.py` | thaw-required | Wave 1 | Internal catalog canonicalization validated before producer/consumer rollout. |
| SWAT downstream topology mapping | `wepppy/nodb/mods/swat/swat.py` | thaw-required | Wave 3 | Mod consumer path coupled to network/slope read behavior. |
| RHEM hillslope prep | `wepppy/nodb/mods/rhem/rhem.py` | thaw-required | Wave 3 | Mod FS-boundary consumer integration scope. |
| Path-CE data loader | `wepppy/nodb/mods/path_ce/data_loader.py` | archive-ready | Wave 3 | Mod-side validation in same wave as other watershed mod consumers. |
| OMNI scenario clone (`watershed` root handling) | `wepppy/nodb/mods/omni/omni.py` | archive-ready | Wave 3 | Root-form clone behavior validated with integration consumers. |
| Salvage flowpath utility | `wepppy/nodb/mods/salvage_logging/flowpaths.py` | thaw-required | Wave 3 | Direct flowpath glob/path coupling addressed in integration wave. |
| DuckDB watershed query helpers | `wepppy/nodb/duckdb_agents.py` | archive-ready | Wave 1 | Low-risk sidecar query baseline in foundation wave. |
| Watershed migration utility | `wepppy/tools/migrations/watershed.py` | archive-ready | Wave 1 | Internal tooling-first conversion target. |
| Core WEPP watershed input prep | `wepppy/nodb/core/wepp.py` | thaw-required | Wave 3 | Highest-impact watershed consumer (slope/network file dependency). |

## Wave Preconditions

| Wave | Preconditions |
| --- | --- |
| Wave 1 | Stage A and Stage B artifacts accepted as the mutation/read contract baseline; thaw/freeze lock contract unchanged (`nodb-lock:<runid>:nodir/watershed`); migration execution plan requires explicit run-safety policy (`READONLY` for bulk migration operations). |
| Wave 2 | Wave 1 complete: controller mixed-state bootstrap blocker resolved, migration paths stable, and canonical mutation helper boundary agreed for watershed root mutation entry points. |
| Wave 3 | Wave 2 complete: producer flows generate consistent watershed artifacts in Dir and archive forms; RQ mutation entry points enforce canonical NoDir preflight/lock/thaw/freeze behavior. |
| Wave 4 | Waves 1-3 complete: no open producer/consumer regressions, and remaining work is serialized-path cleanup plus behavior-matrix conformance hardening. |

## Wave Deliverables

| Wave | Deliverables | Handoff Requirements to Next Wave |
| --- | --- | --- |
| Wave 1 | Implement watershed foundation fixes in migration/tooling scope; eliminate constructor mixed-state side effect; ensure migration/canonicalization paths do not require unsafe controller bootstrap under archive form. | Provide explicit list of remaining root mutation entry points (for Wave 2) and confirm no regression in sidecar query consumers. |
| Wave 2 | Implement thaw/modify/freeze orchestration for canonical watershed mutation producers in RQ/controller/peridot abstraction flows; keep route layer as validation/enqueue boundary. | Provide producer verification evidence (Dir vs archive form) and final list of consumer call sites still using direct `wat_dir` assumptions (Wave 3 backlog). |
| Wave 3 | Implement watershed consumer integrations for exports/mods/WEPP prep with FS-boundary materialization where required; remove direct archive-form breakpoints in blocked/thaw-required consumer paths. | Provide residual hardening list limited to serialized-path cleanup and behavior-matrix consistency checks for Wave 4. |
| Wave 4 | Remove `_structure` serialized-path hazard and complete consistency hardening across browse/files/download/dtale/gdalinfo semantics for watershed NoDir states. | Mark watershed Phase 6a execution plan as implementation-ready for Stage D validation gates. |

## Wave Risk Notes

| Wave | Primary Risks | Rollback Trigger Conditions |
| --- | --- | --- |
| Wave 1 | Foundation changes can silently reintroduce mixed-state creation (`WD/watershed` + `WD/watershed.nodir`) during controller/migration startup. | Any new mixed-state creation on archive-form runs; incomplete transition artifacts (`.thaw.tmp`/`.nodir.tmp`) after migration flow; loss of canonical watershed sidecar catalog visibility. |
| Wave 2 | Producer mutation cutover can leave runs in thawed/dirty state or generate incomplete abstraction outputs when lock/state ordering is wrong. | Abstraction jobs producing partial outputs after freeze; repeated `503 NODIR_LOCKED` outside real transition windows; unexpected `409 NODIR_MIXED_STATE` in normal producer path. |
| Wave 3 | Consumer integration can break exports/mod workflows by missing slope/network materialization boundaries or by retaining direct `wat_dir` assumptions. | Export/mod/WEPP-prep failures on archive-form runs where Dir-form still succeeds; materialization lock contention/limits causing unacceptable failure rate; regressions in run-to-run output parity. |
| Wave 4 | Hardening changes can regress public-surface semantics or legacy run compatibility while resolving serialized-path hazards. | Browse/files/download semantics diverge from behavior matrix; legacy watershed runs fail to load structure/network metadata; invalid-archive or mixed-state codes/statuses deviate from canonical contract. |

## Wave Exit Criteria

| Wave | Exit Criteria | Handoff Requirements |
| --- | --- | --- |
| Wave 1 | Blocking touchpoints for constructor/bootstrap and migration paths are closed; low-risk internal watershed read/canonicalization paths remain stable in Dir and archive forms. | Wave 2 receives a stable mutation-helper boundary and an explicit producer entry-point implementation list. |
| Wave 2 | Canonical watershed mutation producers are mapped to thaw/modify/freeze behavior with deterministic lock/state transitions; no unresolved producer ownership ambiguity remains. | Wave 3 receives verified producer artifacts plus a precise consumer integration backlog. |
| Wave 3 | Export/mod/WEPP watershed consumers no longer rely on unsafe archive-form path assumptions; blocked consumer touchpoints are cleared or explicitly deferred with bounded rationale. | Wave 4 receives only hardening/serialized-path cleanup scope (no new producer or broad integration work). |
| Wave 4 | Serialized-path hazard is resolved and watershed read-surface semantics match NoDir contracts for mixed/invalid/locked states; touchpoint-to-wave plan has no unresolved ownership gaps. | Stage C handoff to Stage D validation gates is complete. |
