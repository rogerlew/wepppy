# M3 Run preparation tracker

- Starting revision: e8edf2030.
- Contract checkpoint: both independent reviews approved; see
  [review disposition](artifacts/20260915_contract_reviews.md). Ancestor: e8c40adda.
- Implementation: wired generic first-use acquisition, locked authority callback
  and narrow snapshot rebasing. Existing source pointers remain local-only.
- Tests: pre-fix first-use regression reproduced the defect; final independent
  focused unit/native suite 44 passed (119.47 seconds).
  First full run: 2,988 passed before an outdated native-failure fixture entered
  first-use preparation. Added its missing prepared metadata; restarted full gate.
- Real Run M3 on overpriced-sprawl: passed with initially absent source pointer;
  27,450 events, 12 design and 3 inverse rows available; all 410,121 cells valid.
  See [live evidence](artifacts/20260915_live_acceptance.md).
- Security/noninterference: independent implementation approval; 2,648 protected
  files unchanged. See [security review](artifacts/20260915_security_review.md)
  and [correctness review](artifacts/20260915_correctness_review.md).
- Docs lint, changed exception gate and whitespace check pass.
- Production test module: 56 passed; canonical postfire archive/restore: 1 passed;
  test-stub completeness passes. Independent review approved the old fixture correction.
- Entire postfire test set: 598 passed, 24 warnings in 182.08 seconds. Final
  independent security evidence disposition passed with no open medium/high findings.
- Implementation/evidence commit: 74647327c. Observe-only quality report is
  retained in artifacts; new helper is 54 SLOC, no new red/yellow hotspot.
  Existing production maximum-function length is unchanged. Radon unavailable,
  so no Python cyclomatic-complexity claim is made.

## Closeout — 2026-09-15

Final `wctl run-pytest tests --maxfail=1 -q --tb=short`: **8,632 passed,
103 skipped, 3,129 warnings, 12 subtests passed in 1,082.38 seconds**. This
supersedes the earlier fixture-related failure. Entire postfire suite, archive
regression, docs lint, stub completeness and changed-exception checks pass.
No open correctness/security findings. The live basin is left with current,
nonpartial M3 results. Existing area-range warning remains; no production
deployment or changes to scientific parameters, soils or shared caches.

Durable decision: module `docs/production_m3_runtime.md`, section
“2026-09-15 Run-preparation amendment”; user-facing instructions are in the module
README. Closed 20260914 history was not modified. Existing unrelated root code
quality report edits were preserved.
