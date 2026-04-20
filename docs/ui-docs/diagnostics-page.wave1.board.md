# Diagnostics Wave 1 Parallel Execution Board

Wave 1 corresponds to parallel implementation of:

- `WP-01`: WEPPcloud diagnostics route + page shell
- `WP-05`: Query-engine async bandwidth endpoints

## Parallelization Contract

- Run `WP-01` and `WP-05` concurrently.
- Keep write scopes disjoint to avoid merge conflicts.
- Do not edit shared planning/spec docs in either agent run.

## Write Ownership

- `WP-01` owner:
  - `wepppy/weppcloud/routes/weppcloud_site.py`
  - `wepppy/weppcloud/templates/**`
  - `tests/weppcloud/routes/**`
- `WP-05` owner:
  - `wepppy/query_engine/app/**`
  - `tests/query_engine/**`

## Launch Order

1. Launch WP-01 agent with `docs/ui-docs/diagnostics-page.wp01.prompt.md`.
2. Launch WP-05 agent with `docs/ui-docs/diagnostics-page.wp05.prompt.md`.
3. Wait for both to complete.
4. Integrate both change sets.
5. Run combined validation:
   - `wctl run-pytest tests/weppcloud/routes --maxfail=1 -k diagnostics`
   - `wctl run-pytest tests/query_engine --maxfail=1`
   - `wctl run-pytest tests --maxfail=1` (if practical in session budget)

## Exit Criteria

- Both WPs meet their acceptance criteria from `diagnostics-page.plan.md`.
- No cross-scope file edits occurred.
- No docs/spec drift introduced during Wave 1.

## Execution Snapshot (2026-04-20)

- Subagent execution was attempted repeatedly but failed with transient platform `high demand` errors.
- Wave 1 was completed directly in-thread with disjoint scope adherence:
  - WP-01: WEPPcloud route/template/tests.
  - WP-05: query-engine bandwidth endpoints/tests.
- Validation evidence captured in shell logs:
  - local pytest for new diagnostics route tests passed.
  - query-engine bandwidth-targeted tests passed.
  - full `tests/query_engine` suite passed.
