# Diagnostics Wave C Parallel Execution Board

Wave C corresponds to parallel implementation of:

- `WP-02`: client diagnostics core engine + report model
- `WP-03`: auth/session probes
- `WP-04`: realtime websocket probes

## Preconditions

- `WP-01` complete (`/diagnostics/` route + shell)
- `WP-05` complete (query-engine bandwidth endpoints)

## Parallelization Contract

- Run `WP-02`, `WP-03`, and `WP-04` concurrently.
- Keep write scopes disjoint.
- Do not edit `docs/ui-docs/diagnostics-page.spec.md` or `docs/ui-docs/diagnostics-page.plan.md` during implementation unless a contract contradiction is discovered.

## Write Ownership

- `WP-02` owner:
  - `wepppy/weppcloud/templates/diagnostics/diagnostics.htm`
  - `wepppy/weppcloud/static/js/diagnostics/diagnostics-core.js` (and related core/report files)
  - `tests/weppcloud/routes/test_diagnostics_page.py`
- `WP-03` owner:
  - `wepppy/weppcloud/static/js/diagnostics/diagnostics-auth.js`
  - additive auth contract tests only if required (prefer existing suites)
- `WP-04` owner:
  - `wepppy/weppcloud/static/js/diagnostics/diagnostics-realtime.js`
  - additive realtime probe tests

## Merge and Integration Order

1. Land `WP-02` first (core engine and plugin registration API).
2. Rebase/merge `WP-03` onto latest `WP-02`.
3. Rebase/merge `WP-04` onto latest `WP-02` + `WP-03`.
4. Run combined validation and disposition.

## Combined Validation Gate

Run after integration:

- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl run-pytest tests/weppcloud/routes --maxfail=1 -k diagnostics`
- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py --maxfail=1`

If `wctl` services are unavailable, run local equivalents and document service blockers.

## Exit Criteria

- All three WPs satisfy acceptance criteria in `diagnostics-page.plan.md`.
- `diagRunId` contract preserved exactly.
- Auth checks correctly produce `skipped` when unauthenticated.
- Realtime degradations do not mark overall result as blocker-only failure.
- No secret/token leakage in UI or copied JSON report.
