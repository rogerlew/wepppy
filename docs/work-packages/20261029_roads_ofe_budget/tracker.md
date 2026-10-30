# Roads OFE budget tracker

Complete: scientific execution, reporting and regression closeout.

- 66/66 native runs complete under
  `/wc1/runs/ro/roads-ofe-budget-20261029-v2/factorial-v1`.
- All input hashes, complete WAT calendars, factorial invariants and modern water
  transfers pass; six all-on endpoints reproduce prior native outputs exactly.
- 53/60 terminal ELEMENT/report budgets reconcile; seven failures and 22 EBE
  discrepancies remain explicit. No precision tolerance widened.
- Two selected site-climate unrutted failures remain beyond factor ten across all
  eight combinations. Buffers are major net sources; drainage/storage is next.
- Full repository coverage: 12,151 passed, 298 skipped (including the 16 focused
  budget tests). Docs lint, spelling previews and whitespace checks pass.

See [report](report.md), [validation](artifacts/validation.md),
[output semantics](artifacts/output-semantics.md) and
[self-review](artifacts/review.md). No production parameter changes or deployment.
