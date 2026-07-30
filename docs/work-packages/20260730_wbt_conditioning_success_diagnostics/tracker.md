# Tracker - WBT Conditioning Success Diagnostics

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-30
**Current phase**: Checkpoint commit
**Last updated**: 2026-07-30
**Next milestone**: standalone ancestor commit, then WBT implementation
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/2026-07-30_security_review.md`

## Task Board

### In Progress

- [ ] Complete and commit the contract-first checkpoint.

### Ready

- [ ] Implement four WBT diagnostic sidecars and wrappers.
- [ ] Integrate sidecar validation, RQ propagation, and summary presentation.
- [ ] Run focused and broad gates; close review findings.
- [ ] Commit and push `weppcloud-wbt`.

### Blocked

- Implementation is gated on the reviewed standalone checkpoint ancestor.

### Done

- [x] Reviewed all four algorithms and measured the incident fixture.
- [x] Selected an additive, versioned JSON sidecar boundary.
- [x] Revised the checkpoint to close initial governance and
  operations/security findings.
- [x] Received independent governance and operations/security PASS with no
  remaining blocking, high, or medium findings.

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
| Diagnostics change numerical output | High | Instrument existing mutations and compare golden raster hashes | Open |
| Malformed/stale sidecar is shown | High | Remove before run; validate schema/tool/status/finite numbers | Open |
| Paths or raw JSON reach browser | Medium | Publish allowlisted formatted fields only | Open |
| Flat increments inflate impact | Medium | Stage-specific counters and wording | Open |
| Runtime binary omitted from release | High | Build/install/discover/execute and record SHA-256 | Open |

## Verification Checklist

- [ ] WBT Rust unit and generated-output tests pass.
- [ ] Four raster outputs retain baseline hashes.
- [ ] Incident fixture maximum fill is asserted from source-to-output delta.
- [ ] WEPPpy topo and RQ tests pass.
- [ ] Channel and GL controller tests pass.
- [ ] Frontend lint/test and generated bundle pass.
- [ ] Documentation lint passes.
- [ ] Full Python sanity gate passes.
- [ ] Independent final correctness/security reviews have no unresolved
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
