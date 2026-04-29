# Tracker - Geneva HRU Choropleth Series

> Living orchestration tracker for the Geneva Interactive Summary HRU choropleth implementation series.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-29 06:34 UTC  
**Current phase**: WP02 implementation complete; WP03 unblocked
**Last updated**: 2026-04-29 07:39 UTC
**Next milestone**: Execute WP03 deck.gl map UI + controls
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Execute WP03: deck.gl map UI and themed controls.
- [ ] Execute WP04: validation, docs closure, and rollout evidence.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Confirmed current Geneva state: no persisted per-event HRU measure table; only storm-level summary artifacts are persisted (2026-04-29 06:20 UTC).
- [x] Confirmed `peak_discharge` is computed and persisted at watershed summary level (2026-04-29 06:23 UTC).
- [x] Confirmed gl-dashboard water-measure colormap policy uses `winter` (and `WATAR` uses `jet2`) (2026-04-29 06:25 UTC).
- [x] Authored series package, child package scaffolds, and orchestration board doc (2026-04-29 06:34 UTC).
- [x] Added series entry to `PROJECT_TRACKER.md` backlog (2026-04-29 06:34 UTC).
- [x] Executed WP01 end-to-end (docs/contracts only): measure-scope matrix, watershed-only `peak_discharge` rationale, canonical keys/units, and legacy-run compatibility policy (2026-04-29 06:43 UTC).
- [x] Executed WP02 end-to-end: HRU event-measure artifact materialization, query-engine-style HRU row retrieval, measure-scope enforcement, legacy unavailable behavior, and join-key integrity checks (2026-04-29 07:11 UTC).
- [x] WP02 lifecycle/docs validation completed (`doc-lint`, `git diff --check`) and orchestration gates synchronized (2026-04-29 07:13 UTC).
- [x] Applied post-review WP02 hygiene fixes: blank `storm_id` now returns `400 invalid_input`; package/tracker status docs synchronized (2026-04-29 07:39 UTC).

## Timeline

- **2026-04-29 06:20 UTC** - Current-state data/persistence analysis completed.
- **2026-04-29 06:25 UTC** - Colormap/theming baseline captured from gl-dashboard sources.
- **2026-04-29 06:34 UTC** - Series orchestration docs and child packages created.
- **2026-04-29 06:43 UTC** - WP01 specification and contract updates completed; WP02/WP03 unblocked.
- **2026-04-29 07:11 UTC** - WP02 runtime/query integration completed; WP03 unblocked.

## Decisions Log

### 2026-04-29 06:26 UTC: Keep `peak_discharge` watershed-level
**Context**: HRU choropleth request introduces per-HRU measures for map rendering.

**Options considered**:
1. Add HRU-level `peak_discharge` for map mode.
2. Keep `peak_discharge` as watershed-level summary metric only.

**Decision**: Option 2.

**Impact**: Avoids contract ambiguity and preserves existing Geneva summary semantics.

---

### 2026-04-29 06:28 UTC: Standardize HRU map data retrieval on query-engine patterns
**Context**: Request asks for deck.gl-like API usage and crisp vector map rendering.

**Options considered**:
1. Continue bespoke report route payload only.
2. Use query-engine-based payloads/API patterns aligned with gl-dashboard data fetch style.

**Decision**: Option 2.

**Impact**: Better consistency with existing map/query patterns and simpler future measure expansion.

---

### 2026-04-29 06:41 UTC: Canonicalize HRU map joins via `storm_id` + `hru_id` (+ legend `hru_value`)
**Context**: WP02/WP03 require stable event/measure/geometry joins for query-engine data access and deck.gl rendering.

**Options considered**:
1. Implicit joins derived from mixed row ordering and ad hoc metadata.
2. Explicit join-key contract: event `storm_id`; HRU `hru_id`; raster-value crosswalk via `hru_map_legend`.

**Decision**: Option 2.

**Impact**: Removes ambiguity for WP02 implementation and map renderer wiring while keeping legacy runs backward compatible.

---

### 2026-04-29 07:08 UTC: Produce HRU event-measure artifact during `run_batch`
**Context**: WP02 required new run-scoped data for event+measure map queries.

**Decision**: Materialize `geneva/hru_event_measure_rows.parquet` during `run_batch` from completed storm `hru_excess` rows + frequency-panel event dimensions.

**Impact**: Keeps provenance with existing batch artifacts and avoids post-run orchestration steps.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| HRU identifiers may not align cleanly with vector geometry join keys | High | Medium | Require explicit join-key contract in WP01 and contract tests in WP02 | Open |
| Large event+HRU payloads may degrade report interaction latency | Medium | Medium | Use query-engine filters/limits and add range/stat prequeries; validate in WP04 | Open |
| Map controls diverge from gl-dashboard look-and-feel | Medium | Medium | Reuse gl-dashboard color/theme conventions and document style tokens in WP03 | Open |
| Scope creep into non-map Geneva report redesign | Medium | Medium | Keep package boundaries strict and enforce orchestration board gates | Open |

## Verification Checklist

### Documentation
- [x] Series package docs created.
- [x] Child package docs created.
- [x] Orchestration board created and linked.
- [x] Execution progress reflected for WP01.
- [x] Execution progress reflected for WP02.

### Governance
- [x] `peak_discharge` watershed-level policy captured.
- [x] Specification-update package included as first-class workstream.
- [x] Query-engine strategy captured for data access.
- [x] Colormap baseline captured (`winter` for water measures).

## Progress Notes

### 2026-04-29 06:34 UTC: Series scaffold creation
**Agent/Contributor**: Codex

**Work completed**:
- Created orchestration package `20260428_geneva_hru_choropleth_series`.
- Added `orchestration_board.md` with package dependency/status matrix.
- Created four child packages (WP01-WP04) with scoped package/tracker docs and execution prompts.
- Updated `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute WP01 first (spec + contract updates).
2. Gate WP02/WP03 implementation on WP01 contract merge.
3. Close WP04 after full validation and rollout notes.

**Test results**:
- Documentation scaffolding only; doc-lint pending.

### 2026-04-29 06:43 UTC: WP01 execution closure
**Agent/Contributor**: Codex

**Work completed**:
- Updated Geneva specification with WP01 additive HRU-choropleth contracts (measure scope matrix, join keys, units, legacy-run policy, and additive artifact contract).
- Kept `peak_discharge` explicitly watershed-only with normative rationale.
- Updated WP01 tracker, series tracker, and orchestration board status/gate notes.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute WP02 against the finalized WP01 contract.
2. Add contract tests for legacy-no-artifact and unsupported-measure (`peak_discharge`) paths in WP02.

**Test results**:
- `wctl doc-lint` and `git diff --check` run in WP01 closure phase (see WP01 handoff).

### 2026-04-29 07:11 UTC: WP02 execution closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented `run_batch` materialization for `geneva/hru_event_measure_rows.parquet`.
- Added Geneva HRU map query surface with query-engine-style retrieval and canonical availability envelope.
- Enforced HRU map measure scope (`runoff_depth|runoff_volume`) and explicit rejection for `peak_discharge`.
- Added legacy compatibility (`legacy_hru_event_measures_missing`) and join-crosswalk integrity validation.
- Updated WP02 tracker and orchestration board gate notes.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute WP03 deck.gl integration using the finalized WP02 query contract.
2. Validate UI joins against `hru_id` and legend `hru_value` crosswalk assumptions.

**Test results**:
- `wctl run-pytest tests/nodb/mods/geneva --maxfail=1` passed.
- `wctl run-pytest tests/query_engine --maxfail=1` passed.
- `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py --maxfail=1` passed.
