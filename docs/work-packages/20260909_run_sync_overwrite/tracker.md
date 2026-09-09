# Run sync overwrite tracker

2026-09-09 UTC: user approved cleanup/replacement behavior; inspected worker and
source manifest producer. Source supplies no checksums. Prepared canonical
contract and decision before implementation.

- Completed: source/worker investigation, valid-state matrix and contract draft.
- Completed: two independent contract reviews; all findings resolved and confirmed.
- Completed: contract/package doc lint and whitespace checks pass.
- Pending: checkpoint commit authority.
- Pending: worker implementation, filesystem/aria2 tests, full suite, final
  correctness/QA review and actual workflow evidence.

Checkpoint revision: pending. Implementation: not started.
Decision: fresh download for every listed file in current checksum-free manifests.
Risk: interrupted pulls can leave partial/missing files; no snapshot guarantee.
