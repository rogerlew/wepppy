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
- [ ] Milestone 1: Create module scaffold and wire contract-level public interfaces.
- [ ] Milestone 2: Implement persistent cache backend (index, payloads, keying, TTL, cleanup).
- [ ] Milestone 3: Implement Overpass client, batched query strategy, and normalization/clip/reproject pipeline.
- [ ] Milestone 4: Implement cross-process lock-safe cache fill/refresh and stale-on-error behavior.
- [ ] Milestone 5: Integrate TerrainProcessor consumer seam and add tests/docs.

## Surprises & Discoveries

- Observation: `terrain_processor.concept.md` already codifies a server-wide cache requirement and separation of OSM roads module from TerrainProcessor implementation.
  Evidence: `wepppy/topo/wbt/terrain_processor.concept.md` (`OSM Roads Module` section).

- Observation: Existing WEPPpy guidance explicitly discourages speculative dependency additions and asks for owned-stack preference.
  Evidence: Root `AGENTS.md` dependency/performance discipline section.

## Decision Log

- Decision: Treat `module_contract.md` as the source of truth for signatures and cache semantics.
  Rationale: Keeps implementation and tests anchored to one concrete contract document.
  Date/Author: 2026-03-04 / Codex.

- Decision: Use persistent file-backed cache in v1 (SQLite index + GeoParquet payloads).
  Rationale: Durable and deployable without requiring additional external infrastructure.
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
  Rationale: Avoids SQLite lock-coordination ambiguity and ensures safety across worker processes.
  Date/Author: 2026-03-04 / Codex.

## Outcomes & Retrospective

Initial planning deliverables are complete: package scaffold, contract, tracker, and active ExecPlan. Implementation is not started.

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

Implement cache index and payload storage:
- deterministic tile/request key builders,
- SQLite index schema and CRUD (WAL + busy-timeout),
- payload read/write abstraction (GeoParquet),
- TTL decision function (fresh/stale/expired + force-refresh semantics),
- cleanup/eviction routine for expired entries.

Acceptance:
- repeated same request key resolves same cache record,
- restart-safe persistence validated in tests,
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
- cross-process lock acquire/release with timeout,
- wait/poll behavior for concurrent callers,
- stale-on-error return when policy and TTL permit,
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

3. Implement service + overpass mock tests (including query batching and GeoJSON artifact output semantics).

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
- Force-refresh behavior is explicit and tested.
- Returned roads are clipped to AOI and reprojected to requested EPSG.
- Expired cache entries are removable via module cleanup routine.
- Consumer path for `roads_source="osm"` uses this module only (no direct Overpass calls).
- All targeted tests and lint checks pass.

## Idempotence and Recovery

- Cache implementation steps are additive and safe to re-run.
- Schema migrations for cache index must be idempotent (`CREATE TABLE IF NOT EXISTS` and version checks).
- If upstream Overpass is unavailable during tests, mocked-service tests must still validate core behavior.
- If cache corruption is detected, module should fail with `OSMRoadsCacheError` and allow explicit operator cleanup.

## Artifacts and Notes

Keep implementation evidence in this package:

- `notes/` for command transcripts and ad hoc profiling notes.
- `artifacts/` for finalized schema diagrams, example cache entries, and rollout notes.
- Dependency decision record: `artifacts/osmnx_decision.md`.

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
