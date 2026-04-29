# Tracker - Geneva HRU Choropleth WP01 (Spec and Contract Updates)

> Living tracker for WP01 contract-definition work.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-29 06:34 UTC  
**Current phase**: Completed  
**Last updated**: 2026-04-29 06:43 UTC  
**Next milestone**: Hand off contract to WP02/WP03 implementation packages  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffolded and linked from orchestration board (2026-04-29 06:34 UTC).
- [x] Added Geneva spec section `12.4 HRU Choropleth Measure Contract (WP01 Additive)` with canonical measure-scope matrix (2026-04-29 06:43 UTC).
- [x] Documented watershed-only `peak_discharge` policy and rationale in the measure-scope matrix (2026-04-29 06:43 UTC).
- [x] Defined canonical event/measure/HRU join keys and units, including `hru_map_legend` crosswalk expectations (2026-04-29 06:43 UTC).
- [x] Defined additive artifact contract `geneva/hru_event_measure_rows.parquet` and legacy-run fallback behavior for missing HRU event-measure artifacts (2026-04-29 06:43 UTC).
- [x] Updated series tracker and orchestration board with WP01 completion and gate notes (2026-04-29 06:43 UTC).
- [x] Archived WP01 execution prompt from `prompts/active` to `prompts/completed` with outcome note (2026-04-29 07:03 UTC).

## Timeline

- **2026-04-29 06:38 UTC** - Confirmed baseline Geneva keys/units and existing legend crosswalk (`hru_id`, `hru_value`) from current implementation/tests.
- **2026-04-29 06:43 UTC** - Completed WP01 contract updates in `wepppy/nodb/mods/geneva/specification.md`.
- **2026-04-29 06:43 UTC** - Synchronized WP01 and series lifecycle trackers/orchestration board.

## Decisions Log

### 2026-04-29 06:40 UTC: Keep `peak_discharge` watershed-only
**Context**: HRU choropleth adds event+HRU measure rows for map rendering.

**Decision**: Retain `peak_discharge` as watershed-only (`m3_s`) and explicitly reject it for HRU map scope.

**Rationale**: `peak_discharge` is a watershed-composite hydrograph metric; per-HRU map values would be a non-canonical derived disaggregation.

---

### 2026-04-29 06:41 UTC: Use long-form HRU event-measure table
**Context**: WP02/WP03 need stable query/report contracts for selected measures.

**Decision**: Define `hru_event_measure_rows.parquet` with one row per `(storm_id, hru_id, measure_id)` and explicit `unit`.

**Rationale**: Long-form rows preserve additive extensibility, support measure filtering, and keep units explicit for query/report consumers.
