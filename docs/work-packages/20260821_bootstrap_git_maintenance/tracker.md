# Tracker – Bootstrap Git Maintenance

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-22 04:45 UTC
**Current phase**: Review and deployment
**Last updated**: 2026-08-22 04:55 UTC
**Next milestone**: merge, publish, and canary benchmark
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/20260822_security_review.md`

## Task Board

### In Progress

- [ ] Merge, publish, and validate on the private canary.

### Ready / Backlog

- [ ] Benchmark a post-maintenance clone and close the package.

### Done

- [x] Implement initial repository maintenance (2026-08-22 04:50 UTC).
- [x] Add command-budget, real-repository preservation, and failure-order
  regression tests (2026-08-22 04:52 UTC).
- [x] Complete correctness and security reviews (2026-08-22 04:55 UTC).

## Decisions Log

### 2026-08-22 04:45 UTC: Reuse the WEPPpy CPU budget

Use `WEPPPY_NCPU`, exposed through WEPPpy's existing `NCPU` constant, for
`pack.threads`. Run normal `git gc` under the Bootstrap-enable lock with bitmap
generation enabled. Do not use `--prune=now`; do not add another tuning variable;
do not change production Compose values.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Maintenance races repository mutation | High | Execute inside the existing Bootstrap-enable Git lock; fixed initial-enable boundary | Mitigated in design |
| Immediate pruning removes concurrently referenced objects | High | Retain Git's normal grace period; prohibit `--prune=now` | Mitigated in design |
| CPU oversubscription | Medium | `pack.threads` equals existing `WEPPPY_NCPU` budget | Mitigated in design |
| Maintenance failure leaves partial enable state | Medium | Git object operations are atomic; job fails visibly and retry remains possible | Mitigated; live retry remains a follow-up |

## Verification Evidence

- `python3 -m py_compile` passed for the changed implementation and test files.
- A direct temporary-repository invocation of the exact 12-thread Git command
  preserved both commit and tree SHA and produced one pack plus one bitmap.
- PR 630 checks: documentation, Markdown, broad-exception guard, and code-quality
  observability passed; stubtest was still pending at this update.
- Targeted pytest regressions are authored but were not executed locally because
  the iMac and `dev-01` do not currently have the WEPPpy test environment. Do not
  record them as passing until a compatible test runner executes them.
