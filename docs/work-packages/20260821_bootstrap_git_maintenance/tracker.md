# Tracker – Bootstrap Git Maintenance

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-22 04:45 UTC
**Current phase**: Closed
**Last updated**: 2026-08-22 05:10 UTC
**Next milestone**: none; periodic maintenance is explicitly deferred
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/20260822_security_review.md`

## Task Board

### Done

- [x] Implement initial repository maintenance (2026-08-22 04:50 UTC).
- [x] Add command-budget, real-repository preservation, and failure-order
  regression tests (2026-08-22 04:52 UTC).
- [x] Complete correctness and security reviews (2026-08-22 04:55 UTC).
- [x] Merge PR 630 and publish immutable runtime image (2026-08-22 05:02 UTC).
- [x] Deploy seven default/batch RQ workers via openWEPP PR 128
  (2026-08-22 05:06 UTC).
- [x] Maintain and benchmark the validation repository; close package
  (2026-08-22 05:10 UTC).

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
- The common runtime workflow run `32552889160` rehydrated and verified all LFS
  assets and published digest `9cb4fed5...aaecf` from merge `e94ead9d`.
- Before rollout, both queues were empty and all eight registered workers were
  idle. Seven replacement default/batch Pods became Ready with zero restarts;
  fork/archive and unrelated workloads retained their prior digest.
- Live maintenance on `manly-systematization` acquired and released the existing
  Bootstrap lock, completed in 27.990 seconds, produced one pack, and preserved
  HEAD, tree, and working-status fingerprints.
- A disposable authenticated clone completed in 4.65 seconds at approximately
  35 MiB/s; Git reported `pack-reused 1153 (from 1)`. The prior clone took 70.8
  seconds after transport tuning and 215-220 seconds before that tuning.
