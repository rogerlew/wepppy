# Queue-Sequencing Checkpoint Operations and Security Review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Review date**: 2026-07-30 UTC
- **Comparison ancestor**:
  `4d2ef5838868bfa02d4badc403ace43f3a95fe84`
- **Working-tree HEAD**:
  `4e5845a04c5b4808d78f4c4806db24e5b90ff70f`
- **Scope**: documentation-only queue-sequencing delta in the user-context
  amendment and ADR-0033
- **Implementation or test review**: not performed
- **Implementation, acceptance, Forest, or production mutation**: none

This checkpoint reviews only the complete mutable child, nonmutating
completion receipt, admission/root-link ordering, lock lifetime, persistent
tail, stale-tail handling, and related recovery contract added after
`4d2ef5838`. It does not approve or reject the current implementation.

## Verdict

**FAIL — reject the documentation-only queue-sequencing ancestor until
admission is fenced and interruption recovery is specified.**

- **Unresolved High**: 1
- **Unresolved Medium**: 1
- **Unresolved Low**: 0
- **Decision**: reject

The steady-state design materially improves same-run serialization and trace
integrity. It does not yet cover lease expiry during admission or a hard
interruption after a child has been saved but before it is activated. Those
are shared-state boundary failures, not merely availability edge cases.

No break-glass basis exists for committing a contract that permits two
admitters to proceed without fencing or leaves operators without a safe,
auditable recovery path for a nonterminal orphan.

## Findings

### QUEUE-OPS-01 — High: the admission lease is time-bounded but unfenced

The amendment gives the admission lock a fixed 30-second lease and a
10-second acquisition limit. Admission then performs several distinct
operations:

1. read and classify the prior tail;
2. allocate the new child and receipt;
3. update the tail;
4. save the non-runnable child;
5. register the receipt;
6. persist both root links; and
7. activate the mutable child.

The contract does not:

- bound the whole critical section to less than 30 seconds;
- renew the lease while the admitting process is healthy;
- assign a monotonic fencing token;
- require lock ownership and the expected prior-tail value to be rechecked
  before tail publication, root linkage, and activation; or
- define an atomic commit point that makes exactly one admission runnable.

If the process stalls before publishing its tail and the lease expires, a
second submitter may complete admission. The first process can then resume and
publish or activate a child based on stale state. A Redis lock alone does not
stop a former lock holder after its lease expires. The result can be two
mutable children without a dependency edge, defeating the complete-child
watershed lock ordering and risking final raster/readiness state that depends
on timing.

This is High because the contract explicitly protects shared same-run
mutation integrity. A low-probability network or scheduler stall does not
reduce the consequence of an unfenced former lease holder.

#### Required closure

Amend the contract and ADR to define one reviewed admission protocol that
guarantees at most one newly runnable mutable child. Acceptable designs
include:

- a fenced admission state machine with a unique/monotonic token, atomic
  expected-tail transition, and ownership/token validation immediately before
  activation;
- a renewable lease plus an atomic commit that rejects a former lease holder;
  or
- another RQ/Redis-native transaction whose durable postcondition is
  equivalent.

The contract must state what happens when the admission lock cannot be
acquired or is lost: the root fails with no runnable child, no new tail, and
no partial public tree.

Regression evidence must force lease expiry and two admitters at every
pre-activation boundary, then prove one ordered runnable child tree, one
current tail, complete root links, and no untraced mutation.

### QUEUE-OPS-02 — Medium: a saved but inactive child has no safe recovery path

The stale-tail rule removes a tail only when the referenced job is missing or
already terminal. It does not cover a hard process interruption after the
mutable child is saved but before its receipt/root links are committed or the
child is activated.

In that state:

- the child exists and can remain nonterminal;
- it may not belong to a runnable queue or registry;
- the persistent tail can continue to reference it;
- later submissions depend on a job that cannot emit a terminal transition;
  and
- ordinary missing/terminal cleanup never repairs the run.

The partial-admission paragraph describes exception cleanup by a live
admitter. It is not a crash-recovery contract. It also does not specify a
durable admission phase/receipt that lets an operator distinguish a safe
pre-activation orphan from a delayed or executing job.

This is Medium because the immediate effect is a contained run-level denial
of service, but improvised tail deletion or job activation could escalate it
into the High shared-state race the design is intended to prevent.

#### Required closure

