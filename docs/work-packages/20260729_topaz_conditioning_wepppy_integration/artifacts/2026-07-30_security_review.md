# Security Review - Topaz Conditioning WEPPpy Integration

## Metadata

- **Package**:
  `docs/work-packages/20260729_topaz_conditioning_wepppy_integration/`
- **Reviewer**: Independent operations/security control reviewer
- **Date**: 2026-07-30
- **Scope**: additive channel enum across UI, rq-engine, NoDb, worker, WBT
  subprocess wrapper, run-scoped raster output, and release rollback
- **Revision context**: documentation-only checkpoint based on
  `efd526ef72d13a893b7d3b88dc4aab02a34d6eea`

## Security Triage

- **Impact**: `high`
- **Dedicated review required**: yes
- **Rationale**: an authenticated UI value crosses persistence and RQ worker
  boundaries and selects a native geospatial subprocess operation.

Threat assumptions are that existing run authorization and CSRF controls are
canonical, the WBT sibling repository is the owned binary source, and the
output remains under the active run's `dem/wbt` directory.

## Findings

The initial independent operations/security checkpoint review returned FAIL.
It identified pre-mutation enum validation, the canonical config/run integrity
guard, bounded native-process cleanup, staged rollback, release provenance, and
operation-schema constraints as blocking/high/medium controls. The governance
review also required explicit width 2, exact persisted/default semantics, and
auditable rollback.

All findings are accepted in
`2026-07-30_checkpoint_review_disposition.md`. The independent
operations/security reviewer returned post-fix PASS with no unresolved
blocking, high, or medium checkpoint findings.

## Required Surface Checks

- [x] Existing auth, role, CSRF, endpoint, and queue contracts are unchanged by
  the normative delta.
- [x] The checkpoint requires all four values to be allowlisted before any
  mutation/enqueue and again at the defensive NoDb boundary.
- [ ] Wrapper invocation uses fixed arguments without shell interpolation.
- [ ] Output remains the run-scoped `relief.tif`.
- [ ] Native binary provenance and discovery are verified after installation.
- [ ] Failure is explicit; no silent algorithm fallback exists.
- [ ] NoDb locking/dump/cache behavior remains unchanged.
- [x] Rollback is staged to preserve persisted `topaz`; full removal requires
  separate authorization, auditable migration, and zero-residual proof.
- [x] No secrets, external egress, or new dependency is introduced.
- [ ] Forced timeout proves process-group termination, wait/reap, and no
  surviving native child.
- [ ] Config mismatch and invalid enum prove no controller/timestamp/persistence
  or enqueue mutation in normal and batch/base paths.
- [ ] Relevant frontend, RQ, Python, binary, and docs gates pass.

## Verdict

- **Gate status**: checkpoint PASS; implementation controls remain pending
- **Release recommendation**: hold until reviewed checkpoint and final
  implementation evidence pass
