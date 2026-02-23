# Top Modules Broad-Exception Closure

**Status**: Closed (2026-02-23)

## Overview

Close broad-exception debt for the top remaining production module trees from the latest scanner run. This package drives milestone-based closure with required sub-agent orchestration, boundary classification, allowlist normalization, and validation gates.

## Objectives

- Keep global `bare except:` count at zero.
- Reach zero unresolved broad-exception findings in allowlist-aware mode for the target module scope.
- Complete residual global allowlist-aware broad-exception closure to `findings_count == 0` (Milestone 6).
- Ensure remaining broad catches in scope are treated as deliberate boundaries only and tracked in the canonical allowlist.
- Produce baseline/post-refactor artifacts and milestone evidence for auditability.

## Scope

### Included

- `services/cao/src/cli_agent_orchestrator/**`
- `wepppy/wepp/**`
- `wepppy/weppcloud/**` (non-routes included; routes only when touched by refactor)
- `wepppy/tools/**`
- `wepppy/profile_recorder/**`
- `wepppy/microservices/**` (non-rq_engine)
- `wepppy/nodir/**`
- `wepppy/query_engine/**`
- `wepppy/webservices/**`
- `wepppy/climates/**`

### Explicitly Out of Scope

- Non-target module broad-exception cleanup.
- Queue topology or API contract redesign not required for exception-boundary policy closure.

## Success Criteria

- [x] Global `bare except:` remains zero under `--no-allowlist` hard gate.
- [x] Target module unresolved findings are zero in allowlist-aware mode.
- [x] Global allowlist-aware unresolved findings are zero (`findings_count == 0`).
- [x] Remaining target-module broad catches are boundary-documented and allowlisted.
- [x] Required validation gates and test suites pass.
- [x] ExecPlan, tracker, `PROJECT_TRACKER.md`, and root `AGENTS.md` pointer are synchronized at closeout.

## Deliverables

- Active ExecPlan: `docs/work-packages/20260224_top_modules_broad_exception_closure/prompts/active/top_modules_broad_exception_closure_execplan.md`
- Tracker: `docs/work-packages/20260224_top_modules_broad_exception_closure/tracker.md`
- Required artifacts under `docs/work-packages/20260224_top_modules_broad_exception_closure/artifacts/`:
  - `baseline_allowlist_aware.json`
  - `baseline_no_allowlist.json`
  - `module_resolution_matrix.md`
  - `post_refactor_allowlist_aware.json`
  - `post_refactor_no_allowlist.json`
  - `final_validation_summary.md`
  - `milestone_6_residual_baseline.json`
  - `milestone_6_resolution_matrix.md`
  - `milestone_6_postfix.json`
  - `milestone_6_final_validation_summary.md`

## References

- `AGENTS.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `docs/standards/broad-exception-boundary-allowlist.md`
- `tools/check_broad_exceptions.py`

## Closure Notes

- Target-scope unresolved findings (allowlist-aware): `354 -> 0`.
- Target-scope broad catches (`--no-allowlist`): `680 -> 680` (all in-scope residual broad catches are now allowlisted as deliberate boundaries).
- Global `bare except:` (`--no-allowlist`): `0 -> 0`.
- Milestone 6 residual global unresolved findings (allowlist-aware): `51 -> 0`.
- Global unresolved findings (allowlist-aware): `405 -> 0`.
- Global broad catches (`--no-allowlist`): `974 -> 936` after Milestone 6 narrowing/removal pass.
