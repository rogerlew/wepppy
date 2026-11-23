# Large-watershed interchange tracker

## Timeline

- 2026-11-22 23:16 UTC. Recorded PASS failure, confirmed the 32,768-group error and scoped six bulk families, AgFields, streaming outputs, baseline daily and Roads accounting.
- 2026-11-22 23:21 UTC. Reproduced the old failure. Implemented source packing and footer accounting, cross-group identity validation and totalwatsed3 mixed-group selection. Correctness review identified a decoded-length check for mixed spans, incorporated in the final binary.
- 2026-11-22 23:25 UTC. Paired release verified at full source count on one day, and on four real 45-year hillslopes. Native release and targeted WEPPpy tests passed. Broad validation started.

- 2026-11-23 00:12 UTC. Recorded the AgFields source delta in the Roads historical publication ledger. All three publication checks passed on continuation. QA follow-up regressions passed against the same native binary.

- 2026-11-23 00:26 UTC. Broad validation caught a candidate-only MOFE endpoint change in the provisional extension. Restored the shipped slope source in the isolated native build, published the corrected pair on task branches and repeated independent sample comparisons. Final broad run started.

## Recovery and observation

The original job tree still showed the hillslope child failed, watershed modeling started and post-watershed interchange deferred at the time of review. All 47,582 raw inputs in each six required families were present. The failed child is `6b56bb1a-4066-4dd0-b952-594e6fcda338`. Once the coordinated release is installed and the worker startup hash verified, retry that child and observe its dependent stages through publication. Read the final footers, identities, dates and watershed daily totals. Preserve the raw model outputs. Production deployment and a complete 45-year replay remain operational follow-up.

## Decision and evidence

The [compatibility contract](../../../wepppy/wepp/interchange/wepppyo3-interchange-spec.md#data-contract) preserves source order and identity across arbitrary storage boundaries. The [assessment](artifacts/failure-class.md), [validation](artifacts/validation.md) and [independent review](artifacts/20261122_correctness_review.md) record coverage and limits.
