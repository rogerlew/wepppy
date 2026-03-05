# OSM Roads Client with Persistent Server-Side Cache

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

WEPPpy terrain preprocessing needs repeatable OSM roads acquisition without issuing duplicate Overpass queries for the same geography. After this change, a consumer can request roads for an AOI and target EPSG and get deterministic road artifacts from a server-wide persistent cache when available, with lock-safe refresh when not.

Success is observable when identical requests across independent runs/users hit the same cache entry, output roads are correctly clipped/reprojected, and upstream Overpass instability does not force unnecessary failures when stale cache is allowed.

## Progress

- [x] (2026-03-04 21:55Z) Created package scaffold at `docs/work-packages/20260304_osm_roads_client_cache/`.
- [x] (2026-03-04 22:00Z) Authored package brief, tracker, and concrete module contract (`module_contract.md`).
- [x] (2026-03-04 22:05Z) Authored this active ExecPlan and end-to-end execution prompt.
- [x] (2026-03-04 22:10Z) Updated `PROJECT_TRACKER.md` backlog and root `AGENTS.md` active plan pointer.
- [x] (2026-03-04 22:20Z) Added decision artifact documenting why OSMnx is not selected for v1 (`artifacts/osmnx_decision.md`).
- [x] (2026-03-04 23:05Z) Refined contract from design review: fixed tile-grid/keying semantics, GeoParquet-vs-GeoJSON output semantics, cross-process locking, batched Overpass strategy, cleanup contract, and force-refresh behavior.
- [x] (2026-03-05 00:15Z) Locked backend approach to hybrid cache: PostgreSQL metadata/locks + `/wc1` GeoParquet payloads, with bounded expired-on-error fallback policy.
- [x] (2026-03-05 07:50Z) Milestone 1 complete: added `wepppy/topo/osm_roads/` public contracts/errors/package exports.
- [x] (2026-03-05 08:05Z) Milestone 2 complete: implemented cache keying, TTL evaluation, in-memory and PostgreSQL metadata stores, advisory lock helpers, payload read/write, and cleanup routines.
- [x] (2026-03-05 08:20Z) Milestone 3 complete: implemented Overpass query builder/client with retry/backoff and line-feature normalization.
- [x] (2026-03-05 08:35Z) Milestone 4 complete: implemented lock-safe refresh with stale/expired-on-error boundaries and force-refresh behavior.
- [x] (2026-03-05 08:45Z) Milestone 5 complete: added TerrainProcessor consumer seam (`resolve_roads_source`), topology tests, runtime README, and package docs updates.
- [x] (2026-03-05 09:10Z) Validation gates complete: targeted topo suites, `tests --maxfail=1`, broad-exception check, and required doc-lint checks all passed.
- [x] (2026-03-05 09:35Z) Added dedicated Postgres functional pytest (`tests/topo/test_osm_roads_postgres_integration.py`) and migration/deployment artifact (`artifacts/postgres_migration_setup.md`) for forest1/prod rollout.

## Surprises & Discoveries

- Observation: `terrain_processor.concept.md` already codifies a server-wide cache requirement and separation of OSM roads module from TerrainProcessor implementation.
  Evidence: `wepppy/topo/wbt/terrain_processor.concept.md` (`OSM Roads Module` section).

- Observation: Existing WEPPpy guidance explicitly discourages speculative dependency additions and asks for owned-stack preference.
  Evidence: Root `AGENTS.md` dependency/performance discipline section.

- Observation: There is no executable TerrainProcessor runtime path yet in `wepppy/topo/wbt`; only a concept document exists.
  Evidence: `wepppy/topo/wbt/terrain_processor.concept.md` is the only `roads_source="osm"` reference in the topo/wbt module tree.

- Observation: Importing `wepppy.topo.wbt` through the package root can unintentionally pull heavy dependencies if consumer seams import from `wepppy.topo.osm_roads` package root.
  Evidence: `wepppy/topo/osm_roads/__init__.py` re-exports cache types that import pandas.

