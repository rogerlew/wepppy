# CLIGEN Seed Pipeline Validation Summary

Date: 2026-10-05. Environment: local WEPPpy development stack.

## Results

- Focused Python boundary suite: 464 passed, 28 warnings.
- Broader climate and batch regression sweep: 299 passed, 377 warnings.
- Canonical full Python suite: 10,317 passed, 126 skipped, 4,013 warnings in
  2,834.03 seconds.
- Frontend: lint passed; 113 Jest suites and 923 tests passed.
- Stub gates: test-stub check passed; stubtest passed for all eight configured
  modules.
- Isolation: two randomized-order iterations (seeds 42 and 123) passed, then
  all 14 changed Python test files passed individual isolation checks.
- Documentation: package and affected user/developer docs passed markdown lint;
  usersum contracts and generated index validated across 74 documents.
- RQ graph: 147 dependency edges regenerated for current source line metadata;
  the dependency-graph drift check and catalog lint passed with no semantic edge
  changes.
- Patch hygiene: `git diff --check` passed.

## Generated-Artifact Acceptance

The normalized `canine-liar` acceptance run persisted seed `24680`, logged one
exact `-r24680` native argument, verified the vendored binary and release
sidecar, parsed a fresh 365-row climate, and produced identical SHA-256 hashes
across two queued builds. See
[`2026-10-05_canine_liar_acceptance.md`](2026-10-05_canine_liar_acceptance.md)
for job IDs, hashes, source-preservation evidence, and cleanup details.

## Scope

These results validate the implementation locally. No production deployment
was performed by this work package.
