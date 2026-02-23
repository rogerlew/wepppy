# Tracker - Top Modules Broad-Exception Closure

## Quick Status

**Started**: 2026-02-23  
**Current phase**: Closed (Milestone 6 complete)  
**Last updated**: 2026-02-23  
**Next milestone**: none (package complete)

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Milestones 0-5 completed in initial package closure.
- [x] Reopened package for Milestone 6 residual broad-exception closure (`51` unresolved allowlist-aware findings).
- [x] Executed required Milestone 6 orchestration:
  - residual `explorer` inventory/classification,
  - parallel workers A-D with disjoint subsystem ownership,
  - tests/contracts worker,
  - final `explorer` review pass.
- [x] Integrated narrowing/removal refactors across touched modules (`services/cao/ci-samurai`, `services/profile_playback`, `wepppy/all_your_base`, `wepppy/config`, `wepppy/export`, `wepppy/landcover`, `wepppy/locales`, `wepppy/soils`, `wepppy/topo`, `wepppy/watershed_boundary_dataset`).
- [x] Added Milestone 6 residual boundary allowlist entries with owner/rationale/expiry in `docs/standards/broad-exception-boundary-allowlist.md`.
- [x] Published Milestone 6 required artifacts:
  - `artifacts/milestone_6_residual_baseline.json`
  - `artifacts/milestone_6_resolution_matrix.md`
  - `artifacts/milestone_6_postfix.json`
  - `artifacts/milestone_6_final_validation_summary.md`
- [x] Passed required gates:
  - allowlist-aware global closure gate (`findings_count == 0`)
  - bare-exception hard gate (`bare-except == 0`)
  - changed-file enforcement (`--enforce-changed --base-ref origin/master`)
- [x] Passed targeted tests and pre-handoff full-suite sanity.

## Milestones

- [x] Milestone 0: baseline scan + frozen scope + risk-ranked module plan.
- [x] Milestone 1: highest-risk modules (`cao`, `profile_recorder`, `weppcloud`).
- [x] Milestone 2: `wepp` and `query_engine`.
- [x] Milestone 3: `tools`, `microservices`, `nodir`, `webservices`, `climates`.
- [x] Milestone 4: contract/regression tests + allowlist normalization.
- [x] Milestone 5: closure audit + docs/tracker closeout.
- [x] Milestone 6: residual global broad-exception closure to zero unresolved findings.

## Decisions

### 2026-02-23: Milestone 6 uses narrow/remove first, allowlist only for residual true boundaries

**Context**: 51 residual unresolved findings remained in allowlist-aware mode after Milestone 5 closeout.

**Decision**: Apply targeted narrowing/removal where contract-safe, then allowlist only the remaining true boundaries with owner/rationale/expiry.

**Impact**: Reached `findings_count == 0` while reducing no-allowlist broad footprint (`974 -> 936`).

## Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Behavior regression from exception narrowing | High | Medium | Targeted tests + full-suite sanity + final explorer review | Closed |
| Allowlist line drift | Medium | Medium | Final gate reruns and milestone artifacts captured from post-change scans | Closed |
| Boundary over-allowlisting | Medium | Medium | Kept allowlisting to residual true boundaries after narrowing pass | Mitigated |

## Verification Checklist

- [x] Allowlist-aware closure gate passed (`findings_count == 0`).
- [x] Hard bare gate passed (`bare-except == 0`).
- [x] Changed-file enforcement passed.
- [x] Targeted touched-module tests passed.
- [x] `wctl run-pytest tests --maxfail=1` passed.
- [x] `wctl doc-lint` passed for changed docs.

## Progress Notes

### 2026-02-23: Milestone 6 completion

- Baseline unresolved (allowlist-aware): `51`.
- Postfix unresolved (allowlist-aware): `0`.
- Global no-allowlist broad findings: `974 -> 936`.
- Full-suite sanity: `2066 passed, 29 skipped`.
