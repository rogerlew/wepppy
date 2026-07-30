# Tracker - WBT Conditioning Success Diagnostics

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-30
**Current phase**: Complete locally
**Last updated**: 2026-07-30
**Next milestone**: production promotion under the WBT release runbook
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/2026-07-30_security_review.md`

## Task Board

### In Progress

- None.

### Ready

- Production promotion is outside this package.

### Blocked

- Implementation is gated on the reviewed standalone checkpoint ancestor.

### Done

- [x] Reviewed all four algorithms and measured the incident fixture.
- [x] Selected an additive, versioned JSON sidecar boundary.
- [x] Revised the checkpoint to close initial governance and
  operations/security findings.
- [x] Received independent governance and operations/security PASS with no
  remaining blocking, high, or medium findings.
- [x] Implemented and fixture-tested all four WBT sidecars.
- [x] Integrated validation, RQ propagation, and both channel summaries.
- [x] Committed and pushed WBT commits `bd8e0e4` and `ef69a38`.

## Decisions

### 2026-07-30: Show effects, not implementation jargon

The primary summary always states the method, maximum raise, and maximum cut.
Method-specific actions follow in plain language. Pit counts are labelled
“detected low points” for least-cost output. Volumes remain secondary details.

### 2026-07-30: Preserve stage attribution

Flat gradients, single-cell pit filling, residual/fallback filling, ordinary
fills, and breach cuts remain separate. A broad “changed cells” count must not
allow tiny flat increments to obscure a large fill.

### 2026-07-30: No diagnostic warning thresholds

The package reports measured values without classifying them as safe or unsafe.
Threshold policy would require separate operator approval and an ADR.

## Risks

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Diagnostics change numerical output | High | Instrument existing mutations and compare generated rasters | Mitigated |
| Malformed/stale sidecar is shown | High | Remove before run; validate schema/tool/status/finite numbers | Mitigated |
| Paths or raw JSON reach browser | Medium | Publish allowlisted formatted fields only | Mitigated |
| Flat increments inflate impact | Medium | Stage-specific counters and wording | Mitigated |
| Runtime binary omitted from release | High | Build/install/discover/execute and record SHA-256 | Mitigated |

## Verification Checklist

- [x] WBT Rust unit and generated-output tests pass.
- [x] Four WBT fixture executions produce valid sidecars.
- [x] Incident fixture maximum fill is measured from source-to-output delta.
- [x] WEPPpy topo and RQ tests pass.
- [x] Channel and GL controller tests pass.
- [x] Frontend lint/test and generated bundle pass.
- [x] Documentation lint passes.
- [ ] Full Python sanity gate passes at the production-promotion gate.
- [x] Independent final correctness/security reviews have no unresolved
  high/medium findings.

## Progress Notes

### 2026-07-30: Package scaffolded

The package is executing DOM-05B, not either unrelated root-level active
ExecPlan. No implementation files have been edited. The operator explicitly
requested this behavior and authorized execution, commit, and WBT push.

### 2026-07-30: Contract checkpoint passed

Initial reviews found underspecified schema, correlation, atomicity, failure,
fallback, and rollback behavior. The exact diagnostics schema now defines those
boundaries and amends both canonical jobstatus documents. Both independent
post-fix reviews passed with no remaining blocking/high/medium findings.

### 2026-07-30: Completion-summary overwrite conformance fix

Live job `ea906fe3-bb11-4268-bfe7-b63a38274614` confirmed that the worker and
aggregate `jobstatus` response carried the validated fill diagnostic (maximum
raise `379.22729369142326 m`). Both channel controllers rendered it and then
overwrote it during their asynchronous layer refresh. The unchanged contract
requires the diagnostic to remain the successful completion summary. Regression
coverage now verifies the terminal summary after layer refresh; no payload,
schema, threshold, or numerical behavior changes.
