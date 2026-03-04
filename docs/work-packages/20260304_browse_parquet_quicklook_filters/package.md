# Browse Parquet Quick-Look Filter Builder

**Status**: Closed (2026-03-04)

## Overview
Large watershed interchange outputs are often too large for the existing browse table preview and conversion flow, which currently load whole parquet files into memory. This package adds a secure, performant parquet filter workflow so users can define a reusable filter first, then apply it consistently to HTML preview, download, CSV export, and D-Tale launch without needing full-file reads.

The package is scoped to browse microservice and D-Tale integration behavior, with a rollout path designed to minimize regression risk.

## Objectives
- Deliver a user-facing `Parquet Filter Builder` that supports nested boolean logic (`AND`/`OR`) and five operators: `Equals`, `NotEquals`, `Contains`, `GreaterThan`, `LessThan`.
- Apply the same filter contract to all parquet quick-look surfaces: browse HTML table, filtered parquet download, `?as_csv=1` conversion, and D-Tale open.
- Enforce a secure filter pipeline (schema validation, bounded AST complexity, no unsafe SQL string interpolation, explicit errors).
- Preserve current behavior for all non-parquet paths and any requests without filter state.
- Add regression coverage and docs so agents can implement and maintain the feature end-to-end.

## Scope

### Included
- Browse microservice parquet filter parsing/validation and execution.
- Browse template/UI enhancements for filter authoring and filter-state propagation.
- Filter-aware parquet handling in:
  - `browse` HTML table preview
  - `download` parquet endpoint (returns filtered parquet when filter state is active)
  - parquet-to-CSV conversion (`as_csv=1`)
  - `dtale` loader bridge
- Operator semantics:
  - `Contains` uses case-insensitive matching.
  - `GreaterThan` and `LessThan` are numeric-only operators.
  - `GreaterThan` and `LessThan` gracefully exclude missing and `NaN` values instead of failing the whole request.
- Test coverage for happy paths, invalid filters, zero-row results, and auth/security boundaries.
- Work-package docs and execution prompt/plan updates.

### Explicitly Out of Scope
- Query-engine public API redesign.
- Generic filtering for non-parquet file formats.
- Replacing D-Tale itself or adding alternate dataframe viewers.
- Broad UI redesign outside browse-related templates/scripts.

## Stakeholders
- **Primary**: WEPPcloud users who inspect large interchange parquet outputs.
- **Reviewers**: WEPPpy maintainers for browse microservice, D-Tale wrapper, and route/template ownership.
- **Informed**: Project owners and agent implementers consuming the ExecPlan.

## Success Criteria
- [x] Users can build nested `AND`/`OR` parquet filters from browse UI before selecting a parquet action.
- [x] The same filter is applied consistently in HTML preview, download, CSV export, and D-Tale launch.
- [x] Invalid filters return clear, contract-compliant errors; empty selections show explicit zero-row feedback.
- [x] No auth, path-security, or run-scope regressions in browse/download/dtale routes.
- [x] Existing non-filter behavior remains unchanged when no filter is supplied.
- [x] Automated tests cover parser validation, operator semantics, security boundaries, and cross-surface consistency.

## Dependencies

### Prerequisites
- Browse microservice route/auth contracts remain authoritative:
  - `docs/schemas/weppcloud-browse-auth-contract.md`
  - `docs/schemas/weppcloud-csrf-contract.md`
- Existing browse and dtale route test suites in `tests/microservices/`.
- Runtime availability of DuckDB/Parquet stack already used by query-engine and browse conversion paths.

### Blocks
- Any production rollout of filtered quick-look parquet workflows.
- Follow-on UX improvements for advanced query presets tied to browse flows.

## Related Packages
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Related**: [20260224_weppcloud_csrf_rollout](../20260224_weppcloud_csrf_rollout/package.md)
- **Follow-up**: Potential package for filter presets/shared profiles if adopted by users.

## Timeline Estimate
- **Expected duration**: 1-2 weeks.
- **Complexity**: High.
- **Risk level**: Medium-High (cross-surface consistency and large-file performance requirements).

## References
- `wepppy/microservices/browse/browse.py` - Browse Starlette routes, template environment, error handling.
- `wepppy/microservices/browse/flow.py` - File/directory render flow and table preview logic.
- `wepppy/microservices/browse/_download.py` - Download + parquet-to-CSV logic.
- `wepppy/microservices/browse/dtale.py` - Browse-to-D-Tale loader bridge.
- `wepppy/webservices/dtale/dtale.py` - Internal D-Tale dataset loader service.
- `wepppy/weppcloud/routes/browse/templates/browse/directory.htm` - Browse directory UI shell.
- `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm` - HTML table quick-look template.
- `tests/microservices/test_browse_routes.py`
- `tests/microservices/test_download.py`
- `tests/microservices/test_browse_dtale.py`
- `tests/microservices/test_files_routes.py`

## Deliverables
- Archived completed ExecPlan at `prompts/completed/browse_parquet_quicklook_filters_execplan.md` with milestone-level implementation guidance and outcomes.
- Browse/dtale code changes implementing shared parquet filter contract.
- Filter builder UI for browse pages with persisted filter state.
- Updated tests covering new functionality and regressions.
- Updated browse documentation describing filter query contract and behavior.

## Closure Summary
- Package closed on 2026-03-04 after Milestones 1-5 implementation, schema preview UX follow-on, Caddy schema proxy routing, and Playwright parity confirmation for parquet/non-parquet row height.
- Validation evidence is captured at `artifacts/20260304_e2e_validation_results.md`.
- Functional scope is complete; broad-exception enforcement drift in touched legacy files is explicitly deferred to a dedicated follow-up package.

## Follow-up Work
- Evaluate user demand for saved/shared filter presets.
- Add telemetry dashboard for filtered-query latency and zero-row hit rates.
- Consider extending filter support to query-engine console payload helper if this pattern proves effective.
