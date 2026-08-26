# Tracker - Batch Runner OMNI Selective Retry

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-06 20:30 UTC

**Closed**: 2026-08-06 21:18 UTC

**Current phase**: Closed - design rejected

**Next milestone**: None; full OMNI scenario rerun remains required

**Security impact**: none (no implementation)

**Dedicated security review**: not applicable

## Task Board

### Done

- [x] Characterized the destructive Batch Runner OMNI reset and existing
  scenario freshness behavior. (2026-08-06 20:30 UTC)
- [x] Drafted and independently reviewed a selective-retry design.
  (2026-08-06 21:18 UTC)
- [x] Operator rejected the revised selective-retry contract before checkpoint
  commit or production implementation. (2026-08-06 21:18 UTC)
- [x] Withdrew the proposed canonical amendments and closed the package around
  the full-rerun decision. (2026-08-06 21:18 UTC)

## Decision Log

### 2026-08-06 21:18 UTC: Require a full OMNI scenario rerun

**Context**: Checkpoint review showed that safe scenario-selective retry must
coordinate modeled-year parity, dependent scenario ordering, aggregate output,
OMNI contrasts, active execution admission, path containment, and split-state
recovery. Production multi-watershed iteration is slow.

**Decision**: Do not implement selective scenario preservation or a selective
administrative invalidator. Require the complete OMNI scenario stage to rerun
when regeneration is needed, and treat contrasts as downstream of that complete
scenario set.

**Rationale**: The simpler whole-stage boundary is easier to reason about and
reduces the risk of mixing scenario and contrast artifacts from incompatible
generations.

**Impact**: More model execution is accepted in exchange for coherent outputs
and lower operational complexity. No production code, schema, parameter,
deployment, or production state changed in this package.

## Verification Checklist

- [x] No production implementation files changed.
- [x] No standalone checkpoint commit exists.
- [x] Proposed SURF-02D/GOV-00A-M1H canonical amendments were withdrawn.
- [ ] Documentation lint passes after closure edits.
- [ ] `git diff --check` passes after closure edits.

## Progress Notes

### 2026-08-06 21:18 UTC: Rejected after checkpoint review

**Agent/Contributor**: Repository operator and Codex

**Work completed**:

- Stopped before production implementation.
- Rejected the selective-retry and administrative-invalidation design.
- Recorded full scenario rerun as the required operational boundary.
- Withdrew uncommitted canonical amendments.

**Test results**: Documentation-only closure; no Python tests required.