- Observation: `wctl run-pytest` does not forward arbitrary shell env vars into the container unless wired via compose env keys, so toggle-gated integration tests can appear skipped unexpectedly.
  Evidence: `OSM_ROADS_POSTGRES_INTEGRATION=1 wctl run-pytest tests/topo/test_osm_roads_postgres_integration.py` initially skipped both tests until direct-file invocation logic was added.

## Decision Log

- Decision: Treat `module_contract.md` as the source of truth for signatures and cache semantics.
  Rationale: Keeps implementation and tests anchored to one concrete contract document.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use persistent file-backed cache in v1 (SQLite index + GeoParquet payloads).
  Rationale: Durable and deployable without requiring additional external infrastructure during initial planning.
  Status: Superseded on 2026-03-05 by hybrid backend decision.
  Date/Author: 2026-03-04 / Codex.

- Decision: Preserve OSMnx non-adoption rationale in a dedicated artifact rather than only in tracker/chat context.
  Rationale: Future agents need a stable, discoverable reference with revisit criteria.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use fixed-origin EPSG:4326 tiling with separate tile-level and request-level keys.
  Rationale: Removes ambiguity for multi-tile AOIs and keeps per-tile reuse with deterministic request identity.
  Date/Author: 2026-03-04 / Codex.

- Decision: Keep cache payload format as GeoParquet but return a consumer-facing GeoJSON artifact path.
  Rationale: Preserves efficient cache storage while honoring existing TerrainProcessor-style consumer expectations.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use cross-process file locks for single-flight semantics; SQLite remains metadata/index only.
  Rationale: Interim lock strategy before backend decision lock-in.
  Status: Superseded on 2026-03-05; replaced by PostgreSQL advisory lock contract.
  Date/Author: 2026-03-04 / Codex.

- Decision: Lock backend target to hybrid cache: PostgreSQL for metadata + lock coordination and `/wc1` file payloads for vector storage.
  Rationale: Better long-term concurrency/reliability and cleanup ergonomics while preserving efficient payload storage and simple rollout.
  Date/Author: 2026-03-05 / Codex.

- Decision: Allow bounded expired-cache fallback on upstream fetch failure.
  Rationale: Improves resilience during Overpass outages/rate limits while containing stale-data risk with an explicit maximum expired age policy.
  Date/Author: 2026-03-05 / Codex.

- Decision: Keep the TerrainProcessor integration seam as `wepppy/topo/wbt/osm_roads_consumer.py::resolve_roads_source` rather than wiring a non-existent runtime class.
  Rationale: Enforces the consumer contract today without inventing speculative TerrainProcessor runtime structure.
  Date/Author: 2026-03-05 / Codex.

- Decision: Enforce strict highway-filter token validation (`[a-z0-9_]+`) before query construction.
  Rationale: Avoids malformed/unsafe regex fragments in Overpass query generation and keeps request validation explicit.
  Date/Author: 2026-03-05 / Codex.

- Decision: Default service requires an explicit PostgreSQL URL (module env or runtime DB env); no silent fallback to non-persistent metadata backends.
  Rationale: Preserves production contract expectations and avoids hidden behavior drift.
  Date/Author: 2026-03-05 / Codex.

- Decision: Allow direct invocation of `tests/topo/test_osm_roads_postgres_integration.py` without opt-in flag, while keeping broader suites opt-in via `OSM_ROADS_POSTGRES_INTEGRATION`.
  Rationale: Keeps a dedicated functional pytest ergonomic on forest while preventing accidental inclusion in broad default suites.
  Date/Author: 2026-03-05 / Codex.

- Decision: Resolve Postgres test credentials from `/run/secrets/postgres_password` when explicit password env vars are absent.
  Rationale: Matches compose runtime defaults and prevents false negatives from DSNs missing passwords.
  Date/Author: 2026-03-05 / Codex.

## Outcomes & Retrospective

Implementation and validation are complete across all five milestones.

Delivered behavior:
- New OSM roads module under `wepppy/topo/osm_roads/` with contract dataclasses, typed errors, cache/key/TTL logic, Overpass client, and service orchestration.
- Hybrid cache architecture support with PostgreSQL metadata/advisory-lock backend and `/wc1`-style file payload artifacts.
- Per-key lock-safe refresh behavior with stale and bounded expired fallback on upstream failure.
- AOI clip + target EPSG reprojection with request-level GeoJSON artifact output.
- TerrainProcessor-style consumer seam via `wepppy/topo/wbt/osm_roads_consumer.py::resolve_roads_source`.

