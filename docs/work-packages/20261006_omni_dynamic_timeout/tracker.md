# Tracker - Omni dynamic timeout

> Living document tracking WRT-02 execution.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-10-06 16:42 UTC  
**Current phase**: Contract checkpoint  
**Last updated**: 2026-10-06 16:54 UTC  
**Next milestone**: Standalone ancestor commit, then implementation  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `artifacts/20261006_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Implement WRT-02 after the checkpoint ancestor exists.
- [ ] Run focused, graph, broad, and documentation validation.
- [ ] Obtain independent final correctness and security reviews.
- [ ] Close and archive the package without claiming deployment.

### In Progress

- [ ] Create the standalone contract checkpoint ancestor commit.

### Blocked

- [ ] Implementation is blocked until the reviewed contract checkpoint is a
  standalone ancestor commit.

### Done

- [x] Package, active ExecPlan, canonical contract delta, and ADR scope amendment
  drafted (2026-10-06 16:42 UTC).
- [x] Production failure and missing deployment diagnosed
  (2026-10-06 16:37 UTC).
- [x] Two independent contract reviews approved all dispositions with no
  blocking findings (2026-10-06 16:54 UTC).

## Timeline

- **2026-10-06 16:37 UTC** - Confirmed the production leaf timed out at 43,200
  seconds and that current WRT-01 does not cover Omni leaves.
- **2026-10-06 16:42 UTC** - Package and contract checkpoint drafted.
- **2026-10-06 16:52 UTC** - Independent reviews held the checkpoint on ordering,
  aggregate-resource, real-serialization, and precision gaps; all findings were
  dispositioned in the contract/package/plan for confirmation.
- **2026-10-06 16:54 UTC** - Both reviewers approved the amended checkpoint.

## Decisions Log

### 2026-10-06 16:42 UTC: Reuse WRT-01 without changing its formula

**Context**: The operator requested that Omni scenarios and contrasts use the
dynamic timeout after the production scenario exceeded the fixed limit.

**Options considered**:

1. Raise all Omni jobs globally, which would hide workload differences.
2. Invent an Omni-specific coefficient, which lacks retained empirical evidence.
3. Apply existing WRT-01 options only to scenario and contrast leaf jobs.

**Decision**: Choose option 3. It is the smallest change matching the request and
preserves the accepted finite workload formula.

**Impact**: Coordinator, compile, finalizer, queue, dependencies, model inputs,
and retry semantics remain unchanged.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Longer leaves consume workers longer | Medium | Medium | Retain finite WRT-01 alarm range and metadata | Open |
| Invalid workload creates a partial graph | High | Low | Calculate once before the first affected leaf enqueue | Open |
| Formula does not cover total Omni overhead | Medium | Medium | Record as acceptance risk; do not change coefficient without evidence | Open |
| Existing fan-out occupies batch workers for longer | Medium | Medium | Preserve scenario/contrast sets, batch size, chaining, conflict checks, and inspect live graph | Open |
| Existing jobs are silently mutated | High | Low | Apply only to newly enqueued jobs | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: affected production scenario failed at exactly
  43,200 seconds.
- **Post-change health signals**: pending implementation and serialized-job
  evidence.
- **Danger signals observed**: WRT-01 is absent from deployed wepp1 and absent
  from Omni leaf enqueue options on current source.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable.

## Verification Checklist

### Code Quality

- [ ] Focused pytest passes.
- [ ] Full `wctl run-pytest tests --maxfail=1` passes.
- [ ] `wctl check-rq-graph` passes and catalog is current.
- [ ] Changed broad-exception enforcement passes.

### Security

- [x] Security impact and rationale recorded.
- [ ] Dedicated security review passes.
- [ ] No unresolved medium/high security findings remain.

### Documentation

- [ ] RQ README, contract, ADR, tracker, and package agree.
- [ ] Package docs lint cleanly.
- [ ] Active ExecPlan is archived with outcome.

### Testing

- [ ] Scenario leaf serialized timeout/metadata verified.
- [ ] Contrast leaf serialized timeout/metadata verified.
- [ ] Single-storm fixed timeout verified.
- [ ] Empty/skipped paths do not require unused workload.
- [ ] Malformed required workload fails before affected leaf enqueue.
- [ ] Dependency edges and fixed non-leaf allowances remain unchanged.

### Generated Artifacts

- [ ] Existing controller workload is read through normal readers.
- [ ] Actual RQ enqueue data is inspected, not inferred from status.
- [ ] Disposable real-Redis jobs are inspected through `job_info` and removed.
- [ ] Exact candidate revision is recorded.
- [ ] Completion remains no stronger than locally validated.

### Deployment

- [ ] Not in package scope; record wepp1 deployment and rerun as follow-up.

## Progress Notes

### 2026-10-06 16:42 UTC: Scaffold and checkpoint draft

**Agent/Contributor**: Codex

**Work completed**:

- Diagnosed the exact production failure and current source gap.
- Drafted WRT-02 package, plan, contract, ADR scope amendment, and checkpoint.

**Blockers encountered**:

- Contract-first implementation gate remains in force until independent review
  and standalone checkpoint commit.

**Next steps**:

- Complete independent contract reviews and disposition findings.
- Commit the checkpoint before touching implementation files.

**Test results**: Not started; implementation is intentionally gated.

## Watch List

- **Whole-leaf overhead**: WRT-01 was fitted to watershed runtime; production
  acceptance must determine whether its finite allowance also covers scenario
  preparation/hillslope overhead without changing the formula in this package.
- **Deployment separation**: local completion does not authorize deployment or
  retry.
- **Timeout cleanup**: WRT-02 does not repair subprocess cleanup after an RQ
  alarm; deployment review must retain that known risk.

## Communication Log

### 2026-10-06 16:42 UTC: Operator authorization

**Participants**: operator and Codex  
**Question/Topic**: Scaffold and execute a work package to patch Omni scenarios
and contrasts to use the dynamic timeout.  
**Outcome**: WRT-02 is authorized to apply unchanged WRT-01 options to new Omni
scenario and contrast leaves.
