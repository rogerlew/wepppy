# Tracker - Bare Exception Zero Closure and Boundary Safety

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-02-23  
**Current phase**: Closed  
**Last updated**: 2026-02-23  
**Next milestone**: none (package complete)

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package scaffold (`package.md`, `tracker.md`, active prompt path, artifacts directory) (2026-02-23).
- [x] Captured mandatory baseline snapshots (`artifacts/baseline.json`, `artifacts/baseline_no_allowlist.json`) (2026-02-23).
- [x] Spawned required inventory `explorer` and produced risk-ranked disjoint slices (2026-02-23).
- [x] Spawned 4 disjoint parallel `worker` refactor agents with required collaboration note (2026-02-23).
- [x] Spawned dedicated regression/test `worker` and captured validation results (2026-02-23).
- [x] Ran final `explorer` review pass for regressions and contract drift (2026-02-23).
- [x] Removed all scanner-reported production `bare except:` handlers (`82 -> 0`) (2026-02-23).
- [x] Aligned broad-boundary allowlist entries (owner/rationale/expiry retained; no bare entries) (2026-02-23).
- [x] Passed required gates:
  - hard bare gate (`jq -e '.kinds["bare-except"] == 0'`)
  - changed-file enforcement (`--enforce-changed --base-ref origin/master`)
  - targeted subsystem tests and full-suite sanity (`wctl run-pytest tests --maxfail=1`) (2026-02-23).
- [x] Updated trackers for in-progress and done transitions (`PROJECT_TRACKER.md`) and reset root active ad hoc ExecPlan pointer to `none` in `AGENTS.md` (2026-02-23).

## Timeline

- **2026-02-23** - Package created, baselines captured, and active ExecPlan authored.
- **2026-02-23** - Deferred files handled first; four parallel worker slices completed broad/bare cleanup.
- **2026-02-23** - Enforcement issues resolved (new broad catch in `inbox_service.py`; allowlist line drift in `user.py`/`nodb/base.py`).
- **2026-02-23** - Validation gates passed and package closed.

## Decisions

### 2026-02-23: Use four disjoint worker slices for full bare-except coverage
**Context**: Baseline reported 82 production bare catches spread across WEPPcloud, NoDb, mixed wepppy modules, and CAO services.

**Options considered**:
1. Single-worker serial cleanup.
2. Two-worker split by top-level directory.
3. Four-worker disjoint slices aligned to risk hotspots and subsystem ownership.

**Decision**: Use four-worker disjoint slices (WEPPcloud, NoDb, remaining wepppy, CAO services).

**Impact**: Faster closure and reduced file-edit collision risk.

---

### 2026-02-23: Keep bare-except policy absolute with no allowlist escape hatch
**Context**: Hard closure gate required `bare except` to be exactly zero and forbids allowlisting bare handlers.

**Options considered**:
1. Allowlist residual bare handlers at boundaries.
2. Convert all bare handlers to narrow or explicit boundary catches; allowlist only deliberate broad boundaries.

**Decision**: Enforce zero bare handlers with no allowlist exceptions.

**Impact**: Deterministic scanner gate against `BaseException` swallowing.

---

### 2026-02-23: Realign allowlist entries to true boundary handlers after line drift
**Context**: Changed-file enforcement initially failed due allowlist line drift in `user.py` and `nodb/base.py`.

**Options considered**:
1. Add new allowlist entries for drifted lines without rationale review.
2. Re-point existing entries to actual intended boundaries and keep rationale accurate.

**Decision**: Re-point `BEA-20260223-010/011` to `_build_meta`/`_build_map_meta` boundaries and refresh NoDb line numbers.

**Impact**: Enforcement pass restored with auditability preserved.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Contract drift in route boundaries during bulk edits | High | Medium | Deferred hotspots first + route suite validation | Mitigated |
| NoDb lock/persistence behavior regression | High | Medium | Targeted NoDb tests + full-suite rerun after final NoDb edits | Mitigated |
| Hidden broad-catch growth in changed files | Medium | Medium | Enforced `--enforce-changed --base-ref origin/master` | Closed |
| Allowlist line drift after edits | Medium | Medium | Final allowlist synchronization to live line numbers and handlers | Closed |

## Verification Checklist

### Code Quality
- [x] Hard bare gate passes (`--no-allowlist` + jq check).
- [x] Changed-file enforcement passes (`--enforce-changed --base-ref origin/master`).
- [x] `wctl run-pytest tests --maxfail=1` passes.

### Documentation
- [x] ExecPlan living sections updated milestone-by-milestone.
- [x] Tracker reflects completed milestones and validation command outcomes.
- [x] `PROJECT_TRACKER.md` moved this package In Progress -> Done.

### Testing
- [x] Targeted WEPPcloud route tests pass.
- [x] Targeted NoDb tests pass.
- [x] Targeted CAO/service tests pass.

### Deployment / Runtime Safety
- [x] No `bare except:` remains in scanner output.
- [x] Remaining broad boundaries in touched files are documented and contract-safe.
- [x] New/updated allowlist entries include owner, rationale, and expiry.

## Progress Notes

### 2026-02-23: Package bootstrap and parallel execution launch
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and active ExecPlan.
- Captured required baseline artifacts.
- Completed required `explorer` inventory and launched four disjoint worker slices.

**Test results**:
- Baseline commands executed and artifacts written (non-zero exit expected from scanner findings mode).

### 2026-02-23: Milestone closure and gate validation
**Agent/Contributor**: Codex

**Work completed**:
- Integrated worker edits and removed all production `bare except:` handlers.
- Resolved enforcement deltas via one code fix (`inbox_service.py`) and allowlist line/rationale alignment (`user.py`, `nodb/base.py`).
- Added NoDb logging breadcrumbs to avoid silent swallow in allowlisted boundaries.
- Completed required validation gates and generated `artifacts/final_validation_summary.md`.
- Closed package docs and global trackers.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes --maxfail=1` -> pass (`228 passed`, after one in-run contract fix).
- `wctl run-pytest tests/nodb --maxfail=1` -> pass (`495 passed, 3 skipped`).
- `wctl run-pytest services/cao/test/services/test_inbox_service.py --maxfail=1` -> pass (`10 passed`).
- `wctl run-pytest tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py --maxfail=1` -> pass (`40 passed`).
- `wctl run-pytest tests --maxfail=1` -> pass (`2057 passed, 29 skipped`) on final state.

## Watch List

- Remaining non-bare broad boundaries in touched files are intentional but should be revisited in follow-up packages for possible narrowing.
- Any future edits to allowlisted handlers must update line numbers and rationale in `docs/standards/broad-exception-boundary-allowlist.md` in the same change.
