# Tracker - Climate Multiple-Build Finalize Lock

> Living record for the multiple-interpolated climate stale-write hardening.

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-21 04:23 UTC

**Current phase**: Scoping / contract checkpoint

**Last updated**: 2026-08-21 04:23 UTC

**Next milestone**: Ratify the minimal finalize-lock contract and add failing regressions

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/2026-08-21_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Ratify refresh-on-finalize behavior in the canonical NoDb contract.
- [ ] Add a failing same-size concurrent-rewrite regression for GridMET.
- [ ] Add parity coverage for Daymet multiple-interpolated finalization.
- [ ] Implement collection results and fresh-state finalization.
- [ ] Run focused and full validation.
- [ ] Complete independent correctness, QA, and security reviews.
- [ ] Deploy through the separately authorized canary workflow and observe.

### In Progress

- None; implementation has not started.

### Blocked

- Production implementation is held until the contract checkpoint is reviewed.
- Deployment is outside this scaffold request and requires separate authority.

### Done

- [x] Captured the incident signature and constrained scope (2026-08-21 04:23 UTC).
- [x] Identified the existing culvert finalizer precedent (2026-08-21 04:23 UTC).
- [x] Scaffolded package, tracker, ExecPlan, and review gates (2026-08-21 04:23 UTC).

## Timeline

- **2026-08-21 04:12:03 UTC** - Climate job began collection.
- **2026-08-21 04:13:17 UTC** - `climate.nodb` received a same-size rewrite.
- **2026-08-21 04:15:03 UTC** - Final stale Climate dump was correctly rejected.
- **2026-08-21 04:23 UTC** - Package scaffolded.

## Decisions Log

### 2026-08-21 04:23 UTC: Use a collect-then-finalize lock pattern

**Context**: The current multiple GridMET build holds one hydrated Climate
object across minutes of parallel work and then dumps that stale mutation base.

**Options considered**:

1. Weaken stale-write detection or retry the stale dump.
2. Build a generation/manifests orchestration subsystem.
3. Collect derived results outside the lock, then refresh and finalize under a
   short lock after verifying relevant inputs.

**Decision**: Option 3. It is the smallest pattern conforming to the canonical
NoDb multiple-writer contract.

**Impact**: The implementation must explicitly enumerate input and output
fields; it must not provide generic automatic object merging.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Relevant input comparison omits a field | High | Medium | Explicit build-input snapshot plus GridMET/Daymet parity tests | Open |
| Finalizer overwrites unrelated state | High | Low | Fresh durable rehydrate and derived-field allowlist | Open |
| Lock remains held during expensive work | High | Low | Direct lock-duration regression/instrumentation | Open |
| Partial generated files survive failure | Medium | Existing | Preserve current behavior; do not expand scope without evidence | Accepted baseline |
| GridMET and Daymet diverge | Medium | Medium | Shared semantic contract and separate path tests | Open |

## Hardening Signal Log

- **Baseline health signals**: one observed GridMET build lost its successful
  computation at final persistence due to a same-size concurrent rewrite.
- **Post-change health signals**: pending implementation and canary observation.
- **Danger signals observed**: long-lived mutation base and final dump after
  expensive parallel work.
- **Temporary callus register**: none planned.
- **Softening experiments**: N/A.

## Verification Checklist

### Code Quality

- [ ] Focused NoDb and climate tests pass.
- [ ] Full `wctl run-pytest tests --maxfail=1` passes.
- [ ] Changed-file broad-exception and quality checks recorded.
- [ ] `git diff --check` passes.

### Security

- [ ] NoDb strict stale-write and ownership checks remain unchanged.
- [ ] Worker subprocess inputs and run-tree boundaries remain unchanged.
- [ ] Dedicated review has no unresolved medium/high findings.

### Documentation

- [ ] Contract checkpoint precedes production implementation edits.
- [ ] NoDb docs describe the finalize-lock pattern.
- [ ] Package, tracker, and ExecPlan remain synchronized.

### Testing

- [ ] Unrelated same-size rewrite is preserved.
- [ ] Relevant climate-input rewrite supersedes the finalizer.
- [ ] GridMET and Daymet success paths persist derived outputs.
- [ ] Collection failure performs no final controller mutation.
- [ ] Existing single-climate paths remain unchanged.

### Deployment

- [ ] Local/container validation completed.
- [ ] Canary deployment separately authorized and completed.
- [ ] Fourteen-day observation window started.

## Progress Notes

### 2026-08-21 04:23 UTC: Package scaffolded

**Agent/Contributor**: Codex

**Work completed**:

- Reduced the proposed design to a refresh-on-finalize lock pattern.
- Recorded the exact incident and relevant culvert precedent.
- Defined contract-first, correctness, and security gates.

**Blockers encountered**: None during scaffolding.

**Next steps**:

- Review and ratify the contract checkpoint.
- Write the exact interleaving regressions before production code.

**Test results**: `git diff --check` passed. `wctl doc-lint` was unavailable on
the macOS authoring host (`wctl: command not found`) and remains a Linux
development-environment validation step.

## Watch List

- **Input snapshot completeness**: every value that affects outputs must
  participate in the finalizer conflict decision.
- **Lock duration**: finalization must remain a short read-modify-write
  transaction.
