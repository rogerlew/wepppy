# Tracker - OSM Roads Client with Persistent Server-Side Cache

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-04  
**Current phase**: Closed - implementation complete, prompts archived  
**Last updated**: 2026-03-05  
**Next milestone**: Monitor forest1/production rollout using migration artifact.  
**Implementation plan**: `docs/work-packages/20260304_osm_roads_client_cache/prompts/completed/osm_roads_client_cache_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `module_contract.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-03-04).
- [x] Authored concrete module contract specification with API, cache schema, lock semantics, error contract, and observability requirements (2026-03-04).
- [x] Authored active ExecPlan with milestone-by-milestone implementation/validation sequence (2026-03-04).
- [x] Added end-to-end execution prompt for implementation agent (2026-03-04).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-03-04).
- [x] Updated root `AGENTS.md` active work-package ExecPlan pointer to this package (2026-03-04).
- [x] Added persistent dependency decision artifact documenting why OSMnx is not selected for v1 (`artifacts/osmnx_decision.md`) (2026-03-04).
- [x] Ran docs lint checks for package docs, root AGENTS, and `PROJECT_TRACKER.md` (2026-03-04).
- [x] Incorporated design-review clarifications into contract and active ExecPlan (tiling/keying, output semantics, locking, batching, cleanup, force-refresh) (2026-03-04).
- [x] Locked backend architecture to hybrid cache (PostgreSQL metadata/locks + `/wc1` payloads) and added bounded expired-on-error fallback policy to contract/ExecPlan (2026-03-05).
- [x] Added backend architecture decision artifact for hybrid cache approach (`artifacts/cache_backend_decision.md`) (2026-03-05).
- [x] Implemented `wepppy/topo/osm_roads/` module files (`contracts.py`, `errors.py`, `cache.py`, `overpass.py`, `service.py`, `README.md`) (2026-03-05).
- [x] Implemented TerrainProcessor-style consumer seam at `wepppy/topo/wbt/osm_roads_consumer.py` and exported from `wepppy/topo/wbt/__init__.py` (2026-03-05).
- [x] Added topo test suites: `tests/topo/test_osm_roads_contracts.py`, `tests/topo/test_osm_roads_cache.py`, `tests/topo/test_osm_roads_service.py` (2026-03-05).
- [x] Added dedicated Postgres functional suite `tests/topo/test_osm_roads_postgres_integration.py` and updated `tests/README.md` run guidance (2026-03-05).
- [x] Added PostgreSQL migration/deployment artifact `artifacts/postgres_migration_setup.md` for forest1 and production rollout (2026-03-05).
- [x] Executed validation gates from active prompt/ExecPlan (targeted topo suites, `tests --maxfail=1`, broad-exception check, doc-lint checks) (2026-03-05).
- [x] Archived prompts from `prompts/active/` into `prompts/completed/` and closed package docs (2026-03-05).

## Timeline

- **2026-03-04** - Package created and scoped.
- **2026-03-04** - Module contract specification authored.
- **2026-03-04** - Active ExecPlan and e2e agent prompt authored.
- **2026-03-04** - Project tracker and root AGENTS pointers updated.
- **2026-03-04** - Contract and ExecPlan clarified from external design review feedback.
- **2026-03-05** - Hybrid backend and expired-on-error fallback approach locked.
- **2026-03-05** - Milestones 1-5 implemented; all required validation gates passed.
- **2026-03-05** - Dedicated Postgres functional test and migration/deployment artifact added and validated.
- **2026-03-05** - Work package closed; active prompts archived to `prompts/completed/`.

## Decisions

### 2026-03-04: Prefer direct Overpass client + WEPPpy-owned persistent cache over OSMnx runtime dependency
**Context**: The user asked whether to use OSMnx and how to implement cache.

**Options considered**:
1. Build around OSMnx for Overpass + cache behavior.
2. Build WEPPpy-owned Overpass client/cache contract with deterministic keying and server lock control.

**Decision**: Use WEPPpy-owned module contract and persistent cache; do not make OSMnx a required runtime dependency for this path.

**Impact**: Better control over multi-tenant server cache semantics and lock-safe refresh behavior.

---