Validation outcomes:
- `wctl run-pytest tests/topo/test_osm_roads_contracts.py` PASS.
- `wctl run-pytest tests/topo/test_osm_roads_cache.py` PASS.
- `wctl run-pytest tests/topo/test_osm_roads_service.py` PASS.
- `wctl run-pytest tests/topo/test_osm_roads_postgres_integration.py` PASS.
- `wctl run-pytest tests/topo -k osm_roads` PASS.
- `wctl run-pytest tests --maxfail=1` PASS (`2214 passed, 30 skipped`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` PASS.
- Required doc-lint gates PASS.

## Context and Orientation

This package introduces a new WEPPpy subsystem under `wepppy/topo/osm_roads/` with explicit contracts documented in:

- `docs/work-packages/20260304_osm_roads_client_cache/module_contract.md`

Primary implementation targets (new files):

- `wepppy/topo/osm_roads/__init__.py`
- `wepppy/topo/osm_roads/contracts.py`
- `wepppy/topo/osm_roads/errors.py`
- `wepppy/topo/osm_roads/cache.py`
- `wepppy/topo/osm_roads/overpass.py`
- `wepppy/topo/osm_roads/service.py`

Primary consumer seam:

- TerrainProcessor caller path for `roads_source="osm"` (exact consumer file to be finalized during Milestone 5).

Testing targets (new/updated):

- `tests/topo/test_osm_roads_contracts.py`
- `tests/topo/test_osm_roads_cache.py`
- `tests/topo/test_osm_roads_service.py`
- optional integration fixture tests under `tests/topo/fixtures/osm_roads/`

## Plan of Work

### Milestone 1: Module scaffold and public contract wiring

Implement contract dataclasses, protocol interface, and typed errors exactly as specified in `module_contract.md`.

Deliverables:
- request/response dataclasses,
- protocol/service entrypoint,
- error class hierarchy,
- minimal package exports.

Acceptance:
- imports resolve from `wepppy.topo.osm_roads` package,
- contract tests validate dataclass defaults and signature invariants.

### Milestone 2: Persistent cache backend

Implement hybrid cache backend:
- deterministic tile/request key builders,
- PostgreSQL schema/tables and CRUD for tile/request metadata,
- PostgreSQL advisory lock helpers for per-tile single-flight,
- payload read/write abstraction (GeoParquet),
- TTL decision function (fresh/stale/expired + bounded expired fallback + force-refresh semantics),
- cleanup/eviction routine for expired entries.

Acceptance:
- repeated same request key resolves same cache record,
- restart-safe persistence validated in tests,
- lock semantics work across independent processes using PostgreSQL advisory locks,
- expired entries are deletable by cleanup with idempotent behavior.

### Milestone 3: Overpass client and normalization pipeline

Implement upstream fetch path:
- Overpass query generation from uncovered tile batches + highway filter,
- retry/backoff and timeout handling,
- response parsing + normalization (line geometry only, tags, `osm_id`),
- AOI clipping and target EPSG reprojection,
- request artifact materialization as GeoJSON.

Acceptance:
- mocked Overpass response path produces valid clipped/reprojected output artifacts,
- bounded query count for multi-tile AOIs (batching behavior),
- malformed upstream payloads fail with typed errors.

### Milestone 4: Lock-safe cache fill and stale-on-error

Implement per-key single-flight lock and refresh behavior:
- PostgreSQL advisory lock acquire/release with timeout,
- wait/poll behavior for concurrent callers,
- stale-on-error return when policy and TTL permit,
- expired-on-error return when policy and TTL permit,
- explicit handling for force-refresh fallback boundaries.

Acceptance:
- concurrent test proves one upstream fetch for identical requests,
- stale cache path works on simulated upstream failure.

### Milestone 5: Consumer seam integration, tests, docs

Integrate service call into OSM roads consumer path and document runtime configs.

Deliverables:
- consumer wiring for `roads_source="osm"`,
- test coverage for contract/cache/service behavior,
- docs updates referencing configuration/env vars and operational policy,
- operational note that `/wc1` default cache root is persistent across deployments and remains configurable.

Acceptance:
- end-to-end consumer path returns cached roads artifact in target EPSG,
- docs + tests pass and tracker/ExecPlan sections updated.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Create module scaffold and contract tests.

    wctl run-pytest tests/topo/test_osm_roads_contracts.py

2. Implement cache backend and TTL/key tests.

    wctl run-pytest tests/topo/test_osm_roads_cache.py

3. Implement service + overpass mock tests (including query batching, GeoJSON artifact output semantics, and expired fallback behavior).

    wctl run-pytest tests/topo/test_osm_roads_service.py

4. Run focused topo regression and full safety suite.

    wctl run-pytest tests/topo -k osm_roads
    wctl run-pytest tests --maxfail=1

5. Validate exception discipline on changed files.

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

6. Lint docs and trackers.

    wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache
    wctl doc-lint --path PROJECT_TRACKER.md
    wctl doc-lint --path AGENTS.md

## Validation and Acceptance

The package implementation is accepted when all of the following are true:

- `OSMRoadsRequest` and `OSMRoadsResult` conform to `module_contract.md`.
- Persistent cache survives restart and serves hits for identical requests.
- Concurrent identical requests cause one upstream fetch.
- Stale-on-error behavior works exactly as contract-defined.
- Expired-on-error behavior is bounded and tested.
- Force-refresh behavior is explicit and tested.
- Returned roads are clipped to AOI and reprojected to requested EPSG.
- Expired cache entries are removable via module cleanup routine.
- Consumer path for `roads_source="osm"` uses this module only (no direct Overpass calls).
- All targeted tests and lint checks pass.

## Idempotence and Recovery

- Cache implementation steps are additive and safe to re-run.
- Schema migrations for cache index must be idempotent (`CREATE TABLE IF NOT EXISTS` and version checks).
- If upstream Overpass is unavailable during tests, mocked-service tests must still validate core behavior.
- If cache metadata corruption is detected, module should fail with `OSMRoadsCacheError` and allow explicit operator cleanup.

## Artifacts and Notes

Keep implementation evidence in this package:

- `notes/` for command transcripts and ad hoc profiling notes.
- `artifacts/` for finalized schema diagrams, example cache entries, and rollout notes.
- Dependency decision record: `artifacts/osmnx_decision.md`.
- Backend architecture decision record: `artifacts/cache_backend_decision.md`.
- Postgres rollout/migration artifact: `artifacts/postgres_migration_setup.md`.

At each milestone completion, update:
- `tracker.md` Task Board,
- `Progress` and `Decision Log` in this ExecPlan,
- `Outcomes & Retrospective` with observed results.

## Interfaces and Dependencies

Module interfaces and cache semantics are normative in:
- `docs/work-packages/20260304_osm_roads_client_cache/module_contract.md`

Dependency policy:
- Prefer existing WEPPpy geospatial/runtime stack.
- Do not add OSMnx as required runtime dependency for this module without a separate dependency evaluation package and evidence.
- Keep failures explicit and typed; do not introduce silent fallback wrappers.

---
Revision Note (2026-03-04, Codex): Initial ExecPlan authored with concrete module targets and implementation milestones aligned to package contract.
Revision Note (2026-03-04, Codex): Added explicit OSMnx dependency decision artifact for future-reference continuity.
Revision Note (2026-03-04, Codex): Incorporated design-review clarifications for tiling/keying, output artifact semantics, cross-process locking, batching strategy, cleanup contract, and force-refresh behavior.
Revision Note (2026-03-05, Codex): Locked hybrid cache architecture (PostgreSQL metadata/locks + `/wc1` payload files) and added bounded expired-on-error fallback semantics.
Revision Note (2026-03-05, Codex): Completed milestones 1-5, added implementation/validation evidence, and synchronized living sections for handoff.
Revision Note (2026-03-05, Codex): Added dedicated Postgres functional integration coverage and a deployment/migration artifact for forest1 and production rollout.
