# Residual Broad-Exception Closure Finish Line

**Status**: Closed (2026-02-24)

## Overview

Close Debt Project #1 residual broad-exception findings for:

- `wepppy/query_engine/app/mcp/router.py`
- `wepppy/weppcloud/app.py`

This package drives an end-to-end closure workflow with mandatory sub-agent orchestration, minimal safe narrowing/removal, focused regression tests, and synchronized closeout docs.

## Objectives

- Reduce allowlist-aware unresolved broad-exception findings to zero for in-scope files.
- Preserve existing API/runtime contracts and request lifecycle behavior.
- Avoid broad scope expansion and speculative refactors.
- Keep changed-file broad-exception enforcement passing.

## Scope

### Included

- Narrow/remove non-boundary broad catches in:
  - `wepppy/query_engine/app/mcp/router.py`
  - `wepppy/weppcloud/app.py`
- Focused tests:
  - `tests/query_engine/test_mcp_router.py`
  - `tests/query_engine/test_server_routes.py`
  - `tests/weppcloud/test_config_logging.py`
  - `tests/test_observability_correlation.py`
- Required scanner/test gates and package artifacts.

### Out of Scope

- Broad-exception cleanup outside the two target files.
- API redesign, queue topology changes, or unrelated observability rewrites.

## Success Criteria

- [x] In-scope allowlist-aware unresolved broad-exception findings = `0`.
- [x] No new silent swallow behavior.
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- [x] Required targeted and full-suite pytest commands pass.
- [x] ExecPlan + tracker + `PROJECT_TRACKER.md` synchronized and closed.

## Deliverables

- `docs/work-packages/20260224_residual_broad_exception_finishline/package.md`
- `docs/work-packages/20260224_residual_broad_exception_finishline/tracker.md`
- `docs/work-packages/20260224_residual_broad_exception_finishline/prompts/active/residual_broad_exception_finishline_execplan.md`
- `docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/baseline_broad_exceptions.json`
- `docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/postfix_broad_exceptions.json`
- `docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/baseline_scope_inventory.md`
- `docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/scope_resolution_matrix.md`
- `docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/final_validation_summary.md`

## References

- `AGENTS.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `wepppy/weppcloud/AGENTS.md`
- `tests/AGENTS.md`
- `tools/check_broad_exceptions.py`

## Closure Notes

- Baseline in-scope unresolved findings (`router.py` + `app.py`): `8`.
- Postfix in-scope unresolved findings (`router.py` + `app.py`): `0`.
- Net in-scope reduction: `-8`.
- Baseline global unresolved findings: `41`.
- Postfix global unresolved findings: `33`.
- Changed-file broad-exception enforcement: PASS (`router.py` base `7` -> current `0`, delta `-7`).
- Required tests:
  - `wctl run-pytest tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py` -> `36 passed`
  - `wctl run-pytest tests/weppcloud/test_config_logging.py tests/test_observability_correlation.py` -> `18 passed`
  - `wctl run-pytest tests --maxfail=1` -> `2107 passed, 29 skipped`