### 2026-03-04: Use server-wide file-backed cache (SQLite metadata + GeoParquet payloads) for v1
**Context**: Initial planning phase needed a low-friction baseline cache model.

**Options considered**:
1. Pure in-memory cache.
2. Redis-only cache with ephemeral payloads.
3. File-backed cache with index + payload files.

**Decision**: Adopt file-backed persistent cache with SQLite index and GeoParquet payload storage (superseded on 2026-03-05 by hybrid approach).

**Impact**: Enabled fast contract bootstrap; later replaced to improve long-term concurrency/operations.

---

### 2026-03-04: Capture explicit dependency decision record for OSMnx
**Context**: Requester asked to preserve rationale for future reference.

**Options considered**:
1. Keep rationale only in ephemeral chat history.
2. Keep rationale inline in tracker only.
3. Create a dedicated decision artifact and link it from package docs.

**Decision**: Created `artifacts/osmnx_decision.md` as the canonical reference and linked it from package references/deliverables.

**Impact**: Future agents have a stable, discoverable rationale and revisit criteria without relying on prior chat context.

---

### 2026-03-04: Clarify v1 tiling/keying, locking model, output semantics, and cleanup expectations
**Context**: External plan review identified ambiguity around tile alignment, multi-tile behavior, lock mechanism, cache cleanup, and output-format expectations.

**Options considered**:
1. Keep docs broad and resolve details during implementation.
2. Resolve contract ambiguity before implementation and update active ExecPlan/tracker accordingly.

**Decision**: Update contract/plan now with fixed-origin tiling, request-vs-tile keys, cross-process lock contract, batched Overpass query strategy, explicit GeoParquet-cache/GeoJSON-output semantics, cleanup contract, and force-refresh semantics.

**Impact**: Reduces implementation variance and test ambiguity; improves handoff quality for end-to-end implementation agents.

---

### 2026-03-05: Lock backend architecture to hybrid (PostgreSQL metadata/locks + `/wc1` payload files)
**Context**: Project direction shifted toward long-term reliability and easier lifecycle operations as cache usage scales across projects.

**Options considered**:
1. Keep SQLite/file-index approach.
2. Move fully to PostGIS/Postgres for both metadata and payload geometry storage.
3. Adopt hybrid: Postgres metadata/locking with file payloads on `/wc1`.

**Decision**: Adopt option 3 now. Keep payload files on `/wc1` and use Postgres for metadata state, cleanup coordination, and single-flight locks.

**Impact**: Better multi-process reliability and cleanup ergonomics with minimal payload-format churn; keeps future path open for PostGIS if DB-side spatial querying becomes necessary.

---

### 2026-03-05: Permit bounded expired-cache fallback on upstream failure
**Context**: Upstream Overpass outages/rate limits can otherwise force avoidable failures when a slightly over-TTL cache entry exists.

**Options considered**:
1. Reject all expired entries unconditionally.
2. Allow expired fallback with explicit policy bounds.

**Decision**: Allow expired fallback when upstream fetch fails and age is within `hard_ttl + max_expired_staleness_days`.

**Impact**: Improves availability while bounding stale-data exposure and preserving explicit observability.

---

### 2026-03-05: Keep consumer integration as explicit seam function under `wepppy/topo/wbt/`
**Context**: There is no executable TerrainProcessor class/path in the current repository; only concept documentation exists.

**Options considered**:
1. Invent a new TerrainProcessor runtime class and wire OSM there.
2. Add a strict seam function for existing/future TerrainProcessor-style callers.

**Decision**: Implemented `resolve_roads_source(...)` seam in `wepppy/topo/wbt/osm_roads_consumer.py`.

**Impact**: Enforces `roads_source=\"osm\"` delegation contract now without speculative runtime abstractions.

---

### 2026-03-05: Keep Postgres functional suite opt-in for broad runs but runnable directly as a dedicated test file
**Context**: `wctl run-pytest` does not automatically forward arbitrary shell env vars into the container unless those vars are wired via compose env keys.

**Options considered**:
1. Require env flag always and rely on non-obvious wrapper behavior.
2. Run this integration file only via ad hoc `wctl run-python`/custom commands.
3. Allow direct file invocation to run tests while retaining opt-in gate for broad suite selections.

**Decision**: Implemented option 3 in `tests/topo/test_osm_roads_postgres_integration.py`.