Define durable, idempotent reconciliation for each interruption point. At
minimum it must:

- identify the admission phase, parent, child, receipt, prior tail, queue, and
  creation time without secrets;
- distinguish queued, deferred, started, terminal, missing, and saved-but-not-
  activated children;
- prove no worker/current directory-root lock can still execute the child
  before repair;
- restore the prior tail or complete the new tree under the fenced admission
  protocol;
- remove only receipt-, root-link-, dependency-, and tail-state owned by that
  exact admission attempt;
- emit a correlated audit record and preserve enough evidence for post-action
  review; and
- fail closed for ambiguous state rather than deleting a tail manually.

Tests must inject process-style interruption after child save, receipt
registration, root linking, and activation, then demonstrate idempotent
recovery and a subsequent successful same-run submission.

## Passing Control Assessment

### Complete mutable child and lock lifetime

**PASS, subject to QUEUE-OPS-01.**

The documentation places subcatchment construction and abstraction inside one
watershed directory-root lock. The 43,500-second lock lifetime exceeds the
43,200-second RQ task timeout by a 300-second containment margin. This avoids
the earlier gap in which the second mutable phase could be reordered behind a
different user's child.

The lock lifetime is explicitly classified as an operational coordination
parameter rather than a hydrologic default. No formula, threshold, edge test,
or configuration default changes.

### Nonmutating completion receipt

**PASS.**

The historical abstraction node remains observable but is expressly
nonmutating. It may not repeat abstraction or write readiness. A failed
complete child cancels only its matching receipt, preserving other users'
trees while preventing a false success transition.

### Root trace before activation

**PASS for the normal and handled-error path; hard interruption remains open
under QUEUE-OPS-02.**

The child is saved without becoming runnable, its receipt is registered, and
both IDs are durably linked from the root before activation. This ordering
prevents normal execution from outrunning its public trace and closes the
failure-before-receipt registration race.

The partial-admission contract restores the previous tail and removes only
attempt-owned jobs/root links for handled failures. It preserves provenance
and limits cleanup blast radius.

### Persistent tail and terminal predecessor handling

**PASS for missing and terminal predecessors; nonterminal orphan recovery
remains open under QUEUE-OPS-02.**

The tail intentionally has no expiry while work is pending, so queue delay
cannot silently discard the dependency chain. A later child depends on the
complete mutable predecessor with failure allowed. Compare-and-delete prevents
an older child from erasing a newer reservation. Missing and terminal
predecessors are explicitly self-healed.

These are sound steady-state controls. They require the fencing and
reconciliation additions above before the persistent state is safe under
lease loss and process interruption.

## Required Evidence for Re-review

A corrected documentation checkpoint must require durable tests for:

- admission-lock acquisition failure with no state mutation;
- lease expiry before tail publication, after tail publication, after child
  save, after receipt registration, and after root linkage;
- two concurrent admitters with a delayed former lease holder;
- abrupt process loss at every admission phase;
- saved-but-inactive child detection and idempotent reconciliation;
- exact rollback to the previous tail without deleting a newer reservation;
- one complete root trace before any mutable child can execute;
- at most one unordered runnable complete child per run;
- successful predecessor, failed predecessor, missing predecessor, terminal
  stale predecessor, and recovered orphan;
- empty attempt-owned queue/deferred/dependency residue after failed admission;
  and
- correlated, secret-free recovery and post-action audit evidence.

## Reviewed Snapshot

The documents were uncommitted working-tree state based at
`4e5845a04c5b4808d78f4c4806db24e5b90ff70f`.

| Document | SHA-256 |
| --- | --- |
| user-context amendment | `a73508baa7e0c02f020759328c98d96cb9140228ccd1ddd4952683e641e07fe4` |
| ADR-0033 | `f04d06a428826916652f83d2e06604f2564ae41c1be1cc9af460e9afdfb54d84` |

No implementation, test, runtime, acceptance, Forest, or production state was
used to reach this documentation-only verdict.

## Gate Decision

- **Documentation-only queue-sequencing ancestor**: rejected
- **Implementation review**: not performed by this checkpoint
- **Local acceptance mutation**: not authorized
- **Forest preflight/migration/canary**: not authorized
- **Production/wepp1**: unauthorized and untouched

After the contract and ADR define fenced admission and durable orphan
reconciliation, obtain a new independent checkpoint review before committing
the documentation-only ancestor.
