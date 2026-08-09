# Tracker - Execute the Frozen Topanga Peak-Flow Census

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-09 05:17 UTC
**Current phase**: Scaffolded; execution not started
**Last updated**: 2026-08-09 05:17 UTC
**Next milestone**: Freeze compatibility, preflight, and execution-selection contracts
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/20260809_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Write the execution data-compatibility and regression plan before data or
  schema mutations.
- [ ] Verify the frozen plan, binary, authorities, storage, and empty census
  evidence root.
- [ ] Add and test explicit selection-file, bounded-worker, progress, resume,
  aggregation, and validation wiring.
- [ ] Freeze the exact 1,088-trial eligible selection.
- [ ] Execute and reconcile the complete local hillslope census.
- [ ] Aggregate event pairs, candidates, denominators, and local prevalence.
- [ ] Complete scientific, code, QA, and security reviews.
- [ ] Publish the execution disposition and follow-up handoff.

### In Progress

- None.

### Blocked

- [ ] Full-matrix execution is blocked until preflight, compatibility, selection,
  dry-run, and security checkpoint gates pass.
- [ ] Candidate adjudication and watershed routing are outside this package.

### Done

- [x] Preparation GO verified and separately dated execution package scaffolded
  (2026-08-09 05:17 UTC).

## Timeline

- **2026-08-09 05:17 UTC** - Created package, tracker, active ExecPlan, and
  failing initial security gate; no census trial executed.

## Decisions Log

### 2026-08-09 05:17 UTC: Consume the frozen plan without replanning

**Context**: Preparation froze 1,120 requested records, including 1,088
eligible and 32 excluded cover records, before full-census outcomes existed.

**Options considered**:

1. Re-run planning at execution start and accept the newly generated matrix.
2. Execute from the frozen bytes and use regeneration only as a mismatch check.
3. Copy eligible records into an unrelated execution-specific plan.

**Decision**: Use option 2. The execution package consumes the frozen plan
unchanged and freezes a separate explicit selection of its eligible IDs.

**Impact**: Any plan, authority, executable, eligibility, mutation, or screening
change invalidates preparation GO and blocks this package rather than silently
creating a new matrix.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Wrong or partial selection executes | High | Medium | Exact 1,088-ID selection hash and dry-run reconciliation | Open |
| Parallel workers corrupt evidence | High | Low | One trial-owned directory, atomic terminals, bounded workers | Open |
| Retry mixes incompatible attempts | High | Medium | Plan/input/executable/schema hash bindings and preserved attempts | Open |
| Partial execution appears complete | High | Medium | Requested/eligible/terminal reconciliation before aggregation | Open |
| Event absence becomes numeric zero | High | Low | Immutable outer-join parity and null-presence tests | Open |
| Storage exhaustion interrupts runs | High | Medium | Preflight capacity floor, projections, and explicit stopped state | Open |
| Routing or adjudication scope creeps in | Medium | Low | Forbidden-artifact scan and scoped disposition | Open |

## Verification Checklist

### Code and Data

- [ ] Frozen plan and explicit selection hashes match authorities.
- [ ] Compatibility and downstream generated-artifact plan is published.
- [ ] Focused engine and execution tests pass.
- [ ] All terminal and event-pair denominators reconcile.
- [ ] Broad-exception and code-quality checks pass.

### Security

- [x] High security impact recorded for path, subprocess, and concurrency surfaces.
- [ ] Dedicated security review has no unresolved medium/high findings.
- [ ] Source and evidence paths remain root-constrained and symlink-safe.
- [ ] Explicit selection cannot introduce excluded or unknown trials.
- [ ] Subprocesses use the pinned binary and no shell interpretation.

### Documentation

- [x] Package, tracker, active ExecPlan, and security-review scaffold exist.
- [ ] Operator execution, recovery, retention, and disposition docs are synchronized.
- [ ] Documentation lint and spelling normalization pass.

## Progress Notes

### 2026-08-09 05:17 UTC: Execution package scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Verified the preparation GO identifiers and execution boundaries.
- Created the execution package lifecycle documents and initial security hold.
- Recorded that no full-census trial may run before the active plan's checkpoints.

**Blockers encountered**:

- None for scaffolding. Full execution is deliberately held by preflight gates.

**Next steps**:

- Write `artifacts/data-contract-compatibility-plan.md` before changing
  execution schemas or producing census data.
- Implement and validate explicit selection and bounded execution wiring.

**Test results**: Scaffold only; documentation lint is the validation target.

## Watch List

- **Frozen bytes**: do not overwrite or normalize the preparation plan.
- **Evidence root**: preserve prior attempts and never delete terminal evidence.
- **Scientific language**: candidates are screened signals, not adjudicated
  mechanisms or downstream effects.
