# NFMS-01 final security review

Reviewer: `/root/final_security`, 2026-10-31 UTC. Checkpoint ancestor `2b998e08d`.
Scope: actual working implementation and regressions, canonical NFMS, manual,
grouped and prelock consumers. Primary transcribed independent review; reviewer
did not edit files or personally execute tests. Triage: high, shared ownership and
state enforcement. Dedicated security review required: yes.

## Findings

| ID | Severity | Finding | Resolution / evidence | Status |
| --- | --- | --- | --- | --- |
| S1 | High | Recovery could install another lock identity or follow rejected identity fields | Captured acquired identity governs recovery/unlock; decoded identity checked; dump rejects identity drift; matrix identity tests | Resolved |
| S2 | Medium | Abandoned failed lock prevented later-thread recovery | Coordinated failed-instance recovery with no live scope; active owners protected; outage/new-thread test | Resolved |
| S3 | Medium | Ordinary deletion bypassed quarantine | __delattr__ fence; direct access/assignment/deletion regression | Resolved |
| S4 | Medium | Secondary cancellation swallowed/replaced during recovery/cleanup | Signals propagate with primary context; ordinary cleanup failures preserve primary; combined signal/unlock tests | Resolved |
| S5 | High | Overlapping explicit recovery could replace ownership | Exclusive recovery reservation also fences ordinary acquisition; captured-token cleanup; overlap/expiry regression | Resolved |

## Surface assessment and valid-state noninterference

No auth, permission, deployment identity, endpoint or queue expansion. Ordinary
held-reference reads/mutations/persistence reject quarantined state. Recovery uses
durable coherent reads, not Redis payload authority; runtime metadata is excluded
from serialization and logging resources preserved. Source-candidate deletion
stays under ownership with authoritative-pointer checks; uncertain bytes remain.
Grouped compensation is ownership/generation constrained and final memory matches
actual durable state. Optional absence, first initialization, legacy/detached/
readonly states, direct retries and cancellation are explicitly tested.

Reviewed `tests/nodb/test_failed_mutation_matrix.py`; independent validator reports
36 passed, zero skips, with disposable Redis. Coverage includes stale writes,
identity, held references, recovery overlap/failure, later-thread recovery,
secondary cancellation, initialization and transient-cache rebuilding. See
`validation_matrix.md` and final gate summary in `validation.md`.

## Verdict and limits

APPROVE local implementation scope; zero unresolved high/medium findings.
Correctness/QA and broad gates remain independent. No deployment or affected-run
recovery approval/claim. Threat model remains cooperative participating writers;
no arbitrary external alias, out-of-band writer or process-death recovery promise.

## Broad-gate compatibility follow-up

The NoDb sweep exposed an ordinary unknown-commit exception-class regression in
_derived_build. Restore the existing _CommitOutcomeUnknown(RuntimeError), chained
from the original storage failure; cancellation remains the original marked signal.
Both paths retain recovery artifacts. An initially omitted restored class definition
was caught by review/focused failure and corrected before the final focused run.
All three reviewers reread and retain local approval; QA verified **51 passed**
in the actual RAP contention/manual-publication rerun. This is existing-contract
conformance, not a new normative decision. Broad outcomes remain in validation.md.
