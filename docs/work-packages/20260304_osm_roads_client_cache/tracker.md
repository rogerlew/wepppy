# Tracker - OSM Roads Client with Persistent Server-Side Cache

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-04  
**Current phase**: Discovery complete; module contract/ExecPlan refined for implementation clarity  
**Last updated**: 2026-03-04  
**Next milestone**: Milestone 1 implementation scaffold from active ExecPlan.  
**Implementation plan**: `docs/work-packages/20260304_osm_roads_client_cache/prompts/active/osm_roads_client_cache_execplan.md`

## Task Board

### Ready / Backlog
- [ ] Implement OSM roads module scaffold (`contracts.py`, `service.py`, `cache.py`, `overpass.py`, `errors.py`).
- [ ] Implement persistent cache index + payload store with per-tile key locking and request-level keying.
- [ ] Implement Overpass client with retry/backoff and batched multi-tile query strategy.
- [ ] Implement AOI clip + target-CRS reprojection and output artifact writer.
- [ ] Implement cache cleanup/eviction routine for expired entries and interval-gated execution.
- [ ] Integrate TerrainProcessor `roads_source="osm"` call path with module contract.
- [ ] Add tests (keying, TTL, force-refresh, lock safety, stale-on-error, batching, cleanup, reprojection, integration).
- [ ] Add runtime docs/config docs and rollout notes.

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

## Timeline

- **2026-03-04** - Package created and scoped.
- **2026-03-04** - Module contract specification authored.
- **2026-03-04** - Active ExecPlan and e2e agent prompt authored.
- **2026-03-04** - Project tracker and root AGENTS pointers updated.
- **2026-03-04** - Contract and ExecPlan clarified from external design review feedback.

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
**Context**: Need durable cache across process restarts without mandatory external DB.

**Options considered**:
1. Pure in-memory cache.
2. Redis-only cache with ephemeral payloads.
3. File-backed cache with index + payload files.

**Decision**: Adopt file-backed persistent cache with SQLite index and GeoParquet payload storage.

**Impact**: Simpler deployment, deterministic artifacts, durable cache reuse across runs/users.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Overpass rate limits or upstream instability | High | Medium | Retry/backoff, stale-on-error behavior, bounded batched query strategy, explicit timeout controls | Open |
| Concurrent cache fills duplicate work | High | Medium | Per-key single-flight lock contract and lock tests | Open |
| CRS/geometry mismatches produce unusable roads | High | Medium | Strict CRS validation + AOI clip/reproject tests | Open |
| Cache growth exceeds expected disk usage | Medium | Medium | TTL policy + cleanup routines + cache sizing telemetry | Open |
| Large AOIs create excessive tile/query pressure | Medium | Medium | Max tiles per query, request batching, and bounded query-count tests | Open |
| Semantic drift between contract and implementation | Medium | Low | Keep contract doc + ExecPlan as living docs and enforce tests against signatures | Open |

## Verification Checklist

### Code Quality
- [ ] `wctl run-pytest tests/topo -k osm_roads`
- [ ] `wctl run-pytest tests --maxfail=1`
- [ ] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

### Documentation
- [x] Package docs created (`package.md`, `tracker.md`, `module_contract.md`, active ExecPlan).
- [ ] Runtime/config usage docs updated in relevant module README/docs.
- [x] `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path AGENTS.md`

### Functional Validation
- [ ] Repeated identical request returns persistent cache hit.
- [ ] Concurrent identical requests result in single upstream fetch.
- [ ] Stale cache is served correctly when upstream fails and policy permits.
- [ ] Force-refresh attempts upstream even when entry is fresh.
- [ ] Multi-tile AOI execution stays within configured query-batch bounds.
- [ ] Expired entries are removed by cleanup routine.
- [ ] Returned roads are clipped to AOI and in requested target EPSG.

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

## Communication Log

### 2026-03-04: Work-package request
**Participants**: User, Codex  
**Question/Topic**: Create work-package with clear WEPPpy OSM module contract and detailed ExecPlan.  
**Outcome**: Package scaffold, concrete contract specification, active ExecPlan, and execution prompt were authored and wired into project trackers.
