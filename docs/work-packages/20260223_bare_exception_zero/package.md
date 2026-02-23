# Bare Exception Zero Closure and Boundary Safety

**Status**: Closed (Phase 2 completed 2026-02-23)

## Overview

Phase 1 of this package removed all production `bare except:` handlers. Phase 2 closes broad-exception boundary debt for:
- `wepppy/weppcloud/routes/**`
- `wepppy/microservices/rq_engine/**`
- `wepppy/rq/**`

After Phase 2, target modules should not need another broad-exception cleanup pass: each remaining broad catch must be a true boundary with logging, canonical contract handling, and explicit allowlist entry.

## Objectives

- Keep global `bare except:` at zero under `tools/check_broad_exceptions.py --json --no-allowlist`.
- Reach zero unresolved broad-exception findings in target modules in allowlist-aware mode.
- Replace non-boundary broad catches with narrow exceptions or remove dead handlers.
- Ensure every remaining target-module broad catch is boundary-justified and allowlisted line-by-line.
- Keep active ExecPlan, tracker, and `PROJECT_TRACKER.md` synchronized at milestone boundaries.

## Scope

### Included

- Broad-exception boundary closure for `weppcloud/routes`, `rq_engine`, and `rq` modules.
- Classification artifact with per-handler disposition (`boundary`, `narrowable`, `remove`).
- Targeted regression/contract tests for changed boundary behavior.
- Allowlist consolidation in `docs/standards/broad-exception-boundary-allowlist.md`.
- Required validation gates and phase closeout documentation.

### Explicitly Out of Scope

- New architecture redesign beyond exception-boundary normalization.
- Broad-exception cleanup in non-target modules.
- Queue topology redesign unless required by exception semantics.

## Stakeholders

- **Primary**: WEPPpy maintainers and AI agents editing runtime boundaries.
- **Reviewer**: Roger.
- **Informed**: WEPPcloud route maintainers, rq-engine maintainers, rq worker maintainers.

## Success Criteria

- [x] Global `bare except:` remains `0` (`--no-allowlist`).
- [x] Target modules report zero unresolved findings in allowlist-aware scan.
- [x] Remaining broad catches in target modules are true boundaries only, logged, contract-safe, and allowlisted.
- [x] Required subsystem targeted tests and final `wctl run-pytest tests --maxfail=1` pass.
- [x] Required artifacts are present under `docs/work-packages/20260223_bare_exception_zero/artifacts/`.

## Dependencies

### Prerequisites

- Root and subsystem AGENTS guidance (`AGENTS.md`, `wepppy/weppcloud/AGENTS.md`, `wepppy/microservices/rq_engine/AGENTS.md`, `tests/AGENTS.md`).
- ExecPlan template requirements (`docs/prompt_templates/codex_exec_plans.md`).
- Canonical contracts: `docs/schemas/rq-response-contract.md`.
- Canonical boundary allowlist: `docs/standards/broad-exception-boundary-allowlist.md`.

### Blocks

- Follow-on hardening work that assumes broad-boundary closure in target modules.

## Related Packages

- **Related**: [20260222_broad_exception_elimination](../20260222_broad_exception_elimination/package.md)

## Timeline Estimate

- **Expected duration**: 1-2 days (Phase 2).
- **Complexity**: High.
- **Risk level**: High (route and worker boundary contract risk).

## References

- `tools/check_broad_exceptions.py`
- `docs/standards/broad-exception-boundary-allowlist.md`
- `docs/schemas/rq-response-contract.md`
- `docs/work-packages/20260223_bare_exception_zero/prompts/active/bare_exception_zero_execplan.md`

## Deliverables

- Active ExecPlan: `docs/work-packages/20260223_bare_exception_zero/prompts/active/bare_exception_zero_execplan.md`
- Tracker: `docs/work-packages/20260223_bare_exception_zero/tracker.md`
- Required artifacts:
  - `artifacts/baseline_broad_exceptions.json`
  - `artifacts/postfix_broad_exceptions.json`
  - `artifacts/target_module_classification.md`
  - `artifacts/final_validation_summary.md`

## Follow-up Work

- Revisit allowlisted boundaries at expiry/revisit dates for continued narrowing opportunities.

## Phase History

### Phase 1 (Closed 2026-02-23)

Removed all production `bare except:` handlers (`82 -> 0`), passed hard bare gate and full-suite regression sanity, and synchronized package/docs artifacts.

### Phase 2 (Closed 2026-02-23)

Completed comprehensive broad-exception boundary closure for target modules with required sub-agent orchestration, allowlist consolidation, and validation gates.

Key Phase 2 outcomes:
- Target unresolved findings (allowlist-aware): `516 -> 0`.
- Target broad catches (`--no-allowlist`): `523 -> 475`.
- Global broad catches (`--no-allowlist`): `1066 -> 1018`.
- Global `bare except` stayed at `0`.
