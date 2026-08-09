# Tracker - Execute the Frozen Topanga Peak-Flow Census

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-09 05:17 UTC
**Current phase**: Completed
**Last updated**: 2026-08-09 06:35 UTC
**Next milestone**: Separately governed candidate adjudication or cross-site replication
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/20260809_security_review.md`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None. Candidate adjudication and watershed routing remain outside this package.

### Done

- [x] Preparation GO verified and separately dated execution package scaffolded
  (2026-08-09 05:17 UTC).
- [x] Execution data-contract compatibility and generated-artifact regression
  plan published before code or data changes (2026-08-09 05:45 UTC).
- [x] Frozen plan, selection, staged inputs, observer, paths, and storage passed
  preflight and dry-run; independent interim security review issued GO.
- [x] Bounded eight-worker execution completed 1,088/1,088 terminals with zero
  failed or stopped trials (2026-08-09 06:06 UTC).
- [x] Immutable aggregation reconciled 225,654 event pairs, 11,506 candidate
  rows, all denominators, and 24,265 retained non-lock artifacts.
- [x] Independent scientific, code, QA, and security re-reviews passed with no
  unresolved medium/high findings.
- [x] Final execution disposition published and lifecycle documents synchronized.

## Timeline

- **2026-08-09 05:17 UTC** - Created package, tracker, active ExecPlan, and
  failing initial security gate; no census trial executed.
- **2026-08-09 05:45 UTC** - Froze the additive execution compatibility and
  generated-artifact regression plan; confirmed the frozen plan hash and clean
  worktree, and observed that the evidence parent is absent rather than populated.
- **2026-08-09 05:52 UTC** - Independent security checkpoint issued GO after
  three HOLD/remediation cycles; launched the frozen matrix with eight workers.
- **2026-08-09 06:06 UTC** - Reconciled 1,088 complete terminals and no failures.
- **2026-08-09 06:20 UTC** - Published deterministic outer-pair, candidate,
  denominator, prevalence, and complete storage-inventory evidence; final
  reviews returned HOLDs that are being remediated before disposition.
- **2026-08-09 06:35 UTC** - Closed every review finding, published the PASS
  disposition, synchronized the project board, and archived the ExecPlan.

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

- [x] Frozen plan and explicit selection hashes match authorities.
- [x] Compatibility and downstream generated-artifact plan is published.
- [x] Focused engine and execution tests pass.
- [x] All terminal and event-pair denominators reconcile.
- [x] Broad-exception and code-quality checks pass.

### Security

- [x] High security impact recorded for path, subprocess, and concurrency surfaces.
- [x] Dedicated security review has no unresolved medium/high findings.
- [x] Source and evidence paths remain root-constrained and symlink-safe.
- [x] Explicit selection cannot introduce excluded or unknown trials.
- [x] Subprocesses use the pinned binary and no shell interpretation.

### Documentation

- [x] Package, tracker, active ExecPlan, and security-review scaffold exist.
- [x] Operator execution, recovery, retention, and disposition docs are synchronized.
- [x] Documentation lint passed; spelling normalization was previewed and the
  canonical US `afterward` form was retained.

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
