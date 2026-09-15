# M3 Run preparation tracker

- Starting revision: e8edf2030.
- Contract checkpoint: both independent reviews approved; see
  [review disposition](artifacts/20260915_contract_reviews.md). Ancestor: e8c40adda.
- Implementation: wired generic first-use acquisition, locked authority callback
  and narrow snapshot rebasing. Existing source pointers remain local-only.
- Tests: pre-fix first-use regression reproduced the defect; final independent
  focused unit/native suite 44 passed (119.47 seconds). Full Python gate running.
- Real Run M3 on overpriced-sprawl: passed with initially absent source pointer;
  27,450 events, 12 design and 3 inverse rows available; all 410,121 cells valid.
  See [live evidence](artifacts/20260915_live_acceptance.md).
- Security/noninterference: independent implementation approval; 2,648 protected
  files unchanged. See [security review](artifacts/20260915_security_review.md)
  and [correctness review](artifacts/20260915_correctness_review.md).
- Docs lint, changed exception gate and whitespace check pass.