**Impact**: Functional validation remains straightforward on forest (`wctl run-pytest <file>`) without pulling the integration suite into broader default runs.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Overpass rate limits or upstream instability | High | Medium | Retry/backoff, stale-on-error behavior, bounded batched query strategy, explicit timeout controls | Open |
| Concurrent cache fills duplicate work | High | Medium | Per-key single-flight lock contract and lock tests | Open |
| CRS/geometry mismatches produce unusable roads | High | Medium | Strict CRS validation + AOI clip/reproject tests | Open |
| Cache growth exceeds expected disk usage | Medium | Medium | TTL policy + cleanup routines + cache sizing telemetry | Open |
| Large AOIs create excessive tile/query pressure | Medium | Medium | Max tiles per query, request batching, and bounded query-count tests | Open |
| Postgres lock/metadata contention under burst load | Medium | Medium | Advisory-lock timeout/poll tuning, index tuning, and concurrency tests | Open |
| Semantic drift between contract and implementation | Medium | Low | Keep contract doc + ExecPlan as living docs and enforce tests against signatures | Open |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/topo -k osm_roads`
- [x] `wctl run-pytest tests/topo/test_osm_roads_postgres_integration.py`
- [x] `wctl run-pytest tests --maxfail=1`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

### Documentation
- [x] Package docs created (`package.md`, `tracker.md`, `module_contract.md`, archived ExecPlan).
- [x] Runtime/config usage docs updated in relevant module README/docs.
- [x] `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path AGENTS.md`

### Functional Validation
- [x] Repeated identical request returns persistent cache hit.
- [x] Concurrent identical requests result in single upstream fetch.
- [x] Stale cache is served correctly when upstream fails and policy permits.
- [x] Expired cache is served on upstream failure only within bounded policy window.
- [x] Force-refresh attempts upstream even when entry is fresh.
- [x] Multi-tile AOI execution stays within configured query-batch bounds.
- [x] Expired entries are removed by cleanup routine.
- [x] Returned roads are clipped to AOI and in requested target EPSG.

## Progress Notes

### 2026-03-04: Work-package and contract authoring
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and authored:
  - `package.md`
  - `tracker.md`
  - `module_contract.md`
  - active ExecPlan and end-to-end agent prompt
- Added package backlog entry in `PROJECT_TRACKER.md`.
- Switched root active work-package ExecPlan pointer in `AGENTS.md` to this package.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute Milestone 1 implementation scaffold from active ExecPlan.
2. Keep tracker and ExecPlan living sections synchronized during implementation.
3. Add initial tests before integration into TerrainProcessor consumer path.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache` -> pass.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass.
- `wctl doc-lint --path AGENTS.md` -> pass.
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache` -> pass (post-decision-artifact update).

### 2026-03-04: Contract refinement from design review
**Agent/Contributor**: Codex

**Work completed**:
- Updated `module_contract.md` to remove ambiguity on:
  - fixed-origin tile alignment and multi-tile keying semantics,
  - GeoParquet cache payloads versus consumer-facing GeoJSON output artifact,
  - cross-process lock model and SQLite metadata role,
  - batched Overpass strategy for multi-tile misses/stale refresh,
  - cleanup/eviction contract and force-refresh behavior.
- Updated active ExecPlan milestones and acceptance criteria to match contract refinements.
- Updated tracker decisions/risks/task board to reflect clarified implementation requirements.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute Milestone 1 implementation scaffold with updated contract signatures.
2. Start Milestone 2 with keying + cache schema + cleanup scaffolding together.
3. Add focused tests for batching and force-refresh semantics early.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache` -> pass (post-review-incorporation update).

### 2026-03-05: Hybrid backend lock-in
**Agent/Contributor**: Codex

**Work completed**:
- Updated `module_contract.md` to make hybrid architecture canonical:
  - PostgreSQL metadata/lock contract.
  - `/wc1` GeoParquet payload storage contract.
  - bounded expired-on-error fallback semantics.
