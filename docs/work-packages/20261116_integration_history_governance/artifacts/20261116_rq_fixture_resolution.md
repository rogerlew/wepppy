# RQ fixture-contract repair — 2026-11-16

## Decision and scope

The operator requested resolution of the four retained RQ failures. No operator
decision is needed: the production consumers match the existing RQ job and NoDb
contracts. Repair the local test doubles; do not suppress observer errors or
remove locking in production. No application behavior or queue wiring changes.

Worker tests now provide a nonbatch callable identity, as real RQ jobs do, and
reuse that job double for the injected status-refresh failure. The real batch
failure observer still executes; original traceback and notification assertions
remain intact.

The culvert runner double now models the per-run job mapping and successful
lock-exit persistence. Queue assertions require the replacement job ID to be
persisted after lock release and before enqueue, including injected enqueue
failure. Cleanup/receipt-save failures retain the original mapping and never
enter the mutation lock. Other operations do not mutate the per-run mapping.
This is a narrow recording double, not a claim of real NoDb locking coverage.

## Validation

- `wctl run-pytest tests/rq/test_rq_worker_runid.py tests/rq/test_specialized_admission_contract.py -q`: **81 passed** in 12.69s, including all four previously failing nodes.
- `wctl run-pytest tests/rq/test_batch_outcome.py tests/rq/test_fork_failure.py -q`: **19 passed, 36 skipped** in 11.90s. The skipped cases require the unavailable isolated `redis-server` executable; no real batch-outcome integration pass is claimed.
- `wctl check-test-stubs`: passed.

Validation is scoped to two local test doubles and their neighboring consumers.
No shared harness or production code changed, so a new full repository sweep was
not run. Earlier broad failures remain historical evidence; this repair resolves
the four identified failures without claiming the entire repository is green.
Unrelated working changes remain outside the repair.
