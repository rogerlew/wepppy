# NFMS-01 independent QA review

Reviewer: `/root/final_qa`, 2026-10-31 UTC. Ancestor: `2b998e08d`.
Actual working code/tests, operator matrix, artifacts and performance reviewed.
Primary transcribed reviewer result; no files edited by reviewer.

## Findings and disposition

QA-01 (medium coverage gap): first-create quarantine alone did not prove fresh
initialization retry or optional absence. Resolved by real matrix state test.
QA-02 (medium coverage gap): transient-cache rebuild was not established by logger
identity test. Resolved by persisted test controller with declared transient field
and real post-load reconstruction hook.
QA-03 (low documentation): remove stale “Candidate comparison pending” in completed
performance evidence; resolved. Discovery matrix pending rows need final candidate
dispositions; now appended, preserving original discovery provenance.

## Evidence assessment

Real serialization/filesystem faults, held references, manual/grouped producers
and exact executable-input parsing establish the changed boundaries. Explicit test
doubles have direct real-file companions. Independent 36-case matrix passed with
actual Redis and zero skips, including resolved state gaps. Logging lifecycle,
intentional direct dump retry, cancellation and ownership interleavings are covered.

Performance evidence records observed ~10–12% locked-update increase and roughly
0.50–0.55 microseconds per field access, workload/concurrent-load limitations and
held-reference fencing rationale. No zero-cost or production-throughput claim.

## Verdict

APPROVE code/test quality; no unresolved medium/high QA findings. Final consumer
matrix/tracker status and broad-gate results are handoff obligations. This verdict
does not certify an uninterrupted full-suite pass, production performance,
deployment or affected-run repair; see `validation.md` for actual gate outcomes.

## Broad-gate compatibility follow-up

The NoDb sweep exposed an ordinary unknown-commit exception-class regression in
_derived_build. Restore the existing _CommitOutcomeUnknown(RuntimeError), chained
from the original storage failure; cancellation remains the original marked signal.
Both paths retain recovery artifacts. An initially omitted restored class definition
was caught by review/focused failure and corrected before the final focused run.
All three reviewers reread and retain local approval; QA verified **51 passed**
in the actual RAP contention/manual-publication rerun. This is existing-contract
conformance, not a new normative decision. Broad outcomes remain in validation.md.

## TTL fixture compatibility follow-up

The old TTL race test simulated a separate process with the same cached singleton.
It now uses a distinct detached controller, records success after persistence,
and asserts only the accepted second writer remains in memory and on disk.
Correctness and QA reviewers approved this test-only clarification; production
locking is unchanged. The complete race module passed 17 tests. Same-singleton
ownership fencing remains covered by the actual-Redis matrix.

## Filesystem fixture follow-up

QA independently approved replacing five global islocked=True stubs with the
existing locked=nullcontext pattern in filesystem-only __new__ doubles. No
production changes or weakened filesystem assertions. Focused root-directory
and actual prelock ownership modules: 17 passed, 10.45 seconds.
