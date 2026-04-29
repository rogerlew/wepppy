# Tracker - Geneva HRU Choropleth WP02 (Query Engine HRU Data API)

> Living tracker for WP02 data-access implementation.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-29 06:34 UTC  
**Current phase**: Completed
**Last updated**: 2026-04-29 07:39 UTC
**Next milestone**: Hand off runtime/query contract to WP03 map UI implementation
**Security impact**: `low`  
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
- [x] WP01 contract dependency cleared; package is unblocked for implementation start (2026-04-29 07:03 UTC).
- [x] Materialized `geneva/hru_event_measure_rows.parquet` during `run_batch` from completed storm `hru_excess` rows (2026-04-29 07:08 UTC).
- [x] Added run-scoped event+measure HRU row retrieval using query-engine-style request patterns (`QueryRequest`, catalog activation, `run_query`) (2026-04-29 07:08 UTC).
- [x] Added HRU map measure-scope enforcement: allow `runoff_depth|runoff_volume`; reject `peak_discharge` with `unsupported_measure_scope` (2026-04-29 07:08 UTC).
- [x] Added legacy compatibility for missing HRU artifact: unavailable response with `reason_code=legacy_hru_event_measures_missing` (2026-04-29 07:08 UTC).
- [x] Added join-key integrity checks for `storm_id`, `hru_id`, and legend crosswalk `hru_value <-> hru_id` in materialization/query paths (2026-04-29 07:08 UTC).
- [x] Added route surface `POST /runs/<runid>/<config>/query/geneva/hru_map_rows` and contract tests in Geneva route suite (2026-04-29 07:09 UTC).
- [x] Ran required pytest commands for Geneva NoDb, query-engine, and Geneva route contracts (2026-04-29 07:10 UTC).
- [x] Updated Geneva specification runtime sections (`12.4`, `13.1`, `15`) for WP02 contracts and availability semantics (2026-04-29 07:11 UTC).
- [x] Synchronized series tracker + orchestration board WP02 status/gates (2026-04-29 07:12 UTC).
- [x] Ran required docs/format validation (`wctl doc-lint`, `git diff --check`) with clean results (2026-04-29 07:13 UTC).
- [x] Corrected blank `storm_id` classification for HRU map query from server error (`500`) to `invalid_input` (`400`) and added regression tests (2026-04-29 07:39 UTC).

## Timeline

- **2026-04-29 07:06 UTC** - Started WP02 implementation from WP01 contract baseline.
- **2026-04-29 07:08 UTC** - Completed HRU event-measure artifact materialization and query service implementation.
- **2026-04-29 07:09 UTC** - Completed Geneva route integration and added endpoint contract tests.
- **2026-04-29 07:10 UTC** - Required pytest suites passed (`tests/nodb/mods/geneva`, `tests/query_engine`, `tests/weppcloud/routes/test_geneva_bp.py`).

## Decisions Log

### 2026-04-29 07:07 UTC: Query surface shape
**Context**: WP02 needed HRU map rows with event+measure filters while staying additive and Geneva-scoped.

**Options considered**:
1. Extend existing `GET /query/geneva/summary` payload with HRU row payload branches.
2. Add a dedicated HRU-map query endpoint under the existing Geneva query surface.

**Decision**: Option 2. Added `POST /runs/<runid>/<config>/query/geneva/hru_map_rows`.

**Rationale**: Keeps summary contract stable, isolates HRU-map inputs (`storm_id`, `measure_id`, `include_schema`, `limit`), and remains additive/backward-compatible.

---

### 2026-04-29 07:08 UTC: Availability/error envelope placement
**Context**: Legacy runs can miss HRU event-measure artifacts, and scope validation must remain explicit.

**Decision**:
- Put availability in the successful payload envelope (`availability.status`, `reason_code`, empty `records` when unavailable).
- Keep validation and contract failures in canonical Geneva error envelope (`error.code`, including `unsupported_measure_scope`).

**Rationale**: Separates data-availability state from request/contract errors and allows legacy compatibility without route-level exceptions.

---

### 2026-04-29 07:08 UTC: Artifact production timing
**Context**: HRU rows can be produced either during `run_batch` or via separate post-run materialization.

**Options considered**:
1. Post-run materialization step.
2. Materialize during `run_batch`.

**Decision**: Option 2.

**Rationale**: Reuses in-memory storm kernel outputs (`hru_excess`), avoids additional orchestration, and keeps artifact provenance aligned with `batch_summary`.

## Command Evidence

- `wctl run-pytest tests/nodb/mods/geneva --maxfail=1` -> `66 passed`.
- `wctl run-pytest tests/query_engine --maxfail=1` -> `115 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py --maxfail=1` -> `14 passed`.
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api` -> `3 files validated, 0 errors, 0 warnings`.
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api --path docs/work-packages/20260428_geneva_hru_choropleth_series --path wepppy/nodb/mods/geneva/specification.md` -> `7 files validated, 0 errors, 0 warnings`.
- `git diff --check` -> clean.
