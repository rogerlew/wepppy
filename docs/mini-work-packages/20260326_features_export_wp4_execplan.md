# WP-4 Features Export Service Orchestration, RQ Wiring, and rq-engine Integration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` will be kept current as implementation proceeds.

This plan follows the repository template at `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Implement WP-4 only for Features Export. After this change, API callers can submit asynchronous features export jobs through rq-engine, poll canonical RQ endpoints, and download completed artifacts through a run-scoped authenticated download route. The orchestration path must use completed WP-1/WP-2/WP-3 module contracts and must preserve legacy geopackage/geodatabase endpoints until WP-6 cutover.

## Progress

- [x] (2026-03-26 18:24Z) Read required AGENTS docs, WP-4 specification sections (5/6/10/11/13/14), and existing WP-1/WP-2/WP-3 modules.
- [x] (2026-03-26 18:24Z) Created and activated this WP-4 ExecPlan at `docs/mini-work-packages/20260326_features_export_wp4_execplan.md`.
- [x] (2026-03-26 18:34Z) Implemented `wepppy/nodb/mods/features_export/service.py` orchestration with cache miss/hit result payload contract and download artifact resolution.
- [x] (2026-03-26 18:35Z) Implemented `wepppy/rq/features_export_rq.py` with full-export and cache-hit worker entrypoints, status messaging, and RedisPrep timestamp lifecycle.
- [x] (2026-03-26 18:37Z) Extended `wepppy/microservices/rq_engine/export_routes.py` with:
  - `POST /api/runs/{runid}/{config}/export/features`
  - `GET /api/runs/{runid}/{config}/export/features/{job_id}/download`
  including strict JSON transport validation, queue wiring, and canonical error handling.
- [x] (2026-03-26 18:37Z) Updated `wepppy/nodb/redis_prep.py` and `wepppy/nodb/redis_prep.pyi` with `TaskEnum.run_features_export` label `Export Features` and emoji `📦`.
- [x] (2026-03-26 18:39Z) Added tests:
  - `tests/nodb/mods/test_features_export_service.py`
  - `tests/rq/test_features_export_rq.py`
  - `tests/microservices/test_rq_engine_features_export_routes.py`
- [x] (2026-03-26 18:45Z) Detected queue graph drift via `wctl check-rq-graph`, regenerated artifacts with `python tools/check_rq_dependency_graph.py --write`, and revalidated graph consistency.
- [x] (2026-03-26 18:49Z) Ran required validation command set and recorded evidence.
- [x] (2026-03-26 18:49Z) Completed correctness self-review and QA review loop; patched findings (stubtest type drift and worker status-task naming clarity).
- [x] (2026-03-26 18:49Z) Finalized outcomes and residual-risk notes.

## Surprises & Discoveries

- Observation: `export_routes.py` currently contains only synchronous legacy file-export handlers; no existing features-export async route scaffold exists.
  Evidence: current route file exports `/export/ermit`, `/export/geopackage`, `/export/geodatabase`, and `/export/prep_details` only.
- Observation: WP-2 cache-key hashing requires a concrete `swat_run_id`; WP-4 orchestration must resolve default `latest` before hash construction.
  Evidence: `build_request_hash(...)` in `cache_key.py` raises if `swat_run_id` remains `latest`.
- Observation: `wctl check-rq-graph` reported static graph/catalog drift immediately after enqueue wiring edits.
  Evidence: drift reported for `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md`; resolved with `python tools/check_rq_dependency_graph.py --write`.
- Observation: `wctl run-stubtest wepppy.nodb.mods.features_export` surfaced type-surface issues in `service.py` (Unitizer attribute typing and imported `Any` export leak).
  Evidence: initial stubtest failure output for `preferences_fingerprint` attr typing and `service.Any` inconsistency; resolved by patching service typing path and removing the unused `Any` import.

## Decision Log

- Decision: Keep route and RQ adapters thin and centralize WP-4 business logic in `features_export/service.py`.
  Rationale: Matches specification section 14 keep-it-organized rule for adapter boundaries.
  Date/Author: 2026-03-26 / Codex
- Decision: Preserve legacy `/export/geopackage` and `/export/geodatabase` endpoints unchanged in WP-4.
  Rationale: User explicitly scoped cutover removal to WP-6.
  Date/Author: 2026-03-26 / Codex
- Decision: Use dedicated cache-hit enqueue path (`run_features_export_cache_hit_rq`) while still returning HTTP 202 for submit.
  Rationale: Meets WP-4 cache-hit fast-path contract with new async job IDs while keeping submit/download adapters thin.
  Date/Author: 2026-03-26 / Codex
- Decision: Enforce strict `application/json` media type and reject empty JSON object bodies at transport boundary before planner invocation.
  Rationale: Matches WP-4 API transport contract (415 for non-JSON, 400 for empty/invalid JSON payloads).
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

WP-4 implementation completed in scope:

- Added `features_export` orchestration service with:
  - submit-time normalization/planning/dependency snapshot/cache-key preparation
  - cache miss artifact+manifest write path
  - cache-hit finalize path with new job-scoped manifest and required result keys
  - download artifact mapping resolution from job result or job manifest
- Added new RQ worker module `wepppy/rq/features_export_rq.py` with:
  - full-export worker entrypoint
  - cache-hit finalize worker entrypoint
  - RedisPrep timestamp lifecycle integration for `TaskEnum.run_features_export`
- Extended rq-engine export routes with:
  - async submit endpoint for features export (`POST .../export/features`)
  - authenticated download endpoint (`GET .../export/features/{job_id}/download`)
  - strict JSON transport enforcement and canonical 400/404/409/415 error payload handling
  - job enqueue response contract (`job_id`, `status_url`, `download_url`)
- Updated RedisPrep enum/type stubs:
  - `TaskEnum.run_features_export = "run_features_export"`
  - label `Export Features`
  - emoji `📦`
- Added focused tests for service, RQ worker behavior, and rq-engine route contracts.
- Updated queue graph artifacts after wiring changes.

Correctness self-review findings:
- Finding (medium): worker status messages used `_run_features_export_worker` rather than public task names.
  Resolution: added explicit `task_name` parameter so status stream emits `run_features_export_rq` / `run_features_export_cache_hit_rq`.

QA review findings:
- Finding (high): stubtest failures in `service.py` type surface (`preferences_fingerprint` attr typing and leaked `Any` symbol).
  Resolution: patched Unitizer fingerprint access to a typed boundary-safe getter and removed unused `Any` import; reran stubtest to green.
- Finding (medium): no test asserting cache-hit submit path enqueues cache-hit worker.
  Resolution: added route test `test_features_export_submit_cache_hit_enqueues_finalize_job`.

Final review status: no remaining high/medium findings.

## Context and Orientation

WP-1 already provides request validation/planning (`contracts.py`, `catalog_loader.py`, `planner.py`).
WP-2 already provides dependency snapshot + cache key/index helpers (`dependency_tracker.py`, `cache_key.py`).
WP-3 already provides writer contracts and manifest construction (`exporters/*`, `manifest.py`).

WP-4 must connect those contracts into asynchronous execution and authenticated download:

- New orchestration module: `wepppy/nodb/mods/features_export/service.py`
- New RQ module: `wepppy/rq/features_export_rq.py`
- Existing route integration point: `wepppy/microservices/rq_engine/export_routes.py`
- Redis task tracking: `wepppy/nodb/redis_prep.py`, `wepppy/nodb/redis_prep.pyi`

## Plan of Work

Implement the service layer first so route and worker adapters call one orchestrator API. The service will provide submit-time request preparation (WP-1 + WP-2), cache-hit detection, artifact/manifest write helpers, and deterministic job result payloads matching the WP-4 contract (`artifact_id`, `download_url`, `cache_hit`, `source_job_id`, `manifest_relpath`, `warnings`).

Then implement the RQ module with worker entrypoints and status messaging boundaries. One entrypoint performs full execution and another handles cache-hit finalize jobs so cache hits still produce a fresh async `job_id` and job-scoped manifest.

Next, extend rq-engine export routes for strict JSON submit behavior and authenticated download behavior. Submit returns 202 with canonical keys (`job_id`, `status_url`, optional `download_url`) and canonical 400/415 errors. Download enforces run auth, checks finished terminal state, and returns `FileResponse` or canonical 404/409 errors.

Finally, add focused tests for service, worker, and routes; update RedisPrep enum wiring; run required validation commands; update queue dependency artifacts if drift is reported; then run self-review and QA review loops and patch findings.

## Concrete Steps

From `/workdir/wepppy`:

1. Add `wepppy/nodb/mods/features_export/service.py`.
2. Add `wepppy/rq/features_export_rq.py`.
3. Patch `wepppy/microservices/rq_engine/export_routes.py`.
4. Patch `wepppy/nodb/redis_prep.py` and `wepppy/nodb/redis_prep.pyi`.
5. Patch package exports as needed (`wepppy/nodb/mods/features_export/__init__.py`).
6. Add tests:
   - `tests/nodb/mods/test_features_export_service.py`
   - `tests/microservices/test_rq_engine_features_export_routes.py`
   - `tests/rq/test_features_export_rq.py`
7. Run validation commands requested by the user.
8. If queue graph drift is detected: regenerate using `python tools/check_rq_dependency_graph.py --write` and update `wepppy/rq/job-dependencies-catalog.md`/graph artifacts.
9. Run correctness self-review and QA review pass; patch high/medium findings.
10. Finalize this ExecPlan with outcomes/retrospective and residual risks.

## Validation and Acceptance

Acceptance requires:

- Submit endpoint enforces `application/json` only and returns canonical 415/400 where required.
- Valid submit returns 202 with `job_id` and `status_url`.
- Worker result payload includes required WP-4 fields.
- Cache hit path returns a new job id and `cache_hit=true` with `source_job_id`.
- Download endpoint returns 409 before finished, returns file after finished, and canonical 404 for missing mapping/artifact.
- RedisPrep task tracking is wired with `TaskEnum.run_features_export` and `set_rq_job_id("features_export", job.id)`.
- Legacy geopackage/geodatabase endpoints remain present.
- Required validation command set is executed and reported.

## Idempotence and Recovery

Changes are additive and localized to features-export orchestration and rq-engine adapters. Re-running submit/download tests is safe. Artifact writes are namespaced per job/artifact id under `export/features/` and do not alter legacy export locations.

## Artifacts and Notes

Validation evidence (2026-03-26):

- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1` -> pass
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> pass
- `wctl run-pytest tests/rq/test_features_export_rq.py --maxfail=1` -> pass
- `wctl run-pytest tests/microservices/test_rq_engine_export_routes.py --maxfail=1` -> pass
- `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py --maxfail=1` -> pass
- `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py --maxfail=1` -> pass
- `wctl run-stubtest wepppy.nodb.mods.features_export` -> pass (after service typing fixes)
- `wctl check-test-stubs` -> pass
- `wctl check-rq-graph` -> drift detected, regenerated with `python tools/check_rq_dependency_graph.py --write`, re-run -> pass
- `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md` -> pass
- `wctl doc-lint --path docs/mini-work-packages/20260326_features_export_wp4_execplan.md` -> pass

## Interfaces and Dependencies

Planned WP-4 interfaces:

- Service APIs in `wepppy.nodb.mods.features_export.service` for submit preparation, export execution, cache finalize, and job-manifest/artifact resolution.
- Worker APIs in `wepppy.rq.features_export_rq` for queue entrypoints.
- Route APIs in `wepppy.microservices.rq_engine.export_routes` for `/export/features` submit/download.

No new third-party dependencies are planned.

---

Revision note (2026-03-26 18:24Z): Initial WP-4 ExecPlan created and activated before code implementation.
