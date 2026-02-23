# Bare Exception Zero Closure and Boundary Safety

**Status**: Closed (2026-02-23)

## Overview

Production Python under `wepppy/` and `services/` still contains `bare except:` handlers that can accidentally swallow `BaseException` subclasses and hide real failures. This package removes every remaining production bare handler while preserving route/worker/runtime contracts and documenting any boundary broad catches that must remain explicit.

## Objectives

- Reduce scanner-reported production `bare except:` findings to exactly zero in `tools/check_broad_exceptions.py --no-allowlist` output.
- Start with deferred hotspots (`wepppy/weppcloud/routes/user.py`, `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`) before broader slice cleanup.
- Preserve canonical API/worker contracts and add logging/context where broad boundaries remain.
- Keep active ExecPlan/tracker/project tracker synchronized milestone-by-milestone.

## Scope

### Included

- Production Python under `wepppy/` and `services/` reported by the broad-exception scanner.
- Deferred hotspot review for `user.py` and `inbox_service.py`.
- Boundary allowlist maintenance in `docs/standards/broad-exception-boundary-allowlist.md` (no bare-except entries allowed).
- Validation gates and work-package/project-tracker closeout updates.

### Explicitly Out of Scope

- Non-production test-only exception style cleanup.
- Broad-catch eradication to zero across all production files (only bare-except is hard zero gate in this package).
- Queue topology or API redesign unrelated to exception safety.

## Stakeholders

- **Primary**: WEPPpy maintainers and AI agents touching runtime paths.
- **Reviewers**: Roger.
- **Informed**: WEPPcloud, NoDb, rq-engine, and CAO maintainers.

## Success Criteria

- [ ] `bare except:` count is `0` with `python3 tools/check_broad_exceptions.py --json --no-allowlist`.
- [ ] Changed-file enforcement passes with no per-file broad-catch increase.
- [ ] Deferred files (`user.py`, `inbox_service.py`) are refactored and validated first.
- [ ] Targeted subsystem tests and final `wctl run-pytest tests --maxfail=1` pass.
- [ ] Work-package docs, root tracker pointers, and `PROJECT_TRACKER.md` are consistent at closure.

## Dependencies

### Prerequisites

- Root and subsystem AGENTS guidance (`AGENTS.md`, `wepppy/weppcloud/AGENTS.md`, `wepppy/nodb/AGENTS.md`, `services/cao/AGENTS.md`, `tests/AGENTS.md`).
- ExecPlan authoring standard: `docs/prompt_templates/codex_exec_plans.md`.
- Canonical boundary allowlist: `docs/standards/broad-exception-boundary-allowlist.md`.

### Blocks

- Follow-on exception-hardening packages that assume bare-except closure.

## Related Packages

- **Related**: [20260222_broad_exception_elimination](../20260222_broad_exception_elimination/package.md)

## Timeline Estimate

- **Expected duration**: 1 day.
- **Complexity**: High.
- **Risk level**: High (behavior regression risk in route/NoDb boundaries).

## References

- `AGENTS.md` - global exception and ExecPlan policy.
- `docs/prompt_templates/codex_exec_plans.md` - required ExecPlan structure.
- `docs/standards/broad-exception-boundary-allowlist.md` - deliberate broad-boundary registry.
- `tools/check_broad_exceptions.py` - scanner and changed-file enforcement gate.

## Deliverables

- Active ExecPlan: `docs/work-packages/20260223_bare_exception_zero/prompts/active/bare_exception_zero_execplan.md`.
- Tracker: `docs/work-packages/20260223_bare_exception_zero/tracker.md`.
- Baseline and closeout artifacts under `docs/work-packages/20260223_bare_exception_zero/artifacts/`, including `final_validation_summary.md`.

## Follow-up Work

- Revisit non-bare broad catches in remaining high-risk files with characterization coverage where narrowing is still feasible.

## Closure Notes

**Closed**: 2026-02-23

**Summary**: Bare-exception hard closure was completed end-to-end with required sub-agent orchestration, milestone tracking, and validation gates. Scanner no-allowlist output reached `bare-except = 0` (`82 -> 0`) across production scan scope, changed-file enforcement passed, deferred hotspots (`user.py`, `inbox_service.py`) were handled first, and broad boundary allowlist entries were aligned to real boundary handlers with owner/rationale/expiry retained.

**Lessons Learned**: Parallel disjoint slice workers made large inventory cleanup tractable, but changed-file enforcement can fail from allowlist line drift even without semantic broad-catch growth. Keeping allowlist maintenance in the same milestone as code edits is required for deterministic closure.

**Archive Status**: Closed with artifacts retained under `docs/work-packages/20260223_bare_exception_zero/artifacts/`.
