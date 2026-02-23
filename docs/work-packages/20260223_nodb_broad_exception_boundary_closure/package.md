# NoDb Broad-Exception Boundary Closure

**Status**: Closed (2026-02-23)

## Overview

This package completes broad-exception classification and stabilization for `wepppy/nodb/**` so NoDb does not require another broad-exception cleanup package. The work removes non-boundary broad catches, narrows expected exception handling in internal logic, and constrains remaining broad catches to explicit boundary blocks with logging, rationale comments, and canonical allowlist coverage.

## Objectives

- Reach zero `bare except:` handlers in `wepppy/nodb/**`.
- Reach zero unresolved broad-exception findings in `wepppy/nodb/**` after allowlist application.
- Classify every baseline NoDb broad-catch finding as one of: `narrowed`, `boundary+allowlisted`, or `removed`.
- Preserve NoDb lock/release and persistence invariants while tightening exception handling.
- Close package with synchronized ExecPlan/tracker/project tracker state and validation artifacts.

## Scope

### Included

- Broad-exception inventory, classification, and refactor for `wepppy/nodb/base.py`, `wepppy/nodb/core/**`, and `wepppy/nodb/mods/**`.
- Tests-first characterization for high-risk lock, dump, persistence, and orchestration boundaries.
- NoDb-focused regression updates under `tests/nodb/**` and `tests/nodir/**` when touched.
- Canonical allowlist updates for remaining NoDb broad boundary catches in `docs/standards/broad-exception-boundary-allowlist.md`.
- Full required validation gates and closeout artifacts.

### Explicitly Out of Scope

- Refactors outside `wepppy/nodb/**` except test/doc/allowlist synchronization required by this package.
- Non-exception architectural redesign that changes NoDb public contracts.
- Speculative abstractions for unconfirmed future exception flows.

## Stakeholders

- **Primary**: WEPPpy maintainers and NoDb maintainers.
- **Reviewer**: Roger.
- **Informed**: RQ/runtime maintainers consuming NoDb contracts.

## Success Criteria

- [x] `python3 tools/check_broad_exceptions.py wepppy/nodb --json --no-allowlist` reports `bare-except = 0`.
- [x] `python3 tools/check_broad_exceptions.py wepppy/nodb --json` reports `findings_count = 0`.
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- [x] Required tests pass:
  - `wctl run-pytest tests/nodb`
  - `wctl run-pytest tests/nodir`
  - `wctl run-pytest tests --maxfail=1`
- [x] Required artifacts exist under `artifacts/`.

## Dependencies

### Prerequisites

- Root and subsystem guidance: `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`.
- ExecPlan template: `docs/prompt_templates/codex_exec_plans.md`.
- Checker and policy docs: `tools/check_broad_exceptions.py`, `docs/standards/broad-exception-boundary-allowlist.md`.

### Blocks

- Follow-on NoDb hardening work that assumes clean exception boundary taxonomy.

## Related Packages

- **Related**: [20260223_bare_exception_zero](../20260223_bare_exception_zero/package.md)
- **Related**: [20260222_broad_exception_elimination](../20260222_broad_exception_elimination/package.md)

## Timeline Estimate

- **Expected duration**: 1 day
- **Complexity**: High
- **Risk level**: High (lock and persistence boundary behavior)

## References

- `tools/check_broad_exceptions.py`
- `docs/standards/broad-exception-boundary-allowlist.md`
- `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/prompts/active/nodb_broad_exception_boundary_closure_execplan.md`

## Deliverables

- Active ExecPlan: `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/prompts/active/nodb_broad_exception_boundary_closure_execplan.md`
- Tracker: `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/tracker.md`
- Required artifacts:
  - `artifacts/baseline_nodb_broad_exceptions.json`
  - `artifacts/final_nodb_broad_exceptions.json`
  - `artifacts/nodb_broad_exception_resolution_matrix.md`
  - `artifacts/final_validation_summary.md`

## Follow-up Work

- Revisit allowlisted NoDb boundaries at expiry for further narrowing opportunities.
