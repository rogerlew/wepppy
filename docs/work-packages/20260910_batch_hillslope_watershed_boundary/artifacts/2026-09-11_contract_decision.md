# Batch task boundary contract checkpoint

- Starting implementation revision: `0c34afdb5b1b8bd2af88d5a2d41d0f0e7b45ae22`.
- Operator authorization: Roger Lew requested execution of this package in this
  session, including its two-job topology, failure-contract decision, reviews,
  commits/push, Forest deployment and GHCR verification.
- Classification: intended orchestration behavior change; faithful extraction
  of scientific execution. No parameterization change or dependency addition.
- Canonical delta: new `docs/schemas/batch-task-boundary-contract.md`, cross-linked
  from `docs/schemas/rq-response-contract.md`. The watershed job is a gated
  terminal observer on upstream failure, never a consumer of failed output.
- Unchanged applicable authorities: NoDb persistence/concurrency contract,
  scoped NoDb mutation-cache guard standard, artifact observability standard.
- Compatibility/regression plan: preserve terminal metadata schema, timestamp
  retry selection and scientific artifacts; add attempt-specific visible handoff
  receipts and stage job metadata. Validate generated artifacts are retained
  across the boundary, receipt archive/restore and browser access, real RQ
  failures/retries/cancellation, finalizer release, and all directive states.
- Security impact: high (queue wiring and run-tree handoff). Validate identifiers
  and exact predecessor/consumer lineage before mutation. Preserve submission
  locking, conditional deferred reconciliation, NoDb ownership and scoped cache
  invalidation. Do not clear locks in stage two.
- State and exception policy: canonical contract sections “Failure, retry and
  cancellation” and “Compatibility, state matrix and artifacts”. Missing optional
  mods remain valid; invalid/missing prerequisite proof is explicit leaf failure.
- Baseline: Forest, `master`; graph check passed; focused batch retry suite:
  35 passed in 12.43 seconds. Existing dirty code-quality reports are preserved.
- Independent contract reviews and disposition: approved after resolving four
  medium findings; see `2026-09-11_contract_reviews.md`. Implementation must
  wait for reviewed standalone ancestor commit.