- Updated active ExecPlan milestones/acceptance criteria for hybrid implementation.
- Updated tracker decisions/task board/risks/functional validation to align with the locked approach.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement Milestone 2 as hybrid cache schema + lock helpers + payload writer.
2. Add advisory-lock concurrency tests and expired-fallback policy tests early.
3. Keep cleanup behavior tied to Postgres metadata scans and payload deletions.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache` -> pass (post-hybrid-lock-in update).

### 2026-03-05: End-to-end implementation and validation
**Agent/Contributor**: Codex

**Work completed**:
- Implemented OSM roads module under `wepppy/topo/osm_roads/`:
  - contracts, typed errors, cache keying/TTL/payload/cleanup helpers,
  - PostgreSQL metadata/advisory-lock backend implementation path,
  - Overpass query + retry/backoff + normalization path,
  - service orchestration for lock-safe refresh, stale/expired fallback, clip/reproject, and request artifact output.
- Added TerrainProcessor-style consumer seam at `wepppy/topo/wbt/osm_roads_consumer.py`.
- Added runtime/config documentation at `wepppy/topo/osm_roads/README.md`.
- Added regression coverage:
  - `tests/topo/test_osm_roads_contracts.py`
  - `tests/topo/test_osm_roads_cache.py`
  - `tests/topo/test_osm_roads_service.py`

**Blockers encountered**:
- None.

**Next steps**:
1. Archive/close active prompt and ExecPlan artifacts in package docs.
2. Monitor production rollout behavior (cache growth, upstream error rates, lock contention).

**Test results**:
- `wctl run-pytest tests/topo/test_osm_roads_contracts.py` -> pass.
- `wctl run-pytest tests/topo/test_osm_roads_cache.py` -> pass.
- `wctl run-pytest tests/topo/test_osm_roads_service.py` -> pass.
- `wctl run-pytest tests/topo -k osm_roads` -> pass.
- `wctl run-pytest tests --maxfail=1` -> pass (`2214 passed, 30 skipped`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass.
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache` -> pass.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass.
- `wctl doc-lint --path AGENTS.md` -> pass.

### 2026-03-05: Postgres functional test hardening and migration artifact
**Agent/Contributor**: Codex

**Work completed**:
- Added/validated dedicated Postgres integration suite:
  - `tests/topo/test_osm_roads_postgres_integration.py`
- Updated integration run guidance in:
  - `tests/README.md`
- Added rollout/migration artifact:
  - `artifacts/postgres_migration_setup.md`
- Added password-secret fallback logic for integration DSN resolution (`/run/secrets/postgres_password`) and dedicated-file invocation behavior.

**Blockers encountered**:
- `wctl run-pytest` did not forward opt-in env var from host shell by default for this toggle.

**Next steps**:
1. Apply `artifacts/postgres_migration_setup.md` rollout steps in forest1/prod deployment workflows.
2. Monitor advisory-lock contention and cache growth during first production rollout window.

**Test results**:
- `wctl run-pytest tests/topo/test_osm_roads_postgres_integration.py -rs` -> pass (`2 passed`).
- `wctl run-pytest tests/topo -k osm_roads_postgres_integration -rs` -> skip without flag (`2 skipped`), as expected.
- `wctl doc-lint --path tests/README.md` -> pass.
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache/artifacts/postgres_migration_setup.md` -> pass.

### 2026-03-05: Package closeout and prompt archival
**Agent/Contributor**: Codex

**Work completed**:
- Archived prompt artifacts from `prompts/active/` to `prompts/completed/`:
  - `osm_roads_client_cache_execplan.md`
  - `run_osm_roads_client_cache_e2e.prompt.md`
- Updated package/tracker status to closed state.
- Updated `terrain_processor.concept.md` to reference the shipped `wepppy/topo/osm_roads/` module and explicit forest1/production PostgreSQL rollout requirement.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute rollout steps from `artifacts/postgres_migration_setup.md` on forest1 and production.
2. Monitor cache growth and advisory-lock contention after rollout.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache` -> pass.
- `wctl doc-lint --path wepppy/topo/wbt/terrain_processor.concept.md` -> pass.

## Communication Log

### 2026-03-04: Work-package request
**Participants**: User, Codex  
**Question/Topic**: Create work-package with clear WEPPpy OSM module contract and detailed ExecPlan.  
**Outcome**: Package scaffold, concrete contract specification, active ExecPlan, and execution prompt were authored and wired into project trackers.
