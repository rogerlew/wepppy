# Tracker - Omni dynamic timeout

> Living document tracking WRT-02 execution.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-10-06 16:42 UTC  
**Current phase**: Completed with validation exception
**Last updated**: 2026-10-06 19:07 UTC
**Next milestone**: Separately authorize wepp1 deployment and retry
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `artifacts/20261006_security_review.md`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Package, active ExecPlan, canonical contract delta, and ADR scope amendment
  drafted (2026-10-06 16:42 UTC).
- [x] Production failure and missing deployment diagnosed
  (2026-10-06 16:37 UTC).
- [x] Two independent contract reviews approved all dispositions with no
  blocking findings (2026-10-06 16:54 UTC).
- [x] Contract checkpoint committed as `3c8c9c622` (2026-10-06 16:54 UTC).
- [x] Implementation candidate committed as `adff42d6d`; focused suite reports
  `97 passed` (2026-10-06 17:24 UTC).
- [x] Graph, stubs, broad-exception, docs, and exact-candidate real-Redis gates
  pass (2026-10-06 17:25 UTC).
- [x] Independent final correctness and security gates pass with no unresolved
  medium/high findings (2026-10-06 17:29 UTC).
- [x] Functional broad coverage completed with an unrelated catalog-latency
  exception retained; package closed without deployment claims
  (2026-10-06 19:07 UTC).

## Timeline

- **2026-10-06 16:37 UTC** - Confirmed the production leaf timed out at 43,200
  seconds and that current WRT-01 does not cover Omni leaves.
- **2026-10-06 16:42 UTC** - Package and contract checkpoint drafted.
- **2026-10-06 16:52 UTC** - Independent reviews held the checkpoint on ordering,
  aggregate-resource, real-serialization, and precision gaps; all findings were
  dispositioned in the contract/package/plan for confirmation.
- **2026-10-06 16:54 UTC** - Both reviewers approved the amended checkpoint.
- **2026-10-06 17:24 UTC** - Implementation candidate committed.
- **2026-10-06 17:29 UTC** - Independent final correctness and security gates
  passed.
- **2026-10-06 19:07 UTC** - Broad functional coverage reconciled; package
  closed with the unrelated PostgreSQL latency exception retained.

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
| Invalid workload creates a partial graph | High | Low | Calculate once before the first affected leaf enqueue | Mitigated |
| Formula does not cover total Omni overhead | Medium | Medium | Record as acceptance risk; do not change coefficient without evidence | Open |
| Existing fan-out occupies batch workers for longer | Medium | Medium | Preserve scenario/contrast sets, batch size, chaining, conflict checks, and inspect live graph | Accepted operational risk |
| Existing jobs are silently mutated | High | Low | Apply only to newly enqueued jobs | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: affected production scenario failed at exactly
  43,200 seconds.
- **Post-change health signals**: candidate-bound serialized leaves expose
  50,400-second WRT-01 options and preserve fixed non-leaf jobs/dependencies.
- **Danger signals observed**: WRT-01 remains absent from deployed wepp1. Its
  prior absence from current Omni leaf enqueue options is fixed in the candidate.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable.

## Verification Checklist

### Code Quality

- [x] Focused pytest passes.
- [ ] Full `wctl run-pytest tests --maxfail=1` passes.
- [x] Qualified broad result retained: 10,122 passes before unrelated latency
  failure; isolated benchmark pass; 143-test functional continuation pass.
- [x] `wctl check-rq-graph` passes and catalog is current.
- [x] Changed broad-exception enforcement passes.

### Security

- [x] Security impact and rationale recorded.
- [x] Dedicated security review passes.
- [x] No unresolved medium/high security findings remain.

### Documentation

- [x] RQ README, contract, ADR, tracker, and package agree.
- [x] Package docs lint cleanly.
- [x] Active ExecPlan is archived with outcome.

### Testing

- [x] Scenario leaf serialized timeout/metadata verified.
- [x] Contrast leaf serialized timeout/metadata verified.
- [x] Single-storm fixed timeout verified.
- [x] Empty/skipped paths do not require unused workload.
- [x] Malformed required workload fails before affected leaf enqueue.
- [x] Dependency edges and fixed non-leaf allowances remain unchanged.

### Generated Artifacts

- [x] Existing controller workload is read through normal readers.
- [x] Actual RQ enqueue data is inspected, not inferred from status.
- [x] Disposable real-Redis jobs are inspected through `job_info` and removed.
- [x] Exact candidate revision is recorded.
- [x] Completion remains no stronger than locally validated.

### Deployment

- [x] Not in package scope; record wepp1 deployment and rerun as follow-up.

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

### 2026-10-06 19:07 UTC: Implementation and qualified closeout

**Agent/Contributor**: Codex

**Work completed**:

- Committed WRT-02 as `adff42d6d`, retained exact-candidate real-Redis evidence,
  and obtained independent correctness/security approval.
- Completed focused, graph, stub, broad-exception, docs, and functional-tail
  validation; archived the ExecPlan and closed the local package.

**Blockers encountered**:

- The broad suite did not pass cleanly because unrelated PostgreSQL catalog
  latency benchmarks exceeded their 50 ms delta thresholds under multi-second
  database variance. The original failure passed alone; the functional tail
  passed with four latency benchmarks deselected.

**Next steps**:

- Separately authorize/deploy the candidate to wepp1, then retry and inspect the
  named workload under the production gate.
- Resolve or calibrate the catalog benchmark isolation outside WRT-02 scope.

**Test results**: See `artifacts/validation.md` for exact commands and qualified
broad-suite evidence.

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
