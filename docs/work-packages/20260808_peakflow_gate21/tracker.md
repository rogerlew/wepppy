# Tracker – Peak-Flow Gate 2.1 Remediation

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-08 21:55 UTC
**Current phase**: Remediation complete; awaiting GO review
**Last updated**: 2026-08-08 22:55 UTC
**Next milestone**: Independent Gate 2.1 disposition
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- [ ] Phase 2 census — held pending an explicit post-remediation GO.

### Done

- [x] Review findings converted into a bounded package (2026-08-08 21:55 UTC).
- [x] WEPP-Forest observer branch pushed (2026-08-08 21:53 UTC).
- [x] Observer corrected and pinned at `ea25ad79` (2026-08-08 22:35 UTC).
- [x] Typed schemas and APPMTH domain diagnostics corrected (2026-08-08 22:44 UTC).
- [x] Complete one-command acceptance passed (2026-08-08 22:53 UTC).

## Timeline

- **2026-08-08 21:55 UTC** – Gate 2.1 package opened; census hold retained.
- **2026-08-08 22:53 UTC** – Both active-trace parity lanes, exact replay,
  1986 fixtures, and inactive control passed; census hold retained for review.

## Decisions Log

### 2026-08-08 21:55 UTC: Provenance authority

**Decision**: Use the final pushed WEPP-Forest observer commit as source
authority and regenerate manifests from it.

**Impact**: The older `f24c957e + patch hash` authority will be superseded for
Gate 2.1 evidence without rewriting the historical Phase 1 record.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Observer changes model outputs | High | Low | Active/inactive byte parity on both lanes | Closed |
| Packet remains fixture-specific | High | Medium | Typed run/hillslope/OFE/call identity | Closed |
| Acceptance script trusts stale artifacts | High | Medium | Regenerate and compare frozen full-precision hashes and replay objects | Closed |

## Hardening Signal Log

- **Baseline health signals**: exact selected replay on two fixtures.
- **Post-change health signals**: active byte parity and exact selected replay.
- **Danger signals observed**: retired `.pass.dat` fixture contract; migrated to `.hbp`.
- **Temporary callus register**: none.
- **Softening experiments**: N/A.

## Verification Checklist

### Documentation

- [x] Package, tracker, ExecPlan, investigation, and artifact guide synchronized.
- [ ] Documentation lint passes.

### Testing

- [x] WEPP-Forest source builds and observer fixtures pass.
- [x] Active marker parity passes for both lanes.
- [x] APPMTH boundary tests pass.
- [x] All committed evidence validates against its schema.
- [x] One-command Gate 2.1 acceptance passes.

## Progress Notes

### 2026-08-08 21:55 UTC: Package initialization

**Agent/Contributor**: Codex

**Work completed**:

- Recorded the HOLD/GO boundary and seven remediation conditions.
- Pushed the existing observer feature branch for durable provenance.

**Next steps**:

- Correct actual branch logging, post-clamp peak capture, and event completeness.

**Test results**: not yet run for remediation.

### 2026-08-08 22:55 UTC: Gate 2.1 acceptance

**Agent/Contributor**: Codex

**Work completed**:

- Pinned the pushed observer source and conforming build manifests.
- Regenerated strict event packets, replay reports, and active parity evidence.
- Verified 1980, 1986, and inactive-control fixtures in one acceptance command.

**Next steps**:

- Obtain an independent GO/HOLD disposition before any pilot or census.

**Test results**: Gate 2.1 acceptance passed; targeted pytest pending final gate.

## Watch List

- **Unrelated WEPPpy changes**: preserve the existing RQ/job-dashboard worktree
  changes and exclude them from remediation commits.
