# Independent contract reviews and disposition

Date: 2026-10-31 UTC. Review scope: proposed checkpoint, not implementation.
Reviewers independently inspected canonical contract/package and relevant source;
read-only agent tasks `contract_correctness` (reviewer) and `contract_security`
(security_reviewer). Primary author: Codex root.

## Correctness review

Initial result: one medium finding. NoDb may recreate `locked:*` and
`last_modified` before RedisPrep recovery; a blanket nonempty-hash rejection
would reject a valid recovery state or overwrite newer unrelated metadata.

Disposition: resolved in canonical "Coherent initialization and restoration":
explicit field ownership and NoDb-only cold recovery, preserving live values.
The legacy-snapshot loaded-marker interruption test is explicitly mandatory.
Reviewer re-review: finding resolved; ready for operator disposition/commit
approval, not yet accepted because the historic damaged-state limit needs approval.

## Security review

Initial result: two medium findings, no high findings.

1. Same NoDb-only valid-recovery ambiguity. Resolved as above.
2. Historic partial-restore acceptance had been narrowed without explicit
   disposition. Resolved as a checkpoint-presentation issue: canonical contract
   now marks it unresolved and pending explicit operator acceptance. No claim of
   automatic historic damage detection or fulfilled original acceptance remains.

Reviewer re-review: both presentation findings addressed; ready to present for
that specific acceptance decision and commit authority. This does not grant
implementation/security approval or accept the remaining limitation.

## Remaining gates

Operator must explicitly accept reconciliation for already-partial legacy hashes
whose true loaded marker is indistinguishable from valid later deletions, or
choose a separately scoped migration policy. New-reader atomicity tests cannot
be waived by that disposition. Commit authority is also required. After the
ancestor exists, prove concrete lock ordering, namespaces, lifecycle fencing,
file access and actual mount behavior, then obtain final independent reviews.

## Operator approval — 2026-10-31 UTC

Operator answered "yes" to committing this reviewed checkpoint and proceeding,
including explicit reconciliation for already-partial legacy hashes with a true
loaded marker. Commit authority and that acceptance disposition are granted.
Implementation and environment validation remain pending.
