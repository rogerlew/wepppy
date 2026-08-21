# Security Review - Climate Multiple-Build Finalize Lock

## Metadata

- **Package**: `docs/work-packages/20260820_climate_finalize_lock/`
- **Reviewer**: Pending independent reviewer
- **Date**: Pending
- **Scope reviewed**: NoDb locking, run-tree writes, RQ worker, and climate subprocess paths
- **Commit/branch context**: Pre-implementation scaffold
- **Related artifacts**:
  - Correctness: `artifacts/2026-08-21_correctness_review.md`
  - Code review: Pending
  - QA review: Pending

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: Worker subprocess execution, run-tree files, and shared
  concurrency ownership are high-impact governed surfaces.
- **Threat model assumptions**: Existing authenticated enqueue and validated
  run-root boundaries remain unchanged; no new external input or dependency is
  introduced; the stale-write guard remains strict.
- **Valid states controls must preserve**: See linked correctness review.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | NoDb concurrency | Implementation has not yet proven fresh ownership, atomic finalization, or relevant-input conflict handling | Scaffold | Review implementation and direct concurrency regressions | Open |
| SEC-02 | Medium | Run-tree/subprocess | Collection refactor must not widen paths, inputs, or command composition | Scaffold | Verify unchanged boundaries and failure cleanup | Open |

## Verdict

- **Gate status**: fail
- **Unresolved findings**: High 1; Medium 1; Low 0
- **Release recommendation**: hold

## Validation Evidence

- Automated checks: Pending implementation.
- Manual checks: Pending implementation.

## Residual Risk

- **Accepted residual risks**: None accepted.
- **Follow-up packages/issues**: None currently.

## Sign-off

- **Security reviewer**: Pending
- **Package owner**: Pending
