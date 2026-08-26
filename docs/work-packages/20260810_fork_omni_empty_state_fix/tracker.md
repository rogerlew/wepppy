# Tracker - Fork Omni Empty-State Conformance Fix

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-11 00:00 UTC
**Current phase**: Closed
**Last updated**: 2026-08-11 00:50 UTC
**Next milestone**: 30-day production observation after a separately authorized deployment
**Security impact**: `high`
**Dedicated security review**: `yes`

## Task Board

### In Progress

- None.

### Ready / Backlog

- None.

### Blocked

- None.

### Done

- [x] Captured canonical Redis tracebacks and host/container layout evidence
  (2026-08-10 23:30 UTC).
- [x] Classified the change as strict conformance to the unchanged SURF-04B
  contract (2026-08-11 00:00 UTC).
- [x] Dispatched independent correctness, QA, and security pre-reviews
  (2026-08-11 00:00 UTC).
- [x] Amended governance and affected user/developer documentation before
  implementation (2026-08-11 00:08 UTC).
- [x] Captured a failing direct regression with the exact production
  `FileNotFoundError('_pups')` traceback before patching production code
  (2026-08-11 00:09 UTC).
- [x] Added the reset-only safe creation helper and absent/empty/populated/
  hostile/race/retry/orchestration regression evidence (2026-08-11 00:12 UTC).
- [x] Closed all correctness, QA, and security findings (2026-08-11 00:18 UTC).
- [x] Attempted monolithic and sharded repository-wide gates and isolated both
  unrelated cross-module failures (2026-08-11 00:49 UTC).
- [x] Closed package with documented external validation exception
  (2026-08-11 00:50 UTC).

## Timeline

- **2026-08-10 21:28-22:09 UTC** - Three checked fork jobs failed on wepp1.
- **2026-08-10 23:30 UTC** - Redis and run-tree triage confirmed the shared
  `FileNotFoundError('_pups')` signature.
- **2026-08-11 00:00 UTC** - Remediation package opened.
- **2026-08-11 00:09 UTC** - New direct regression failed at
  `_open_fork_chain(root_fd, ("_pups", "omni"))` with the production
  `FileNotFoundError` signature.
- **2026-08-11 00:12 UTC** - Minimal patch and first focused suite passed 100 tests.
- **2026-08-11 00:17 UTC** - Review remediation added real reset orchestration
  and Unix-socket ancestor evidence; focused suite passed 102 tests.
- **2026-08-11 00:25 UTC** - First full-suite attempt stopped during fixture
  setup because pytest could not allocate a numbered directory under its shared
  default `/tmp` base; rerun started with a dedicated `mktemp` base directory.
- **2026-08-11 00:42 UTC** - Monolithic run reached 4,463 passed / 61 skipped;
  cwd-leaked peakflow failure passed in isolation.
- **2026-08-11 00:49 UTC** - Sharded run completed one shard at 3,016 passed / 23
  skipped and reached 2,220 passed / 32 skipped in the second before an opt-in
  WBT integration failure; the exact test skips correctly in isolation.
- **2026-08-11 00:50 UTC** - Package closed.

## Decisions

- **2026-08-11 00:00 UTC - Treat absence as a valid state**: Create missing
  `_pups` and `_pups/omni` descriptor-relatively, then verify/open them with the
  existing no-follow boundary. Existing hostile entries still fail. This
  restores the accepted final-state contract without weakening containment.
- **2026-08-11 00:00 UTC - Correct review governance**: Correctness and UX must
  enumerate valid states before security review; security controls must prove
  noninterference with every valid state. Attack-only evidence cannot close a
  product-correctness gate.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Path race between creation and open | High | Descriptor-relative `mkdir`; final `O_DIRECTORY | O_NOFOLLOW` open | Mitigated |
| Existing hostile ancestor is replaced | High | Never replace ancestors; reject existing non-directory entries | Mitigated |
| Unrelated `_pups` content is deleted | High | Create only missing nodes; preservation assertions | Mitigated |
| Tests repeat the populated-fixture blind spot | High | Direct absent/empty/populated/hostile matrix plus orchestration smoke | Mitigated |

## Hardening Signal Log

- **Baseline**: three identical production failures in 41 minutes; focused suite
  reported 85 passed while containing no absent-ancestor case.
- **Post-change**: local focused/review gates pass; production observation is
  pending a separately authorized deployment.
- **Danger signals observed**: security-focused fixtures displaced the ordinary
  never-used-feature state; orchestration tests mocked the failing boundary.
- **Temporary callus register**: none.

## Verification Checklist

- [x] Focused RQ tests pass (102 passed, 4 warnings).
- [x] Repository-wide pytest attempted; unrelated monolithic and sharded
  isolation blockers documented with isolated-test evidence.
- [x] Changed broad-exception enforcement passes.
- [x] Documentation lint passes.
- [x] Correctness review passes with no unresolved findings.
- [x] QA review passes with no unresolved findings.
- [x] Security review passes with no unresolved findings.
- [x] No queue wiring changes; RQ catalog remains unchanged.

## Progress Notes

### 2026-08-11 00:00 UTC - Incident scoping

- Confirmed the code contradicts accepted SURF-04B final-state and idempotence
  requirements; no new product behavior needs ratification.
- Independent correctness and QA pre-reviews both classified the missing
  valid-state coverage as release-blocking.
- Next: write the regression before the production patch, then run focused
  tests and dispatch final reviews.

### 2026-08-11 00:14 UTC - Tests-first implementation

- Ran
  `wctl run-pytest tests/rq/test_project_rq_fork.py::test_reset_fork_omni_directories_creates_absent_ancestors_and_is_idempotent -q`
  before the production edit; it failed with the exact
  `FileNotFoundError: '_pups'` at `project_rq_fork.py:984`.
- Added a reset-only descriptor-relative create/open helper without relaxing
  strict traversal elsewhere.
- Added direct state-matrix and race/retry tests plus a fork orchestration test
  that mocks unrelated controller work but executes the real
  `_reset_fork_omni_directories` boundary.
- Focused result after review remediation: 102 passed, 4 warnings.
- Scoped documentation lint: all changed documentation paths passed with zero
  errors and zero warnings.
- The first full-suite attempt stopped at 169 passed / 13 skipped on a pytest
  temp-directory allocation error, not an assertion. `/tmp` had free inodes but
  the overlay reported 100% block use. A fresh rerun uses the explicit validated
  base `/tmp/wepppy-full-eRrjYB` to isolate pytest numbering.

### 2026-08-11 00:50 UTC - Validation and closeout

- Monolithic repository validation ultimately reached 4,463 passed and 61
  skipped before a relative-path peakflow test failed under leaked cwd; the
  exact test passed alone from the canonical repository directory.
- Canonical sharded validation completed one 3,039-test shard cleanly (3,016
  passed / 23 skipped). The second reached 2,220 passed / 32 skipped before a
  real-WBT integration test ran unexpectedly and failed; alone, without the
  opt-in integration state leaked by its shard, it skipped as designed.
- All fork-focused, review, docs, diff, and broad-exception gates pass. The
  package closes under the hardening standard's documented external-blocker
  allowance without claiming a clean monolithic repository run.
