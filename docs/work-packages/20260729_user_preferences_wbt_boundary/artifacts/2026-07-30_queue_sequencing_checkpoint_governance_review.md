# SURF-14A Queue-Sequencing Amendment Governance Checkpoint

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Accepted base**: `4d2ef5838868bfa02d4badc403ace43f3a95fe84`
- **Review boundary**: only the post-`4d2ef5838` queue-sequencing delta in
  `2026-07-30_contract_amendment_delineation_snapshot.md` and ADR-0033
- **Implementation, test, acceptance, Forest, or production review**: none

This checkpoint considered only the proposed complete mutable child,
nonmutating completion receipt, admission/root-link ordering, lock timeouts,
and persistent-tail recovery contract. Existing implementation in the shared
working tree was deliberately excluded from the decision.

## Verdict

**FAIL — REJECT checkpoint ratification and a documentation-only standalone
ancestor for this fingerprint.**

**Findings**: 1 High, 1 Medium, 0 Low.

The complete build-plus-abstraction lock scope and nonmutating receipt are
reasonable containment choices. The proposed persistent-tail admission
protocol does not yet define recovery from every durable interruption state,
and the ADR does not preserve the required provenance, alternatives, evidence,
or rollback record for its new workflow parameters.

No break-glass basis was requested or documented. Runtime implementation,
local acceptance, Forest, and production remain unauthorized.

## Findings

### GOV-SEQ-01 — High: a saved but never activated child can become an unrecoverable tail

The amendment requires admission to:

1. write a non-expiring per-run tail;
2. create and save the mutable child without making it runnable;
3. register the completion receipt;
4. durably link both children from the root; and
5. activate the mutable child.

It says exception-time partial admission restores the prior tail and removes
the new jobs and root links. It also permits later admission to discard a tail
only when its referenced job is missing or terminal.

That rule does not cover process or host loss after the child has been saved
but before it becomes runnable. The tail then references a present,
nonterminal child that no worker can finish. Exception cleanup cannot execute,
the missing/terminal stale rule cannot reclaim it, and every later same-run
submission can remain dependent on the orphan indefinitely. Process loss
after root linkage but before activation can additionally leave a public tree
that appears admitted but can never become terminal.

This is a durable denial-of-service and revocation gap at the new coordination
boundary. The assertion that failure cannot precede receipt registration is
not true until interruption recovery is defined for every phase.

Required closure:

1. Define a crash-consistent admission state machine or atomic transaction.
   Its durable record must distinguish reservation, saved child, registered
   receipt, root-linked, and activated states and bind the exact parent,
   mutable child, receipt, run, and prior tail.
2. Define how a later admission or bounded reconciler proves that a present
   nonterminal job was never activated before reclaiming it. A time-only
   expiry must not release a legitimately queued or running mutation.
3. Define the resulting root/child/receipt terminal states, tail restoration,
   dependency cleanup, audit record, and operator-visible recovery action for
   interruption at every phase.
4. Require deterministic fault-injection evidence at tail write, child save,
   receipt registration, root linkage, and activation. Each case must prove
   that the prior tail is preserved when applicable, no runnable mutation is
   duplicated, no hidden orphan or dependency residue remains, public polling
   terminates coherently, and a later same-run submission can proceed.

### GOV-SEQ-02 — Medium: ADR-0033 does not preserve the queue decision record

ADR-0033 adds exact workflow parameters: a 43,200-second task timeout,
300-second lock margin, 30-second admission-lock TTL, 10-second acquisition
limit, and non-expiring tail. It gives a concise purpose for those values, but
its provenance still describes only the earlier user-preference decision.

For the queue amendment, the ADR does not identify the decision owner or
implementer, record when and why the complete-child/receipt design replaced
the rejected alternative, link supporting RQ behavior evidence, or state
queue-specific risks and rollback/revert conditions. Its Evidence section
lists ownership files rather than evidence supporting these coordination
values. This is insufficient under
`docs/standards/parameterization-adr-standard.md` for workflow
parameterization.

Required closure:

1. Record the queue decision venue and time, participants, decision owner,
   implementer, and the exact authority under which the technical choice was
   made.
2. Record the rejected sequencing alternatives and why their RQ
   dependency/pipeline semantics were unsafe.
3. Link evidence supporting the timeouts, lock margin, receipt semantics,
   persistent-tail choice, and crash-recovery behavior.
4. Add queue-specific risks, observability, revocation/reconciliation, and
   rollback conditions. State which exact docs/code/release must be reverted
   together.

## Accepted Portions

The following can be retained while the findings are corrected:

- One mutable child performing build and abstraction under one directory-root
  lock prevents another submission from entering between those mutations.
- A nonmutating receipt preserves the historical two-node public tree without
  executing abstraction twice.
- Root linkage before worker activation is the correct visibility objective.
- A later child may wait for a prior same-run mutable child while allowing the
  later submission to proceed after a controlled prior failure.
- Compare-and-delete release prevents an older child from deleting a newer
  reservation.
- A non-expiring tail avoids silently losing ordering solely because queue
  delay exceeds a guessed TTL, provided the orphan-recovery gap is closed.

## Required Re-review

The next checkpoint remains documentation-only. Before re-review:

1. amend the contract with crash-consistent admission and exact
   revocation/reconciliation rules;
2. complete ADR-0033's queue-specific provenance, alternatives, evidence,
   risks, and rollback record;
3. retain explicit fault-injection requirements for every partial-admission
   boundary; and
4. run documentation lint and spelling normalization on both amended sources.

After two independent PASS reviews, record findings disposition and commit
only the approved documentation as a standalone ancestor. Any later change to
the admission phases, tail lifetime, dependency policy, lock parameters,
receipt semantics, cleanup authority, or recovery behavior invalidates those
approvals.

## Review Fingerprint

The review used Git `HEAD`
`4e5845a04c5b4808d78f4c4806db24e5b90ff70f` and compared the two documents
against accepted base `4d2ef5838868bfa02d4badc403ace43f3a95fe84`.
Hashes are SHA-256:

| Reviewed item | SHA-256 |
| --- | --- |
| `docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md` | `f04d06a428826916652f83d2e06604f2564ae41c1be1cc9af460e9afdfb54d84` |
| `artifacts/2026-07-30_contract_amendment_delineation_snapshot.md` | `a73508baa7e0c02f020759328c98d96cb9140228ccd1ddd4952683e641e07fe4` |
| Ordered post-`4d2ef5838` binary diff | `47f96037acea9cb6e3cb8594e4b6b5152edf5c68ed169fc27aace572d5cc0097` |

