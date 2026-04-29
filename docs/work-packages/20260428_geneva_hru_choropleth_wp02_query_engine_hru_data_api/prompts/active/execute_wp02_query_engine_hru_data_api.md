# Execute WP02 - Query Engine HRU Data API

Execute after WP01 contract updates are merged and read first:

- `/workdir/wepppy/AGENTS.md`
- `/workdir/wepppy/docs/work-packages/20260428_geneva_hru_choropleth_series/orchestration_board.md`
- `/workdir/wepppy/docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/package.md`
- `/workdir/wepppy/docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/tracker.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md` (section `12.4`)

Required outcomes:
1. Materialize `geneva/hru_event_measure_rows.parquet` per the WP01 schema contract.
2. Implement a run-scoped retrieval path for event+measure-filtered HRU rows using query-engine-style API patterns.
3. Enforce HRU map measure scope: allow `runoff_depth` and `runoff_volume`; reject `peak_discharge` with `unsupported_measure_scope`.
4. Return contract-compliant unavailable responses for legacy runs without the artifact (`reason_code=legacy_hru_event_measures_missing`).
5. Validate join-key integrity across `storm_id`, `hru_id`, and legend crosswalk `hru_value <-> hru_id`.

Open WP02 implementation decisions to resolve explicitly in tracker Decision Log:
- Query surface shape: dedicated HRU map query endpoint vs extension of existing Geneva query surface.
- Availability/error envelope placement in response payload.
- Artifact production timing: during `run_batch` vs post-run materialization step.

Execution constraints:
- Keep changes additive/backward-compatible.
- Do not change watershed-level `peak_discharge` semantics.
- Do not introduce unrelated query-engine or report-shell refactors.

Validation commands (minimum; expand as needed for touched files):
- `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- `wctl run-pytest tests/query_engine --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api`
- `git diff --check`

Lifecycle updates required:
- Update WP02 `tracker.md` with UTC-stamped evidence.
- Update series `orchestration_board.md` and tracker status.

Finish with:
- changed files
- behavior delta
- validation command results
- residual risks/blockers for WP03
